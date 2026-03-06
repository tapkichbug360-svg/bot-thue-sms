#!/bin/bash
gunicorn main:app &
python bot.py
