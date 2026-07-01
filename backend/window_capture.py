"""窗口捕获模块 - 定位Linux微信窗口并截图"""
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple

import mss
import mss.tools
from PIL import Image

from config import cfg


class WindowCapture:
    def __init__(self):
        self._wechat_wid: Optional[int] = None
        self._last_geometry: Optional[dict] = None

    def find_wechat_window(self) -> Optional[int]:
        """通过xdotool搜索微信窗口ID（排除桌面应用）"""
        try:
            result = subprocess.run(
                ["xdotool", "search", "--name", cfg.config["window"]["wechat_name"]],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                wids = result.stdout.strip().split("\n")
                # 有多个同名窗口，取最大的（主窗口）
                best_wid = None
                best_area = 0
                for wid in wids:
                    if not wid:
                        continue
                    try:
                        geo_result = subprocess.run(
                            ["xdotool", "getwindowgeometry", "--shell", wid],
                            capture_output=True, text=True, timeout=3
                        )
                        geo = {}
                        for line in geo_result.stdout.strip().split("\n"):
                            if "=" in line:
                                k, v = line.split("=")
                                geo[k] = int(v)
                        area = geo.get("WIDTH", 0) * geo.get("HEIGHT", 0)
                        if area > best_area:
                            best_area = area
                            best_wid = wid
                    except:
                        pass

                if best_wid:
                    self._wechat_wid = int(best_wid)
                    cfg.log(f"找到微信窗口: WID={best_wid} ({best_area}px²)")
                    return self._wechat_wid
            cfg.log("未找到微信窗口", "WARN")
            return None
        except Exception as e:
            cfg.log(f"搜索微信窗口失败: {e}", "ERROR")
            return None

    def get_window_geometry(self, wid: int = None) -> Optional[dict]:
        """获取窗口位置和大小"""
        wid = wid or self._wechat_wid
        if wid is None:
            return None
        try:
            result = subprocess.run(
                ["xdotool", "getwindowgeometry", "--shell", str(wid)],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                geo = {}
                for line in result.stdout.strip().split("\n"):
                    if "=" in line:
                        k, v = line.split("=", 1)
                        geo[k.strip()] = int(v.strip())
                self._last_geometry = geo
                return geo
            return None
        except Exception as e:
            cfg.log(f"获取窗口几何信息失败: {e}", "ERROR")
            return None

    def capture_chat_region(self, save_path: str = None) -> Optional[Image.Image]:
        """截取微信聊天消息区域"""
        geo = self.get_window_geometry()
        if geo is None:
            # 尝试重新查找窗口
            if self.find_wechat_window():
                geo = self.get_window_geometry()
            if geo is None:
                cfg.log("无法获取微信窗口位置，跳过截图", "ERROR")
                return None

        crop = cfg.config["window"]["chat_crop"]
        x = geo["X"] + crop["x_offset"]
        y = geo["Y"] + crop["y_offset"]
        w = geo["WIDTH"] - crop["x_offset"] - crop["x_right_margin"]
        h = geo["HEIGHT"] - crop["y_offset"] - crop["y_bottom_margin"]

        if w <= 0 or h <= 0:
            cfg.log(f"截图区域异常: w={w}, h={h}", "ERROR")
            return None

        try:
            with mss.mss() as sct:
                monitor = {"left": x, "top": y, "width": w, "height": h}
                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

            if save_path:
                img.save(save_path)
                cfg.log(f"截图已保存: {save_path}")
            return img
        except Exception as e:
            cfg.log(f"截图失败: {e}", "ERROR")
            return None

    def capture_full_window(self, save_path: str = None) -> Optional[Image.Image]:
        """截取完整微信窗口"""
        geo = self.get_window_geometry()
        if geo is None:
            return None

        try:
            with mss.mss() as sct:
                monitor = {
                    "left": geo["X"], "top": geo["Y"],
                    "width": geo["WIDTH"], "height": geo["HEIGHT"]
                }
                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

            if save_path:
                img.save(save_path)
            return img
        except Exception as e:
            cfg.log(f"截取完整窗口失败: {e}", "ERROR")
            return None

    def is_wechat_active(self) -> bool:
        """检查微信窗口是否当前激活"""
        try:
            result = subprocess.run(
                ["xdotool", "getactivewindow"],
                capture_output=True, text=True, timeout=3
            )
            if result.returncode == 0:
                active_wid = int(result.stdout.strip())
                return active_wid == self._wechat_wid
            return False
        except Exception:
            return False

    def activate_wechat(self):
        """激活微信窗口到前台"""
        if self._wechat_wid:
            try:
                subprocess.run(
                    ["xdotool", "windowactivate", "--sync", str(self._wechat_wid)],
                    timeout=5
                )
                time.sleep(0.3)
            except Exception as e:
                cfg.log(f"激活微信窗口失败: {e}", "ERROR")


# 全局单例
capture = WindowCapture()
