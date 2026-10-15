"""Приём материалов владельца и карточка поста (по логике GENPLAN 5).

Владелец бросает пост прямо боту (или в канал PAPA HUB). Бот:
  1) кладёт копию в PAPA HUB (склад и источник публикации), альбом — целиком;
  2) сам выбирает канал (по умолчанию — главный) и угадывает рубрику по смыслу текста;
  3) показывает карточку: первая кнопка — «🧠 Умное время · ЧЧ:ММ» (одно нажатие), дальше — 🆘 Сейчас,
     🕐 Другое время, 📂 Рубрика, 📺 Канал, 🗑 Убрать;
  4) предупреждает о повторе (такой пост уже был / уже в очереди).
Интерфейс владельца — по-русски.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import time

from . import plan, smart, store

NAMES = {"davra": "🎉 КАТТА ДАВРА", "paparazzi": "⭐ PaparazziUZ", "xojaobod": "📍 Хўжаобод"}
CODE = {"d": "davra", "p": "paparazzi", "x": "xojaobod"}
REV = {v: k for k, v in CODE.items()}
BOTH = ("davra", "paparazzi")   # «в оба»: главный канал + PaparazziUZ
MEDIA_KEYS = ("photo", "video", "animation", "document", "audio", "voice", "video_note")
ALBUM_WAIT = 2.5                  # сек тишины — альбом собран
ALBUMS: dict[str, dict] = {}      # media_group_id → {"msgs": [...], "last": ts, "chat": id, "dm": bool}


# ---------- содержимое ----------

def media_of(msg: dict) -> list[dict]:
    for k in MEDIA_KEYS:
        if k in msg:
            o = msg[k][-1] if k == "photo" else msg[k]
            return [{"type": k, "file_id": o.get("file_id"), "uid": o.get("file_unique_id")}]
    return []


def fingerprint(text: str, media: list[dict]) -> str | None:
    uids = sorted(m["uid"] for m in media if m.get("uid"))
    if uids:
        return "m:" + hashlib.sha1(",".join(uids).encode()).hexdigest()[:20]
    from .text import strip_sources
    norm = re.sub(r"\W+", "", strip_sources(text or "").lower())
    return ("t:" + hashlib.sha1(norm[:500].encode()).hexdigest()[:20]) if len(norm) >= 20 else None


def duplicate_note(db, m) -> str:
    if not m["fp"]:
        return ""
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=14)).isoformat()
    r = db.execute("SELECT channel, status, scheduled_at FROM materials WHERE fp=? AND id<>? AND hub_msg<>? "
                   "AND status IN ('queued','published') AND created_at>=? ORDER BY id DESC LIMIT 1",
                   (m["fp"], m["id"], m["hub_msg"], since)).fetchone()
    if not r:
        return ""
    where = NAMES.get(r["channel"], r["channel"] or "")
    return f"⚠️ Повтор: такой пост уже {'опубликован' if r['status'] == 'published' else 'в очереди'} — {where}"


def rubrics(cfg: dict, channel: str) -> list[str]:
    out: list[str] = []
    for s in cfg["channels"][channel]["slots"]:
        if s["kind"] in ("content", "music"):
            for r in [s.get("rubric")] + list(s.get("fallback", [])):
                if r and r not in out:
                    out.append(r)
    return out


def preview(text: str, has_media: bool, n_media: int = 1) -> str:
    from . import translit
    from .text import strip_sources
    t, conv = translit.auto(strip_sources(text or "").strip())       # владелец видит уже очищенный текст
    t = (t[:280] + "…") if len(t) > 280 else t
    notes = [n for n in (("🔤 Латиница → кириллица (автоматически)" if conv else ""), translit.language_note(text)) if n]
    note = ("\n\n" + "\n".join(notes)) if notes else ""
    icon = f" 🖼×{n_media}" if n_media > 1 else (" 🖼" if has_media else "")
    return f"📥 Новый материал{icon}\n\n{t or '(без текста)'}{note}"


# ---------- карточка ----------

def _now() -> dt.datetime:
    return dt.datetime.now(plan.TZ)


def card(db, cfg: dict, mid: int, now: dt.datetime | None = None) -> tuple[str, dict]:
    now = now or _now()
    m = store.get(db, mid)
    media = json.loads(m["media"] or "[]")
    base = preview(m["text"], bool(m["has_media"]), len(media) or 1)
    name = NAMES.get(m["channel"], m["channel"])
    dup = duplicate_note(db, m)
    dup = f"\n{dup}" if dup else ""
    if m["status"] == "published":
        return f"{base}\n\n✔️ {name} · {m['rubric']} — опубликовано", {"inline_keyboard": []}
    if m["status"] == "rejected":
        return f"{base}\n\n🗑 Убрано", {"inline_keyboard": []}
    if m["status"] == "queued" and m["scheduled_at"]:
        t = dt.datetime.fromisoformat(m["scheduled_at"])
        when = "сейчас (🆘)" if m["urgent"] else smart.fmt(t, now)
        txt = f"{base}\n\n✅ {name} · {m['rubric']} — {when}{' 🔒' if m['locked'] else ''}{dup}"
        kb = [[{"text": "🕐 Изменить время", "callback_data": f"ot:{mid}"}, {"text": "🆘 Сейчас", "callback_data": f"ur:{mid}"}],
              [{"text": "📂 Рубрика", "callback_data": f"rs:{mid}"}, {"text": "🗑 Убрать", "callback_data": f"del:{mid}"}]]
        return txt, {"inline_keyboard": kb}
    st = smart.smart_time(db, cfg, m["channel"], m["rubric"], now, exclude=mid)
    head = f"{name} · {m['rubric']}{' (угадано)' if m['guessed'] else ''}"
    kb = []
    if st:
        t, why = st
        head += f"\n🧠 УМНОЕ ВРЕМЯ: {smart.fmt(t, now)} — {why}"
        kb.append([{"text": f"🧠 Умное время · {t:%H:%M}", "callback_data": f"sm:{mid}:{int(t.timestamp())}"}])
    else:
        head += "\n⚠️ Свободного времени в ближайшие дни нет — выберите время вручную или 🆘"
    kb += [[{"text": "🆘 Сейчас", "callback_data": f"ur:{mid}"}, {"text": "🕐 Другое время", "callback_data": f"ot:{mid}"}],
           [{"text": "📂 Рубрика", "callback_data": f"rs:{mid}"}, {"text": "📺 Канал", "callback_data": f"cs:{mid}"}],
           [{"text": "🗑 Убрать", "callback_data": f"del:{mid}"}]]
    return f"{base}\n\n{head}{dup}", {"inline_keyboard": kb}


def kb_times(db, cfg, mid: int, now: dt.datetime) -> dict:
    m = store.get(db, mid)
    ts = smart.other_times(db, cfg, m["channel"], m["rubric"], now, n=10, exclude=mid)
    btn = [{"text": smart.fmt(t, now), "callback_data": f"tm:{mid}:{int(t.timestamp())}"} for t in ts]
    rows = [btn[i:i + 2] for i in range(0, len(btn), 2)]
    return {"inline_keyboard": rows + [[{"text": "‹ Назад", "callback_data": f"bk:{mid}"}]]}


def kb_rubric(cfg: dict, mid: int, channel: str) -> dict:
    rs = rubrics(cfg, channel)
    btn = [{"text": r, "callback_data": f"rb:{mid}:{i}"} for i, r in enumerate(rs)]
    return {"inline_keyboard": [btn[i:i + 2] for i in range(0, len(btn), 2)] + [[{"text": "‹ Назад", "callback_data": f"bk:{mid}"}]]}


def kb_channel(mid: int, cfg: dict | None = None) -> dict:
    chans = list((cfg or {}).get("channels", {}) or NAMES)
    btn = [{"text": NAMES.get(c, c), "callback_data": f"ch:{mid}:{REV[c]}"} for c in chans if c in REV]
    rows = [btn[i:i + 2] for i in range(0, len(btn), 2)]
    rows.append([{"text": "🔁 Давра + Paparazzi", "callback_data": f"ch:{mid}:b"}, {"text": "‹ Назад", "callback_data": f"bk:{mid}"}])
    return {"inline_keyboard": rows}


# ---------- приём ----------

def intake(bot, db, cfg: dict, owners: set[int], hub: int, hub_ids: list[int], msgs: list[dict],
           reply_chat: int | None = None) -> str:
    """Новый материал (одиночный пост или альбом) → черновик с угаданными каналом и рубрикой → карточка владельцу."""
    text = next((x.get("text") or x.get("caption") for x in msgs if x.get("text") or x.get("caption")), "") or ""
    media = [md for x in msgs for md in media_of(x)]
    fp = fingerprint(text, media)
    mid = store.add_material(db, hub, hub_ids[0], text, bool(media), media=media, hub_msgs=hub_ids, fp=fp)
    if mid is None:
        return "dup"
    channel = cfg.get("default_channel") or next(iter(cfg["channels"]))
    from .text import strip_sources
    rub = smart.guess_rubric(cfg, channel, strip_sources(text), has_audio=any(md["type"] == "audio" for md in media))
    store.update(db, mid, channel=channel, rubric=rub, guessed=1, status="draft")
    txt, kb = card(db, cfg, mid)
    for o in ([reply_chat] if reply_chat else owners):
        p = {"chat_id": o, "text": txt, "reply_markup": kb, "disable_web_page_preview": True}
        if reply_chat:
            p["reply_to_message_id"] = msgs[0]["message_id"]
        r = bot("sendMessage", **p)
        store.update(db, mid, owner_msg=r["message_id"])
    return "material"


def direct(bot, db, cfg, owners, hub: int, msgs: list[dict]) -> str:
    """Пост прямо в чат с ботом: копия (или весь альбом) — в PAPA HUB, карточка — ответом владельцу."""
    msgs = sorted(msgs, key=lambda x: x["message_id"])
    if not any(k in msgs[0] for k in MEDIA_KEYS) and not (msgs[0].get("text") or "").strip() and len(msgs) == 1:
        return "skip"
    chat = msgs[0]["chat"]["id"]
    if len(msgs) > 1:
        r = bot("copyMessages", chat_id=hub, from_chat_id=chat, message_ids=[x["message_id"] for x in msgs])
        ids = [x["message_id"] for x in r]
    else:
        ids = [bot("copyMessage", chat_id=hub, from_chat_id=chat, message_id=msgs[0]["message_id"])["message_id"]]
    return intake(bot, db, cfg, owners, hub, ids, msgs, reply_chat=chat)


def flush_albums(bot, db, cfg: dict, env: dict, now_ts: float | None = None) -> int:
    """Собранные альбомы (2,5 с без новых частей) → один материал."""
    now_ts = now_ts or time.time()
    owners = {int(x) for x in str(env.get("OWNER_IDS", "")).split(",") if x.strip()}
    hub = int(env["HUB_CHAT_ID"])
    n = 0
    for gid in [g for g, a in ALBUMS.items() if now_ts - a["last"] >= ALBUM_WAIT]:
        a = ALBUMS.pop(gid)
        try:
            if a["dm"]:
                direct(bot, db, cfg, owners, hub, a["msgs"])
            else:
                msgs = sorted(a["msgs"], key=lambda x: x["message_id"])
                intake(bot, db, cfg, owners, hub, [x["message_id"] for x in msgs], msgs)
            n += 1
        except Exception as e:  # noqa: BLE001
            print(f"album: {type(e).__name__}: {e}", flush=True)
    return n


def _album(msg: dict, dm: bool) -> bool:
    gid = msg.get("media_group_id")
    if not gid:
        return False
    a = ALBUMS.setdefault(gid, {"msgs": [], "last": 0.0, "dm": dm})
    a["msgs"].append(msg)
    a["last"] = time.time()
    return True


# ---------- обработчик обновлений ----------

def handle(bot, db, cfg: dict, env: dict, upd: dict) -> str | None:
    owners = {int(x) for x in str(env.get("OWNER_IDS", "")).split(",") if x.strip()}
    hub = int(env["HUB_CHAT_ID"])
    post = upd.get("channel_post")
    if post:
        if int(post["chat"]["id"]) == hub:
            if _album(post, dm=False):
                return "album"
            return intake(bot, db, cfg, owners, hub, [post["message_id"]], [post])
        uname = (post["chat"].get("username") or "").lower()
        for c, ch in cfg["channels"].items():
            if ch["username"].lower() == uname:           # ручной пост в нашем канале — учитываем в промежутках
                store.pulse_add(db, c, dt.datetime.fromtimestamp(post.get("date", time.time()), plan.TZ), "manual")
                return "pulse"
        return None

    cq = upd.get("callback_query")
    if cq:
        return callback(bot, db, cfg, owners, cq)

    msg = upd.get("message")
    if msg and int(msg["from"]["id"]) in owners and msg["chat"].get("type") == "private":
        from .menu import BY_BUTTON, B_ALL, B_QUEUE, B_TODAY, B_HELP
        txt = (msg.get("text") or "").strip()
        if txt.startswith("/") or txt in BY_BUTTON or txt in (B_ALL, B_QUEUE, B_TODAY, B_HELP):
            return "cmd:" + txt.split()[0]
        if _album(msg, dm=True):
            return "album"
        return direct(bot, db, cfg, owners, hub, [msg])
    return None


def callback(bot, db, cfg: dict, owners: set[int], cq: dict, now: dt.datetime | None = None) -> str:
    now = now or _now()
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
    note = ""

    def show(markup=None, text=None):
        t, kb = card(db, cfg, mid, now)
        bot("editMessageText", chat_id=chat, message_id=msg_id, text=text or t, reply_markup=markup or kb,
            disable_web_page_preview=True)

    if kind in ("sm", "tm", "nx"):
        t = dt.datetime.fromtimestamp(int(arg[0]), plan.TZ) if arg else None
        if t is None:                                   # старая кнопка «⏰ Ближайший слот»
            st = smart.smart_time(db, cfg, m["channel"], m["rubric"], now, exclude=mid)
            t = st[0] if st else None
        busy = smart.occupied(db, m["channel"], now, exclude=mid)
        ch = cfg["channels"][m["channel"]]
        if t and t >= now - dt.timedelta(minutes=1) and smart.is_free(ch, t, busy) and smart.allowed(ch, t, m["rubric"]):
            store.update(db, mid, status="queued", scheduled_at=t.isoformat(), urgent=0, locked=int(kind == "tm"))
        else:
            note = "Это время уже занято — показываю новое"
        show()
    elif kind == "ur":
        store.update(db, mid, status="queued", urgent=1, scheduled_at=now.isoformat(), rubric=m["rubric"] or "Срочно")
        show()
    elif kind == "ot":
        t, _ = card(db, cfg, mid, now)
        show(kb_times(db, cfg, mid, now), t + "\n\n🕐 Выберите время:")
    elif kind == "rs":
        t, _ = card(db, cfg, mid, now)
        show(kb_rubric(cfg, mid, m["channel"]), t + "\n\n📂 Выберите рубрику:")
    elif kind == "cs":
        t, _ = card(db, cfg, mid, now)
        show(kb_channel(mid, cfg), t + "\n\n📺 Выберите канал:")
    elif kind == "rb":
        r = rubrics(cfg, m["channel"])[int(arg[0])]
        upd = {"rubric": r, "guessed": 0}
        if m["status"] == "queued" and not m["locked"] and not m["urgent"]:
            st = smart.smart_time(db, cfg, m["channel"], r, now, exclude=mid)
            upd["scheduled_at"] = st[0].isoformat() if st else m["scheduled_at"]
        elif m["status"] != "queued":
            upd["status"] = "draft"
        store.update(db, mid, **upd)
        show()
    elif kind == "ch":
        from .text import strip_sources
        targets = list(BOTH) if arg[0] == "b" else [CODE[arg[0]]]
        if targets[0] not in cfg["channels"]:
            note = "Канал не настроен"
        else:
            store.update(db, mid, channel=targets[0], status="draft", scheduled_at=None, urgent=0, locked=0,
                         rubric=smart.guess_rubric(cfg, targets[0], strip_sources(m["text"])), guessed=1)
            show()
            for extra in targets[1:]:
                if extra not in cfg["channels"]:
                    continue
                cid = store.clone_for(db, mid, extra)
                store.update(db, cid, status="draft", rubric=smart.guess_rubric(cfg, extra, strip_sources(m["text"])), guessed=1)
                t, kb = card(db, cfg, cid, now)
                r = bot("sendMessage", chat_id=chat, text=t, reply_markup=kb, disable_web_page_preview=True)
                store.update(db, cid, owner_msg=r["message_id"])
    elif kind == "bk":
        show()
    elif kind == "del":
        store.update(db, mid, status="rejected")
        show()
    bot("answerCallbackQuery", callback_query_id=cq["id"], **({"text": note} if note else {}))
    return kind
