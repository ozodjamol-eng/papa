#!/usr/bin/env bash
# YUKLA: тесты → обновить yt-dlp → перезапуск papa-yukla (токен не трогает). Откат: git revert + эта же задача.
set -euo pipefail
( cd /opt/papa/modules/yukla && python3 -m unittest discover -q -s tests 2>&1 | tail -1 )
/opt/papa-venv/yukla/bin/pip install -q --upgrade yt-dlp && echo "yt-dlp: $(/opt/papa-venv/yukla/bin/yt-dlp --version)"
systemctl restart papa-yukla; sleep 3
echo "papa-yukla: $(systemctl is-active papa-yukla)"
journalctl -u papa-yukla -n 5 -o cat --no-pager
echo "== YUKLA_RESTART_DONE"
