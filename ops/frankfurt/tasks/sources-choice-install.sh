#!/usr/bin/env bash
# 📡 26.10 владелец: «система предлагает — я выбираю». Карточки выбора источников в PAPA ШТАБ.
# Делает папку /var/lib/papa-sources-choice (пишет genplan по кнопке «✅ Утверждаю», читает куратор Разведки),
# разрешает GENPLAN писать туда (drop-in systemd), перезапускает GENPLAN с новым кодом и запускает отбор заново.
# В каналы ничего не публикует. Откат: rm /etc/systemd/system/papa-genplan.service.d/sources-choice.conf;
# systemctl daemon-reload; systemctl restart papa-genplan (куратор без choice.json работает по папкам каналов).
set -Eeuo pipefail
D=/var/lib/papa-sources-choice
PY=/opt/papa-venv/razvedka/bin/python
( cd /opt/papa/modules/genplan && $PY -m unittest -q tests.test_sources_choice 2>&1 | tail -1 )
( cd /opt/papa/modules/razvedka && $PY -m unittest -q tests.test_sources 2>&1 | tail -1 )
install -d -m 2750 -o papa-genplan -g papa-razvedka "$D"
mkdir -p /etc/systemd/system/papa-genplan.service.d
cat > /etc/systemd/system/papa-genplan.service.d/sources-choice.conf <<EOF
[Service]
ReadWritePaths=$D
EOF
systemctl daemon-reload
systemctl restart papa-genplan
sleep 5
echo "genplan: $(systemctl is-active papa-genplan)"
systemctl is-active -q papa-genplan || { journalctl -u papa-genplan -n 30 --no-pager -o cat; exit 1; }
# отбор заново (прежний прогон старым кодом — остановить); карточки уйдут в ШТАБ, когда прочитает папки
systemctl stop papa-razvedka@sources.service 2>/dev/null || true
rm -f /var/lib/papa-razvedka-pub/sources/sent_week
for u in collect run curate hunt pain; do
  if systemctl is-active -q "papa-razvedka@$u.service"; then echo "Разведка занята ($u) — отбор запустит понедельничный/ежедневный прогон"; echo "== SOURCES_CHOICE_DONE"; exit 0; fi
done
systemctl start --no-block papa-razvedka@sources.service
echo "Отбор запущен — карточки выбора придут в PAPA ШТАБ (30–90 мин)."
echo "== SOURCES_CHOICE_DONE"
