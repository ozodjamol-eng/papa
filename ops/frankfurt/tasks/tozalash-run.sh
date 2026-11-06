#!/usr/bin/env bash
# 🧹 06.11 Отдел Архив · Тозаловчи: внеочередной прогон архивариуса + чистка хабов KATTA BANK —
# «Хайрли тонг» / «Жума муборак» / «Хайрли тун» переносятся (копия → удаление оригинала) в хаб «ТАБРИКЛАР».
# В каналы ничего не публикует. Откат: посты лежат в «ТАБРИКЛАР», вернуть вручную; код — git revert.
set -euo pipefail
PY=/opt/papa-venv/razvedka/bin/python
( cd /opt/papa/modules/razvedka && $PY -m unittest -q tests.test_archive tests.test_tozalash 2>&1 | tail -1 )
for u in collect run curate hunt pain sources insta archive muhim; do
  if systemctl is-active -q "papa-razvedka@$u.service"; then echo "Разведка занята ($u) — Тозаловчи пройдёт с архивариусом по таймеру"; echo "== TOZALASH_BUSY"; exit 0; fi
done
systemctl start papa-razvedka@archive.service || true
journalctl -u papa-razvedka@archive.service --since "-60 min" -o cat --no-pager | grep -E "🧹|ARCHIVE_DONE|Тозаловчи" | tail -n 60
echo "== TOZALASH_DONE"
