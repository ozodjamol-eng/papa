"""Переход Хўжаобода на PAPA (решение владельца 20.10). Данные — ops/frankfurt/xojaobod-handover.json (из GENPLAN 5).
1) тестовые остатки Хўжаобода в очереди PAPA (режим теста) — убрать, чтобы не хлынули в настоящую группу;
2) рекламные пакеты (оставшиеся дни) — из уже опубликованных в группе рекламных постов (медиа + текст берёт аккаунт PAPA);
3) 🌙 Якуний пост — из сегодняшнего поста GENPLAN 5 в группе (видео муфтия);
4) флаг Куратора для Хўжаобода.
Копия базы делается задачей до запуска. Ничего не публикует."""
import asyncio
import datetime as dt
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, "/opt/papa/modules/genplan")
from telethon import TelegramClient  # noqa: E402
from telethon.sessions import StringSession  # noqa: E402

from genplan import extras, plan, store  # noqa: E402

H = json.loads(Path("/opt/papa/ops/frankfurt/xojaobod-handover.json").read_text(encoding="utf-8"))
PUB = dict(l.split("=", 1) for l in Path("/etc/papa-tg/publisher.env").read_text().splitlines() if "=" in l)
DB = "/var/lib/papa-genplan/genplan.sqlite3"


async def captions(ids_by_key: dict) -> dict:
    acc = TelegramClient(StringSession(PUB["PAPA_TG_SESSION"]), int(PUB["PAPA_TG_API_ID"]), PUB["PAPA_TG_API_HASH"])
    await acc.connect()
    out = {}
    try:
        for k, ids in ids_by_key.items():
            msgs = [m for m in await acc.get_messages(H["group_id"], ids=ids) if m]
            if msgs and msgs[0].grouped_id:                 # альбом — берём все его сообщения
                around = [m for m in await acc.get_messages(H["group_id"], ids=list(range(ids[0] - 10, ids[0] + 11))) if m]
                msgs = sorted((m for m in around if m.grouped_id == msgs[0].grouped_id), key=lambda m: m.id)
                ids_by_key[k][:] = [m.id for m in msgs]
                print(f"{k}: альбом из {len(msgs)} — {ids_by_key[k]}")
            if not msgs or not any(m.media for m in msgs):
                raise SystemExit(f"❌ {k}: в группе нет медиа сообщений {ids}")
            out[k] = next((m.message for m in msgs if m.message), "") or ""
    finally:
        await acc.disconnect()
    return out


def main() -> None:
    keys = {**{a["name"]: a["ids"] for a in H["ads"]}, **({"final": H["final"]["ids"]} if H.get("final") else {})}
    caps = asyncio.run(captions(keys))        # альбомы расширяются на месте (ids в H)
    db = store.connect(DB)
    now = dt.datetime.now(plan.TZ)
    # 1) тестовые остатки
    left = db.execute("SELECT id, status, stock, substr(text,1,40) t FROM materials WHERE channel='xojaobod' "
                      "AND status IN ('queued','draft')").fetchall()
    for r in left:
        store.update(db, r["id"], status="rejected")
    print(f"тестовые остатки Хўжаобода убраны: {len(left)}")
    # 2) реклама
    for a in H["ads"]:
        if int(a["days_left"]) <= 0:
            continue
        ids = a["ids"]
        mid = store.add_material(db, H["group_id"], ids[0], caps[a["name"]], True, hub_msgs=ids)
        if mid is None:
            mid = db.execute("SELECT id FROM materials WHERE hub_chat=? AND hub_msg=?", (H["group_id"], ids[0])).fetchone()[0]
        at = plan.slot_time(now.date(), a["at"])          # сегодня, если время ещё впереди, иначе завтра
        if at <= now + dt.timedelta(minutes=5):
            at = plan.slot_time(now.date() + dt.timedelta(days=1), a["at"])
        store.update(db, mid, channel="xojaobod", rubric="Реклама", status="queued", scheduled_at=at.isoformat(),
                     locked=1, guessed=0, via="xojaobod")
        c = extras.campaign_from(db, store.get(db, mid), int(a["days_left"]), name=a["name"])
        print(f"📣 {a['name']}: {extras.campaign_note(c)}")
    # 3) Якуний пост
    if H.get("final"):
        f = H["final"]
        v = {"material_id": 0, "text": caps["final"], "hub_chat": H["group_id"], "hub_msg": f["ids"][0], "hub_msgs": f["ids"],
             "has_media": True, "set_at": now.isoformat()}
        store.kv_set(db, "final_xojaobod", json.dumps(v, ensure_ascii=False))
        print(f"🌙 Якуний пост: «{caps['final'][:50]}…» — каждый день 22:00")
    db.commit()
    print("== XOJAOBOD_GOLIVE_DATA_DONE")


main()
