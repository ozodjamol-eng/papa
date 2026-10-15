"""Служба GENPLAN PAPA: раз в минуту — план дня по каждому каналу → публикация того, что пора.
Режим shadow (теневой): всё уходит в тестовые чаты (PAPA TEST GROUP / PAPA TEST), рабочие каналы не трогаются.
Якоря (намоз, дуо) и реклама пока остаются за GENPLAN 5 — здесь только контент из хаба."""
from __future__ import annotations

import datetime as dt

from . import plan, store, text
from .publish import PublishError


def to_materials(rows) -> list[plan.Material]:
    return [plan.Material(r["id"], r["rubric"], dt.datetime.fromisoformat(r["created_at"]), r["channel"], r["text"])
            for r in rows]


def channel_mode(cfg: dict, channel: str) -> str:
    """Режим канала: свой (channels.X.mode) важнее общего — каналы переводятся в работу по одному."""
    return cfg["channels"][channel].get("mode") or cfg.get("mode", "shadow")


def target(cfg: dict, env: dict, channel: str) -> str | int:
    if channel_mode(cfg, channel) == "live":
        return "@" + cfg["channels"][channel]["username"]
    return int(env["TEST_GROUP_ID"]) if cfg["channels"][channel]["publisher"] == "account" else int(env["TEST_CHANNEL_ID"])


def share_button(ch: dict) -> dict | None:
    """Кнопка под постом «Дўстларга улашиш» — подписчик одним нажатием отправляет канал друзьям (рост)."""
    if not ch.get("share_button"):
        return None
    from urllib.parse import quote
    url = f"https://t.me/{ch['username']}"
    return {"text": ch["share_button"], "url": f"https://t.me/share/url?url={quote(url)}&text={quote(ch.get('share_text', ''))}"}


async def publish_one(db, cfg, env, pubs, channel: str, m, slot: str | None, day: str, log=print) -> bool:
    ch = cfg["channels"][channel]
    own = (ch["username"],) + tuple(c["username"] for c in cfg["channels"].values())
    body = text.finalize(m["text"], ch.get("signature", ""), own=own, hook=text.pick_hook(ch, m["rubric"], int(m["id"])),
                         limit=1024 if m["has_media"] else 4096)
    p = pubs[ch["publisher"]]
    try:
        if ch["publisher"] == "account":
            mid = await p.publish(target(cfg, env, channel), body, m["hub_chat"], m["hub_msg"], bool(m["has_media"]))
        else:
            mid = p.publish(target(cfg, env, channel), body, m["hub_chat"], m["hub_msg"], bool(m["has_media"]),
                            button=share_button(ch))
        store.update(db, m["id"], status="published")
        store.record(db, channel, day, slot, m["id"], "done", mid)
        log(f"{channel} {slot or 'срочно'}: опубликовано ({m['rubric']})")
        return True
    except PublishError as e:
        store.record(db, channel, day, slot, m["id"], "failed", error=str(e))
        log(f"{channel} {slot or 'срочно'}: ОШИБКА {e}")
        return False


async def tick(db, cfg: dict, env: dict, pubs: dict, now: dt.datetime | None = None, log=print) -> dict:
    now = (now or dt.datetime.now(plan.TZ)).astimezone(plan.TZ)
    day = now.date().isoformat()
    out = {"published": 0, "failed": 0}
    for channel in cfg["channels"]:
        for m in db.execute("SELECT * FROM materials WHERE status='queued' AND urgent=1 AND channel=?", (channel,)).fetchall():
            ok = await publish_one(db, cfg, env, pubs, channel, m, None, day, log)
            out["published" if ok else "failed"] += 1
            if not ok:
                store.update(db, m["id"], status="failed")
        entries = plan.build(channel, cfg["channels"][channel], now.date(), to_materials(store.queued(db, channel)),
                             ads={}, published=store.published_today(db, channel, day), now=now)
        for e in plan.due(entries, now):
            if e.material_id is None:      # якорь/реклама — пока за GENPLAN 5
                continue
            m = store.get(db, e.material_id)
            ok = await publish_one(db, cfg, env, pubs, channel, m, e.at.strftime("%H:%M"), day, log)
            out["published" if ok else "failed"] += 1
    return out


def today_text(db, cfg: dict, now: dt.datetime | None = None) -> str:
    now = (now or dt.datetime.now(plan.TZ)).astimezone(plan.TZ)
    day = now.date().isoformat()
    parts = []
    for channel, ch in cfg["channels"].items():
        entries = plan.build(channel, ch, now.date(), to_materials(store.queued(db, channel)), ads={},
                             published=store.published_today(db, channel, day), now=now)
        parts.append(plan.render(ch["title"], entries))
    modes = ", ".join(f"{ch['title']}: {'🟢 работа' if channel_mode(cfg, c) == 'live' else '🧪 тест'}"
                      for c, ch in cfg["channels"].items())
    return f"Режим — {modes}\n(🧪 тест — публикации идут в тестовые чаты)\n\n" + "\n\n".join(parts)
