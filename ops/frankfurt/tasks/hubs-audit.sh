#!/usr/bin/env bash
# 🔎 07.11 владелец: «в МОТИВАЦИИ 60% не то и много копий — что с другими хабами?» ТОЛЬКО ЧТЕНИЕ: по каждому хабу
# KATTA BANK — копии, без фото/видео, не по теме (Gemini, 1 запрос на хаб). Ничего не удаляет.
set -uo pipefail
for u in collect run curate hunt pain sources insta archive; do
  if systemctl is-active -q "papa-razvedka@$u.service"; then echo "Разведка занята ($u) — повторить через 5 мин"; echo "== HUBS_AUDIT_BUSY"; exit 0; fi
done
systemctl start papa-razvedka@hub-audit.service
journalctl -u papa-razvedka@hub-audit.service -n 40 --no-pager -o cat | grep -vE "^(Started|Finished|papa-razvedka)" | tail -n 25
echo "== HUBS_AUDIT_DONE"
