#!/bin/bash
# WeChat Auto Reply 一键安装（自动检测CPU选OCR引擎）
set -e
G='\033[0;32m'; R='\033[0;31m'; Y='\033[1;33m'; N='\033[0m'

echo ""
echo -e "${Y}WeChat Auto Reply 安装程序${N}"
echo ""

# 1. 系统依赖
echo -e "${Y}[1/4]${N} 系统依赖..."
for pkg in xdotool xclip tesseract-ocr tesseract-ocr-chi-sim; do
    dpkg -l $pkg 2>/dev/null | grep -q "^ii" || sudo apt-get install -y $pkg 2>/dev/null
    echo -e "  ${G}✓${N} $pkg"
done

# 2. Python基础
echo -e "${Y}[2/4]${N} Python基础依赖..."
pip3 install --user -q -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com \
    fastapi uvicorn mss pillow requests numpy pytesseract 2>&1 | tail -2
echo -e "  ${G}✓${N} 基础依赖 + pytesseract"

# 3. 检测CPU，选OCR引擎
echo -e "${Y}[3/4]${N} 检测CPU选OCR引擎..."
CPU_MODEL=$(grep "model name" /proc/cpuinfo | head -1 | cut -d: -f2 | xargs)
HAS_AVX2=$(grep -o 'avx2' /proc/cpuinfo | head -1)
echo "  CPU: $CPU_MODEL"

if [ -n "$HAS_AVX2" ]; then
    echo -e "  ${G}✓${N} 检测到AVX2，安装PaddleOCR..."
    pip3 install --user -q -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com \
        paddlepaddle paddleocr 2>&1 | tail -2 && \
        echo -e "  ${G}✓${N} PaddleOCR就绪" || \
        echo -e "  ${Y}⚠${N} PaddleOCR安装失败，将使用Tesseract"
else
    echo -e "  ${Y}⚠${N} CPU无AVX2（$CPU_MODEL），跳过PaddleOCR"
    echo -e "  ${G}✓${N} 使用Tesseract引擎（已安装）"
fi

# 4. 验证
echo -e "${Y}[4/4]${N} 验证OCR引擎..."
$PYTHON -c "from paddleocr import PaddleOCR; print('  ✓ PaddleOCR可用')" 2>/dev/null || \
$PYTHON -c "import pytesseract; print('  ✓ Tesseract可用')" 2>/dev/null || \
echo -e "  ${R}✗ OCR引擎不可用${N}"

chmod +x ~/wechat-auto-reply/start.sh 2>/dev/null

echo ""
echo -e "${G}✅ 安装完成！${N}"
echo "  启动: cd ~/wechat-auto-reply && ./start.sh"
echo ""
