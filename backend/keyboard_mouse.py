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
        验证过的坐标:
        - 聊天列表中心x ≈ 200
        - 第一项y ≈ 100
        - 每项间距 ≈ 60px
        """
        from window_capture import capture
        geo = capture.get_window_geometry(wid)
        if geo is None:
            return

        # 验证过的坐标: x≈200, y从100开始, 间距60px
        list_x = 200 + random.randint(-10, 10)
        list_y = 100 + item_index * 60 + random.randint(-3, 3)

        self.activate_wechat()
        time.sleep(0.3)
        self._run(["xdotool", "mousemove", "--window", str(wid), str(list_x), str(list_y)])
        time.sleep(0.15)
        self._run(["xdotool", "click", "1"])
        cfg.log(f"点击聊天项 #{item_index}: ({list_x}, {list_y})")

    def click_input_box(self, wid: int = None):
        """点击微信输入框区域
        验证: 输入框在窗口底部，右侧约65%位置
        """
        from window_capture import capture
        geo = capture.get_window_geometry(wid)
        if geo is None:
            return

        w, h = geo["WIDTH"], geo["HEIGHT"]
        # 验证过的坐标: x≈842(窗口65%处), y≈652(窗口88%处)
        click_x = int(w * 0.65) + random.randint(-8, 8)
        click_y = int(h * 0.88) + random.randint(-5, 5)

        self.activate_wechat()
        time.sleep(0.2)
        self._run(["xdotool", "mousemove", "--window", str(wid), str(click_x), str(click_y)])
        time.sleep(0.1)
        self._run(["xdotool", "click", "1"])
        cfg.log(f"点击输入框: ({click_x}, {click_y})")

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
