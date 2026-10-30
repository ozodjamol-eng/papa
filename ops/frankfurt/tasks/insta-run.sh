#!/usr/bin/env bash
# 📸 Прогон агента Instagram-трендов сейчас (как по таймеру). Только чтение Instagram (Apify) + посты в хаб разведки.
set -Eeuo pipefail
for u in collect run curate hunt pain sources; do
  if systemctl is-active -q "papa-razvedka@$u.service"; then echo "Разведка занята ($u) — повторите позже"; exit 0; fi
done
systemctl start papa-razvedka@insta.service || true
journalctl -u papa-razvedka@insta.service -n 30 -o cat --no-pager | tail -n 20
echo "== INSTA_RUN_DONE"
