# WeChat Auto Reply 部署说明

## 系统要求

- Ubuntu 22.04/24.04
- Python 3.10+
- Linux微信客户端

## 一键安装

```bash
chmod +x install.sh
./install.sh
```

安装脚本自动检测CPU型号：
- **有AVX2**（Intel i5+ / AMD Ryzen）→ 安装PaddleOCR（识别更快更准）
- **无AVX2**（老CPU如AMD E2系列）→ 使用Tesseract（轻量但够用）

## 启动

```bash
cd ~/wechat-auto-reply
./start.sh
# 浏览器打开 http://localhost:8090
```

## OCR引擎对比

| 特性 | PaddleOCR | Tesseract |
|------|-----------|-----------|
| 速度 | 快 | 较慢 |
| 准确度 | 高 | 中等 |
| 内存占用 | ~500MB | ~50MB |
| CPU要求 | 需AVX2 | 无要求 |
| 适用场景 | 现代电脑 | 老电脑/低配 |

程序自动检测CPU并选择最优引擎，无需手动配置。

## 手动安装（不用安装脚本）

```bash
# 系统依赖
sudo apt install xdotool xclip tesseract-ocr tesseract-ocr-chi-sim

# Python依赖（阿里源加速）
pip3 install --user -i https://mirrors.aliyun.com/pypi/simple/ \
    fastapi uvicorn mss pillow requests numpy pytesseract

# 有AVX2的CPU再装PaddleOCR
pip3 install --user -i https://mirrors.aliyun.com/pypi/simple/ \
    paddlepaddle paddleocr
```

## 项目结构

```
wechat-auto-reply/
├── backend/
│   ├── main.py              # FastAPI主入口
│   ├── config.py             # 配置管理
│   ├── window_capture.py     # 窗口截图
│   ├── ocr_engine.py         # OCR（自动降级）
│   ├── llm_client.py         # LLM调用
│   ├── keyboard_mouse.py     # 键鼠模拟
│   ├── memory_store.py       # 记忆存储
│   ├── auto_pilot.py         # 自动托管
│   └── time_schedule.py      # 时段调度
├── frontend/
│   └── index.html            # 控制面板
├── install.sh                # 一键安装
├── start.sh                  # 启动脚本
└── DEPLOY.md                 # 本文档
```

## 常见问题

**Q: 微信窗口找不到？**
确保微信已打开。运行 `xdotool search --name 微信` 验证。

**Q: OCR识别不准？**
调整配置页的「窗口裁剪」参数，或用校准页面框选区域。

**Q: PaddleOCR安装失败？**
老CPU（无AVX2）会自动降级到Tesseract，不影响使用。

**Q: API调用失败？**
检查API Key和地址是否正确，用「验证密钥」按钮测试。

**Q: 自动回复没反应？**
检查微信窗口是否被遮挡（截图需要窗口可见）。
