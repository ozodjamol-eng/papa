#!/usr/bin/env bash
# Франкфурт: перезапуск бота Shodiyona после изменения кода/config.toml (данные и токен не трогаются).
set -Eeuo pipefail
( cd /opt/papa/modules/shodiyona && python3 -m unittest discover -q -s tests 2>&1 | tail -1 )
systemctl restart papa-shodiyona; sleep 5
echo "papa-shodiyona: $(systemctl is-active papa-shodiyona)"
journalctl -u papa-shodiyona -n 5 --no-pager -o cat
echo "== SHODIYONA_BOT_RESTARTED"
