#!/usr/bin/env bash
# 📡 Нейроновинки (владелец 01.11: «каждый день идут новости… очень актуально для нас»): таймер каждый день 13:30 Ташкент
# (первый выпуск — по таймеру). Аккаунт Разведки только читает папку «Нейросеть» (каналы, без групп). Расход $0 (бесплатный Gemini).
# Откат: systemctl disable --now papa-neyro.timer
set -Eeuo pipefail
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-razvedka@.service /opt/papa/ops/frankfurt/systemd/papa-neyro.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable -q --now papa-neyro.timer
echo "таймер: $(systemctl list-timers papa-neyro.timer --no-pager --no-legend 2>/dev/null | cut -c1-40 || true)"
echo "первый выпуск — по таймеру сегодня в 13:30 Ташкент (до обнуления лимита Gemini разбор не выйдет). Внеочередной: systemctl start papa-razvedka@neyro-auto.service"
echo "== NEYRO_INSTALL_DONE"
