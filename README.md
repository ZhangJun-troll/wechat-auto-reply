# WeChat Auto Reply

基于AI视觉识别的Linux微信自动回复工具。

## 功能

- 🤖 AI视觉识别聊天内容，无需OCR
- 💬 自动检测未读消息并生成回复
- 🎯 支持多种大模型（NVIDIA NIM免费视觉模型）
- 🔒 黑白名单过滤
- ⏰ 时段调度轮询
- 🖥️ PySide6桌面控制面板

## 快速开始

```bash
# 克隆仓库
git clone https://github.com/ZhangJun-troll/wechat-auto-reply.git
cd wechat-auto-reply

# 一键安装
chmod +x install.sh
./install.sh

# 启动
./start.sh
```

浏览器打开 `http://localhost:8090` 或运行桌面版 `python3 app.py`

## 支持的模型

| 模型 | 类型 | 说明 |
|------|------|------|
| nvidia/nemotron-nano-12b-v2-vl | 视觉 | ⭐ 推荐 |
| nvidia/llama-3.1-nemotron-nano-vl-8b-v1 | 视觉 | 可用 |
| meta/llama-3.2-11b-vision-instruct | 视觉 | 中文一般 |
| step-3.7-flash | 纯文本 | 需推理 |
| DeepSeek-V3 | 纯文本 | 可能不稳定 |

## 工作原理

```
微信窗口 → mss截图 → 视觉大模型识别未读 → 分析聊天内容 → 生成回复 → xdotool模拟发送
```

## 系统要求

- Ubuntu 22.04/24.04
- Python 3.10+
- Linux微信客户端（需可见窗口）
- xdotool, xclip

## 项目结构

```
wechat-auto-reply/
├── backend/
│   ├── main.py           # FastAPI入口
│   ├── window_capture.py # 窗口截图
│   ├── llm_client.py     # AI视觉+文本
│   ├── keyboard_mouse.py # xdotool模拟
│   ├── auto_pilot.py     # 自动托管
│   ├── ocr_engine.py     # OCR降级
│   ├── name_list.py      # 黑白名单
│   ├── time_schedule.py  # 时段调度
│   └── config.py         # 配置管理
├── app.py                # PySide6桌面应用
├── frontend/index.html   # Web控制面板
├── install.sh            # 一键安装
├── daemon.sh             # 守护进程
└── start.sh              # 启动脚本
```

## 依赖

```bash
# 系统依赖
sudo apt install xdotool xclip tesseract-ocr tesseract-ocr-chi-sim

# Python依赖
pip3 install --user fastapi uvicorn mss pillow requests numpy pytesseract PySide6
```

CPU无AVX2会自动使用Tesseract，有AVX2可选装PaddleOCR。

## 配置

在Web面板或桌面应用中配置：
- API Key（NVIDIA NIM免费）
- 模型选择
- 轮询间隔
- 黑白名单
- 时段调度

## License

MIT
