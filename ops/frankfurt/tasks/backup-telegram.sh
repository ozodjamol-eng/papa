#!/usr/bin/env bash
# 🗄 Копии баз в закрытый канал «PAPA РЕЗЕРВ» (18.10, владелец: «да»).
# Находит канал по названию (аккаунт Разведки должен в нём состоять, бот отчётов — админ), записывает его id,
# ставит новый backup.sh (3 копии на сервере + копия в Telegram) и сразу делает копию.
# Ключ шифрования в вывод не печатается. Откат: rm /etc/papa-backup.env (копии снова только на сервере).
set -Eeuo pipefail
PY=/opt/papa-venv/razvedka/bin/python
set -a; . /etc/papa-razvedka/telegram.env; set +a
id=$(cd /opt/papa/modules/razvedka && runuser -u papa-razvedka -- $PY -c '
import asyncio
from razvedka.telegram import client_from_env
async def m():
    c = client_from_env(); await c.connect()
    try:
        async for d in c.iter_dialogs():
            if d.is_channel and not d.is_group and "papa резерв" in (d.title or "").lower().replace("ë", "ё"):
                print(f"-100{d.entity.id}"); return
    finally:
        await c.disconnect()
asyncio.run(m())')
[[ -n "$id" ]] || { echo "NO_CHANNEL: канал «PAPA РЕЗЕРВ» не найден — добавьте в него аккаунт PAPA (@papa_admin_uz)"; exit 1; }
umask 077; echo "PAPA_BACKUP_CHAT_ID=$id" > /etc/papa-backup.env
echo "канал PAPA РЕЗЕРВ: $id"
L=/usr/local/lib/nexus-v2
cp -p "$L/backup.sh" "$L/backup.sh.prev" 2>/dev/null || true
install -m 755 /opt/papa/ops/frankfurt/backup.sh "$L/"
systemctl start nexus-v2-backup.service
journalctl -u nexus-v2-backup.service -n 20 -o cat --no-pager | grep -E "BACKUP_OK|TELEGRAM_|SKIP|integrity|FAIL" | tail -8
du -sh /var/backups/nexus-v2 | awk '{print "на сервере копий: " $1}'
echo "== BACKUP_TELEGRAM_DONE"
