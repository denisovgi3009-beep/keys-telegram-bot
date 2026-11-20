#!/usr/bin/env bash
# Универсальный стартер для Python-хостингов/панелей (Pterodactyl, VPS, shared).
set -e
cd "$(dirname "$0")"
if [ -f requirements.txt ]; then
  python3 -m pip install --user -r requirements.txt 2>/dev/null \
    || python3 -m pip install -r requirements.txt
fi
exec python3 bot.py
