#!/usr/bin/env bash
# 🏦 KATTA BANK (30.10): создать недостающие хабы направлений (УЙДА БИЗНЕС, МОТИВАЦИЯ) и папку «KATTA BANK» со всеми хабами
# в Telegram владельца. Ничего не удаляет; повтор безопасен (папка обновится).
set -euo pipefail
PY=/opt/papa-venv/razvedka/bin/python
set -a; . /etc/papa-razvedka/telegram.env; set +a
export PYTHONUNBUFFERED=1
( cd /opt/papa/modules/razvedka && runuser -u papa-razvedka -- $PY -m razvedka bank ) | tail -n 20
echo "== BANK_DONE"
