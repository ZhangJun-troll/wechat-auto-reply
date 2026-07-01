#!/bin/bash
# 生成抖音推广视频 - 30秒
set -e
OUTDIR="/tmp/douyin_video"
mkdir -p "$OUTDIR"

echo "===== 生成推广视频 ====="

# 1. 截取微信窗口
DISPLAY=:0 import -window $(xdotool search --name "微信" | sort -n | tail -1) "$OUTDIR/wechat.png" 2>/dev/null || true
# 截桌面应用
DISPLAY=:0 import -window $(xdotool search --name "WeChat Auto Reply" | sort -n | tail -1) "$OUTDIR/app.png" 2>/dev/null || true

# 2. 生成文字卡片（FFmpeg生成纯色背景+文字）
# 片头：3秒
ffmpeg -y -f lavfi -i "color=c=#1a1a2e:s=1080x1920:d=3" \
  -vf "drawtext=text='WeChat Auto Reply':fontcolor=white:fontsize=72:x=(w-text_w)/2:y=h/2-100,\
drawtext=text='AI自动回复微信消息':fontcolor=#c0522e:fontsize=48:x=(w-text_w)/2:y=h/2,\
drawtext=text='Ubuntu Linux 桌面工具':fontcolor=#a09484:fontsize=36:x=(w-text_w)/2:y=h/2+80" \
  -c:v libx264 -pix_fmt yuv420p "$OUTDIR/01_intro.mp4" 2>/dev/null

# 功能介绍：5秒
ffmpeg -y -f lavfi -i "color=c=#1a1a2e:s=1080x1920:d=5" \
  -vf "drawtext=text='核心功能':fontcolor=white:fontsize=60:x=(w-text_w)/2:y=200,\
drawtext=text='✓ AI视觉识别聊天内容':fontcolor=#c0522e:fontsize=40:x=100:y=400,\
drawtext=text='✓ 自动检测未读消息':fontcolor=#c0522e:fontsize=40:x=100:y=500,\
drawtext=text='✓ 自动生成3条回复':fontcolor=#c0522e:fontsize=40:x=100:y=600,\
drawtext=text='✓ 黑白名单过滤':fontcolor=#c0522e:fontsize=40:x=100:y=700,\
drawtext=text='✓ 桌面控制面板':fontcolor=#c0522e:fontsize=40:x=100:y=800" \
  -c:v libx264 -pix_fmt yuv420p "$OUTDIR/02_features.mp4" 2>/dev/null

# 截图展示：5秒
if [ -f "$OUTDIR/app.png" ]; then
  ffmpeg -y -loop 1 -i "$OUTDIR/app.png" -t 5 \
    -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=#1a1a2e,\
    drawtext=text='桌面控制面板':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=h-200" \
    -c:v libx264 -pix_fmt yuv420p "$OUTDIR/03_app.mp4" 2>/dev/null
fi

# 技术栈：5秒
ffmpeg -y -f lavfi -i "color=c=#1a1a2e:s=1080x1920:d=5" \
  -vf "drawtext=text='技术栈':fontcolor=white:fontsize=60:x=(w-text_w)/2:y=200,\
drawtext=text='Python + FastAPI':fontcolor=#c0522e:fontsize=40:x=100:y=400,\
drawtext=text='NVIDIA NIM 免费视觉模型':fontcolor=#c0522e:fontsize=40:x=100:y=500,\
drawtext=text='PySide6 桌面应用':fontcolor=#c0522e:fontsize=40:x=100:y=600,\
drawtext=text='xdotool 键鼠模拟':fontcolor=#c0522e:fontsize=40:x=100:y=700,\
drawtext=text='GitHub 开源':fontcolor=#c0522e:fontsize=40:x=100:y=800" \
  -c:v libx264 -pix_fmt yuv420p "$OUTDIR/04_tech.mp4" 2>/dev/null

# 结尾：3秒
ffmpeg -y -f lavfi -i "color=c=#1a1a2e:s=1080x1920:d=3" \
  -vf "drawtext=text='GitHub 开源免费':fontcolor=#c0522e:fontsize=48:x=(w-text_w)/2:y=h/2-80,\
drawtext=text='github.com/ZhangJun-troll':fontcolor=white:fontsize=36:x=(w-text_w)/2:y=h/2,\
drawtext=text='wechat-auto-reply':fontcolor=white:fontsize=36:x=(w-text_w)/2:y=h/2+50,\
drawtext=text='⭐ Star 支持一下':fontcolor=#c0522e:fontsize=40:x=(w-text_w)/2:y=h/2+130" \
  -c:v libx264 -pix_fmt yuv420p "$OUTDIR/05_outro.mp4" 2>/dev/null

# 3. 合并所有片段
CONCAT="$OUTDIR/concat.txt"
> "$CONCAT"
for f in "$OUTDIR"/0{1,2,3,4,5}_*.mp4; do
  [ -f "$f" ] && echo "file '$f'" >> "$CONCAT"
done

ffmpeg -y -f concat -safe 0 -i "$CONCAT" -c:v libx264 -pix_fmt yuv420p "$OUTDIR/final.mp4" 2>/dev/null

# 4. 转成抖音格式（竖屏1080x1920）
cp "$OUTDIR/final.mp4" ~/Desktop/wechat_auto_reply_promo.mp4

echo ""
echo "✅ 视频已生成: ~/Desktop/wechat_auto_reply_promo.mp4"
echo "   格式: 竖屏 1080x1920, 适合抖音"
echo "   时长: 约21秒"
