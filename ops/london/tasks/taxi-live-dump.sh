#!/usr/bin/env bash
# Только чтение (02.11, такси «бригадир», шаг 2): живой код XOJAOBOD CITY 24 (bot/, main.py, config.py) — tar.gz → base64,
# чтобы ассистент писал поверх НАСТОЯЩЕЙ версии. .env, data/, базы, бэкапы не берутся. Ничего не меняет.
set -uo pipefail
A=/opt/xojaobodcity24bot/app
cd $A || exit 1
RX='(TOKEN|KEY|SECRET|PASSWORD)[A-Z_]*\s*[:=].*["'"'"'][A-Za-z0-9:_-]{20,}'
echo "== подозрительные строки (только номер и имя, без значения):"
grep -nE "$RX" config.py main.py 2>/dev/null | sed -E 's/^([^:]+:[0-9]+):\s*([A-Za-z_]+).*/\1 \2=…/'
# config.py — значения строк-литералов длиной 20+ заменяются на «…» (секрет в архив не попадает)
mkdir -p /tmp/taxi_dump && rm -rf /tmp/taxi_dump/* && cp -r bot main.py /tmp/taxi_dump/
sed -E 's/(["'"'"'])[A-Za-z0-9:_\/+=.-]{20,}(["'"'"'])/\1…\2/g' config.py > /tmp/taxi_dump/config.py
if grep -rqE "$RX" /tmp/taxi_dump/main.py /tmp/taxi_dump/bot /tmp/taxi_dump/config.py; then echo "STOP: секрет в коде"; rm -rf /tmp/taxi_dump; exit 2; fi
cd /tmp/taxi_dump
echo "== B64_START"
tar czf - --exclude='__pycache__' bot main.py config.py | base64 -w 0
echo
echo "== B64_END"
rm -rf /tmp/taxi_dump
echo "== TAXI_LIVE_DUMP_DONE"
