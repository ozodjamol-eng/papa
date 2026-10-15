"""PAPA HUB: владелец пересылает пост в закрытый канал-хаб → бот спрашивает канал и рубрику (2 нажатия).
Кнопки: канал (Хўжаобод / PaparazziUZ / оба) → рубрика → в очередь; «🆘 Срочно» — сразу; «🗑» — убрать.
Интерфейс владельца — по-русски (как в GENPLAN 5)."""
from __future__ import annotations

from . import store

NAMES = {"xojaobod": "📍 Хўжаобод", "paparazzi": "⭐ PaparazziUZ"}
CODE = {"x": "xojaobod", "p": "paparazzi"}
MEDIA_KEYS = ("photo", "video", "animation", "document", "audio", "voice", "video_note")


def rubrics(cfg: dict, channel: str) -> list[str]:
    out: list[str] = []
    for s in cfg["channels"][channel]["slots"]:
        if s["kind"] in ("content", "music"):
            for r in [s.get("rubric")] + list(s.get("fallback", [])):
                if r and r not in out:
                    out.append(r)
    return out


def kb_channel(mid: int) -> dict:
    return {"inline_keyboard": [
        [{"text": NAMES["xojaobod"], "callback_data": f"ch:{mid}:x"},
         {"text": NAMES["paparazzi"], "callback_data": f"ch:{mid}:p"}],
        [{"text": "🔁 В оба канала", "callback_data": f"ch:{mid}:b"},
         {"text": "🗑 Убрать", "callback_data": f"del:{mid}"}]]}


def kb_rubric(cfg: dict, mid: int, channel: str) -> dict:
    rs = rubrics(cfg, channel)
    rows = [[{"text": r, "callback_data": f"rb:{mid}:{i}"} for i, r in enumerate(rs)][k:k + 2] for k in range(0, len(rs), 2)]
    rows.append([{"text": "🆘 Срочно, сейчас", "callback_data": f"ur:{mid}"},
                 {"text": "🗑 Убрать", "callback_data": f"del:{mid}"}])
    return {"inline_keyboard": rows}


def preview(text: str, has_media: bool) -> str:
    t = (text or "").strip()
    t = (t[:280] + "…") if len(t) > 280 else t
    return f"📥 Новый материал{' 🖼' if has_media else ''}\n\n{t or '(без текста)'}"


def handle(bot, db, cfg: dict, env: dict, upd: dict) -> str | None:
    owners = {int(x) for x in str(env.get("OWNER_IDS", "")).split(",") if x.strip()}
    hub = int(env["HUB_CHAT_ID"])
    post = upd.get("channel_post")
    if post and int(post["chat"]["id"]) == hub:
        mid = store.add_material(db, hub, post["message_id"], post.get("text") or post.get("caption") or "",
                                 any(k in post for k in MEDIA_KEYS))
        if mid is None:
            return "dup"
        for o in owners:
            r = bot("sendMessage", chat_id=o, text=preview(post.get("text") or post.get("caption") or "",
                                                            any(k in post for k in MEDIA_KEYS)),
                    reply_markup=kb_channel(mid), disable_web_page_preview=True)
            store.update(db, mid, owner_msg=r["message_id"])
        return "material"

    cq = upd.get("callback_query")
    if cq:
        if int(cq["from"]["id"]) not in owners:
            bot("answerCallbackQuery", callback_query_id=cq["id"], text="Нет доступа")
            return "denied"
        chat, msg_id = cq["message"]["chat"]["id"], cq["message"]["message_id"]
        kind, mid_s, *arg = cq["data"].split(":")
        mid = int(mid_s)
        m = store.get(db, mid)
        if m is None:
            bot("answerCallbackQuery", callback_query_id=cq["id"], text="Материал не найден")
            return "missing"

        def edit(text, markup=None):
            p = {"chat_id": chat, "message_id": msg_id, "text": text, "disable_web_page_preview": True}
            if markup:
                p["reply_markup"] = markup
            bot("editMessageText", **p)

        base = preview(m["text"], bool(m["has_media"]))
        if kind == "ch":
            if arg[0] == "b":
                store.update(db, mid, channel="xojaobod")
                store.clone_for(db, mid, "paparazzi")
                edit(f"{base}\n\n→ {NAMES['xojaobod']}: выберите рубрику", kb_rubric(cfg, mid, "xojaobod"))
            else:
                ch = CODE[arg[0]]
                store.update(db, mid, channel=ch)
                edit(f"{base}\n\n→ {NAMES[ch]}: выберите рубрику", kb_rubric(cfg, mid, ch))
        elif kind == "rb":
            r = rubrics(cfg, m["channel"])[int(arg[0])]
            store.update(db, mid, rubric=r, status="queued")
            sib = db.execute("SELECT id, channel FROM materials WHERE hub_chat=? AND hub_msg=? AND id<>? AND rubric IS NULL "
                             "AND status='draft'", (m["hub_chat"], m["hub_msg"], mid)).fetchone()
            if sib:
                edit(f"{base}\n\n✅ {NAMES[m['channel']]} · {r}\n→ {NAMES[sib['channel']]}: выберите рубрику",
                     kb_rubric(cfg, sib["id"], sib["channel"]))
            else:
                done = db.execute("SELECT channel, rubric FROM materials WHERE hub_chat=? AND hub_msg=? AND status='queued'",
                                  (m["hub_chat"], m["hub_msg"])).fetchall()
                edit(base + "\n\n" + "\n".join(f"✅ {NAMES[d['channel']]} · {d['rubric']} — в очереди" for d in done))
        elif kind == "ur":
            store.update(db, mid, urgent=1, status="queued", rubric=m["rubric"] or "Срочно")
            edit(f"{base}\n\n🆘 {NAMES[m['channel']]} — публикуется сейчас")
        elif kind == "del":
            db.execute("UPDATE materials SET status='rejected' WHERE hub_chat=? AND hub_msg=? AND status IN ('draft','queued')",
                       (m["hub_chat"], m["hub_msg"]))
            db.commit()
            edit(f"{base}\n\n🗑 Убрано")
        bot("answerCallbackQuery", callback_query_id=cq["id"])
        return kind

    msg = upd.get("message")
    if msg and int(msg["from"]["id"]) in owners:
        return "cmd:" + (msg.get("text") or "").split()[0] if msg.get("text") else None
    return None
