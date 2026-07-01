"""异步托管 - 截图→AI看→回复，不点击"""
import threading
import time
from typing import Optional
from config import cfg
from window_capture import capture
from llm_client import llm_client
from keyboard_mouse import kb_mouse
from memory_store import memory_store
from time_schedule import get_current_interval
from name_list import is_blacklisted, needs_human_approval


class AutoPilot:
    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._last_msg_hash = ""
        self._cycle_count = 0
        self._pending = []

    @property
    def is_running(self): return self._running

    def start(self) -> bool:
        if self._running: return False
        if not cfg.config["mimo"]["api_key"]:
            cfg.log("请先配置API Key", "ERROR"); return False
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        cfg.log("自动托管已启动"); return True

    def stop(self) -> bool:
        if not self._running: return False
        self._running = False
        cfg.log("自动托管已停止"); return True

    def _loop(self):
        while self._running:
            try:
                self._cycle()
            except Exception as e:
                cfg.log(f"异常: {e}", "ERROR")
            for _ in range(int(get_current_interval() * 10)):
                if not self._running: break
                time.sleep(0.1)

    def _cycle(self):
        self._cycle_count += 1
        wid = capture.find_wechat_window()
        if not wid: return

        # ponytail: 用裁剪后的聊天区域，不是全窗口
        shot = capture.capture_chat_region()
        if not shot: return
        snap = str(cfg.config_path.parent / "last_snap.png")
        shot.save(snap)

        # ponytail: 一次截图AI看全，不点击
        analysis = llm_client.analyze_chat_screenshot(snap)
        cur = analysis.get("current_chat", "")
        msgs = analysis.get("messages", [])
        need = analysis.get("need_reply", False)
        latest = analysis.get("latest_sender", "")
        unread = analysis.get("unread_chats", [])

        cfg.log(f"#{self._cycle_count} [{cur}] msgs={len(msgs)} need={need} unread={unread}")

        # 没有需要回复的
        if not need or latest != "other" or not msgs:
            return

        last = msgs[-1].get("text", "")
        h = f"{cur}:{last[:30]}"
        if h == self._last_msg_hash: return

        # 黑名单/系统号
        if is_blacklisted(cur):
            cfg.log(f"  跳过黑名单: {cur}"); return

        SKIP = ["公众号", "微信支付", "服务号", "文件传输助手", "微信游戏"]
        if any(k in cur for k in SKIP):
            cfg.log(f"  跳过系统号: {cur}"); return

        # 构建上下文
        ctx = "\n".join(f"{'【我方】' if m.get('sender')=='me' else '【对方】'}{m.get('text','')}" for m in msgs)

        # 白名单/高危 → 存待确认
        if needs_human_approval(cur, last):
            replies = llm_client.generate_replies(ctx)
            if replies:
                self._pending.append({"chat": cur, "msg": last, "reply": replies[0], "context": ctx})
                cfg.log(f"  ⚠ 待确认 [{cur}]: {replies[0][:60]}")
            self._last_msg_hash = h
            return

        # 普通消息 → 自动回复
        replies = llm_client.generate_replies(ctx)
        if not replies or replies[0].startswith("（"):
            cfg.log("  生成失败"); return

        selected = replies[0]
        kb_mouse.send_message(selected)
        memory_store.add_reply(selected, source="ai", context=ctx)
        self._last_msg_hash = h
        cfg.log(f"  ✓ 回复 [{cur}]: {selected[:60]}")

    def approve(self, idx: int, text: str = None) -> bool:
        if idx >= len(self._pending): return False
        e = self._pending.pop(idx)
        kb_mouse.send_message(text or e["reply"])
        memory_store.add_reply(text or e["reply"], source="human_approved")
        return True

    def reject(self, idx: int):
        if idx < len(self._pending): self._pending.pop(idx)

    def get_pending(self): return self._pending

    def get_status(self):
        from time_schedule import get_slot_info
        slot = get_slot_info()
        return {"running": self._running, "cycle_count": self._cycle_count,
                "pending_count": len(self._pending), "slot": slot.get("name", "默认")}

auto_pilot = AutoPilot()
