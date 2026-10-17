#!/usr/bin/env bash
# 🕵️ Досье больших каналов + сравнение с нашими (решение 17.10). Только чтение базы Разведки и одно сообщение
# в PAPA TEST GROUP (не в «Избранное»). Само приходит по понедельникам в ежедневном прогоне; эта задача — сейчас.
# Откат не нужен: ничего не меняет.
set -euo pipefail
PY=/opt/papa-venv/razvedka/bin/python
( cd /opt/papa/modules/razvedka && $PY -m unittest discover -q -s tests 2>&1 | tail -1 )
set -a; . /etc/papa-razvedka/telegram.env; set +a
export PYTHONUNBUFFERED=1
# от пользователя Разведки — файлы базы (WAL) остаются её; runuser сохраняет переменные сессии
( cd /opt/papa/modules/razvedka && runuser -u papa-razvedka -- $PY -m razvedka dossier --send ) | tail -n 60
echo "== DOSSIER_DONE"
