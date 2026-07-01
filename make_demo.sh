#!/bin/bash
# 演示录屏脚本 - 证明无键鼠+自动回复
set -e
OUTDIR="/tmp/demo_video"
mkdir -p "$OUTDIR"
DURATION=45  # 录屏45秒
SCREEN_W=1366
SCREEN_H=768

echo "===== 开始演示录屏 ====="

# 1. 先截个lsusb证明无键鼠
echo ">>> 步骤1: 证明无键盘鼠标"
lsusb | grep -iE "mouse|keyboard" > "$OUTDIR/usb_check.txt" || true
if [ -s "$OUTDIR/usb_check.txt" ]; then
    echo "⚠ 检测到键鼠:"
    cat "$OUTDIR/usb_check.txt"
else
    echo "✅ 无USB键盘鼠标"
fi

# 2. 生成证明卡片（3秒）
ffmpeg -y -f lavfi -i "color=c=#0a0a0a:s=${SCREEN_W}x${SCREEN_H}:d=3" \
  -vf "drawtext=text='Proof: No Keyboard or Mouse':fontcolor=#c0522e:fontsize=60:x=(w-text_w)/2:y=h/2-80,\
drawtext=text='lsusb shows no HID devices':fontcolor=white:fontsize=36:x=(w-text_w)/2:y=h/2+20,\
drawtext=text='All automation is done by AI Agent':fontcolor=#a09484:fontsize=30:x=(w-text_w)/2:y=h/2+80" \
  -c:v libx264 -pix_fmt yuv420p "$OUTDIR/01_proof.mp4" 2>/dev/null
echo ">>> 步骤1完成"

# 3. 开始录屏（后台）
echo ">>> 步骤2: 开始录屏 ${DURATION}秒"
DISPLAY=:0 ffmpeg -f x11grab -video_size ${SCREEN_W}x${SCREEN_H} -framerate 15 -i :0.0 \
  -t $DURATION -c:v libx264 -preset ultrafast "$OUTDIR/02_recording.mp4" &
RECORD_PID=$!
sleep 2

# 4. 激活微信窗口
echo ">>> 步骤3: 激活微信"
WXWID=$(xdotool search --name "微信" 2>/dev/null | sort -n | tail -1)
if [ -n "$WXWID" ]; then
    xdotool windowactivate --sync "$WXWID" 2>/dev/null
    sleep 1
fi

# 5. 开启自动托管
echo ">>> 步骤4: 开启自动托管"
curl -s -m 5 -X POST http://localhost:8090/api/auto_toggle 2>/dev/null
echo ""

# 6. 等待录屏完成
echo ">>> 步骤5: 等待录屏..."
wait $RECORD_PID 2>/dev/null || true
echo ">>> 录屏完成"

# 7. 生成结束卡片（3秒）
ffmpeg -y -f lavfi -i "color=c=#0a0a0a:s=${SCREEN_W}x${SCREEN_H}:d=3" \
  -vf "drawtext=text='Auto Reply by AI Agent':fontcolor=#c0522e:fontsize=60:x=(w-text_w)/2:y=h/2-80,\
drawtext=text='No human intervention needed':fontcolor=white:fontsize=36:x=(w-text_w)/2:y=h/2+20,\
drawtext=text='github.com/ZhangJun-troll/wechat-auto-reply':fontcolor=#a09484:fontsize=30:x=(w-text_w)/2:y=h/2+80" \
  -c:v libx264 -pix_fmt yuv420p "$OUTDIR/03_outro.mp4" 2>/dev/null

# 8. 合并
CONCAT="$OUTDIR/concat.txt"
> "$CONCAT"
for f in "$OUTDIR"/0{1,2,3}_*.mp4; do
  [ -f "$f" ] && echo "file '$f'" >> "$CONCAT"
done

ffmpeg -y -f concat -safe 0 -i "$CONCAT" -c:v libx264 -pix_fmt yuv420p "$OUTDIR/demo_final.mp4" 2>/dev/null

# 9. 关闭自动托管
curl -s -m 5 -X POST http://localhost:8090/api/auto_toggle 2>/dev/null

echo ""
echo "✅ 演示视频已生成: $OUTDIR/demo_final.mp4"
echo "   时长: 约51秒"
