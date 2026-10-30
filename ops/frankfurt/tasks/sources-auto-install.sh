#!/usr/bin/env bash
# ⭐ 30.10 владелец: «кнопка не нужна» — Разведка сама включает ⭐ источники в choice.json, владелец только убирает лишнее.
# Права: Разведка пишет в /var/lib/papa-sources-choice; GENPLAN читает файлы группы papa-razvedka.
# Откат: chmod 2750 /var/lib/papa-sources-choice; rm /etc/systemd/system/papa-razvedka@.service.d/choice.conf; daemon-reload.
set -Eeuo pipefail
D=/var/lib/papa-sources-choice
PY=/opt/papa-venv/razvedka/bin/python
( cd /opt/papa/modules/razvedka && $PY -m unittest -q tests.test_sources 2>&1 | tail -1 )
install -d -m 2770 -o papa-genplan -g papa-razvedka "$D"
id -nG papa-genplan | grep -qw papa-razvedka || usermod -aG papa-razvedka papa-genplan
mkdir -p /etc/systemd/system/papa-razvedka@.service.d
printf '[Service]\nReadWritePaths=%s\n' "$D" > /etc/systemd/system/papa-razvedka@.service.d/choice.conf
systemctl daemon-reload
systemctl restart papa-genplan; sleep 5
echo "genplan: $(systemctl is-active papa-genplan) · группы: $(id -nG papa-genplan)"
systemctl stop papa-razvedka@sources.service 2>/dev/null || true
rm -f /var/lib/papa-razvedka-pub/sources/sent_week
for u in collect run curate hunt pain insta; do
  if systemctl is-active -q "papa-razvedka@$u.service"; then echo "Разведка занята ($u) — ⭐ включатся в ближайшем отборе"; echo "== SOURCES_AUTO_DONE"; exit 0; fi
done
systemctl start --no-block papa-razvedka@sources.service
echo "Отбор запущен: ⭐ включатся сами, карточки — в пульты (30–90 мин)."
echo "== SOURCES_AUTO_DONE"
