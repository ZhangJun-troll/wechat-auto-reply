#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="/usr/bin/python3"

# 检查依赖
$PYTHON -c "import fastapi, uvicorn, mss, PIL, requests, numpy" 2>/dev/null || {
    echo "⚠️  缺少依赖，运行 install.sh 先"
    exit 1
}

# 检查OCR引擎
$PYTHON -c "from paddleocr import PaddleOCR" 2>/dev/null && echo "✓ PaddleOCR就绪" || {
    $PYTHON -c "import pytesseract" 2>/dev/null && echo "✓ Tesseract就绪" || {
        echo "⚠️  缺少OCR引擎，运行 install.sh 先"
        exit 1
    }
}

echo ""
echo "  💬 WeChat Auto Reply 启动中..."
echo "  📌 http://localhost:8090"
echo ""

cd "$SCRIPT_DIR/backend"
exec $PYTHON -m uvicorn main:app --host 0.0.0.0 --port 8090 --log-level info
