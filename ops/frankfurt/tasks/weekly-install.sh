#!/usr/bin/env bash
# 🧹 31.10 план выходных: каждое воскресенье 04:30 — мёртвые/закрытые/«с лого» источники убираются сами,
# разведчик приколов подключает новые чистые. Первый прогон — сразу. Откат: systemctl disable --now papa-weekly.timer
set -Eeuo pipefail
PY=/opt/papa-venv/razvedka/bin/python
( cd /opt/papa/modules/razvedka && $PY -m unittest -q tests.test_clean tests.test_scout 2>&1 | tail -1 )
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-weekly.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable -q --now papa-weekly.timer
echo "таймер: $(systemctl list-timers papa-weekly.timer --no-legend | awk '{print $1, $2, $3}')"
for u in collect run curate hunt pain sources insta archive; do
  if systemctl is-active -q "papa-razvedka@$u.service"; then echo "Разведка занята ($u) — первый прогон в воскресенье"; echo "== WEEKLY_INSTALL_DONE"; exit 0; fi
done
systemctl start papa-razvedka@weekly.service || true
journalctl -u papa-razvedka@weekly.service --since "-40 min" -o cat --no-pager | tail -n 50
echo "== WEEKLY_INSTALL_DONE"
