"""LLM直连模块 - AI视觉识别聊天 + 生成回复 + 密钥验证"""
import base64
import json
import re
import requests
from typing import List, Optional, Dict
from pathlib import Path

from config import cfg
from memory_store import memory_store


def _get_api_config():
    mimo = cfg.config["mimo"]
    return mimo["api_key"], mimo["base_url"], mimo["model"]


def _call_llm(messages: list, temperature=0.7, max_tokens=1024, model_override: str = None, use_reasoning: bool = False) -> str:
    """通用LLM调用"""
    api_key, base_url, model = _get_api_config()
    if model_override:
        model = model_override
    if not api_key:
        raise ValueError("API Key未配置")
    if not base_url:
        raise ValueError("API地址未配置")
    if not model:
        raise ValueError("模型名称未配置")

    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    cfg.log(f"调用API: {base_url}, model={model}")
    resp = requests.post(url, json=payload, headers=headers, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    msg = data["choices"][0]["message"]
    # reasoning模型：content是真实回复，reasoning是思考过程
    content = msg.get("content") or ""
    if use_reasoning and not content:
        content = msg.get("reasoning") or ""
    return content


def _image_to_base64(image_path: str) -> str:
    from PIL import Image
    import io
    img = Image.open(image_path)
    # ponytail: 1024px宽，太大API超时
    if img.width > 1024:
        ratio = 1024 / img.width
        img = img.resize((1024, int(img.height * ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


# ============ API密钥验证 ============

def validate_api_key() -> dict:
    """验证API Key是否可用"""
    api_key, base_url, model = _get_api_config()
    if not api_key:
        return {"ok": False, "error": "API Key未填写"}
    if not base_url:
        return {"ok": False, "error": "API地址未填写"}
    if not model:
        return {"ok": False, "error": "模型名称未填写"}

    try:
        messages = [{"role": "user", "content": "回复OK两个字母即可。"}]
        result = _call_llm(messages, max_tokens=10)
        cfg.log(f"API密钥验证通过, 模型回复: {result[:50]}")
        return {"ok": True, "reply": result.strip()[:100]}
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else 0
        body = ""
        try:
            body = e.response.json().get("error", {}).get("message", str(e))
        except Exception:
            body = str(e)[:200]
        cfg.log(f"API密钥验证失败 HTTP {status}: {body}", "ERROR")
        return {"ok": False, "error": f"HTTP {status}: {body}"}
    except Exception as e:
        cfg.log(f"API密钥验证异常: {e}", "ERROR")
        return {"ok": False, "error": str(e)[:200]}


# ============ AI视觉识别聊天 ============

ANALYZE_PROMPT = """你是微信截图分析器。看这张微信完整窗口截图，完成两件事：

任务1 - 看左侧聊天列表：找出哪些聊天有未读消息（红色数字角标或红点）。列出它们的名字。

任务2 - 看右侧聊天区：如果当前打开了某个聊天，分析里面的最近消息，判断最新一条是"me"（右侧绿色气泡）还是"other"（左侧白色气泡），判断是否需要回复。

输出JSON：
{
  "unread_chats": ["张三", "群聊名"],
  "current_chat": "当前打开的聊天名",
  "messages": [{"sender":"other","text":"消息内容"}],
  "latest_sender": "other",
  "need_reply": true
}
如果没有人发新消息，unread_chats为空数组，need_reply为false。"""

REPLY_PROMPT = """你是一个自然真实的聊天助手。根据微信聊天上下文，生成3条不同的回复备选。

要求：
1. 自然、口语化，像真人聊天
2. 3条回复要有差异化（不同语气/长度/角度）
3. 禁止AI话术（"我理解"、"作为AI"等）
4. 禁止书面语，要口语化
5. 根据聊天场景匹配风格

每条回复单独一行，用数字编号开头。不要输出其他解释。"""


class LLMClient:
    def __init__(self):
        self._last_replies: List[str] = []
        self._last_analysis: Optional[dict] = None

    def quick_scan(self, image_path: str) -> list:
        """快筛：截左侧列表，返回未读会话[{name,y}]"""
        from PIL import Image
        import io
        img = Image.open(image_path)
        w, h = img.size  # ponytail: 保持原尺寸，y坐标要精确
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        b64 = base64.b64encode(buf.getvalue()).decode()

        # 让AI直接返回y坐标，不用固定间距映射
        scan_prompt = (
            f"这是微信左侧聊天列表截图({w}x{h}像素)。"
            "找出所有有红色未读标记（红色数字角标或红点）的会话。"
            '对每个未读会话，输出会话名称和其中心y坐标（从图片顶部算的像素值）。'
            '格式：[{"name":"会话名","y":100}]。没有未读输出[]。只看红色标记。'
        )
        messages = [{"role": "user", "content": [
            {"type": "text", "text": scan_prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
        ]}]
        try:
            result = _call_llm(messages, temperature=0.1, max_tokens=500)
            result = result.strip()
            if "```" in result:
                result = result.split("```")[1].strip()
            # 解析JSON数组
            start = result.find("[")
            end = result.rfind("]") + 1
            if start >= 0 and end > start:
                import json
                items = json.loads(result[start:end])
                # 兼容旧格式（纯数字数组）→ 转成[{name,y}]用默认y
                result_list = []
                for i, item in enumerate(items):
                    if isinstance(item, dict) and "y" in item:
                        result_list.append({"name": item.get("name",""), "y": int(item["y"])})
                    elif isinstance(item, int):
                        result_list.append({"name": "", "y": 70 + (item-1)*50})  # fallback
                cfg.log(f"快筛发现未读: {[(r['name'],r['y']) for r in result_list]}")
                return result_list
        except Exception as e:
            cfg.log(f"快筛失败: {e}", "WARN")
        return []

    def analyze_chat_screenshot(self, image_path: str) -> dict:
        """用AI视觉分析微信截图，提取聊天内容"""
        try:
            b64 = _image_to_base64(image_path)
            messages = [
                {"role": "system", "content": "你是微信聊天截图分析器，只输出JSON，不要其他文字。"},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": ANALYZE_PROMPT},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
                    ]
                }
            ]
            result = _call_llm(messages, temperature=0.3, max_tokens=4096)
            cfg.log(f"AI视觉分析完成")
            cfg.log(f"AI返回: {result[:200]}")

            # 解析JSON
            parsed = self._parse_analysis(result)
            self._last_analysis = parsed
            return parsed
        except Exception as e:
            cfg.log(f"AI视觉分析失败: {e}", "ERROR")
            return {"error": str(e), "messages": [], "need_reply": False}

    def _parse_analysis(self, text: str) -> dict:
        """解析AI返回的JSON，兼容reasoning模型的各种输出"""
        text = text.strip()
        # 去掉markdown代码块
        if "```" in text:
            parts = text.split("```")
            if len(parts) >= 2:
                text = parts[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
        # 找JSON对象
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                # 尝试修复常见问题
                try:
                    cleaned = text[start:end].replace("\n", " ").replace("  ", " ")
                    return json.loads(cleaned)
                except:
                    pass
        # 返回默认结构
        return {"messages": [], "need_reply": False, "current_chat": "unknown", "latest_sender": "unknown", "unread_chats": []}

    def generate_replies(self, chat_context: str, persona: str = "") -> List[str]:
        """生成3条备选回复"""
        try:
            # 读取配置的人设和水印
            cfg_persona = persona or cfg.config.get("persona", "")
            watermark = cfg.config.get("watermark", "")

            memory_context = memory_store.get_memory_context()
            user_msg = ""
            if cfg_persona:
                user_msg += f"你的人设风格：{cfg_persona}\n\n"
            if memory_context:
                user_msg += f"用户历史回复风格参考：\n{memory_context}\n\n"
            user_msg += f"当前聊天上下文：\n{chat_context}\n\n"
            if watermark:
                user_msg += f"重要：每条回复末尾必须加上「{watermark}」\n\n"
            user_msg += "请生成3条差异化备选回复。"

            messages = [
                {"role": "system", "content": REPLY_PROMPT},
                {"role": "user", "content": user_msg}
            ]
            result = _call_llm(messages, temperature=0.85, max_tokens=512, use_reasoning=True)
            replies = self._parse_replies(result)
            replies = self._filter_ai_talk(replies)
            self._last_replies = replies[:3]
            cfg.log(f"生成{len(replies)}条回复")
            return self._last_replies
        except Exception as e:
            cfg.log(f"生成回复失败: {e}", "ERROR")
            return [f"（生成失败: {str(e)[:100]}）"]

    def _parse_replies(self, content: str) -> List[str]:
        replies = []
        # 清理markdown代码块
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        # 按行拆分，每行开头有数字编号的是回复
        lines = [l.strip() for l in content.split("\n") if l.strip()]
        current = []
        for line in lines:
            # 跳过空行和纯编号行
            if re.match(r'^\d+[.、）\)]\s*$', line):
                continue
            # 去掉行首编号
            cleaned = re.sub(r'^\d+[.、）\)]\s*', '', line)
            if cleaned:
                current.append(cleaned)

        # 如果有多行内容，按空行或编号分组
        if current:
            # 简单方案：每段非空内容算一条回复
            replies = [c for c in current if len(c) > 1]

        # 兜底：如果还是没有，把整个内容当一条
        if not replies and content.strip():
            replies = [content.strip()]

        return replies[:3]

    def _filter_ai_talk(self, replies: List[str]) -> List[str]:
        bad_phrases = [
            "作为AI", "作为一个人工智能", "我是一个AI", "我无法", "我不能",
            "我理解你的感受", "我很乐意帮助", "这是个好问题", "让我来回答",
            "根据我的知识", "作为一个助手", "感谢你的提问", "我会尽力",
            "从技术角度", "客观来说", "首先我想说", "总的来说",
        ]
        filtered = [r for r in replies if not any(p in r for p in bad_phrases) and len(r.strip()) >= 2]
        return filtered if filtered else replies

    def get_last_replies(self) -> List[str]:
        return self._last_replies

    def get_last_analysis(self) -> Optional[dict]:
        return self._last_analysis


llm_client = LLMClient()
