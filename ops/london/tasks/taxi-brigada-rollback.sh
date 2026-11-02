#!/usr/bin/env bash
# Откат «🚖 Бригадир» в XOJAOBOD CITY 24 — вернуть файлы из последней резервной копии. Таблицы brigada_* в базе остаются (не мешают).
set -uo pipefail
A=/opt/xojaobodcity24bot/app; BK=/opt/xojaobodcity24bot/deploy-backups
F=$(cat $BK/brigada-LAST 2>/dev/null); [[ -f "$F" ]] || { echo "нет копии"; exit 1; }
tar xzf "$F" -C $A && rm -f $A/bot/handlers/brigada.py $A/tests/test_brigada.py
systemctl restart xojaobodcity24bot; sleep 6; echo "служба: $(systemctl is-active xojaobodcity24bot) · откат из $F"
echo "== TAXI_BRIGADA_ROLLBACK_DONE"
