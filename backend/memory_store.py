"""记忆学习存储模块 - 本地JSON持久化用户回复历史"""
import json
from datetime import datetime
from typing import List, Dict
from pathlib import Path

from config import cfg


class MemoryStore:
    def __init__(self):
        self._memory_path = cfg.memory_path
        self._data: Dict = {"replies": [], "personas": []}

    def _ensure_loaded(self):
        if not self._data.get("replies"):
            self.load()

    def load(self) -> Dict:
        """加载记忆数据"""
        if self._memory_path.exists():
            try:
                with open(self._memory_path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except Exception:
                self._data = {"replies": [], "personas": []}
        else:
            self._data = {"replies": [], "personas": []}
        return self._data

    def save(self):
        """保存记忆数据"""
        self._memory_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._memory_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def add_reply(self, text: str, source: str = "user", context: str = ""):
        """
        添加一条回复记录
        source: 'user' = 用户手动选择/发送, 'ai' = AI生成被采纳
        """
        self._ensure_loaded()
        entry = {
            "text": text,
            "source": source,
            "context": context,
            "timestamp": datetime.now().isoformat()
        }
        self._data["replies"].append(entry)

        # 保持最近500条
        if len(self._data["replies"]) > 500:
            self._data["replies"] = self._data["replies"][-500:]

        self.save()
        cfg.log(f"记忆已保存: [{source}] {text[:30]}...")

    def get_recent_replies(self, n: int = 20) -> List[Dict]:
        """获取最近N条回复记录"""
        self._ensure_loaded()
        return self._data["replies"][-n:]

    def get_memory_context(self) -> str:
        """获取记忆上下文文本，供LLM参考"""
        self._ensure_loaded()
        recent = self._data["replies"][-30:]
        if not recent:
            return ""

        lines = []
        for r in recent:
            tag = "用户" if r["source"] == "user" else "AI"
            lines.append(f"[{tag}]{r['text']}")

        return "\n".join(lines)

    def get_stats(self) -> Dict:
        """获取记忆统计"""
        self._ensure_loaded()
        total = len(self._data["replies"])
        user_count = sum(1 for r in self._data["replies"] if r["source"] == "user")
        ai_count = total - user_count
        return {
            "total": total,
            "user_replies": user_count,
            "ai_replies": ai_count
        }

    def clear(self):
        """清空记忆"""
        self._data = {"replies": [], "personas": []}
        self.save()
        cfg.log("记忆已清空")


# 全局单例
memory_store = MemoryStore()
