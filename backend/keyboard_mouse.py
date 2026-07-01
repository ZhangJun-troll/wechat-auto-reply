"""键鼠模拟模块 - 纯剪贴板粘贴，禁止键盘逐字输入"""
import time
import random
import subprocess
from config import cfg
from window_capture import capture


class KeyboardMouse:
    def __init__(self):
        self._delay_min = 0.8
        self._delay_max = 2.5

    def _random_delay(self):
        delay = random.uniform(self._delay_min, self._delay_max)
        time.sleep(delay)

    def _run(self, cmd):
        try:
            return subprocess.run(cmd, timeout=5, capture_output=True, text=True)
        except Exception as e:
            cfg.log(f"键鼠操作失败: {e}", "ERROR")
            return None

    def activate_wechat(self):
        wid = capture.find_wechat_window()
        if wid:
            try:
                subprocess.run(["xdotool", "windowactivate", "--sync", str(wid)], timeout=5)
                time.sleep(0.3)
            except Exception as e:
                cfg.log(f"激活微信窗口失败: {e}", "ERROR")

    def click_input_box(self, wid: int = None):
        """点击微信输入框"""
        self.activate_wechat()
        time.sleep(0.3)
        x = 842 + random.randint(-8, 8)
        y = 652 + random.randint(-5, 5)
        self._run(["xdotool", "mousemove", "--window", str(wid), str(x), str(y)])
        time.sleep(0.15)
        self._run(["xdotool", "mousedown", "1"])
        time.sleep(0.05)
        self._run(["xdotool", "mouseup", "1"])
        cfg.log(f"点击输入框: ({x}, {y})")

    def paste_text(self, text: str):
        """纯剪贴板粘贴，禁止xdotool type"""
        # 1. 写入剪贴板
        proc = subprocess.Popen(
            ["xclip", "-selection", "clipboard"],
            stdin=subprocess.PIPE
        )
        proc.communicate(input=text.encode("utf-8"))
        time.sleep(0.3)

        # 2. Ctrl+V 粘贴
        self._run(["xdotool", "key", "ctrl+v"])
        time.sleep(0.5)
        cfg.log(f"剪贴板粘贴: {text[:30]}...")

    def send_message(self, text: str) -> bool:
        """完整发送: 点输入框 → 剪贴板粘贴 → 回车
        绝对禁止xdotool type逐字输入"""
        try:
            wid = capture.find_wechat_window()
            if not wid:
                cfg.log("未找到微信窗口", "ERROR")
                return False

            # 先写剪贴板
            proc = subprocess.Popen(
                ["xclip", "-selection", "clipboard"],
                stdin=subprocess.PIPE
            )
            proc.communicate(input=text.encode("utf-8"))
            time.sleep(0.3)

            # 激活窗口
            self.activate_wechat()
            time.sleep(0.3)

            # 点输入框
            self.click_input_box(wid)
            time.sleep(0.3)

            # 全选清空残留 + 粘贴新内容
            self._run(["xdotool", "key", "ctrl+a"])
            time.sleep(0.1)
            self._run(["xdotool", "key", "ctrl+v"])
            time.sleep(0.5)

            # 发送
            self._run(["xdotool", "key", "Return"])
            self._random_delay()
            cfg.log(f"消息已发送: {text[:50]}")
            return True
        except Exception as e:
            cfg.log(f"发送失败: {e}", "ERROR")
            return False


kb_mouse = KeyboardMouse()
