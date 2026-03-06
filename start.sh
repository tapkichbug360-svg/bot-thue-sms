#!/bin/bash
gunicorn main:app --daemon
python bot.py