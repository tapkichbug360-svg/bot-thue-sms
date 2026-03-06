#!/bin/bash
# Chạy Flask ở background
gunicorn main:app --daemon
# Chạy bot ở foreground (giữ service sống)
python bot.py