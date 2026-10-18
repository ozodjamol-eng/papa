#!/usr/bin/env bash
# 🕊 История канала ХОТИРА → база повторов бота (профиль Разведки читает канал, ничего не публикует). Повторять можно.
set -euo pipefail
set -a; . /etc/papa-razvedka/telegram.env; . /etc/papa-xotira/xotira.env; set +a
export XOTIRA_DB=/var/lib/papa-xotira/xotira.sqlite3
/opt/papa-venv/razvedka/bin/python /opt/papa/ops/frankfurt/xotira_scan.py
chown -R papa-xotira:papa-xotira /var/lib/papa-xotira
echo "== XOTIRA_SCAN_DONE"
