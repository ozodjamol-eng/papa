#!/usr/bin/env bash
# YUKLA: тесты → обновить yt-dlp → перезапуск papa-yukla (токен не трогает). Откат: git revert + эта же задача.
set -euo pipefail
# 04.11: перед перезапуском — диагностика (только чтение): состояние службы, ошибки за 12 ч, последние загрузки
echo "== до перезапуска: papa-yukla $(systemctl is-active papa-yukla) · с $(systemctl show -p ActiveEnterTimestamp --value papa-yukla)"
journalctl -u papa-yukla --since "-12h" --no-pager -o cat | sed -E 's/bot[0-9]+:[A-Za-z0-9_-]+/bot***/g' | grep -vE '^\s*$' | tail -25 | cut -c1-300
DB=$(systemctl show -p Environment --value papa-yukla | tr ' ' '\n' | sed -n 's/^YUKLA_DB=//p'); DB=${DB:-/var/lib/papa-yukla/yukla.sqlite3}
[[ -f $DB ]] && python3 -c "import sqlite3,sys;d=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True);print('== последние загрузки:');[print('  ',r) for r in d.execute('SELECT platform,result,ts FROM log ORDER BY rowid DESC LIMIT 8')]" "$DB" 2>&1 | head -10
( cd /opt/papa/modules/yukla && python3 -m unittest discover -q -s tests 2>&1 | tail -1 )
/opt/papa-venv/yukla/bin/pip install -q --upgrade yt-dlp && echo "yt-dlp: $(/opt/papa-venv/yukla/bin/yt-dlp --version)"
systemctl restart papa-yukla; sleep 3
echo "papa-yukla: $(systemctl is-active papa-yukla)"
journalctl -u papa-yukla -n 5 -o cat --no-pager | sed -E 's/bot[0-9]+:[A-Za-z0-9_-]+/bot***/g'
echo "== YUKLA_RESTART_DONE"
