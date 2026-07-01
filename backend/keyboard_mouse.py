"""键鼠模拟模块 - xdotool + xclip"""
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
            subprocess.run(cmd, timeout=5)
        except Exception as e:
            cfg.log(f"键鼠操作失败: {e}", "ERROR")

    def activate_wechat(self):
        """激活微信窗口到前台"""
        wid = capture.find_wechat_window()
        if wid:
            try:
                subprocess.run(["xdotool", "windowactivate", "--sync", str(wid)], timeout=5)
                time.sleep(0.3)
            except Exception as e:
                cfg.log(f"激活微信窗口失败: {e}", "ERROR")

    def click_chat_item(self, item_index: int, wid: int = None):
        """点击聊天列表第N项（0=第一项）
        验证过的坐标（窗口内相对坐标）:
        """
        from window_capture import capture
        geo = capture.get_window_geometry(wid)
        if geo is None:
            return

        # 验证过的坐标：x=200, y从130开始, 每项60px
        CHAT_X = 160
        CHAT_Y_START = 70
        CHAT_Y_STEP = 60  # ponytail: 每项60px高

        list_x = CHAT_X + random.randint(-5, 5)
        list_y = CHAT_Y_START + item_index * CHAT_Y_STEP + random.randint(-2, 2)

        self.activate_wechat()
        time.sleep(0.3)
        self._run(["xdotool", "mousemove", "--window", str(wid), str(list_x), str(list_y)])
        time.sleep(0.15)
        # ponytail: Electron微信不响应xdotool click，用mousedown+mouseup
        self._run(["xdotool", "mousedown", "1"])
        time.sleep(0.05)
        self._run(["xdotool", "mouseup", "1"])
        cfg.log(f"点击聊天项 #{item_index}: ({list_x}, {list_y})")

    def click_input_box(self, wid: int = None):
        """点击微信输入框（写死坐标）"""
        self.activate_wechat()
        time.sleep(0.3)
        x = 842 + random.randint(-8, 8)
        y = 652 + random.randint(-5, 5)
        self._run(["xdotool","mousemove","--window",str(wid),str(x),str(y)])
        time.sleep(0.15)
        # ponytail: Electron微信不响应xdotool click，用mousedown+mouseup
        self._run(["xdotool","mousedown","1"])
        time.sleep(0.05)
        self._run(["xdotool","mouseup","1"])
        cfg.log(f"点击输入框: ({x}, {y})")

    def paste_text(self, text: str):
        """通过剪贴板粘贴文本"""
        try:
            proc = subprocess.Popen(["xclip", "-selection", "clipboard"],
                                    stdin=subprocess.PIPE)
            proc.communicate(input=text.encode("utf-8"))
            time.sleep(0.2)
            self._run(["xdotool", "key", "ctrl+v"])
            cfg.log(f"粘贴文本: {text[:30]}...")
        except Exception as e:
            cfg.log(f"粘贴失败: {e}", "ERROR")

    def send_message(self, text: str) -> bool:
        """完整发送流程: 点输入框 → 粘贴 → 回车"""
        try:
            wid = capture.find_wechat_window()
            if not wid:
                cfg.log("未找到微信窗口", "ERROR")
                return False

            self.click_input_box(wid)
            time.sleep(0.3)
            self.paste_text(text)
            time.sleep(0.3)
            self._run(["xdotool", "key", "Return"])
            self._random_delay()
            cfg.log(f"消息已发送: {text[:50]}")
            return True
        except Exception as e:
            cfg.log(f"发送失败: {e}", "ERROR")
            return False


kb_mouse = KeyboardMouse()
