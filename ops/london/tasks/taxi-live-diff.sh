#!/usr/bin/env bash
# Только чтение (02.11, такси «бригадир», шаг 2): разница живого кода с версией GitHub main (лежит в ops/london/ref/taxi).
# Маленький вывод вместо целых файлов. Ничего не меняет.
set -uo pipefail
A=/opt/xojaobodcity24bot/app; R=/opt/papa/ops/london/ref/taxi
for f in bot/database.py main.py bot/keyboards/reply.py; do
  echo "== DIFF $f"; diff -u "$R/$f" "$A/$f" | sed -E 's/(TOKEN|KEY|SECRET|PASSWORD)([A-Z_]*\s*[:=]\s*)\S+/\1\2…/g'
done
echo "== TAXI_LIVE_DIFF_DONE"
