#!/bin/bash
# Chạy Flask ở foreground (quan trọng: không có --daemon)
gunicorn main:app &
# Lưu PID của gunicorn
GUNICORN_PID=$!
# Chạy bot ở foreground
python bot.py
# Khi bot kết thúc, kết thúc cả gunicorn
kill $GUNICORN_PID