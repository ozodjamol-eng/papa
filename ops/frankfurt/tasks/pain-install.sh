#!/usr/bin/env bash
# 💡 «Боль аудитории», этап А: тесты → служба и таймер (раз в день 10:00 Ташкент) → первый сбор комментариев.
# Только чтение каналов, без ИИ и без расходов. Откат: systemctl disable --now papa-pain.timer
set -Eeuo pipefail
PY=/opt/papa-venv/razvedka/bin/python
echo "1/3 тесты:"
( cd /opt/papa/modules/razvedka && $PY -m unittest discover -q -s tests 2>&1 | tail -1 )
echo "2/3 служба и таймер:"
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-razvedka@.service /opt/papa/ops/frankfurt/systemd/papa-pain.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable -q --now papa-pain.timer
echo "  таймер: $(systemctl list-timers papa-pain.timer --no-pager --no-legend 2>/dev/null | cut -c1-40 || true)"
echo "3/3 первый сбор (2–8 минут):"
systemctl start --no-block papa-razvedka@pain.service; sleep 2
journalctl -u papa-razvedka@pain.service -f -n 0 -o cat & J=$!
while systemctl is-active -q papa-razvedka@pain.service || [[ "$(systemctl show -p ActiveState --value papa-razvedka@pain.service)" == activating ]]; do sleep 3; done
sleep 1; kill $J 2>/dev/null || true
echo "результат: $(systemctl show -p Result --value papa-razvedka@pain.service)"
echo "== PAIN_INSTALL_DONE"
