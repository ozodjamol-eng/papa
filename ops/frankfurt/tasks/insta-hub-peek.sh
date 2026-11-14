#!/usr/bin/env bash
# 📸 ТОЛЬКО ЧТЕНИЕ (14.11 владелец: «изучи, что я там набрал — ты поймёшь меня»): последние посты «INSTAGRAM · ХАБ» —
# дата, вид, откуда, начало текста + сводка аккаунтов/хэштегов. Ничего не публикует и не удаляет.
set -uo pipefail
for u in collect run curate hunt pain sources insta archive; do
  if systemctl is-active -q "papa-razvedka@$u.service"; then echo "Разведка занята ($u) — повторить через 5 мин"; echo "== INSTA_HUB_PEEK_BUSY"; exit 0; fi
done
set -a; . /etc/papa-razvedka/telegram.env; set +a
/opt/papa-venv/razvedka/bin/python /opt/papa/ops/frankfurt/insta_hub_peek.py
