#!/usr/bin/env bash
# Только чтение (02.11, такси «бригадир», шаг 2): живой код XOJAOBOD CITY 24 (bot/, main.py, config.py) — tar.gz → base64,
# чтобы ассистент писал поверх НАСТОЯЩЕЙ версии. .env, data/, базы, бэкапы не берутся. Ничего не меняет.
set -uo pipefail
A=/opt/xojaobodcity24bot/app
cd $A || exit 1
if grep -nE '(TOKEN|KEY|SECRET|PASSWORD)[A-Z_]*\s*[:=].*["'"'"'][A-Za-z0-9:_-]{20,}' config.py main.py >/dev/null; then echo "STOP: похоже на секрет в коде"; exit 2; fi
echo "== B64_START"
tar czf - --exclude='__pycache__' bot main.py config.py | base64 -w 0
echo
echo "== B64_END"
echo "== TAXI_LIVE_DUMP_DONE"
