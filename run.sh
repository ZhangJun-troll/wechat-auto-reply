#!/bin/bash
# ============================================
#  WeChat Auto Reply 桌面版启动器
#  首次运行装依赖，之后直接启动（<1秒）
# ============================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="/usr/bin/python3"
PIP="/usr/bin/pip3"
DEPS_MARKER="$SCRIPT_DIR/.deps_installed"

# ====== 快速检查：依赖已装直接启动 ======
if [ -f "$DEPS_MARKER" ]; then
    # 快速校验关键包是否存在
    if $PYTHON -c "import PySide6, fastapi, uvicorn, mss" 2>/dev/null; then
        cd "$SCRIPT_DIR"
        exec $PYTHON app.py
    fi
    # 标记文件存在但包丢了，删标记重装
    rm -f "$DEPS_MARKER"
fi

# ====== 首次安装流程 ======
G='\033[0;32m'; R='\033[0;31m'; Y='\033[1;33m'; C='\033[0;36m'; N='\033[0m'

clear
echo ""
echo -e "${C}╔══════════════════════════════════════════════╗${NC}"
echo -e "${C}║     💬 WeChat Auto Reply 桌面版              ║${NC}"
echo -e "${C}║     首次运行，正在安装依赖...                ║${NC}"
echo -e "${C}╚══════════════════════════════════════════════╝${NC}"
echo ""

# 检查Python
if ! command -v $PYTHON &>/dev/null; then
    echo -e "${R}✗ 未找到Python3，请先安装:${NC}"
    echo "  sudo apt install python3 python3-pip"
    read -p "按回车退出..."
    exit 1
fi

# 系统依赖
echo -e "${Y}[1/3]${NC} 检查系统依赖..."
for pkg in xdotool xclip; do
    command -v $pkg &>/dev/null || {
        echo -e "  ${Y}○${NC} 安装 $pkg ..."
        sudo apt-get install -y $pkg 2>/dev/null || echo -e "  ${R}✗ $pkg 安装失败，请手动: sudo apt install $pkg${NC}"
    }
done
echo -e "  ${G}✓${NC} 系统依赖就绪"

# Python依赖
echo -e "${Y}[2/3]${NC} 检查Python依赖..."
NEED=""
for pkg in PySide6 fastapi uvicorn mss pillow requests numpy; do
    mod="${pkg//-/_}"
    $PYTHON -c "import $mod" 2>/dev/null || NEED="$NEED $pkg"
done

if [ -n "$NEED" ]; then
    echo -e "  ${Y}○${NC} 安装:$NEED"
    $PIP install --user -q \
        -i https://mirrors.aliyun.com/pypi/simple/ \
        --trusted-host mirrors.aliyun.com \
        $NEED 2>&1 | grep -v "^WARNING" | tail -2
    echo -e "  ${G}✓${NC} Python依赖安装完成"
else
    echo -e "  ${G}✓${NC} 所有依赖已就绪"
fi

# PaddleOCR
echo -e "${Y}[3/3]${NC} 检查OCR引擎..."
$PYTHON -c "from paddleocr import PaddleOCR" 2>/dev/null || {
    echo -e "  ${Y}○${NC} 安装 PaddleOCR（约800MB）..."
    $PIP install --user -q \
        -i https://mirrors.aliyun.com/pypi/simple/ \
        --trusted-host mirrors.aliyun.com \
        paddlepaddle paddleocr 2>&1 | grep -v "^WARNING" | tail -2
}
echo -e "  ${G}✓${NC} OCR引擎就绪"

# 写标记文件，下次跳过安装
touch "$DEPS_MARKER"
echo ""
echo -e "${G}✅ 依赖安装完成，下次启动将直接打开（<1秒）${NC}"
echo ""
sleep 1

# 启动
cd "$SCRIPT_DIR"
exec $PYTHON app.py
