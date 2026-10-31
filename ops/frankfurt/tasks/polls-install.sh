#!/usr/bin/env bash
# 🗳 Опросы (31.10): таймер вт/чт/сб 19:00 Ташкент → готовый пост владельцу в PAPA ШТАБ. Ничего не публикует в каналы сам.
# Откат: systemctl disable --now papa-polls.timer
set -Eeuo pipefail
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-polls.service /opt/papa/ops/frankfurt/systemd/papa-polls.timer /etc/systemd/system/
chmod +x /opt/papa/ops/frankfurt/polls-send.sh
systemctl daemon-reload
systemctl enable -q --now papa-polls.timer
systemctl list-timers papa-polls.timer --no-pager --no-legend | cut -c1-60
ls /opt/papa/ops/frankfurt/polls/
echo "== POLLS_INSTALL_DONE"
