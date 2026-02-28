#!/bin/bash
# Wrapper que activa conda y corre el bot de Telegram
source /opt/anaconda3/etc/profile.d/conda.sh
conda activate base
exec /opt/anaconda3/bin/python3 /Users/josemuniz/.claude/hooks/telegram-bot-daemon.py
