"""异步托管 - 极简：红点在第几个就点第几个"""
import threading, time, random, subprocess
from config import cfg
from window_capture import capture
from llm_client import llm_client
from keyboard_mouse import kb_mouse
from memory_store import memory_store
from time_schedule import get_current_interval
from name_list import is_blacklisted, needs_human_approval

CHAT_X = 160  # ponytail: 侧边栏列表点击x（避开左侧导航图标栏）

def detect_red_dots(img) -> list:
    """纯算法检测侧边栏红点，返回[{y, x}]（像素检测，不耗API）"""
    import numpy as np
    arr = np.array(img)
    # 红色: R>150, G<100, B<100, R-G>50
    r, g, b = arr[:,:,0].astype(int), arr[:,:,1].astype(int), arr[:,:,2].astype(int)
    red = (arr[:,:,0] > 150) & (arr[:,:,1] < 100) & (arr[:,:,2] < 100) & ((r - g) > 50)
    red[:, :50] = False  # 排除左侧导航栏
    ys = np.where(red)[0]
    if len(ys) == 0:
        return []
    sorted_ys = sorted(set(ys))
    clusters = []
    current = [sorted_ys[0]]
    for y in sorted_ys[1:]:
        if y - current[-1] <= 20:
            current.append(y)
        else:
            clusters.append(current)
            current = [y]
    clusters.append(current)
    # 合并间距<50px的聚类（同一个会话项上的多个红元素）
    merged = [clusters[0]]
    for c in clusters[1:]:
        if min(c) - max(merged[-1]) < 50:
            merged[-1] = merged[-1] + c
        else:
            merged.append(c)
    clusters = merged
    result = []
    for c in clusters:
        cy = (min(c) + max(c)) // 2
        red_in = red[min(c):max(c)+1, :]
        xs = np.where(red_in.any(axis=0))[0]
        cx = int((xs.min() + xs.max()) // 2) if len(xs) > 0 else CHAT_X
        result.append({"y": cy, "x": cx})
    return result

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

        # 激活
        try: subprocess.run(["xdotool","windowactivate","--sync",str(wid)],timeout=5); time.sleep(0.5)
        except: pass

        # 截图
        sidebar = capture.capture_sidebar()
        if not sidebar: return
        sidebar_path = str(cfg.config_path.parent / "last_sidebar.png")
        sidebar.save(sidebar_path)

        # 像素检测红点（不耗API，精确到像素）
        dots = detect_red_dots(sidebar)
        dots = dots[:3]
        if not dots:
            cfg.log(f"#{self._cycle} 无未读"); return

        cfg.log(f"#{self._cycle} 红点: {[(d['y'],d['x']) for d in dots]}")

        # 逐个点
        for dot in dots:
            y = dot["y"] + random.randint(-2,2)
            x = dot["x"] + random.randint(-5,5)
            subprocess.run(["xdotool","mousemove","--window",str(wid),str(x),str(y)],timeout=3)
            time.sleep(0.1)
            # ponytail: Electron微信不响应xdotool click，用mousedown+mouseup
            subprocess.run(["xdotool","mousedown","1"],timeout=3)
            time.sleep(0.05)
            subprocess.run(["xdotool","mouseup","1"],timeout=3)
            time.sleep(1.2)

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
