"""FastAPI主入口 - REST接口 + 静态文件服务"""
import os
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# 添加backend目录到path
sys.path.insert(0, str(Path(__file__).parent))

from config import cfg
from window_capture import capture
from ocr_engine import ocr_engine
from llm_client import llm_client
from keyboard_mouse import kb_mouse
from memory_store import memory_store
from auto_pilot import auto_pilot

app = FastAPI(title="WeChat Auto Reply", version="1.0.0")

# CORS 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ 请求模型 ============

class ConfigUpdate(BaseModel):
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    poll_interval: Optional[float] = None
    persona: Optional[str] = None
    watermark: Optional[str] = None
    time_schedule: Optional[list] = None
    calib_regions: Optional[list] = None
    blacklist: Optional[list] = None
    whitelist: Optional[list] = None
    x_offset: Optional[int] = None
    y_offset: Optional[int] = None
    x_right_margin: Optional[int] = None
    y_bottom_margin: Optional[int] = None

class SendMsgRequest(BaseModel):
    text: str

class GenerateReplyRequest(BaseModel):
    context: Optional[str] = None
    persona: Optional[str] = ""


# ============ API接口 ============

@app.get("/api/config")
async def get_config():
    """读取当前配置"""
    c = cfg.config
    return {
        "mimo": {
            "api_key": c["mimo"]["api_key"][:8] + "***" if c["mimo"]["api_key"] else "",
            "base_url": c["mimo"]["base_url"],
            "model": c["mimo"]["model"],
            "has_key": bool(c["mimo"]["api_key"])
        },
        "window": c["window"],
        "auto_pilot": c["auto_pilot"],
        "persona": c.get("persona", ""),
        "watermark": c.get("watermark", ""),
        "time_schedule": c.get("time_schedule", []),
        "calib_regions": c.get("calib_regions", []),
        "blacklist": c.get("blacklist", []),
        "whitelist": c.get("whitelist", []),
        "server": c["server"]
    }


@app.post("/api/config")
async def save_config(req: ConfigUpdate):
    """保存配置"""
    updates = {}
    if req.api_key is not None:
        updates.setdefault("mimo", {})["api_key"] = req.api_key
    if req.base_url is not None:
        updates.setdefault("mimo", {})["base_url"] = req.base_url
    if req.model is not None:
        updates.setdefault("mimo", {})["model"] = req.model
    if req.poll_interval is not None:
        updates.setdefault("auto_pilot", {})["poll_interval"] = req.poll_interval
    if req.persona is not None:
        updates["persona"] = req.persona
    if req.watermark is not None:
        updates["watermark"] = req.watermark
    if req.time_schedule is not None:
        updates["time_schedule"] = req.time_schedule
    if req.calib_regions is not None:
        updates["calib_regions"] = req.calib_regions
    if req.blacklist is not None:
        updates["blacklist"] = req.blacklist
    if req.whitelist is not None:
        updates["whitelist"] = req.whitelist
    if req.x_offset is not None:
        updates.setdefault("window", {}).setdefault("chat_crop", {})["x_offset"] = req.x_offset
    if req.y_offset is not None:
        updates.setdefault("window", {}).setdefault("chat_crop", {})["y_offset"] = req.y_offset
    if req.x_right_margin is not None:
        updates.setdefault("window", {}).setdefault("chat_crop", {})["x_right_margin"] = req.x_right_margin
    if req.y_bottom_margin is not None:
        updates.setdefault("window", {}).setdefault("chat_crop", {})["y_bottom_margin"] = req.y_bottom_margin

    cfg.update(updates)
    cfg.log("配置已更新")
    return {"ok": True, "msg": "配置已保存"}


@app.post("/api/validate_key")
async def validate_key():
    """验证API Key是否可用"""
    from llm_client import validate_api_key
    return validate_api_key()


@app.post("/api/snap_chat")
async def snap_chat():
    """截图 → AI视觉识别聊天内容"""
    try:
        # 找到微信窗口
        wid = capture.find_wechat_window()
        if wid is None:
            raise HTTPException(400, "未找到微信窗口，请确保微信已打开")

        # 截取完整微信窗口
        screenshot = capture.capture_full_window()
        if screenshot is None:
            raise HTTPException(500, "截图失败")

        # 保存截图
        snap_path = str(cfg.config_path.parent / "last_snap.png")
        screenshot.save(snap_path)

        # AI视觉分析
        analysis = llm_client.analyze_chat_screenshot(snap_path)
        if "error" in analysis and not analysis.get("messages"):
            raise HTTPException(500, f"AI分析失败: {analysis['error']}")

        messages = analysis.get("messages", [])
        latest_sender = analysis.get("latest_sender", "unknown")
        need_reply = analysis.get("need_reply", False)
        chat_title = analysis.get("current_chat", analysis.get("chat_title", ""))
        unread_chats = analysis.get("unread_chats", [])

        # 构建上下文文本
        context_lines = []
        for m in messages:
            prefix = "【我方消息】" if m.get("sender") == "me" else "【对方消息】"
            context_lines.append(f"{prefix}{m.get('text', '')}")
        context = "\n".join(context_lines) if context_lines else "（未识别到消息）"

        return {
            "ok": True,
            "messages": messages,
            "context": context,
            "latest_sender": latest_sender,
            "need_reply": need_reply,
            "chat_title": chat_title,
            "unread_chats": unread_chats,
            "snap_path": snap_path,
            "window_id": wid,
            "count": len(messages)
        }
    except HTTPException:
        raise
    except Exception as e:
        cfg.log(f"截图识别异常: {e}", "ERROR")
        raise HTTPException(500, str(e))


@app.get("/api/snap_image")
async def snap_image():
    """获取最新截图"""
    snap_path = str(cfg.config_path.parent / "last_snap.png")
    if os.path.exists(snap_path):
        return FileResponse(snap_path, media_type="image/png")
    raise HTTPException(404, "暂无截图")


@app.post("/api/generate_reply")
async def generate_reply(req: GenerateReplyRequest = None):
    """调用模型生成3条备选回复"""
    try:
        # 如果没有传入上下文，用最近一次AI分析结果
        if req and req.context:
            context = req.context
        else:
            analysis = llm_client.get_last_analysis()
            if not analysis or not analysis.get("messages"):
                raise HTTPException(400, "请先截图识别聊天内容")
            context_lines = []
            for m in analysis["messages"]:
                prefix = "【我方消息】" if m.get("sender") == "me" else "【对方消息】"
                context_lines.append(f"{prefix}{m.get('text', '')}")
            context = "\n".join(context_lines)

        persona = req.persona if req else ""
        replies = llm_client.generate_replies(context, persona)

        return {
            "ok": True,
            "replies": replies,
            "context": context
        }
    except HTTPException:
        raise
    except Exception as e:
        cfg.log(f"生成回复异常: {e}", "ERROR")
        raise HTTPException(500, str(e))


@app.post("/api/send_msg")
async def send_msg(req: SendMsgRequest):
    """模拟键鼠发送消息到微信"""
    if not req.text.strip():
        raise HTTPException(400, "消息内容不能为空")

    try:
        success = kb_mouse.send_message(req.text)
        if success:
            return {"ok": True, "msg": "发送成功"}
        else:
            raise HTTPException(500, "发送失败，请检查微信窗口")
    except HTTPException:
        raise
    except Exception as e:
        cfg.log(f"发送异常: {e}", "ERROR")
        raise HTTPException(500, str(e))


@app.post("/api/select_reply")
async def select_reply(req: SendMsgRequest):
    """选择并发送一条AI回复（同时记录到记忆）"""
    if not req.text.strip():
        raise HTTPException(400, "回复内容不能为空")

    try:
        context = ocr_engine.get_context()
        success = kb_mouse.send_message(req.text)
        if success:
            memory_store.add_reply(req.text, source="ai", context=context)
            return {"ok": True, "msg": "回复已发送并记录到记忆"}
        else:
            raise HTTPException(500, "发送失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/auto_toggle")
async def auto_toggle(enable: Optional[bool] = None):
    """开启/关闭全自动托管"""
    try:
        if enable is None:
            # 切换状态
            if auto_pilot.is_running:
                auto_pilot.stop()
                return {"ok": True, "enabled": False, "msg": "自动托管已关闭"}
            else:
                ok = auto_pilot.start()
                return {"ok": ok, "enabled": ok, "msg": "自动托管已启动" if ok else "启动失败"}
        else:
            if enable:
                ok = auto_pilot.start()
                return {"ok": ok, "enabled": ok}
            else:
                auto_pilot.stop()
                return {"ok": True, "enabled": False}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/auto_status")
async def auto_status():
    """获取自动托管状态"""
    return auto_pilot.get_status()


@app.get("/api/logs")
async def get_logs(lines: int = 100):
    """读取运行日志"""
    return {"logs": cfg.get_logs(lines)}


@app.get("/api/memory")
async def get_memory():
    """读取历史回复记忆库"""
    return {
        "replies": memory_store.get_recent_replies(50),
        "stats": memory_store.get_stats()
    }


@app.post("/api/memory_clear")
async def clear_memory():
    """清空记忆库"""
    memory_store.clear()
    return {"ok": True, "msg": "记忆已清空"}


@app.get("/api/window_info")
async def window_info():
    """获取微信窗口信息"""
    wid = capture.find_wechat_window()
    if wid is None:
        return {"found": False, "msg": "未找到微信窗口"}
    geo = capture.get_window_geometry(wid)
    return {
        "found": True,
        "window_id": wid,
        "geometry": geo
    }


# ============ 静态文件服务 ============

frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    @app.get("/")
    async def index():
        return FileResponse(str(frontend_dir / "index.html"))

    @app.get("/favicon.ico")
    async def favicon():
        fav = frontend_dir / "favicon.ico"
        if fav.exists():
            return FileResponse(str(fav))
        return JSONResponse(status_code=204, content=None)


if __name__ == "__main__":
    import uvicorn
    server_cfg = cfg.config["server"]
    cfg.log(f"启动服务: {server_cfg['host']}:{server_cfg['port']}")
    uvicorn.run(
        "main:app",
        host=server_cfg["host"],
        port=server_cfg["port"],
        reload=False,
        log_level="info"
    )


@app.get("/api/mouse_pos")
async def get_mouse_pos():
    """获取当前鼠标位置"""
    try:
        import subprocess
        result = subprocess.run(["xdotool", "getmouselocation"], capture_output=True, text=True, timeout=3)
        # 输出格式: x:912 y:679 screen:0 window:18874385
        parts = result.stdout.strip().split()
        x = int(parts[0].split(":")[1])
        y = int(parts[1].split(":")[1])
        return {"x": x, "y": y}
    except Exception as e:
        return {"error": str(e)}
