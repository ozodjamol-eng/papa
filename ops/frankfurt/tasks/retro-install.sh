#!/usr/bin/env bash
# 📼 Ретро-разведчик YouTube (12.11): таймер 09:40 каждый день + первый прогон сейчас. Только поиск (Apify, подписка Starter)
# и ОДНО сообщение со ссылками в «БАНК · РЕТРО». Ничего не скачивает и не публикует.
# Откат: systemctl disable --now papa-retro.timer
set -Eeuo pipefail
PY=/opt/papa-venv/razvedka/bin/python
( cd /opt/papa/modules/razvedka && $PY -m unittest -q tests.test_retro 2>&1 | tail -1 )
[[ -s /etc/papa-razvedka/apify.env ]] || { echo "NO_APIFY: сначала papa-update apify-token"; exit 1; }
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-retro.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable -q --now papa-retro.timer
echo "таймер: $(systemctl list-timers papa-retro.timer --no-pager --no-legend 2>/dev/null | cut -c1-40 || true)"
for u in collect run curate hunt pain sources insta; do
  if systemctl is-active -q "papa-razvedka@$u.service"; then echo "Разведка занята ($u) — первый прогон будет по таймеру"; echo "== RETRO_INSTALL_DONE"; exit 0; fi
done
systemctl start papa-razvedka@retro.service || true
journalctl -u papa-razvedka@retro.service -n 30 -o cat --no-pager | tail -n 20
echo "== RETRO_INSTALL_DONE"
