#!/usr/bin/env bash
# 📢 Канал «PAPA ОТЧЁТЫ» (17.10): обновить службу Разведки (токен бота из /etc/papa-test/bot.env) и отправить
# одно тестовое сообщение ботом в канал. Ничего не публикует в каналы аудитории. Откат не нужен.
set -euo pipefail
PY=/opt/papa-venv/razvedka/bin/python
( cd /opt/papa/modules/razvedka && $PY -m unittest discover -q -s tests 2>&1 | tail -1 )
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-razvedka@.service /etc/systemd/system/
systemctl daemon-reload
set -a; . /etc/papa-razvedka/telegram.env; . /etc/papa-test/bot.env; set +a
cd /opt/papa/modules/razvedka && runuser -u papa-razvedka -- $PY -c '
import asyncio
from razvedka.telegram import client_from_env, reports_channel_id, send_report
async def m():
    c = client_from_env(); await c.connect()
    try:
        print("канал:", await reports_channel_id(c))
        print("отправлено:", await send_report(c, "✅ PAPA ОТЧЁТЫ подключён. Сюда приходят все отчёты: Разведка, досье, 🎬 Тренды дня (09:00), 🕵️ Рынок AI-видео (понедельник)."))
    finally:
        await c.disconnect()
asyncio.run(m())'
echo "== REPORTS_CHANNEL_DONE"
