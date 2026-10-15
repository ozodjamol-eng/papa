"""PAPA HUB: владелец пересылает пост прямо боту (или в закрытый канал-хаб) → бот спрашивает канал и рубрику (2 нажатия).
Кнопки: канал (Хўжаобод / PaparazziUZ / оба) → рубрика → в очередь; «🆘 Срочно» — сразу; «🗑» — убрать.
Интерфейс владельца — по-русски (как в GENPLAN 5)."""
from __future__ import annotations

from . import store

NAMES = {"davra": "🎉 КАТТА ДАВРА", "paparazzi": "⭐ PaparazziUZ", "xojaobod": "📍 Хўжаобод"}
CODE = {"d": "davra", "p": "paparazzi", "x": "xojaobod"}
BOTH = ("davra", "paparazzi")   # «в оба»: главный канал + PaparazziUZ
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
        [{"text": NAMES["davra"], "callback_data": f"ch:{mid}:d"},
         {"text": NAMES["paparazzi"], "callback_data": f"ch:{mid}:p"}],
        [{"text": NAMES["xojaobod"], "callback_data": f"ch:{mid}:x"},
         {"text": "🔁 Давра + Paparazzi", "callback_data": f"ch:{mid}:b"}],
        [{"text": "🗑 Убрать", "callback_data": f"del:{mid}"}]]}


def next_free_rubric(cfg: dict, db, channel: str) -> str:
    """Рубрика ближайшего свободного слота канала (кнопка «⏰ Ближайший слот»)."""
    import datetime as dt
    from . import plan, service
    now = dt.datetime.now(plan.TZ)
    e = plan.build(channel, cfg["channels"][channel], now.date(), service.to_materials(store.queued(db, channel)), ads={},
                   published=store.published_today(db, channel, now.date().isoformat()), now=now)
    nxt = next((x for x in e if x.status == plan.EMPTY and x.kind == "content" and x.at > now), None)
    return nxt.rubric if nxt else rubrics(cfg, channel)[0]


def kb_rubric(cfg: dict, mid: int, channel: str) -> dict:
    rs = rubrics(cfg, channel)
    rows = [[{"text": "⏰ Ближайший слот", "callback_data": f"nx:{mid}"}]] + [[{"text": r, "callback_data": f"rb:{mid}:{i}"} for i, r in enumerate(rs)][k:k + 2] for k in range(0, len(rs), 2)]
    rows.append([{"text": "🆘 Срочно, сейчас", "callback_data": f"ur:{mid}"},
                 {"text": "🗑 Убрать", "callback_data": f"del:{mid}"}])
    return {"inline_keyboard": rows}


def preview(text: str, has_media: bool) -> str:
    from . import translit
    t, conv = translit.auto((text or "").strip())
    t = (t[:280] + "…") if len(t) > 280 else t
    notes = [n for n in (("🔤 Латиница → кириллица (автоматически)" if conv else ""), translit.language_note(text)) if n]
    note = ("\n\n" + "\n".join(notes)) if notes else ""
    return f"📥 Новый материал{' 🖼' if has_media else ''}\n\n{t or '(без текста)'}{note}"


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
                store.update(db, mid, channel=BOTH[0])
                store.clone_for(db, mid, BOTH[1])
                edit(f"{base}\n\n→ {NAMES[BOTH[0]]}: выберите рубрику", kb_rubric(cfg, mid, BOTH[0]))
            else:
                ch = CODE[arg[0]]
                store.update(db, mid, channel=ch)
                edit(f"{base}\n\n→ {NAMES[ch]}: выберите рубрику", kb_rubric(cfg, mid, ch))
        elif kind in ("rb", "nx"):
            r = rubrics(cfg, m["channel"])[int(arg[0])] if kind == "rb" else next_free_rubric(cfg, db, m["channel"])
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
    if msg and int(msg["from"]["id"]) in owners and msg["chat"].get("type") == "private":
        from .menu import BY_BUTTON, B_ALL, B_QUEUE, B_TODAY, B_HELP
        txt = (msg.get("text") or "").strip()
        if txt.startswith("/") or txt in BY_BUTTON or txt in (B_ALL, B_QUEUE, B_TODAY, B_HELP):
            return "cmd:" + txt.split()[0]
        return direct(bot, db, hub, msg)
    return None


def direct(bot, db, hub: int, msg: dict) -> str:
    """Пост прямо в чат с ботом (как в боте Хўжаобода): копия уходит в PAPA HUB (архив и источник для публикации),
    владельцу — те же кнопки ответом на его сообщение."""
    has_media = any(k in msg for k in MEDIA_KEYS)
    txt = msg.get("text") or msg.get("caption") or ""
    if not has_media and not txt.strip():
        return "skip"
    r = bot("copyMessage", chat_id=hub, from_chat_id=msg["chat"]["id"], message_id=msg["message_id"])
    mid = store.add_material(db, hub, r["message_id"], txt, has_media)
    if mid is None:
        return "dup"
    sent = bot("sendMessage", chat_id=msg["chat"]["id"], text=preview(txt, has_media), reply_markup=kb_channel(mid),
               reply_to_message_id=msg["message_id"], disable_web_page_preview=True)
    store.update(db, mid, owner_msg=sent["message_id"])
    return "material"
