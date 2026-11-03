#!/usr/bin/env bash
# «🕌 Намоз маркази» (03.11), Лондон: таймер — каждые 15 мин берёт время намаза у PAPA и обновляет бот XOJAOBOD CITY 24
# (только если изменилось; копия базы перед записью). Откат: systemctl disable --now papa-namaz-pull.timer + city24-namaz-rollback
set -euo pipefail
install -m 644 /opt/papa/ops/london/runner/papa-namaz-pull.service /opt/papa/ops/london/runner/papa-namaz-pull.timer /etc/systemd/system/
systemctl daemon-reload
systemctl start papa-namaz-pull.service; journalctl -u papa-namaz-pull -n 3 -o cat --no-pager
systemctl enable -q --now papa-namaz-pull.timer
echo "таймер: $(systemctl is-active papa-namaz-pull.timer)"
cd /opt/xojaobodcity24bot/app && sudo -u xojaobodbot /opt/xojaobodcity24bot/venv/bin/python -c "
import os,datetime as dt;os.environ.setdefault('BOT_TOKEN','0:x');from bot.handlers import prayer as P
print('бот показывает сегодня:', P.confirmed_prayer_timings(dt.date.today()))"
echo "== NAMAZ_PULL_INSTALLED"
