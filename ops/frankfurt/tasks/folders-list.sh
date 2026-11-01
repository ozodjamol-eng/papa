#!/usr/bin/env bash
# 📂 Только чтение: какие папки Telegram видит аккаунт Разведки и сколько в них каналов/групп (01.11 — для обхода «Нейросеть»).
set -Eeuo pipefail
[[ -s /etc/papa-razvedka/telegram.env ]] || { echo "NO_LOGIN"; exit 1; }
set -a; . /etc/papa-razvedka/telegram.env; set +a
cd /opt/papa/modules/razvedka
/opt/papa-venv/razvedka/bin/python - <<'PY'
import asyncio
from razvedka.telegram import client_from_env
from razvedka.curate import folder_peers

async def main():
    c = client_from_env(); await c.connect()
    try:
        me = await c.get_me()
        print("аккаунт:", getattr(me, "first_name", ""), "@" + str(getattr(me, "username", "") or "—"))
        for name, peers in (await folder_peers(c)).items():
            ch = gr = 0
            for p in peers:
                try:
                    e = await c.get_entity(p)
                    if getattr(e, "broadcast", False): ch += 1
                    else: gr += 1
                except Exception:
                    gr += 1
            print(f"📂 {name}: каналов {ch}, групп/прочего {gr}")
    finally:
        await c.disconnect()
asyncio.run(main())
PY
echo "== FOLDERS_LIST_DONE"
