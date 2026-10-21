#!/usr/bin/env bash
# 🕊 История канала ХОТИРА (тексты и фото) → база повторов бота (профиль Разведки читает канал, ничего не публикует). Повторять можно.
set -euo pipefail
set -a; . /etc/papa-razvedka/telegram.env; . /etc/papa-xotira/xotira.env; set +a
export XOTIRA_DB=/var/lib/papa-xotira/xotira.sqlite3
/opt/papa-venv/razvedka/bin/python /opt/papa/ops/frankfurt/xotira_scan.py
# 21.10: отпечатки фото канала (OpenCV из venv бота) + отчёт о повторах, уже попавших в канал
[[ -x /opt/papa-venv/xotira/bin/python ]] && /opt/papa-venv/xotira/bin/python /opt/papa/ops/frankfurt/xotira_prints.py 2>&1 | grep -v "WARN"
chown -R papa-xotira:papa-xotira /var/lib/papa-xotira
echo "== XOTIRA_SCAN_DONE"
