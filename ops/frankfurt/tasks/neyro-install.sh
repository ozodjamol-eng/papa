#!/usr/bin/env bash
# 📡 Нейроновинки (владелец 01.11: «каждый день идут новости… очень актуально для нас»): таймер каждый день 13:30 Ташкент
# + первый выпуск сейчас. Аккаунт Разведки только читает папку «Нейросеть» (каналы, без групп). Расход $0 (бесплатный Gemini).
# Откат: systemctl disable --now papa-neyro.timer
set -Eeuo pipefail
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-razvedka@.service /opt/papa/ops/frankfurt/systemd/papa-neyro.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable -q --now papa-neyro.timer
echo "таймер: $(systemctl list-timers papa-neyro.timer --no-pager --no-legend 2>/dev/null | cut -c1-40 || true)"
echo "первый выпуск (1–3 минуты):"
U=papa-razvedka@neyro-auto.service
systemctl start --no-block "$U"; sleep 2
journalctl -u "$U" -f -n 0 -o cat & J=$!
while systemctl is-active -q "$U" || [[ "$(systemctl show -p ActiveState --value "$U")" == activating ]]; do sleep 3; done
sleep 1; kill $J 2>/dev/null || true
echo "результат: $(systemctl show -p Result --value "$U")"
echo "== NEYRO_INSTALL_DONE"
