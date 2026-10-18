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


REPEAT_DAYS = 7          # решение владельца 16.10: повторы раз в неделю–месяц — нормально, не блокируем


def duplicate_note(db, m) -> str:
    if not m["fp"]:
        return ""
    # повтор — нормально (контент крутится раз в неделю–месяц); предупреждаем только если был меньше REPEAT_DAYS назад
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=REPEAT_DAYS)).isoformat()
    r = db.execute("SELECT channel, status, scheduled_at FROM materials WHERE fp=? AND id<>? AND hub_msg<>? "
                   "AND status IN ('queued','published') AND created_at>=? ORDER BY id DESC LIMIT 1",
                   (m["fp"], m["id"], m["hub_msg"], since)).fetchone()
    if not r:
        return ""
    where = NAMES.get(r["channel"], r["channel"] or "")
    return (f"ℹ️ Такой пост {'уже выходил' if r['status'] == 'published' else 'уже в очереди'} на этой неделе — {where}. "
            f"Повтор можно, но лучше через {REPEAT_DAYS} дн.")


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
    t = (t[:900] + "…") if len(t) > 900 else t          # владелец видит текст почти целиком — проверить перед выходом
    from .human import headline_note
    notes = [n for n in (("🔤 Латиница → кириллица (автоматически)" if conv else ""), translit.language_note(text),
                         headline_note(t)) if n]
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
        what = m["topic"] if "topic" in m.keys() and m["topic"] else m["rubric"]
        tg = f" {m['tag']}" if "tag" in m.keys() and m["tag"] else ""
        txt = f"{base}\n\n{summary(db, cfg, m['channel'], now)}\n✅ {name} · {what}{tg} — {when}{' 🔒' if m['locked'] else ''}{dup}"
        return txt, {"inline_keyboard": kb_queued(db, cfg, m, now)}
    # черновик — экран «➕ ПОСТ» пульта Хўжаобода (GENPLAN 5): группы → подрубрика (= смысл и один хэштег) → умное время
    from . import picker
    rs = rubrics(cfg, m["channel"])
    if m["stock"]:
        return (f"📍 Канал: {name}\n\n{base}\n\n📦 В запасе · {m['rubric']} — выйдет сам, когда у рубрики будет пустой слот{dup}",
                {"inline_keyboard": [[{"text": "🧠 Поставить в план сейчас", "callback_data": f"rq:{mid}:{rs.index(m['rubric']) if m['rubric'] in rs else 0}"}],
                                     [{"text": "📂 Рубрика", "callback_data": f"sr:{mid}"}, {"text": "🗑 Убрать", "callback_data": f"del:{mid}"}]]})
    st = smart.smart_time(db, cfg, m["channel"], m["rubric"], now, exclude=mid) if m["rubric"] else None
    sbtn = {"text": f"🧠 Умное время · {st[0]:%H:%M}" if st and st[0].date() == now.date()
            else (f"🧠 Умное время · {st[0]:%d.%m %H:%M}" if st else "🧠 Умное время"),
            "callback_data": f"sm:{mid}:{int(st[0].timestamp())}" if st else f"sm:{mid}"}
    kb = picker.root_kb(mid, "Якуний пост" in rs, sbtn)
    kb += [[{"text": "📦 В запас", "callback_data": f"sr:{mid}"}],
           [{"text": "✏️ Текст", "callback_data": f"ed:{mid}"}, {"text": "🤖 ИИ-текст", "callback_data": f"ai:{mid}"}],
           [{"text": "⬅️ Отмена", "callback_data": f"del:{mid}"}]]
    return (f"📍 Канал: {name}\n\n{base}\n\nВыберите рубрику — время GENPLAN определит сам.{dup}",
            {"inline_keyboard": kb})


def summary(db, cfg: dict, channel: str, now: dt.datetime) -> str:
    """Сводка над кнопками, как в GENPLAN 5: последний пост и ближайший обязательный."""
    last = smart.last_post(db, channel, now)
    nxt = smart.next_mandatory(db, cfg, channel, now)
    a = f"🕓 Последний пост: {last:%d.%m %H:%M}" if last else "🕓 Последний пост: нет данных"
    b = f"📌 Следующий обязательный: {smart.fmt(nxt[0], now)} — {nxt[1]}" if nxt else "📌 Следующий обязательный: нет"
    return f"{a}\n{b}"


def kb_queued(db, cfg: dict, m, now: dt.datetime) -> list:
    """Кнопки поста в плане — раскладка пульта Хўжаобода (GENPLAN 5): Сегодня / Завтра / Сейчас / Другие варианты."""
    mid, ch = m["id"], m["channel"]
    cur = dt.datetime.fromisoformat(m["scheduled_at"]) if m["scheduled_at"] else None
    rows = []
    btn = []                                                # 17.10: Утро / День / Вечер вместо Сегодня / Завтра
    for icon, label, lo, hi in smart.PARTS:
        r = smart.part_time(db, cfg, ch, m["rubric"], now, lo, hi, exclude=mid)
        if r and not (cur and not m["urgent"] and r[0] == cur):
            t, n = r
            when = f"{t:%H:%M}" if t.date() == now.date() else ("завтра " if t.date() == now.date() + dt.timedelta(days=1) else f"{t:%d.%m} ") + f"{t:%H:%M}"
            btn.append({"text": f"{icon} {label} · {when}" + (f" ({n})" if n else ""), "callback_data": f"tm:{mid}:{int(t.timestamp())}"})
    rows.extend([b] for b in btn)
    rows += [[{"text": "🚀 Сейчас", "callback_data": f"ur:{mid}"}],
             [{"text": "🗓 Другие варианты", "callback_data": f"ot:{mid}"}],
             [{"text": "📂 Рубрика", "callback_data": f"rs:{mid}"}, {"text": "✏️ Текст", "callback_data": f"ed:{mid}"}],
             [{"text": "🤖 ИИ-текст", "callback_data": f"ai:{mid}"}, {"text": "🗑 Убрать", "callback_data": f"del:{mid}"}]]
    return rows


def options_screen(db, cfg: dict, mid: int, now: dt.datetime) -> tuple[str, dict]:
    """«🗓 Другие варианты» как в GENPLAN 5: причины — текстом, на кнопках — только время, по два в ряд."""
    m = store.get(db, mid)
    opts = smart.options(db, cfg, m["channel"], m["rubric"], now, exclude=mid)
    head = f"🗓 Подходящие варианты для «{m['rubric']}»"
    if not opts:
        return head + "\n\n(Пока свободного времени не найдено.)", {"inline_keyboard": [[{"text": "⬅️ Назад", "callback_data": f"bk:{mid}"}]]}
    lines = [head, ""] + [f"{smart.fmt(t, now)} — {lbl}" for t, lbl in opts]
    btn = [{"text": smart.fmt(t, now), "callback_data": f"tm:{mid}:{int(t.timestamp())}"} for t, _ in opts]
    rows = [btn[i:i + 2] for i in range(0, len(btn), 2)] + [[{"text": "⬅️ Назад", "callback_data": f"bk:{mid}"}]]
    return "\n".join(lines), {"inline_keyboard": rows}


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


def movable(cfg: dict, m, env_hub: int | None = None) -> list[str]:
    """Куда можно перенести материал. Из чата бота-пульта канала — только в его канал (другие боты этот чат не видят);
    из главного бота — в каналы, где он админ (Давра, Paparazzi); в группу — только то, что лежит в хабе или может туда
    попасть (главный бот копирует)."""
    via = (m["via"] if "via" in m.keys() else None) or "main"
    if via != "main":
        return [via]
    return list(cfg["channels"])


def kb_channel(mid: int, cfg: dict | None = None, allowed: list[str] | None = None) -> dict:
    chans = [c for c in list((cfg or {}).get("channels", {}) or NAMES) if allowed is None or c in allowed]
    btn = [{"text": NAMES.get(c, c), "callback_data": f"ch:{mid}:{REV[c]}"} for c in chans if c in REV]
    rows = [btn[i:i + 2] for i in range(0, len(btn), 2)]
    both = allowed is None or ("davra" in allowed and "paparazzi" in allowed)
    rows.append(([{"text": "🔁 Давра + Paparazzi", "callback_data": f"ch:{mid}:b"}] if both else [])
                + [{"text": "‹ Назад", "callback_data": f"bk:{mid}"}])
    return {"inline_keyboard": rows}


# ---------- приём ----------

def _norm(t: str | None) -> str:
    return re.sub(r"[^0-9a-zа-яёўқғҳ]+", "", (t or "").lower())


def channel_hub(db, cfg: dict, post: dict, own: str | None) -> str | None:
    """18.10 (владелец): у каждого канала свой ХАБ — частный канал, куда он бросает собранное. Бот канала берёт
    оттуда материал сам. Каждый бот — только свой хаб: главный — КАТТА ДАВРА, пульт PaparazziUZ — PaparazziUZ.
    Хаб узнаётся по названию (hub_title в config.toml), потом запоминается по id."""
    me = own or cfg.get("default_channel") or "davra"
    ch = cfg["channels"].get(me) or {}
    if not ch.get("hub_title"):
        return None
    cid = int(post["chat"]["id"])
    known = store.kv_get(db, f"hub_{me}", "")
    if (known and int(known) == cid) or _norm(post["chat"].get("title")) == _norm(ch["hub_title"]):
        if str(known) != str(cid):
            store.kv_set(db, f"hub_{me}", str(cid))
        return me
    return None


def auto_place(db, cfg: dict, mid: int) -> str | None:
    """Решение 15.10: бросил пост — бот сам ставит рубрику (угаданную) и умное время. Возвращает пометку для карточки."""
    if not cfg.get("auto_place"):
        return None
    m = store.get(db, mid)
    st = smart.smart_time(db, cfg, m["channel"], m["rubric"], _now(), exclude=mid)
    if not st:
        return None
    store.update(db, mid, status="queued", scheduled_at=st[0].isoformat(), urgent=0, locked=0)
    return f"🤖 Поставил сам: {m['rubric']} · {smart.fmt(st[0], _now())}. Не так — поправьте кнопками ниже."


def source_of(msg: dict) -> str | None:
    """Пост переслан из канала (куратор или владелец) → @источник."""
    o = msg.get("forward_origin") or {}
    chat = o.get("chat") or msg.get("forward_from_chat") or {}
    if not chat:
        return None
    return "@" + chat["username"] if chat.get("username") else (chat.get("title") or None)


def intake(bot, db, cfg: dict, owners: set[int], hub: int, hub_ids: list[int], msgs: list[dict],
           reply_chat: int | None = None, notes: list[str] | None = None, channel: str | None = None,
           stock: bool = False) -> str:
    """Новый материал (одиночный пост или альбом) → черновик с угаданными каналом и рубрикой → карточка владельцу."""
    text = next((x.get("text") or x.get("caption") for x in msgs if x.get("text") or x.get("caption")), "") or ""
    media = [md for x in msgs for md in media_of(x)]
    fp = fingerprint(text, media)
    mid = store.add_material(db, hub, hub_ids[0], text, bool(media), media=media, hub_msgs=hub_ids, fp=fp)
    if mid is None:
        return "dup"
    from .text import strip_sources
    has_audio = any(md["type"] == "audio" for md in media)
    from . import bots
    channel = channel if channel in cfg["channels"] else smart.guess_channel(cfg, text, has_audio)
    rub = smart.guess_rubric(cfg, channel, strip_sources(text), has_audio=has_audio)
    src = source_of(msgs[0])
    store.update(db, mid, channel=channel, rubric=rub, guessed=1, status="draft", via=bots.key_of(bot), source=src)
    from .text import link_junk
    ents = next((x.get("entities") or x.get("caption_entities") for x in msgs if x.get("text") or x.get("caption")), None)
    own = tuple(c.get("username", "") for c in cfg["channels"].values())
    junk = link_junk(text, ents, own)
    if junk:
        store.update(db, mid, junk=json.dumps(junk, ensure_ascii=False))
    if src:
        notes = [f"📡 Куратор нашёл · {src}"] + (notes or [])
    pol = smart.policy_note(cfg, channel, strip_sources(text))      # политика каналов (docs/CHANNELS.md)
    if pol:
        notes = (notes or []) + [pol]
    if stock:                                      # 18.10: пост из ХАБа канала — в 📦 запас, выйдет сам в пустой слот
        store.update(db, mid, stock=1)
        notes = ["📥 Из ХАБа канала — уже ваше одобрение"] + (notes or [])
    placed = None if stock else auto_place(db, cfg, mid)
    if placed:
        notes = (notes or []) + [placed]
    txt, kb = card(db, cfg, mid)
    if notes:
        txt = "\n".join(notes) + "\n\n" + txt
    for o in ([reply_chat] if reply_chat else owners):
        p = {"chat_id": o, "text": txt, "reply_markup": kb, "disable_web_page_preview": True}
        if reply_chat:
            p["reply_to_message_id"] = msgs[0]["message_id"]
        r = bot("sendMessage", **p)
        store.update(db, mid, owner_msg=r["message_id"])
    return "material"


def direct(bot, db, cfg, owners, hub: int, msgs: list[dict], channel: str | None = None) -> str:
    """Пост прямо в чат с ботом. Решение 16.10: для каналов (публикует бот) хаб не нужен — пост берётся прямо
    из чата с ботом. В хаб копируется только то, что пойдёт в группу (публикует аккаунт PAPA, ему нужен хаб)."""
    msgs = sorted(msgs, key=lambda x: x["message_id"])
    if not any(k in msgs[0] for k in MEDIA_KEYS) and not (msgs[0].get("text") or "").strip() and len(msgs) == 1:
        return "skip"
    chat = msgs[0]["chat"]["id"]
    text = next((x.get("text") or x.get("caption") for x in msgs if x.get("text") or x.get("caption")), "") or ""
    if channel not in cfg["channels"]:
        channel = smart.guess_channel(cfg, text, any("audio" in x for x in msgs))
    if cfg["channels"][channel]["publisher"] == "bot":
        return intake(bot, db, cfg, owners, chat, [x["message_id"] for x in msgs], msgs, reply_chat=chat, channel=channel)
    if len(msgs) > 1:
        r = bot("copyMessages", chat_id=hub, from_chat_id=chat, message_ids=[x["message_id"] for x in msgs])
        ids = [x["message_id"] for x in r]
    else:
        ids = [bot("copyMessage", chat_id=hub, from_chat_id=chat, message_id=msgs[0]["message_id"])["message_id"]]
    return intake(bot, db, cfg, owners, hub, ids, msgs, reply_chat=chat, channel=channel)


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
                from . import bots
                direct(bots.for_channel(a.get("channel"), bot), db, cfg, owners, hub, a["msgs"], channel=a.get("channel"))
            elif a.get("hub"):                           # альбом из ХАБа канала → в запас, через бота канала
                from . import bots
                msgs = sorted(a["msgs"], key=lambda x: x["message_id"])
                intake(bots.for_channel(a["channel"], bot), db, cfg, owners, a["hub"], [x["message_id"] for x in msgs],
                       msgs, channel=a["channel"], stock=True)
            else:
                msgs = sorted(a["msgs"], key=lambda x: x["message_id"])
                intake(bot, db, cfg, owners, hub, [x["message_id"] for x in msgs], msgs)
            n += 1
        except Exception as e:  # noqa: BLE001
            print(f"album: {type(e).__name__}: {e}", flush=True)
    return n


def _album(msg: dict, dm: bool, channel: str | None = None) -> bool:
    gid = msg.get("media_group_id")
    if not gid:
        return False
    a = ALBUMS.setdefault(gid, {"msgs": [], "last": 0.0, "dm": dm, "channel": channel})
    a["msgs"].append(msg)
    a["last"] = time.time()
    return True


# ---------- обработчик обновлений ----------

HUB_ID: int | None = None


def special_mode(bot, db, cfg: dict, key: str, chat: int) -> str | None:
    """После 🚨 СРОЧНО / 📣 РЕКЛАМА на панели: последний принятый пост — срочно сейчас / реклама с выбором времени."""
    raw = store.kv_get(db, f"mode_{key}", "")
    if not raw:
        return None
    store.kv_set(db, f"mode_{key}", "")
    mode, _, at = raw.partition("|")
    # 17.10: 🚨 СРОЧНО действует 10 минут — иначе забытое нажатие выпускает следующий пост без карточки
    if not at or _now() - dt.datetime.fromisoformat(at) > dt.timedelta(minutes=10):
        return None
    m = db.execute("SELECT * FROM materials WHERE via=? ORDER BY id DESC LIMIT 1", (key,)).fetchone()
    if not m:
        return None
    now = _now()
    if mode == "urgent":
        store.update(db, m["id"], status="queued", urgent=1, scheduled_at=now.isoformat(), stock=0,
                     rubric=m["rubric"] or "Срочно")
        t, kb = card(db, cfg, m["id"], now)
        bot("editMessageText", chat_id=chat, message_id=m["owner_msg"], text="🚨 Срочно — выходит сейчас\n\n" + t, reply_markup=kb)
        return "ur"
    if mode == "ad":
        store.update(db, m["id"], rubric="Реклама", guessed=0)
        t, _ = card(db, cfg, m["id"], now)
        bot("editMessageText", chat_id=chat, message_id=m["owner_msg"], text="📣 Реклама — выберите время:\n\n" + t,
            reply_markup=kb_times(db, cfg, m["id"], now))
        return "ad"
    return None


def to_hub(bot, db, mid: int) -> None:
    """Материал из чата с ботом → копия в хаб (нужно только для группы: аккаунт PAPA видит лишь хаб)."""
    m = store.get(db, mid)
    if HUB_ID is None or str(m["hub_chat"]) == str(HUB_ID):
        return
    ids = json.loads(m["hub_msgs"] or "[]") or [m["hub_msg"]]
    if len(ids) > 1:
        new = [x["message_id"] for x in bot("copyMessages", chat_id=HUB_ID, from_chat_id=m["hub_chat"], message_ids=ids)]
    else:
        new = [bot("copyMessage", chat_id=HUB_ID, from_chat_id=m["hub_chat"], message_id=ids[0])["message_id"]]
    store.update(db, mid, hub_chat=HUB_ID, hub_msg=new[0], hub_msgs=json.dumps(new))


def handle(bot, db, cfg: dict, env: dict, upd: dict) -> str | None:
    from . import bots
    global HUB_ID
    owners = {int(x) for x in str(env.get("OWNER_IDS", "")).split(",") if x.strip()}
    hub = int(env["HUB_CHAT_ID"])
    HUB_ID = hub
    own = bots.channel_of(bot)                       # бот-пульт канала → всё, что брошено в него, идёт в этот канал
    post = upd.get("channel_post")
    if post:
        if int(post["chat"]["id"]) == hub:
            if own:                                  # пост в хабе видят все боты — принимает только главный
                return None
            if _album(post, dm=False):
                return "album"
            return intake(bot, db, cfg, owners, hub, [post["message_id"]], [post])
        hc = channel_hub(db, cfg, post, own)
        if hc:
            if _album(post, dm=False, channel=hc):
                ALBUMS[post["media_group_id"]]["hub"] = int(post["chat"]["id"])
                return "album"
            return intake(bot, db, cfg, owners, int(post["chat"]["id"]), [post["message_id"]], [post],
                          channel=hc, stock=True)
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
        from .menu import BY_BUTTON, B_ALL, B_QUEUE, B_TODAY, B_HELP, B_NAMAZ, PANEL_BUTTONS, P_URGENT, P_ADS
        txt = (msg.get("text") or "").strip()
        cap = (msg.get("caption") or "").strip()
        if cap.lower().startswith("/logo") and ("document" in msg or "photo" in msg):
            return save_logo(bot, db, cfg, env, msg, cap)
        key = bots.key_of(bot)
        if txt in PANEL_BUTTONS:                      # панель пульта: 🚨/📣 — следующий пост особый
            store.kv_set(db, "await_text", "")
            mode = "ad" if txt == P_ADS else ""          # 17.10: 🚨 СРОЧНО больше не выпускает пост вслепую — выбор всегда на карточке
            store.kv_set(db, f"mode_{key}", f"{mode}|{_now().isoformat()}" if mode else "")
            return "panel:" + txt
        if txt.startswith("/") or txt in BY_BUTTON or txt in (B_ALL, B_QUEUE, B_TODAY, B_HELP, B_NAMAZ):
            store.kv_set(db, "await_text", "")
            return "cmd:" + txt.split()[0]
        from . import namaz
        if txt and namaz.looks_like_schedule(txt) and not any(k in msg for k in MEDIA_KEYS):   # 🕌 время намаза
            r = save_namaz(bot, db, cfg, msg, txt)
            if r != "not_namaz":
                return r
        wait = store.kv_get(db, "await_text", "")
        if wait and txt and not any(k in msg for k in MEDIA_KEYS):     # ✏️ новый текст для материала
            store.kv_set(db, "await_text", "")
            mid = int(wait)
            store.update(db, mid, text=txt)
            t, kb = card(db, cfg, mid)
            r = bot("sendMessage", chat_id=msg["chat"]["id"], text="✏️ Текст заменён:\n\n" + t, reply_markup=kb,
                    disable_web_page_preview=True)
            store.update(db, mid, owner_msg=r["message_id"])
            return "edited"
        from .fabrika import find_link
        link = find_link(txt) if txt and not any(k in msg for k in MEDIA_KEYS) else None
        if link:                                                      # ссылка Instagram/TikTok/Shorts → Fabrika
            store.job_add(db, "link", {"url": link, "owner_chat": msg["chat"]["id"], **({"channel": own} if own else {})})
            bot("sendMessage", chat_id=msg["chat"]["id"], reply_to_message_id=msg["message_id"],
                text="⏳ Скачиваю видео, ставлю логотип, готовлю текст — 1–3 минуты…")
            return "link"
        if _album(msg, dm=True, channel=own):
            return "album"
        r = direct(bot, db, cfg, owners, hub, [msg], channel=own)
        return special_mode(bot, db, cfg, key, msg["chat"]["id"]) or r
    return None


def save_namaz(bot, db, cfg: dict, msg: dict, txt: str) -> str:
    from . import namaz
    now = _now()
    try:
        items = namaz.parse(txt, now.date())
    except ValueError as e:
        tl = [ln for ln in txt.splitlines() if any(c.isdigit() for c in ln)
              and any(v in ln.lower() for n in namaz.NAMES for v in namaz.VARIANTS[n])]
        if len(tl) < 3:                       # это не ввод времени, а обычный пост, где упоминаются намазы
            return "not_namaz"
        bot("sendMessage", chat_id=msg["chat"]["id"], reply_to_message_id=msg["message_id"],
            text=f"⚠️ Не сохранено: {e}.\nИсправьте и пришлите весь блок ещё раз — ничего не изменено.")
        return "namaz_error"
    namaz.save(db, items, now)
    for c in cfg["channels"]:
        for d in (now.date(), now.date() + dt.timedelta(days=1)):
            namaz.ensure_day(db, cfg, c, d, now)
    if len(items) == 1:
        t = items[0][1]
        body = "\n".join(f"{namaz.ICON[n]} {namaz.LABEL[n]} — {t[n]}" for n in namaz.NAMES)
        head = "✅ Намоз вақтлари сақланди — бугундан фаол:"
    else:
        body = "\n".join(f"📅 {d:%d.%m}: " + " · ".join(t[n] for n in namaz.NAMES) for d, t in items)
        head = f"✅ Сақланди: {len(items)} кун"
    left = [ln for _, ln in namaz.today_lines(db, "xojaobod", now.date()) if ln.startswith("🕌")] if "xojaobod" in cfg["channels"] else []
    tail = ("\n\nСегодня ещё выйдут:\n" + "\n".join(left)) if left else ""
    bot("sendMessage", chat_id=msg["chat"]["id"], reply_to_message_id=msg["message_id"], text=f"{head}\n{body}{tail}")
    return "namaz"


def save_logo(bot, db, cfg: dict, env: dict, msg: dict, cap: str) -> str:
    """/logo [канал] — логотип для видео и фото канала (по умолчанию главный канал)."""
    import urllib.request
    from pathlib import Path
    from . import fabrika, media as M
    parts = cap.split()
    channel = parts[1] if len(parts) > 1 and parts[1] in cfg["channels"] else (cfg.get("default_channel") or "davra")
    f = msg["document"] if "document" in msg else msg["photo"][-1]
    info = bot("getFile", file_id=f["file_id"])
    raw = fabrika.STATE / f"logo-{channel}.src"
    from . import bots
    with urllib.request.urlopen(f"https://api.telegram.org/file/bot{bots.token_of(bot, env)}/{info['file_path']}", timeout=60) as r:
        raw.write_bytes(r.read())
    M.prepare_logo(raw, fabrika.logo_path(channel))
    bot("sendMessage", chat_id=msg["chat"]["id"], reply_to_message_id=msg["message_id"],
        text=f"✅ Логотип сохранён для {NAMES.get(channel, channel)}. Он будет на всех видео и фото из ссылок.")
    return "logo"


def autopilot_answer(bot, db, cq: dict) -> str:
    """✅ / ❌ владельца на задачу автопилота: ответ пишется в kv, исполнитель papa-autopilot его читает."""
    try:
        _, tid, ans = cq["data"].split(":")
    except ValueError:
        return "bad"
    if not tid.isalnum() or ans not in ("y", "n"):
        return "bad"
    k = f"autopilot_{tid}"
    if store.kv_get(db, k):
        bot("answerCallbackQuery", callback_query_id=cq["id"], text="Ответ уже принят")
        return "dup"
    store.kv_set(db, k, "yes" if ans == "y" else "no")
    text = (cq["message"].get("text") or "") + ("\n\n✅ РАЗРЕШЕНО — выполняю" if ans == "y" else "\n\n❌ ОТКАЗАНО")
    bot("editMessageText", chat_id=cq["message"]["chat"]["id"], message_id=cq["message"]["message_id"], text=text[:4096])
    bot("answerCallbackQuery", callback_query_id=cq["id"], text="✅ Разрешено" if ans == "y" else "❌ Отказано", show_alert=True)
    return "ap_" + ans


def callback(bot, db, cfg: dict, owners: set[int], cq: dict, now: dt.datetime | None = None) -> str:
    now = now or _now()
    if int(cq["from"]["id"]) not in owners:
        bot("answerCallbackQuery", callback_query_id=cq["id"], text="Нет доступа")
        return "denied"
    if cq["data"].startswith("mo:"):                      # предпросмотр утреннего блока
        from . import morning
        return morning.callback(bot, db, cq)
    if cq["data"].startswith("ap:"):                      # автопилот просит разрешения на задачу (Франкфурт)
        return autopilot_answer(bot, db, cq)
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
        t = dt.datetime.fromtimestamp(int(arg[0]), plan.TZ) if arg and arg[0] else None
        if t is None:                                   # старая кнопка «⏰ Ближайший слот»
            st = smart.smart_time(db, cfg, m["channel"], m["rubric"], now, exclude=mid)
            t = st[0] if st else None
        busy = smart.occupied(db, m["channel"], now, exclude=mid)
        ch = cfg["channels"][m["channel"]]
        if (t and t >= now - dt.timedelta(minutes=1) and smart.is_free(ch, t, busy) and smart.allowed(ch, t, m["rubric"])
                and not smart.blocked(db, m["channel"], t)):
            store.update(db, mid, status="queued", scheduled_at=t.isoformat(), urgent=0, locked=int(kind == "tm"), stock=0)
        else:
            note = "Это время уже занято — показываю новое"
        show()
    elif kind in ("pg", "pr", "pi", "pf"):                # выбор рубрики как в пульте Хўжаобода
        from . import picker
        rs = rubrics(cfg, m["channel"])
        t, _ = card(db, cfg, mid, now)
        if kind == "pr":
            show({"inline_keyboard": picker.root_kb(mid, "Якуний пост" in rs) + [[{"text": "⬅️ Назад", "callback_data": f"bk:{mid}"}]]}
                 if m["status"] == "queued" else None)
        elif kind == "pg":
            title, rows = picker.group_kb(mid, arg[0], int(arg[1]) if len(arg) > 1 else 1)
            show({"inline_keyboard": rows}, t + "\n\n" + title)
        else:
            if kind == "pf":
                r, tag, topic = "Якуний пост", (cfg["channels"][m["channel"]].get("hashtags") or {}).get("Якуний пост", ""), "🌙 Якуний пост"
            else:
                it = picker.item(arg[0], int(arg[1]))
                if it is None:
                    bot("answerCallbackQuery", callback_query_id=cq["id"], text="Рубрика не найдена")
                    return kind
                _code, emoji, label, tag, k = it
                r, topic = picker.rubric_for(cfg, m["channel"], k, rs), f"{emoji} {label}"
            upd = {"rubric": r, "guessed": 0, "stock": 0, "tag": tag, "topic": topic}
            if m["status"] == "queued" and (m["locked"] or m["urgent"]):
                store.update(db, mid, **upd)                  # время владельца не трогаем
                show()
            else:
                st = smart.smart_time(db, cfg, m["channel"], r, now, exclude=mid)
                if st:
                    store.update(db, mid, status="queued", scheduled_at=st[0].isoformat(), urgent=0, locked=0, **upd)
                    note = f"🧠 {smart.fmt(st[0], now)} — {st[1]}"
                    show()
                else:
                    store.update(db, mid, **upd)
                    t, _ = card(db, cfg, mid, now)
                    show(kb_times(db, cfg, mid, now), t + "\n\n⚠️ Свободного времени в ближайшие дни нет — выберите вручную:")
    elif kind == "sr":                                  # 📦 В запас: выбрать рубрику
        rs = rubrics(cfg, m["channel"])
        icons = cfg["channels"][m["channel"]].get("icons") or {}
        btn = [{"text": f"{icons.get(r, '•')} {r}{' ✓' if r == m['rubric'] else ''}", "callback_data": f"sk:{mid}:{i}"}
               for i, r in enumerate(rs)]
        t, _ = card(db, cfg, mid, now)
        show({"inline_keyboard": [btn[i:i + 2] for i in range(0, len(btn), 2)] + [[{"text": "‹ Назад", "callback_data": f"bk:{mid}"}]]},
             t + "\n\n📦 В запас — какая рубрика?")
    elif kind == "sk":
        r = rubrics(cfg, m["channel"])[int(arg[0])]
        store.update(db, mid, rubric=r, guessed=0, stock=1, status="draft", scheduled_at=None, urgent=0, locked=0)
        note = "📦 В запасе — выйдет сам в пустой слот рубрики"
        show()
    elif kind == "rq":
        r = rubrics(cfg, m["channel"])[int(arg[0])]
        # нажал подсказку бота (✓) — это подтверждение места в сетке, а не смысл: хэштег рубрики не ставим
        store.update(db, mid, rubric=r, guessed=int(bool(m["guessed"]) and r == m["rubric"]), stock=0)
        st = smart.smart_time(db, cfg, m["channel"], r, now, exclude=mid)
        if st:
            store.update(db, mid, status="queued", scheduled_at=st[0].isoformat(), urgent=0, locked=0)
            note = f"🧠 {smart.fmt(st[0], now)} — {st[1]}"
            show()
        else:
            t, _ = card(db, cfg, mid, now)
            show(kb_times(db, cfg, mid, now), t + "\n\n⚠️ Свободного времени в ближайшие дни нет — выберите вручную:")
    elif kind == "ur":
        last = smart.last_post(db, m["channel"], now)        # GENPLAN 5: прошлый пост был недавно — спросить
        gap = (now - last).total_seconds() / 60 if last else None
        if gap is not None and 0 <= gap < smart.NOW_WARNING_GAP and not arg:
            show({"inline_keyboard": [[{"text": "✅ Да", "callback_data": f"ur:{mid}:y"}],
                                      [{"text": "⬅️ Назад", "callback_data": f"bk:{mid}"}]]},
                 f"⚠️ Последний пост вышел {int(gap)} мин назад.\n\nВсё равно опубликовать сейчас?")
        else:
            store.update(db, mid, status="queued", urgent=1, scheduled_at=now.isoformat(), rubric=m["rubric"] or "Срочно", stock=0)
            show()
    elif kind == "ot":
        if m["status"] == "queued" or m["rubric"]:
            t, kb = options_screen(db, cfg, mid, now)
            show(kb, t)
        else:
            t, _ = card(db, cfg, mid, now)
            show(kb_times(db, cfg, mid, now), t + "\n\n🕐 Выберите время:")
    elif kind == "rs":
        from . import picker
        t, _ = card(db, cfg, mid, now)
        rows = picker.root_kb(mid, "Якуний пост" in rubrics(cfg, m["channel"])) + [[{"text": "⬅️ Назад", "callback_data": f"bk:{mid}"}]]
        show({"inline_keyboard": rows}, t + "\n\n📂 Выберите рубрику:")
    elif kind == "cs":
        t, _ = card(db, cfg, mid, now)
        allowed = movable(cfg, m)
        if len(allowed) <= 1:
            note = "Этот пост пришёл в пульт своего канала. Для другого канала бросьте его в пульт того канала."
        else:
            show(kb_channel(mid, cfg, allowed), t + "\n\n📺 Выберите канал:")
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
        elif any(t not in movable(cfg, m) for t in targets):
            note = "Этот пост можно поставить только в канал своего пульта"
        else:
            if any(cfg["channels"][t]["publisher"] == "account" for t in targets if t in cfg["channels"]):
                to_hub(bot, db, mid)                 # в группу публикует аккаунт PAPA — ему нужен хаб
                m = store.get(db, mid)
            store.update(db, mid, channel=targets[0], status="draft", scheduled_at=None, urgent=0, locked=0,
                         rubric=smart.guess_rubric(cfg, targets[0], strip_sources(m["text"])), guessed=1)
            note = auto_place(db, cfg, mid) or ""
            show()
            for extra in targets[1:]:
                if extra not in cfg["channels"]:
                    continue
                cid = store.clone_for(db, mid, extra)
                store.update(db, cid, status="draft", rubric=smart.guess_rubric(cfg, extra, strip_sources(m["text"])), guessed=1)
                auto_place(db, cfg, cid)
                t, kb = card(db, cfg, cid, now)
                r = bot("sendMessage", chat_id=chat, text=t, reply_markup=kb, disable_web_page_preview=True)
                store.update(db, cid, owner_msg=r["message_id"])
    elif kind == "ed":
        store.kv_set(db, "await_text", mid)
        bot("sendMessage", chat_id=chat, reply_to_message_id=msg_id,
            text="✏️ Пришлите новый текст одним сообщением — он заменит текущий (подпись и призыв бот добавит сам).")
    elif kind == "ai":
        from . import ai
        if not ai.available():
            note = "ИИ ещё не подключён — нужен ключ на сервере"
        else:
            store.job_add(db, "ai", {"mid": mid, "owner_chat": chat})
            note = "🤖 Переписываю… пришлю новую карточку"
    elif kind == "bk":
        show()
    elif kind == "del":
        store.update(db, mid, status="rejected")
        show()
    bot("answerCallbackQuery", callback_query_id=cq["id"], **({"text": note} if note else {}))
    return kind
