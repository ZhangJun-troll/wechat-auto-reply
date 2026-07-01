#!/bin/bash
# 后端守护进程 - 挂了自动重启
cd "$(dirname "$0")/backend"
LOG="/tmp/wechat-backend.log"

echo "后端守护启动 $(date)" > "$LOG"
while true; do
    DISPLAY=:0 /usr/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8090 --log-level info 2>>"$LOG"
    echo "$(date) 后端退出，3秒后重启" >> "$LOG"
    sleep 3
done
