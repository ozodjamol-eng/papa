#!/usr/bin/env bash
# 🩺 Отчёт аудита → «PAPA ОТЧЁТЫ» (владелец 19.10). Узнаёт id канала (профилем Разведки), сохраняет в /etc/papa-reports.env,
# обновляет службы аудита и делает аудит сейчас — отчёт придёт в «PAPA ОТЧЁТЫ». Секретов не печатает. Откат: rm /etc/papa-reports.env
set -Eeuo pipefail
A=/opt/papa/ops/frankfurt/audit
PY=/opt/papa-venv/razvedka/bin/python
out=$($PY -I "$A/test_audit.py" 2>&1) || { echo "$out" | tail -15; echo "ТЕСТЫ НЕ ПРОШЛИ"; exit 1; }
echo "тесты аудита: $(echo "$out" | tail -1)"
set -a; . /etc/papa-razvedka/telegram.env; [ -f /etc/papa-test/bot.env ] && . /etc/papa-test/bot.env; set +a
ID=$(cd /opt/papa/modules/razvedka && runuser -u papa-razvedka -- $PY -c '
import asyncio
from razvedka.telegram import client_from_env, reports_channel_id
async def m():
    c = client_from_env(); await c.connect()
    try:
        print(await reports_channel_id(c) or "")
    finally:
        await c.disconnect()
asyncio.run(m())' | tail -1)
[[ "$ID" =~ ^-100[0-9]+$ ]] || { echo "❌ канал «PAPA ОТЧЁТЫ» не найден у профиля Разведки"; exit 1; }
umask 077; printf 'PAPA_REPORTS_CHANNEL_ID=%s\n' "$ID" > /etc/papa-reports.env; chmod 0644 /etc/papa-reports.env
echo "канал «PAPA ОТЧЁТЫ»: найден"
sed -i 's/отчёт в КАТТА ДАВРА Пульт/отчёт в «PAPA ОТЧЁТЫ» (срочное — ещё и в пульт)/' "$A/papa-audit@.service" 2>/dev/null || true
install -m 644 "$A/papa-audit@.service" /etc/systemd/system/; systemctl daemon-reload
echo "аудит сейчас (1–3 минуты):"
systemctl start papa-audit@full.service || true
journalctl -u papa-audit@full.service -n 3 --no-pager -o cat | grep -E "отправлено|Проблем" || true
echo "== AUDIT_REPORTS_DONE"
