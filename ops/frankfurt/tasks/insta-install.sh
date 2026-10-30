#!/usr/bin/env bash
# 📸 Агент Instagram-трендов (30.10): ключ Apify → в службу Разведки, таймер 10:20 каждый день, первый прогон сейчас.
# Видео приходят карточками в пульт КАТТА ДАВРА — решает владелец. Откат: systemctl disable --now papa-insta.timer
set -Eeuo pipefail
PY=/opt/papa-venv/razvedka/bin/python
( cd /opt/papa/modules/razvedka && $PY -m unittest -q tests.test_insta 2>&1 | tail -1 )
[[ -s /etc/papa-razvedka/apify.env ]] || { echo "NO_APIFY: сначала papa-update apify-token"; exit 1; }
mkdir -p /etc/systemd/system/papa-razvedka@.service.d
printf '[Service]\nEnvironmentFile=-/etc/papa-razvedka/apify.env\n' > /etc/systemd/system/papa-razvedka@.service.d/apify.conf
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-insta.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable -q --now papa-insta.timer
echo "таймер: $(systemctl list-timers papa-insta.timer --no-pager --no-legend 2>/dev/null | cut -c1-40 || true)"
for u in collect run curate hunt pain sources; do
  if systemctl is-active -q "papa-razvedka@$u.service"; then echo "Разведка занята ($u) — первый прогон будет по таймеру"; echo "== INSTA_INSTALL_DONE"; exit 0; fi
done
systemctl start papa-razvedka@insta.service || true
journalctl -u papa-razvedka@insta.service -n 30 -o cat --no-pager | tail -n 20
echo "== INSTA_INSTALL_DONE"
