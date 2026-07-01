"""异步托管 - AI扫描侧边栏（画参考线精确读y坐标）+ 点击"""
import threading, time, random, subprocess
from config import cfg
from window_capture import capture
from llm_client import llm_client
from keyboard_mouse import kb_mouse
from memory_store import memory_store
from time_schedule import get_current_interval
from name_list import is_blacklisted, needs_human_approval

CHAT_X = 160  # 侧边栏列表点击x

class AutoPilot:
    def __init__(self):
        self._running = False
        self._thread = None
        self._last_hash = ""
        self._cycle = 0
        self._pending = []

    def start(self):
        if self._running: return False
        if not cfg.config["mimo"]["api_key"]:
            cfg.log("请先配置API Key","ERROR"); return False
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        cfg.log("自动托管已启动"); return True

    def stop(self):
        self._running = False
        cfg.log("自动托管已停止"); return True

    @property
    def is_running(self): return self._running

    def _loop(self):
        while self._running:
            try: self._tick()
            except Exception as e: cfg.log(f"异常: {e}","ERROR")
            for _ in range(int(get_current_interval()*10)):
                if not self._running: break
                time.sleep(0.1)

    def _tick(self):
        self._cycle += 1
        wid = capture.find_wechat_window()
        if not wid: return

        try: subprocess.run(["xdotool","windowactivate","--sync",str(wid)],timeout=5); time.sleep(0.5)
        except: pass

        # 截侧边栏
        sidebar = capture.capture_sidebar()
        if not sidebar: return
        sidebar_path = str(cfg.config_path.parent / "last_sidebar.png")
        sidebar.save(sidebar_path)

        # AI扫描（带参考线）→ 精确y坐标
        unread = llm_client.scan_sidebar_unread(sidebar_path)
        # 过滤黑名单，点击前就跳过
        unread = [u for u in unread if not is_blacklisted(u.get("name",""))][:3]
        if not unread:
            cfg.log(f"#{self._cycle} 无未读(已过滤黑名单)"); return

        cfg.log(f"#{self._cycle} 未读: {[(u['name'],u['y']) for u in unread]}")

        # 逐个点击
        for item in unread:
            y = item["y"] + random.randint(-2,2)
            x = CHAT_X + random.randint(-5,5)
            subprocess.run(["xdotool","mousemove","--window",str(wid),str(x),str(y)],timeout=3)
            time.sleep(0.1)
            subprocess.run(["xdotool","mousedown","1"],timeout=3)
            time.sleep(0.05)
            subprocess.run(["xdotool","mouseup","1"],timeout=3)
            time.sleep(2.0)  # 等页面刷新

            # 截图看消息
            shot2 = capture.capture_chat_region()
            if not shot2: continue
            snap2 = str(cfg.config_path.parent / "last_snap2.png")
            shot2.save(snap2)

            a = llm_client.analyze_chat_screenshot(snap2)
            need = a.get("need_reply", False)
            latest = a.get("latest_sender", "")
            msgs = a.get("messages", [])
            cur = a.get("current_chat", "")

            if not (need and latest == "other" and msgs): continue
            if is_blacklisted(cur): continue

            last = msgs[-1].get("text","")
            h = f"{cur}:{last[:30]}"
            if h == self._last_hash: continue

            ctx = "\n".join(f"{'【我】' if m.get('sender')=='me' else '【TA】'}{m.get('text','')}" for m in msgs[-5:])

            if needs_human_approval(cur,last):
                r = llm_client.generate_replies(ctx)
                if r: self._pending.append({"chat":cur,"msg":last,"reply":r[0],"context":ctx})
                self._last_hash = h; return

            r = llm_client.generate_replies(ctx)
            if not r or r[0].startswith("（"): cfg.log("  生成失败"); continue
            kb_mouse.send_message(r[0])
            memory_store.add_reply(r[0],source="ai",context=ctx)
            self._last_hash = h
            cfg.log(f"  ✓ 回复 [{cur}]: {r[0][:60]}")
            return

    def approve(self,i,t=None):
        if i>=len(self._pending): return False
        e=self._pending.pop(i); kb_mouse.send_message(t or e["reply"]); return True
    def reject(self,i):
        if i<len(self._pending): self._pending.pop(i)
    def get_pending(self): return self._pending
    def get_status(self):
        from time_schedule import get_slot_info; s=get_slot_info()
        return {"running":self._running,"cycle_count":self._cycle,
                "pending_count":len(self._pending),"slot":s.get("name","默认")}

auto_pilot = AutoPilot()
