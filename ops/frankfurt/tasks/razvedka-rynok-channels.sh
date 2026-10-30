#!/usr/bin/env bash
# 🔎 30.10: найти каналы «PAPA РАЗВЕДКА · ВОДА» и «PAPA РАЗВЕДКА · МЕБЕЛЬ» (по названию среди чатов профиля Разведки),
# записать их id в /etc/papa-genplan/razvedka-rynok.env и отправить в каждый проверочное сообщение ботом PAPA ШТАБ.
# Каналы аудитории не трогает. Откат: rm /etc/papa-genplan/razvedka-rynok.env (отчёты снова пойдут в личку бота).
set -euo pipefail
PY=/opt/papa-venv/razvedka/bin/python
set -a; . /etc/papa-razvedka/telegram.env; set +a
OUT=$(cd /opt/papa/modules/razvedka && runuser -u papa-razvedka -- $PY -c '
import asyncio
from razvedka.telegram import client_from_env
async def m():
    c = client_from_env(); await c.connect()
    try:
        found = {}
        async for d in c.iter_dialogs():
            t = (d.title or "").lower()
            if d.is_channel and not d.is_group and "разведка" in t:
                if "вода" in t or "сув" in t: found["VODA"] = f"-100{d.entity.id}"
                if "мебел" in t: found["MEBEL"] = f"-100{d.entity.id}"
        for k, v in found.items(): print(f"RAZVEDKA_{k}_CHAT={v}")
    finally:
        await c.disconnect()
asyncio.run(m())')
echo "$OUT"
grep -q VODA <<<"$OUT" || echo "⚠️ канал «PAPA РАЗВЕДКА · ВОДА» не найден"
grep -q MEBEL <<<"$OUT" || echo "⚠️ канал «PAPA РАЗВЕДКА · МЕБЕЛЬ» не найден"
[[ -n "$OUT" ]] || exit 1
install -m 600 /dev/null /etc/papa-genplan/razvedka-rynok.env
echo "$OUT" > /etc/papa-genplan/razvedka-rynok.env
set -a; . /etc/papa-genplan/bots.env; . /etc/papa-genplan/razvedka-rynok.env; set +a
for k in VODA MEBEL; do
  v="RAZVEDKA_${k}_CHAT"; [[ -n "${!v:-}" ]] || continue
  python3 -I - "$SHTAB_BOT_TOKEN" "${!v}" "$k" <<'PY'
import json, sys, urllib.parse, urllib.request
t, chat, k = sys.argv[1:]
name = {"VODA": "💧 Вода (GOLD WATER)", "MEBEL": "🛋 Мебель (Shodiyona)"}[k]
d = urllib.parse.urlencode({"chat_id": chat, "text": f"✅ Канал подключён. Сюда приходят отчёты разведчика рынка: {name}."}).encode()
r = json.loads(urllib.request.urlopen(f"https://api.telegram.org/bot{t}/sendMessage", data=d, timeout=60).read())
print(k, "проверка:", "OK" if r.get("ok") else r)
PY
done
echo "== RAZVEDKA_RYNOK_CHANNELS_DONE"
