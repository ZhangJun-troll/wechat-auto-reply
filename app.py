"""WeChat Auto Reply 桌面版 - 全功能"""
import sys, json, time, random
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QFrame, QStackedWidget, QScrollArea, QComboBox,
    QMessageBox, QPlainTextEdit, QSpinBox, QTabWidget
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtGui import QFont, QTextCursor

sys.path.insert(0, str(Path(__file__).parent / "backend"))
from config import cfg
from window_capture import capture
from ocr_engine import ocr_engine
from llm_client import llm_client
from keyboard_mouse import kb_mouse
from memory_store import memory_store
from auto_pilot import auto_pilot

# ===== 主题 =====
STYLE = """
* { font-family: "Noto Serif SC", "SimSun", serif; }
QMainWindow, QWidget { background: #f5f0e8; color: #2c2a26; }
QLabel { background: transparent; }
QPushButton {
    background: #c0522e; color: white; border: none; border-radius: 8px;
    padding: 10px 20px; font-weight: bold; font-size: 13px;
    box-shadow: 0 2px 0 rgba(0,0,0,0.12);
}
QPushButton:hover { background: #a84526; }
QPushButton:disabled { background: #ccc; color: #999; }
QPushButton.secondary {
    background: #ede8df; color: #6b5e4f; border: 1px solid #d4cfc6;
}
QPushButton.secondary:hover { background: #d9d1c5; }
QPushButton.danger { background: #c4554a; }
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox {
    background: #ede8df; border: 1px solid #d4cfc6; border-radius: 8px;
    padding: 8px 12px; color: #2c2a26; font-size: 13px;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #c0522e;
}
QComboBox {
    background: #ede8df; border: 1px solid #d4cfc6; border-radius: 8px;
    padding: 8px 12px; color: #2c2a26; font-size: 13px;
}
QComboBox::drop-down { border: none; }
QComboBox QAbstractItemView { background: #fff; color: #2c2a26; selection-background-color: #c0522e30; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: transparent; width: 6px; }
QScrollBar::handle:vertical { background: #d4cfc6; border-radius: 3px; min-height: 20px; }
"""


class LogSignal(QObject):
    message = Signal(str)

log_signal = LogSignal()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("💬 WeChat Auto Reply")
        self.setMinimumSize(1100, 700)
        self.resize(1200, 750)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 侧边栏
        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet("background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #3a3228,stop:1 #2c2418);")
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(0, 24, 0, 16)
        sb_layout.setSpacing(0)

        brand = QLabel("WECHAT AUTO REPLY")
        brand.setStyleSheet("color: #f5f0e8; font-size: 14px; font-weight: bold; padding: 0 20px 16px; border-bottom: 1px solid rgba(255,255,255,0.08); letter-spacing: 1px;")
        sb_layout.addWidget(brand)
        sb_layout.addSpacing(12)

        self.nav_buttons = []
        nav_items = [("⚙️", "配置", 0), ("💬", "聊天", 1), ("⚡", "托管", 2), ("📝", "日志", 3), ("🧠", "记忆", 4), ("🎯", "校准", 5)]
        for icon, text, idx in nav_items:
            btn = QPushButton(f"  {icon}  {text}")
            btn.setCheckable(True)
            btn.setFixedHeight(44)
            btn.setStyleSheet("""
                QPushButton { text-align: left; padding-left: 16px; background: transparent;
                    color: rgba(255,255,255,0.55); border: none; border-radius: 0; font-size: 13px; }
                QPushButton:hover { background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.8); }
                QPushButton:checked { background: rgba(192,82,46,0.2); color: #f0d9b5; border-left: 3px solid #c0522e; }
            """)
            btn.clicked.connect(lambda checked, i=idx: self.switch_page(i))
            sb_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        sb_layout.addStretch()
        self.status_label = QLabel("● 待机中")
        self.status_label.setStyleSheet("color: rgba(255,255,255,0.3); font-size: 11px; padding: 12px 20px;")
        sb_layout.addWidget(self.status_label)

        main_layout.addWidget(sidebar)

        # 内容区
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: #f5f0e8;")
        self.stack.addWidget(self._build_config_page())   # 0
        self.stack.addWidget(self._build_chat_page())      # 1
        self.stack.addWidget(self._build_auto_page())      # 2
        self.stack.addWidget(self._build_log_page())       # 3
        self.stack.addWidget(self._build_memory_page())    # 4
        self.stack.addWidget(self._build_calibrate_page()) # 5
        main_layout.addWidget(self.stack)

        self.switch_page(0)

        # 定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_status)
        self.timer.start(3000)

        log_signal.message.connect(self.append_log)

        self._load_local_config()

    def switch_page(self, idx):
        self.stack.setCurrentIndex(idx)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == idx)

    # ====== 配置页 ======
    def _build_config_page(self):
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: #f5f0e8; }")
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(16)

        title = QLabel("⚙️  配置")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)
        desc = QLabel("API密钥、模型选择与系统参数")
        desc.setStyleSheet("color: #a09484; font-size: 13px; margin-bottom: 8px;")
        layout.addWidget(desc)

        # API接口
        card1 = self._card("API 接口")
        card1_layout = card1.layout()

        card1_layout.addWidget(QLabel("API Key"))
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("sk-...")
        self.api_key_input.setEchoMode(QLineEdit.Password)
        card1_layout.addWidget(self.api_key_input)

        card1_layout.addWidget(QLabel("接口地址"))
        self.base_url_combo = QComboBox()
        self.base_url_combo.setEditable(True)
        for name, url in [("SiliconFlow", "https://api.siliconflow.cn/v1"), ("DeepSeek", "https://api.deepseek.com/v1"),
                          ("OpenRouter", "https://openrouter.ai/api/v1"), ("NVIDIA NIM", "https://integrate.api.nvidia.com/v1"),
                          ("Together AI", "https://api.together.xyz/v1"), ("Moonshot", "https://api.moonshot.cn/v1"),
                          ("智谱 GLM", "https://open.bigmodel.cn/api/paas/v4"), ("自定义", "")]:
            self.base_url_combo.addItem(name, url)
        card1_layout.addWidget(self.base_url_combo)

        row = QHBoxLayout()
        col1 = QVBoxLayout()
        col1.addWidget(QLabel("模型"))
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        for name, model in [("⭐ Nemotron 12B VL（推荐·视觉）", "nvidia/nemotron-nano-12b-v2-vl"),
                            ("Nemotron 8B VL（视觉·较慢）", "nvidia/llama-3.1-nemotron-nano-vl-8b-v1"),
                            ("Llama 3.2 Vision（视觉·中文一般）", "meta/llama-3.2-11b-vision-instruct"),
                            ("Step 3.7 Flash（纯文本·需推理）", "stepfun-ai/step-3.7-flash"),
                            ("DeepSeek-V3（纯文本·可能不稳定）", "deepseek-ai/DeepSeek-V3"),
                            ("DeepSeek-V3.2（纯文本·可能不稳定）", "deepseek-ai/DeepSeek-V3.2"),
                            ("DeepSeek-R1（推理·需大token）", "deepseek-ai/DeepSeek-R1"),
                            ("Qwen3-235B（纯文本·可能不稳定）", "Qwen/Qwen3-235B-A22B"),
                            ("GLM-4-Plus（纯文本·可能不稳定）", "THUDM/glm-4-plus"),
                            ("Kimi-K2（纯文本·可能不稳定）", "moonshotai/Kimi-K2"),
                            ("自定义", "")]:
            self.model_combo.addItem(name, model)
        col1.addWidget(self.model_combo)
        row.addLayout(col1)

        col2 = QVBoxLayout()
        col2.addWidget(QLabel("轮询间隔（秒）"))
        self.interval_input = QSpinBox()
        self.interval_input.setRange(2, 120)
        self.interval_input.setValue(10)
        col2.addWidget(self.interval_input)
        row.addLayout(col2)
        card1_layout.addLayout(row)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("💾 保存配置")
        save_btn.clicked.connect(self.save_config)
        btn_row.addWidget(save_btn)
        detect_btn = QPushButton("🔍 检测窗口")
        detect_btn.setProperty("class", "secondary")
        detect_btn.clicked.connect(self.detect_window)
        btn_row.addWidget(detect_btn)
        validate_btn = QPushButton("🔑 验证密钥")
        validate_btn.setProperty("class", "secondary")
        validate_btn.clicked.connect(self.validate_key)
        btn_row.addWidget(validate_btn)
        btn_row.addStretch()
        card1_layout.addLayout(btn_row)

        self.config_msg = QLabel("")
        self.config_msg.setStyleSheet("color: #a09484; font-size: 12px;")
        card1_layout.addWidget(self.config_msg)
        layout.addWidget(card1)

        # AI人设
        card2 = self._card("🎭  AI 人设与水印")
        card2_layout = card2.layout()
        card2_layout.addWidget(QLabel("人设风格（可选）"))
        self.persona_input = QLineEdit()
        self.persona_input.setPlaceholderText("活泼开朗 / 幽默风趣 / 专业严谨...")
        card2_layout.addWidget(self.persona_input)
        card2_layout.addWidget(QLabel("每句必带水印（可选）"))
        self.watermark_input = QLineEdit()
        self.watermark_input.setPlaceholderText("这句话由张钧的AI Agent生成，内容可能不准确，请谨慎甄别")
        card2_layout.addWidget(self.watermark_input)
        layout.addWidget(card2)

        # 名单管理
        card3 = self._card("🚫  名单管理")
        card3_layout = card3.layout()
        card3_layout.addWidget(QLabel("黑名单（不回复）"))
        bl_row = QHBoxLayout()
        self.bl_input = QLineEdit()
        self.bl_input.setPlaceholderText("输入微信号后回车")
        self.bl_input.returnPressed.connect(lambda: self._add_tag("blacklist"))
        bl_row.addWidget(self.bl_input)
        bl_add = QPushButton("添加")
        bl_add.setProperty("class", "secondary")
        bl_add.clicked.connect(lambda: self._add_tag("blacklist"))
        bl_row.addWidget(bl_add)
        card3_layout.addLayout(bl_row)
        self.bl_tags_layout = QHBoxLayout()
        card3_layout.addLayout(self.bl_tags_layout)

        card3_layout.addSpacing(10)
        card3_layout.addWidget(QLabel("白名单（优先回复 + 高危需确认）"))
        wl_row = QHBoxLayout()
        self.wl_input = QLineEdit()
        self.wl_input.setPlaceholderText("输入微信号后回车")
        self.wl_input.returnPressed.connect(lambda: self._add_tag("whitelist"))
        wl_row.addWidget(self.wl_input)
        wl_add = QPushButton("添加")
        wl_add.setProperty("class", "secondary")
        wl_add.clicked.connect(lambda: self._add_tag("whitelist"))
        wl_row.addWidget(wl_add)
        card3_layout.addLayout(wl_row)
        self.wl_tags_layout = QHBoxLayout()
        card3_layout.addLayout(self.wl_tags_layout)
        hint = QLabel("白名单普通消息自动回复并通知你；高危消息存待确认")
        hint.setStyleSheet("color: #a09484; font-size: 11px; font-style: italic;")
        card3_layout.addWidget(hint)
        layout.addWidget(card3)

        # 时段调度
        card4 = self._card("⏰  时段调度")
        card4_layout = card4.layout()
        self.schedule_rows_layout = QVBoxLayout()
        card4_layout.addLayout(self.schedule_rows_layout)
        add_sched_btn = QPushButton("+ 添加时段")
        add_sched_btn.setProperty("class", "secondary")
        add_sched_btn.setFixedWidth(120)
        add_sched_btn.clicked.connect(self._add_schedule)
        card4_layout.addWidget(add_sched_btn)
        self.schedule_data = []
        layout.addWidget(card4)

        # 窗口裁剪
        card5 = self._card("✂  窗口裁剪")
        card5_layout = card5.layout()
        crop_row = QHBoxLayout()
        self.crop_x = QSpinBox(); self.crop_x.setRange(0, 2000); self.crop_x.setValue(320)
        self.crop_y = QSpinBox(); self.crop_y.setRange(0, 2000); self.crop_y.setValue(60)
        self.crop_r = QSpinBox(); self.crop_r.setRange(0, 500); self.crop_r.setValue(20)
        self.crop_b = QSpinBox(); self.crop_b.setRange(0, 500); self.crop_b.setValue(140)
        for label, spin in [("左侧X", self.crop_x), ("顶部Y", self.crop_y), ("右侧", self.crop_r), ("底部", self.crop_b)]:
            col = QVBoxLayout()
            col.addWidget(QLabel(label))
            col.addWidget(spin)
            crop_row.addLayout(col)
        card5_layout.addLayout(crop_row)
        layout.addWidget(card5)

        layout.addStretch()
        scroll.setWidget(inner)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)
        return page

    # ====== 聊天页 ======
    def _build_chat_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(12)

        title = QLabel("💬  聊天")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        btn_row = QHBoxLayout()
        self.snap_btn = QPushButton("📸 识别聊天")
        self.snap_btn.clicked.connect(self.snap_chat)
        btn_row.addWidget(self.snap_btn)
        self.gen_btn = QPushButton("⚡ 生成回复")
        self.gen_btn.setEnabled(False)
        self.gen_btn.clicked.connect(self.generate_reply)
        btn_row.addWidget(self.gen_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.chat_info = QLabel("")
        self.chat_info.setStyleSheet("color: #a09484; font-size: 12px;")
        layout.addWidget(self.chat_info)

        self.chat_area = QPlainTextEdit()
        self.chat_area.setReadOnly(True)
        self.chat_area.setPlaceholderText("点击「识别聊天」开始")
        self.chat_area.setMaximumHeight(250)
        layout.addWidget(self.chat_area, 1)

        reply_label = QLabel("✨  AI 备选回复")
        reply_label.setStyleSheet("font-size: 15px; font-weight: bold; margin-top: 8px;")
        layout.addWidget(reply_label)
        self.reply_area = QPlainTextEdit()
        self.reply_area.setReadOnly(True)
        self.reply_area.setPlaceholderText("等待生成回复...")
        self.reply_area.setMaximumHeight(200)
        layout.addWidget(self.reply_area)
        return page

    # ====== 托管页 ======
    def _build_auto_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(16)

        title = QLabel("⚡  自动托管")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        desc = QLabel("后台轮询检测未读消息并自动回复。白名单消息会通知你确认。")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #a09484; font-size: 13px;")
        layout.addWidget(desc)

        self.auto_toggle_btn = QPushButton("  ▶  开启自动托管  ")
        self.auto_toggle_btn.setFixedHeight(50)
        self.auto_toggle_btn.setStyleSheet("""
            QPushButton { background: #c0522e; color: white; border-radius: 8px; font-size: 16px; font-weight: bold; }
            QPushButton:hover { background: #a84526; }
        """)
        self.auto_toggle_btn.clicked.connect(self.toggle_auto)
        layout.addWidget(self.auto_toggle_btn)

        self.auto_status = QLabel("状态: 已关闭")
        self.auto_status.setStyleSheet("color: #6b5e4f; font-size: 13px;")
        layout.addWidget(self.auto_status)

        self.auto_stats = QLabel("轮询: 0 | 待确认: 0 | 时段: 默认")
        self.auto_stats.setStyleSheet("color: #a09484; font-size: 12px;")
        layout.addWidget(self.auto_stats)

        # 待确认消息
        pending_label = QLabel("📋  待确认消息")
        pending_label.setStyleSheet("font-size: 15px; font-weight: bold; margin-top: 16px;")
        layout.addWidget(pending_label)
        self.pending_area = QPlainTextEdit()
        self.pending_area.setReadOnly(True)
        self.pending_area.setPlaceholderText("无待确认消息")
        self.pending_area.setMaximumHeight(150)
        layout.addWidget(self.pending_area)

        pend_btn_row = QHBoxLayout()
        approve_btn = QPushButton("✅ 批准选中")
        approve_btn.setProperty("class", "secondary")
        approve_btn.clicked.connect(self.approve_pending)
        pend_btn_row.addWidget(approve_btn)
        reject_btn = QPushButton("❌ 拒绝选中")
        reject_btn.setProperty("class", "danger")
        reject_btn.clicked.connect(self.reject_pending)
        pend_btn_row.addWidget(reject_btn)
        pend_btn_row.addStretch()
        layout.addLayout(pend_btn_row)

        layout.addStretch()
        return page

    # ====== 日志页 ======
    def _build_log_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 24, 30, 24)

        title = QLabel("📝  日志")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.setProperty("class", "secondary")
        refresh_btn.setFixedWidth(80)
        refresh_btn.clicked.connect(self.refresh_logs)
        layout.addWidget(refresh_btn)

        self.log_area = QPlainTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("""
            QPlainTextEdit { background: #2c2a26; color: #a8a6a0;
                font-family: "JetBrains Mono", monospace; font-size: 12px;
                border-radius: 8px; padding: 10px; }
        """)
        layout.addWidget(self.log_area, 1)
        self.refresh_logs()
        return page

    # ====== 记忆页 ======
    def _build_memory_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 24, 30, 24)

        title = QLabel("🧠  记忆库")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        self.mem_stats = QLabel("总计: 0 | 用户: 0 | AI: 0")
        self.mem_stats.setStyleSheet("color: #a09484; font-size: 12px;")
        layout.addWidget(self.mem_stats)

        clear_btn = QPushButton("🗑 清空")
        clear_btn.setProperty("class", "danger")
        clear_btn.setFixedWidth(80)
        clear_btn.clicked.connect(self.clear_memory)
        layout.addWidget(clear_btn)

        self.mem_area = QPlainTextEdit()
        self.mem_area.setReadOnly(True)
        self.mem_area.setPlaceholderText("暂无记录")
        layout.addWidget(self.mem_area, 1)
        self.refresh_memory()
        return page

    # ====== 校准页 ======
    def _build_calibrate_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 24, 30, 24)

        title = QLabel("🎯  校准")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)
        desc = QLabel("框选微信界面元素位置，用于自动点击定位")
        desc.setStyleSheet("color: #a09484; font-size: 13px; margin-bottom: 16px;")
        layout.addWidget(desc)

        card = self._card("📸  窗口截图")
        card_layout = card.layout()
        self.calib_preview = QLabel("点击「截图预览」查看微信窗口")
        self.calib_preview.setAlignment(Qt.AlignCenter)
        self.calib_preview.setStyleSheet("color: #a09484; padding: 20px;")
        card_layout.addWidget(self.calib_preview)
        cap_btn = QPushButton("截图预览")
        cap_btn.clicked.connect(self.calib_capture)
        card_layout.addWidget(cap_btn)
        layout.addWidget(card)

        card2 = self._card("📋  已记录区域")
        card2_layout = card2.layout()
        self.calib_list_area = QPlainTextEdit()
        self.calib_list_area.setReadOnly(True)
        self.calib_list_area.setPlaceholderText("尚未校准")
        self.calib_list_area.setMaximumHeight(150)
        card2_layout.addWidget(self.calib_list_area)
        layout.addWidget(card2)

        layout.addStretch()
        return page

    # ====== 辅助方法 ======
    def _card(self, title_text):
        card = QFrame()
        card.setStyleSheet("""
            QFrame { background: #fff; border: 1px solid #d4cfc6; border-radius: 10px;
                padding: 20px; }
        """)
        layout = QVBoxLayout(card)
        layout.setSpacing(10)
        label = QLabel(title_text)
        label.setStyleSheet("font-size: 12px; font-weight: bold; color: #a09484; padding-bottom: 8px; border-bottom: 1px dashed #d4cfc6;")
        layout.addWidget(label)
        return card

    # ====== 功能实现 ======
    def _load_local_config(self):
        try:
            p = Path(__file__).parent / "data" / "config.json"
            if p.exists():
                c = json.load(open(p))
                self.persona_input.setText(c.get("persona", ""))
                self.watermark_input.setText(c.get("watermark", ""))
        except: pass

    def save_config(self):
        try:
            updates = {
                "mimo": {"api_key": self.api_key_input.text(),
                         "base_url": self.base_url_combo.currentText(),
                         "model": self.model_combo.currentText()},
                "auto_pilot": {"poll_interval": self.interval_input.value()},
                "persona": self.persona_input.text(),
                "watermark": self.watermark_input.text(),
                "blacklist": self._get_tags("blacklist"),
                "whitelist": self._get_tags("whitelist"),
                "time_schedule": self.schedule_data,
                "window": {"chat_crop": {"x_offset": self.crop_x.value(), "y_offset": self.crop_y.value(),
                                          "x_right_margin": self.crop_r.value(), "y_bottom_margin": self.crop_b.value()}}
            }
            cfg.update(updates)
            self.config_msg.setText("✅ 已保存")
        except Exception as e:
            self.config_msg.setText(f"❌ {e}")

    def detect_window(self):
        wid = capture.find_wechat_window()
        if wid:
            geo = capture.get_window_geometry(wid)
            if geo:
                self.config_msg.setText(f"✅ 窗口 ID:{wid}  {geo['WIDTH']}×{geo['HEIGHT']}")
                return
        self.config_msg.setText("❌ 未找到微信窗口")

    def validate_key(self):
        self.save_config()
        self.config_msg.setText("⏳ 验证中...")
        QApplication.processEvents()
        try:
            import requests
            url = f"{cfg.config['mimo']['base_url'].rstrip('/')}/chat/completions"
            r = requests.post(url, json={"model": cfg.config["mimo"]["model"],
                "messages": [{"role": "user", "content": "OK"}], "max_tokens": 5},
                headers={"Authorization": f"Bearer {cfg.config['mimo']['api_key']}", "Content-Type": "application/json"}, timeout=15)
            if r.status_code == 200:
                reply = r.json()["choices"][0]["message"]["content"]
                self.config_msg.setText(f"✅ 密钥有效！回复: {reply[:30]}")
            else:
                self.config_msg.setText(f"❌ HTTP {r.status_code}")
        except Exception as e:
            self.config_msg.setText(f"❌ {str(e)[:60]}")

    def snap_chat(self):
        self.snap_btn.setEnabled(False)
        self.snap_btn.setText("⏳ AI识别中...")
        QApplication.processEvents()
        try:
            screenshot = capture.capture_full_window()
            if not screenshot:
                self.chat_info.setText("❌ 截图失败")
                return
            snap_path = str(cfg.config_path.parent / "last_snap.png")
            screenshot.save(snap_path)
            analysis = llm_client.analyze_chat_screenshot(snap_path)
            messages = analysis.get("messages", [])
            self.chat_area.clear()
            for m in messages:
                sender = "【我方】" if m.get("sender") == "me" else "【对方】"
                self.chat_area.appendPlainText(f"{sender} {m.get('text', '')}")
            self.chat_info.setText(f"{analysis.get('current_chat', '')} · {len(messages)}条消息")
            self.gen_btn.setEnabled(True)
        except Exception as e:
            self.chat_info.setText(f"❌ {e}")
        finally:
            self.snap_btn.setEnabled(True)
            self.snap_btn.setText("📸 识别聊天")

    def generate_reply(self):
        self.gen_btn.setEnabled(False)
        self.gen_btn.setText("⏳ 生成中...")
        QApplication.processEvents()
        try:
            from llm_client import llm_client
            analysis = llm_client.get_last_analysis()
            if not analysis or not analysis.get("messages"):
                self.reply_area.setPlainText("请先识别聊天")
                return
            context = "\n".join(f"{'【我方】' if m.get('sender')=='me' else '【对方】'}{m.get('text','')}" for m in analysis["messages"])
            replies = llm_client.generate_replies(context)
            self.reply_area.clear()
            for i, r in enumerate(replies):
                self.reply_area.appendPlainText(f"--- 备选 {i+1} ---\n{r}\n")
        except Exception as e:
            self.reply_area.setPlainText(f"❌ {e}")
        finally:
            self.gen_btn.setEnabled(True)
            self.gen_btn.setText("⚡ 生成回复")

    def toggle_auto(self):
        if auto_pilot.is_running:
            auto_pilot.stop()
            self.auto_toggle_btn.setText("  ▶  开启自动托管  ")
            self.auto_toggle_btn.setStyleSheet("QPushButton { background: #c0522e; color: white; border-radius: 8px; font-size: 16px; font-weight: bold; }")
            self.auto_status.setText("状态: 已关闭")
            self.status_label.setText("● 待机中")
        else:
            if not cfg.config["mimo"]["api_key"]:
                QMessageBox.warning(self, "提示", "请先配置API Key")
                return
            auto_pilot.start()
            self.auto_toggle_btn.setText("  ⏹  停止自动托管  ")
            self.auto_toggle_btn.setStyleSheet("QPushButton { background: #c4554a; color: white; border-radius: 8px; font-size: 16px; font-weight: bold; }")
            self.auto_status.setText("状态: 运行中")
            self.status_label.setText("● 托管中")
            self.status_label.setStyleSheet("color: #5cb85c; font-size: 11px; padding: 12px 20px; font-weight: bold;")

    def approve_pending(self):
        pending = auto_pilot.get_pending()
        if not pending:
            self.pending_area.setPlainText("无待确认消息")
            return
        for i in range(len(pending)):
            auto_pilot.approve(0)  # 逐个批准
        self.refresh_pending()
        self.chat_info.setText("✅ 已全部批准发送")

    def reject_pending(self):
        pending = auto_pilot.get_pending()
        if pending:
            auto_pilot.reject(0)
            self.refresh_pending()

    def refresh_pending(self):
        pending = auto_pilot.get_pending()
        self.pending_area.clear()
        if not pending:
            self.pending_area.setPlainText("无待确认消息")
            return
        for i, p in enumerate(pending):
            self.pending_area.appendPlainText(f"[{i}] {p['chat']}: {p['reply'][:60]}")

    def refresh_logs(self):
        try:
            logs = cfg.get_logs(100)
            self.log_area.setPlainText(logs)
            cursor = self.log_area.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.log_area.setTextCursor(cursor)
        except: pass

    def append_log(self, msg):
        self.log_area.appendPlainText(msg)

    def refresh_memory(self):
        try:
            data = memory_store.get_recent_replies(30)
            stats = memory_store.get_stats()
            self.mem_stats.setText(f"总计: {stats['total']} | 用户: {stats['user_replies']} | AI: {stats['ai_replies']}")
            self.mem_area.clear()
            for r in reversed(data):
                tag = "👤 用户" if r["source"] == "user" else "🤖 AI"
                ts = r.get("timestamp", "")[:16]
                self.mem_area.appendPlainText(f"[{tag}] {r['text'][:80]}  ({ts})")
        except: pass

    def clear_memory(self):
        reply = QMessageBox.question(self, "确认", "确定清空所有记忆？")
        if reply == QMessageBox.Yes:
            memory_store.clear()
            self.refresh_memory()

    def calib_capture(self):
        try:
            screenshot = capture.capture_full_window()
            if screenshot:
                from PySide6.QtGui import QPixmap
                snap_path = str(cfg.config_path.parent / "last_snap.png")
                screenshot.save(snap_path)
                pixmap = QPixmap(snap_path)
                scaled = pixmap.scaledToWidth(600, Qt.SmoothTransformation)
                self.calib_preview.setPixmap(scaled)
            else:
                self.calib_preview.setText("❌ 截图失败")
        except Exception as e:
            self.calib_preview.setText(f"❌ {e}")

    def _add_tag(self, tag_type):
        inp = self.bl_input if tag_type == "blacklist" else self.wl_input
        val = inp.text().strip()
        if not val:
            return
        layout = self.bl_tags_layout if tag_type == "blacklist" else self.wl_tags_layout
        # 检查重复
        for i in range(layout.count()):
            w = layout.itemAt(i).widget()
            if w and hasattr(w, '_tag_text') and w._tag_text == val:
                return
        tag_frame = QFrame()
        tag_frame.setStyleSheet("QFrame { background: #ede8df; border: 1px solid #d4cfc6; border-radius: 16px; padding: 4px 8px; }")
        tag_layout = QHBoxLayout(tag_frame)
        tag_layout.setContentsMargins(8, 4, 8, 4)
        tag_layout.setSpacing(6)
        tag_label = QLabel(val)
        tag_label.setStyleSheet("font-size: 12px; font-family: monospace; background: transparent; border: none;")
        tag_layout.addWidget(tag_label)
        del_btn = QPushButton("×")
        del_btn.setFixedSize(18, 18)
        del_btn.setStyleSheet("QPushButton { background: rgba(196,85,74,0.1); color: #c4554a; border: none; border-radius: 9px; font-size: 11px; } QPushButton:hover { background: rgba(196,85,74,0.25); }")
        del_btn.clicked.connect(lambda: self._remove_tag(tag_type, tag_frame))
        tag_layout.addWidget(del_btn)
        tag_frame._tag_text = val
        layout.addWidget(tag_frame)
        inp.clear()

    def _remove_tag(self, tag_type, frame):
        layout = self.bl_tags_layout if tag_type == "blacklist" else self.wl_tags_layout
        layout.removeWidget(frame)
        frame.deleteLater()

    def _get_tags(self, tag_type):
        layout = self.bl_tags_layout if tag_type == "blacklist" else self.wl_tags_layout
        tags = []
        for i in range(layout.count()):
            w = layout.itemAt(i).widget()
            if w and hasattr(w, '_tag_text'):
                tags.append(w._tag_text)
        return tags

    def _add_schedule(self):
        self.schedule_data.append({"name": "", "start": "23:00", "end": "07:00", "interval": 60})
        self._render_schedule()

    def _render_schedule(self):
        while self.schedule_rows_layout.count():
            item = self.schedule_rows_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for i, s in enumerate(self.schedule_data):
            row = QFrame()
            row.setStyleSheet("QFrame { background: #ede8df; border: 1px solid #d4cfc6; border-radius: 8px; padding: 8px; }")
            row_layout = QHBoxLayout(row)
            row_layout.setSpacing(8)
            name_inp = QLineEdit(s.get("name", ""))
            name_inp.setPlaceholderText("名称")
            name_inp.setFixedWidth(100)
            name_inp.textChanged.connect(lambda t, idx=i: self.schedule_data.__setitem__(idx, {**self.schedule_data[idx], "name": t}))
            row_layout.addWidget(name_inp)
            start_inp = QLineEdit(s.get("start", "23:00"))
            start_inp.setFixedWidth(80)
            start_inp.textChanged.connect(lambda t, idx=i: self.schedule_data.__setitem__(idx, {**self.schedule_data[idx], "start": t}))
            row_layout.addWidget(start_inp)
            row_layout.addWidget(QLabel("至"))
            end_inp = QLineEdit(s.get("end", "07:00"))
            end_inp.setFixedWidth(80)
            end_inp.textChanged.connect(lambda t, idx=i: self.schedule_data.__setitem__(idx, {**self.schedule_data[idx], "end": t}))
            row_layout.addWidget(end_inp)
            interval_inp = QSpinBox()
            interval_inp.setRange(2, 3600)
            interval_inp.setValue(s.get("interval", 60))
            interval_inp.setFixedWidth(70)
            interval_inp.valueChanged.connect(lambda v, idx=i: self.schedule_data.__setitem__(idx, {**self.schedule_data[idx], "interval": v}))
            row_layout.addWidget(interval_inp)
            row_layout.addWidget(QLabel("秒"))
            del_btn = QPushButton("×")
            del_btn.setFixedSize(28, 28)
            del_btn.setStyleSheet("QPushButton { background: rgba(196,85,74,0.1); color: #c4554a; border: none; border-radius: 14px; font-size: 14px; } QPushButton:hover { background: rgba(196,85,74,0.2); }")
            del_btn.clicked.connect(lambda _, idx=i: self._del_schedule(idx))
            row_layout.addWidget(del_btn)
            self.schedule_rows_layout.addWidget(row)

    def _del_schedule(self, idx):
        self.schedule_data.pop(idx)
        self._render_schedule()

    def refresh_status(self):
        if auto_pilot.is_running:
            s = auto_pilot.get_status()
            self.auto_stats.setText(f"轮询: {s['cycle_count']} | 待确认: {s['pending_count']} | 时段: {s.get('slot', '默认')}")
            self.refresh_pending()

    def closeEvent(self, event):
        if auto_pilot.is_running:
            auto_pilot.stop()
        event.accept()


from PySide6.QtWidgets import QApplication

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    font = QFont("Noto Serif SC", 10)
    app.setFont(font)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
