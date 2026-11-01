#!/usr/bin/env bash
# 🧹 01.11 владелец: «немедленно просканируй всё… выявить и устранить». Хабы KATTA BANK: удалить материал агентов
# за 24 ч с НЕ нашим текстом (сырой чужой/без текста). Пересланное владельцем не трогает.
set -euo pipefail
PY=/opt/papa-venv/razvedka/bin/python
for u in collect run curate hunt pain sources insta archive; do
  if systemctl is-active -q "papa-razvedka@$u.service"; then echo "Разведка занята ($u) — повторить через 5 мин"; echo "== PURGE_BUSY"; exit 0; fi
done
set -a; . /etc/papa-razvedka/telegram.env; set +a
export PYTHONUNBUFFERED=1
( cd /opt/papa/modules/razvedka && runuser -u papa-razvedka -- $PY -m razvedka purge-raw ) | tail -n 80
echo "== PURGE_DONE"
