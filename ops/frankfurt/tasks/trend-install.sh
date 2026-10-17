#!/usr/bin/env bash
# 🎬 Тренд-разведка (решение 17.10): тесты → таймер (каждый день 09:00 Ташкент) → первый отчёт сейчас в PAPA TEST GROUP.
# Только веб-поиск через Anthropic (ключ уже есть: /etc/papa-genplan/ai.env) и одно сообщение в группу. Каналы не трогает.
# Расход: ~ $3–5 в месяц. Откат: systemctl disable --now papa-trend.timer
set -Eeuo pipefail
PY=/opt/papa-venv/razvedka/bin/python
echo "1/3 тесты:"
( cd /opt/papa/modules/razvedka && $PY -m unittest discover -q -s tests 2>&1 | tail -1 )
grep -q '^ANTHROPIC_API_KEY=' /etc/papa-genplan/ai.env || { echo "NO_AI_KEY: сначала задача genplan-ai-key"; exit 1; }
echo "2/3 таймер:"
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-razvedka@.service /opt/papa/ops/frankfurt/systemd/papa-trend.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable -q --now papa-trend.timer
echo "  таймер: $(systemctl list-timers papa-trend.timer --no-pager --no-legend 2>/dev/null | cut -c1-40 || true)"
echo "3/3 первый отчёт (тренды дня + обзор рынка, 2–6 минут):"
U=papa-razvedka@trend-now.service
systemctl start --no-block "$U"; sleep 2
journalctl -u "$U" -f -n 0 -o cat & J=$!
while systemctl is-active -q "$U" || [[ "$(systemctl show -p ActiveState --value "$U")" == activating ]]; do sleep 3; done
sleep 1; kill $J 2>/dev/null || true
echo "результат: $(systemctl show -p Result --value "$U")"
echo "== TREND_INSTALL_DONE"
