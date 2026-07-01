"""配置管理模块 - 读写大模型接口配置、窗口参数、轮询设置"""
import json
import os
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "data" / "config.json"
MEMORY_PATH = Path(__file__).parent.parent / "data" / "memory.json"
LOG_PATH = Path(__file__).parent.parent / "data" / "app.log"

DEFAULT_CONFIG = {
    "mimo": {
        "api_key": "",
        "base_url": "https://api.siliconflow.cn/v1",
        "model": ""
    },
    "window": {
        "wechat_name": "微信",
        "chat_crop": {
            "x_offset": 320,
            "y_offset": 60,
            "x_right_margin": 20,
            "y_bottom_margin": 140
        }
    },
    "auto_pilot": {
        "poll_interval": 5,
        "enabled": False,
        "max_retries": 3,
        "random_delay_min": 0.8,
        "random_delay_max": 2.5
    },
    "persona": "",
    "watermark": "",
    "time_schedule": [],
    "calib_regions": [],
    "blacklist": [],
    "whitelist": [],
    "server": {
        "host": "0.0.0.0",
        "port": 8090
    }
}


class ConfigManager:
    def __init__(self):
        self.config_path = CONFIG_PATH
        self.memory_path = MEMORY_PATH
        self.log_path = LOG_PATH
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self._config = None

    @property
    def config(self) -> dict:
        if self._config is None:
            self._config = self.load()
        return self._config

    def load(self) -> dict:
        """加载配置，不存在则用默认值"""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                # 合并默认值（处理新增字段）
                merged = self._deep_merge(DEFAULT_CONFIG.copy(), saved)
                return merged
            except Exception:
                pass
        return json.loads(json.dumps(DEFAULT_CONFIG))

    def save(self, config: dict = None):
        """保存配置到文件"""
        if config is not None:
            self._config = config
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, ensure_ascii=False, indent=2)

    def update(self, updates: dict):
        """局部更新配置"""
        self._config = self._deep_merge(self.config, updates)
        self.save()

    def _deep_merge(self, base: dict, override: dict) -> dict:
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def log(self, msg: str, level: str = "INFO"):
        """写入日志文件"""
        from datetime import datetime
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] [{level}] {msg}\n"
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line)
        # 保持日志文件不超过5000行
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if len(lines) > 5000:
                with open(self.log_path, "w", encoding="utf-8") as f:
                    f.writelines(lines[-3000:])
        except Exception:
            pass

    def get_logs(self, lines: int = 100) -> str:
        """读取最近N行日志"""
        if not self.log_path.exists():
            return ""
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                all_lines = f.readlines()
            return "".join(all_lines[-lines:])
        except Exception:
            return ""


# 全局单例
cfg = ConfigManager()
