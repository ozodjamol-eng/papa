"""ИИ-ассистент личного Telegram владельца (@Ozodjamol) через Telegram Business (решение 17.10).

30.10 (владелец: «нужен другой подход, он должен полноценно работать»): есть ключ Gemini → настоящий ИИ-разговор
(бесплатно): понимает поздравления (Жума муборак → ответное поздравление), ведёт разговор о рекламе, личное — «Озод Жамол
сам ответит». Со знакомыми (с кем владелец уже переписывался) — только ответ на поздравления/салом. Владелец написал
сам — бот молчит 24 ч. Нет ключа / ИИ упал — прежние шаблоны (ниже), раз в сутки на чат.

Отвечает ТОЛЬКО на первое сообщение человека (раз в сутки на чат), всегда представляется ИИ-ассистентом:
- 📣 реклама → готовый ответ с прайсом (50 000 сўм — пост только в XO'JAOBOD CITY 24, решение 20.10);
- 👤 всё остальное (личное, непонятное) → «передал, Озоджамол скоро свяжется».
Дальше разговор ведёт владелец. Если владелец сам написал в чат — бот молчит. Каждое обращение пересылается
владельцу в чат с ботом. Никаких скидок, обещаний, договорённостей. Только Bot API, без захвата сессии."""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request

REPLY_EVERY = dt.timedelta(hours=24)        # не чаще одного ответа на чат в сутки
OWNER_QUIET = dt.timedelta(hours=24)        # владелец сам писал в чат — бот молчит

PRICE = """📣 XO'JAOBOD CITY 24 — РЕКЛАМА
1) 1 кун — 50 000 сўм
2) 3 кун (ҳар куни 1 марта) — 130 000 сўм
3) 7 кун (ҳар куни 1 марта) — 280 000 сўм
4) Кечки вақт (18:00–20:00) — +10 000 сўм
5) Тепада қадаб қўйиш (1 кун) — +20 000 сўм
Реклама 10 дақиқа энг тепада туради.

🎬 Моушн-реклама пакети — 500 000 сўм (замонавий моушн-видео + 1 ҳафта ҳар куни XO'JAOBOD CITY 24 да)
🎥 Реклама видеоролик (моушн / ИИ) — нархи иш ҳажмига қараб, Озод Жамол ўзи айтади
💻 Сайт, Telegram-бот — нархи келишилади
Буюртма: @Ozodjamol"""   # 30.10 утверждено владельцем («согласен»)

AD_TEXT = """Ассалому алайкум!
Мен Озод Жамолнинг ИИ-ёрдамчисиман 🤖

""" + PRICE + """

Нимани реклама қилмоқчи эканингизни ёзиб, матн ва расм/видеони юборинг — Озод Жамол тез орада боғланади. Раҳмат!"""

PERSONAL_TEXT = """Ассалому алайкум!
Мен Озод Жамолнинг ИИ-ёрдамчисиман 🤖
Хабарингизни унга етказдим — тез орада ўзи сиз билан боғланади. Раҳмат!"""

AD_WORDS = ("реклам", "reklam", "эълон", "элон", "e'lon", "eʼlon", "elon", "нарх", "narx", "прайс", "price",
            "цена", "стоимост", "сколько стоит", "қанча турад", "qancha tur", "жойла", "joyla", "размест", "тарқат",
            "tarqat")
WORD_RE = re.compile(r"[\s,.!?;:()\"«»]+")


def kind_of(text: str) -> str:
    """'ad' — обращение по рекламе, иначе 'personal'. Только ключевые слова — без ИИ (0 $)."""
    t = " " + WORD_RE.sub(" ", (text or "").lower()) + " "
    return "ad" if any(w in t for w in AD_WORDS) else "personal"


FIX_RIGHTS = """⚠️ ИИ-ассистент получает сообщения, но Telegram НЕ даёт ему отвечать.
Исправить (1 минута):
Настройки → Telegram для бизнеса → Чат-боты → @ozodjamol_ai_bot →
1) «Управление сообщениями» / «Ответ на сообщения» — ВКЛЮЧИТЬ;
2) «Доступ к чатам» — «Все личные чаты» (или хотя бы «Все, кроме контактов»).
После этого напишите себе с другого номера — ассистент ответит."""


def can_reply_of(bc: dict):
    """Право отвечать из business_connection: новое поле rights.can_reply или старое can_reply. None — неизвестно."""
    r = bc.get("rights")
    if isinstance(r, dict) and "can_reply" in r:
        return bool(r["can_reply"])
    if "can_reply" in bc:
        return bool(bc["can_reply"])
    return None


SCHEMA = """
CREATE TABLE IF NOT EXISTS conn (id TEXT PRIMARY KEY, owner INTEGER NOT NULL, owner_chat INTEGER, enabled INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS chats (chat INTEGER PRIMARY KEY, replied_at TEXT, owner_at TEXT, kind TEXT, name TEXT);
CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS msgs (chat INTEGER NOT NULL, role TEXT NOT NULL, text TEXT, at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_msgs ON msgs(chat, at);
"""


def connect(path: str) -> sqlite3.Connection:
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    return db


def _ago(ts: str | None, now: dt.datetime) -> dt.timedelta | None:
    return now - dt.datetime.fromisoformat(ts) if ts else None


def handle(db, upd: dict, api, now: dt.datetime | None = None, ai=None) -> str:
    """Одно обновление Bot API → действие. api(method, **params). Возвращает, что сделано (для журнала/тестов)."""
    now = now or dt.datetime.now(dt.timezone.utc)
    bc = upd.get("business_connection")
    if bc:
        db.execute("INSERT OR REPLACE INTO conn VALUES (?,?,?,?)",
                   (bc["id"], bc["user"]["id"], bc.get("user_chat_id"), int(bc.get("is_enabled", True))))
        db.commit()
        can_reply = can_reply_of(bc)
        print(f"assistant: подключение · ответ разрешён: {can_reply}", flush=True)
        if bc.get("is_enabled", True) and bc.get("user_chat_id"):
            api("sendMessage", chat_id=bc["user_chat_id"],
                text=("✅ ИИ-ассистент подключён к вашему Telegram.\nОтвечаю только на первое сообщение человека "
                      "(реклама — прайс, остальное — «передал, скоро свяжется») и пересылаю вам сюда.")
                if can_reply is not False else FIX_RIGHTS)
        return "connected" if bc.get("is_enabled", True) else "disconnected"
    m = upd.get("business_message")
    if not m:
        return "skip"
    c = db.execute("SELECT * FROM conn WHERE id=?", (m.get("business_connection_id"),)).fetchone()
    if not c or not c["enabled"]:
        return "no_connection"
    chat, frm = m["chat"], m.get("from") or {}
    if chat.get("type") != "private" or frm.get("is_bot"):
        return "skip"
    row = db.execute("SELECT * FROM chats WHERE chat=?", (chat["id"],)).fetchone()
    if frm.get("id") == c["owner"]:                          # владелец ответил сам — дальше бот молчит
        said = _incoming(m)
        _log(db, chat["id"], "owner", said, now)
        if is_auto_owner(db, said, now):                     # 30.10: авто-«Приветствие» Telegram — не живой ответ владельца
            return "owner_auto"
        db.execute("INSERT INTO chats(chat, owner_at) VALUES(?,?) ON CONFLICT(chat) DO UPDATE SET owner_at=excluded.owner_at",
                   (chat["id"], now.isoformat()))
        db.commit()
        return "owner"
    o, r = (_ago(row["owner_at"], now), _ago(row["replied_at"], now)) if row else (None, None)
    text = m.get("text") or m.get("caption") or ""
    if ai is None and os.environ.get("GEMINI_API_KEY"):
        ai = gemini_ai
    if ai is not None:
        if o is not None and o < OWNER_QUIET:            # 30.10: если за сутки от владельца были только авто-приветствия — не молчим
            recent = db.execute("SELECT text FROM msgs WHERE chat=? AND role='owner' AND at>=?",
                                (chat["id"], (now - OWNER_QUIET).isoformat())).fetchall()
            if recent and all(is_auto_owner(db, r[0], now) for r in recent):
                o = None
        if o is not None and o < OWNER_QUIET:           # владелец сам ведёт разговор — молчим
            _log(db, chat["id"], "user", _incoming(m), now)
            return "quiet"
        res = ai_turn(db, c, m, chat, frm, row, api, ai, now)
        if res != "ai_failed":
            return res
        print("assistant: ИИ не ответил — шаблон", flush=True)
    if (o is not None and o < OWNER_QUIET) or (r is not None and r < REPLY_EVERY):
        return "quiet"
    kind = kind_of(text)
    try:
        api("sendMessage", chat_id=chat["id"], business_connection_id=c["id"], text=AD_TEXT if kind == "ad" else PERSONAL_TEXT)
    except RuntimeError as e:
        # 19.10: BUSINESS_PEER_INVALID — у бота нет права отвечать (или чат вне доступа). Владельцу — инструкция, раз в сутки.
        last = db.execute("SELECT v FROM kv WHERE k='rights_alert'").fetchone()
        if c["owner_chat"] and (not last or now - dt.datetime.fromisoformat(last[0]) > dt.timedelta(hours=24)):
            try:
                api("sendMessage", chat_id=c["owner_chat"], text=FIX_RIGHTS + f"\n\n(ошибка Telegram: {str(e)[:80]})")
                db.execute("INSERT OR REPLACE INTO kv VALUES('rights_alert', ?)", (now.isoformat(),))
                db.commit()
            except Exception:  # noqa: BLE001
                pass
        raise
    name = " ".join(x for x in (frm.get("first_name"), frm.get("last_name")) if x) or "—"
    user = f" (@{frm['username']})" if frm.get("username") else ""
    db.execute("INSERT INTO chats(chat, replied_at, kind, name) VALUES(?,?,?,?) ON CONFLICT(chat) DO UPDATE SET "
               "replied_at=excluded.replied_at, kind=excluded.kind, name=excluded.name", (chat["id"], now.isoformat(), kind, name))
    db.commit()
    if c["owner_chat"]:
        head = "📣 РЕКЛАМА" if kind == "ad" else "👤 Личное"
        what = text[:700] if text else "(без текста: " + next((k for k in ("voice", "photo", "video", "sticker", "document",
                                                                           "video_note", "audio") if k in m), "медиа") + ")"
        try:
            api("sendMessage", chat_id=c["owner_chat"], text=f"{head} · {name}{user}\n—\n{what}\n—\n🤖 Ассистент ответил, дальше — вы.")
        except Exception as e:  # noqa: BLE001  — уведомление не должно ломать ответ
            print(f"assistant: уведомление не ушло ({e})", flush=True)
    return kind


# ---------- 30.10: настоящий ИИ-разговор (Gemini, бесплатно) ----------
AI_PER_CHAT_DAY = 20            # не больше ответов ИИ одному человеку в сутки
AI_PER_DAY = 300                # общий предел в сутки (бесплатный лимит Gemini)
HISTORY = 12                    # сколько последних сообщений помнит
HISTORY_FOR = dt.timedelta(hours=48)
KINDS = ("greeting", "ad", "personal", "other")

SYSTEM = """Ты — ИИ-ёрдамчи (ИИ-помощник) Озод Жамола в его личном Telegram (@Ozodjamol).
Озод Жамол — блогер и медиа-владелец из Хўжаобода (Андижон): Telegram-каналы XO'JAOBOD CITY 24, КАТТА ДАВРА, PaparazziUZ,
Instagram @paparazzi.uz. Ты отвечаешь людям, пока он занят.

КАК ОТВЕЧАТЬ: коротко (1–3 предложения), тепло и уважительно (на «сиз»), как воспитанный узбек. Язык — как у собеседника:
узбекский — ТОЛЬКО кириллицей (даже если человек пишет латиницей), русский — по-русски. Ты не Озод Жамол и не выдаёшь себя
за него; если спросят — ты его ИИ-ёрдамчи. Не повторяй одно и то же, учитывай переписку.

ПРАВИЛА:
1) Поздравления и дуо (Жума муборак, байрам, туғилган кун, тилаклар, пересланные открытки/посты с поздравлением) —
   ответь искренним ответным поздравлением и дуо от имени Озод Жамола («Озод Жамол номидан ҳам…»). kind=greeting.
2) Салом / как дела — поприветствуй и спроси, чем можешь помочь. kind=greeting.
3) Реклама — ТОЛЬКО по утверждённому прайсу (ниже), других сумм не называй, скидок не давай. Реклама выходит ТОЛЬКО
   в XO'JAOBOD CITY 24 (в КАТТА ДАВРА и PaparazziUZ рекламы нет). Собери заказ по шагам, не всё сразу:
   что рекламируют → сколько дней (1/3/7) → нужно ли вечернее время и закреп → текст рекламы и фото/видео → желаемая дата.
   Можешь посчитать итог по прайсу (пример: 3 кун + кечки вақт 3 кун = 130 000 + 30 000 = 160 000 сўм).
   Точное время выхода и оплату подтверждает Озод Жамол — так и скажи. Видео/сайт/бот — «нархини Озод Жамол ўзи айтади».
   kind=ad.
ПРАЙС:
""" + PRICE + """
4) Личное (деньги, встречи, просьбы, семья, работа, вопросы о его жизни) — ничего не решай и не выдумывай:
   скажи, что передал и Озод Жамол ответит сам. kind=personal.
5) Никогда не выдумывай факты, номера, адреса, цены (только из прайса). Без политики и религиозных споров.
6) Человек закончил («раҳмат», «ок», стикер) — короткий ответ или пустой reply.
7) Если приложена картинка (открытка, стикер, фото, кадр видео) — смотри на неё: открытка «Жума муборак» = поздравление,
   фото товара/вывески = вероятно реклама. Не описывай картинку, просто отвечай по смыслу.

Ответ — ТОЛЬКО JSON: {"reply": "текст или пусто", "kind": "greeting|ad|personal|other"}"""


def _incoming(m: dict) -> str:
    t = m.get("text") or m.get("caption") or ""
    kind = next((k for k in ("voice", "video_note", "photo", "video", "sticker", "document", "audio", "animation") if k in m), "")
    if m.get("forward_origin") or m.get("forward_from") or m.get("forward_from_chat"):
        t = "[пересланный пост] " + t
    if kind:
        emoji = (m.get("sticker") or {}).get("emoji", "") if kind == "sticker" else ""
        t = f"[{kind}{' ' + emoji if emoji else ''}] {t}".strip()
    return t[:1500]


IMG_MAX = 4 * 1024 * 1024


def image_ref(m: dict) -> tuple[str, str] | None:
    """30.10: что показать ИИ — (file_id, mime): фото, стикер (анимированный — его превью), превью видео/GIF/кружка,
    картинка-документ. Нет картинки — None."""
    if m.get("photo"):
        return m["photo"][-1]["file_id"], "image/jpeg"
    st = m.get("sticker")
    if st:
        if not st.get("is_animated") and not st.get("is_video"):
            return st["file_id"], "image/webp"
        th = st.get("thumbnail") or st.get("thumb")
        return (th["file_id"], "image/webp") if th else None
    for k in ("video", "animation", "video_note"):
        th = (m.get(k) or {}).get("thumbnail") or (m.get(k) or {}).get("thumb")
        if th:
            return th["file_id"], "image/jpeg"
    d = m.get("document") or {}
    if (d.get("mime_type") or "").startswith("image/") and (d.get("file_size") or 0) <= IMG_MAX:
        return d["file_id"], d["mime_type"]
    return None


# 30.10: «Приветствие» Telegram для бизнеса уходит от имени владельца — раньше бот думал, что владелец пишет сам, и молчал сутки.
AUTO_OWNER = {"ассалому алейкум 🙏"}


def is_auto_owner(db, text: str, now: dt.datetime) -> bool:
    """Автосообщение владельца: известный текст или одинаковый текст владельца в 3+ разных чатах за 30 дней."""
    t = (text or "").strip()
    if not t:
        return False
    if t.lower() in AUTO_OWNER:
        return True
    n = db.execute("SELECT COUNT(DISTINCT chat) FROM msgs WHERE role='owner' AND text=? AND at>=?",
                   (t, (now - dt.timedelta(days=30)).isoformat())).fetchone()[0]
    return n >= 3


def _log(db, chat: int, role: str, text: str, now: dt.datetime) -> None:
    db.execute("INSERT INTO msgs VALUES (?,?,?,?)", (chat, role, text, now.isoformat()))
    db.commit()


def _history(db, chat: int, now: dt.datetime) -> list[tuple[str, str]]:
    rows = db.execute("SELECT role, text FROM msgs WHERE chat=? AND at>=? ORDER BY at DESC, rowid DESC LIMIT ?",
                      (chat, (now - HISTORY_FOR).isoformat(), HISTORY)).fetchall()
    return [(r[0], r[1]) for r in reversed(rows)]


def _count(db, chat: int | None, now: dt.datetime) -> int:
    since = (now - dt.timedelta(hours=24)).isoformat()
    if chat is None:
        return db.execute("SELECT COUNT(*) FROM msgs WHERE role='ai' AND at>=?", (since,)).fetchone()[0]
    return db.execute("SELECT COUNT(*) FROM msgs WHERE chat=? AND role='ai' AND at>=?", (chat, since)).fetchone()[0]


def gemini_ai(system: str, history: list[tuple[str, str]], incoming: str, known: bool,
              image: tuple[bytes, str] | None = None) -> dict:
    who = {"user": "Собеседник", "ai": "Ты (ИИ-ёрдамчи)", "owner": "Озод Жамол сам"}
    talk = "\n".join(f"{who.get(r, r)}: {t}" for r, t in history) or "(переписки ещё нет)"
    user = (f"{'Это ЗНАКОМЫЙ Озод Жамола (они уже переписывались).' if known else 'Это новый человек.'}\n"
            f"Переписка (последние сообщения):\n{talk}\n\nНовое сообщение собеседника:\n{incoming}")
    body = {"systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"maxOutputTokens": 2048, "temperature": 0.5, "responseMimeType": "application/json"}}
    if image:
        import base64
        body["contents"][0]["parts"].append({"inlineData": {"mimeType": image[1], "data": base64.b64encode(image[0]).decode()}})
    models = list(dict.fromkeys([os.environ.get("GEMINI_MODEL", "gemini-flash-latest"), "gemini-flash-latest"]))
    data = None
    for i, model in enumerate(models):
        req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                     data=json.dumps(body).encode(),
                                     headers={"content-type": "application/json", "x-goog-api-key": os.environ["GEMINI_API_KEY"]})
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                data = json.loads(r.read())
            break
        except urllib.error.HTTPError as e:
            if e.code not in (500, 503, 404, 429) or i == len(models) - 1:
                raise RuntimeError(f"gemini {e.code}") from None
    parts = ((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
    raw = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
    raw = raw[raw.find("{"): raw.rfind("}") + 1] if "{" in raw else raw
    out = json.loads(raw)
    return {"reply": str(out.get("reply") or "").strip(), "kind": out.get("kind") if out.get("kind") in KINDS else "other"}


def ai_turn(db, c, m: dict, chat: dict, frm: dict, row, api, ai, now: dt.datetime) -> str:
    """Один ход ИИ. Возвращает kind / 'contact_quiet' / 'limit' / 'ai_failed'."""
    cid = chat["id"]
    incoming = _incoming(m)
    known = bool(row and row["owner_at"])             # владелец с этим человеком уже переписывался
    hist = _history(db, cid, now)
    _log(db, cid, "user", incoming, now)
    if _count(db, cid, now) >= AI_PER_CHAT_DAY or _count(db, None, now) >= AI_PER_DAY:
        return "limit"
    img = None
    ref = image_ref(m)
    dl = getattr(api, "download", None)
    if ref and dl:
        try:
            data = dl(ref[0])
            if data and len(data) <= IMG_MAX:
                img = (data, ref[1])
        except Exception as e:  # noqa: BLE001  — без картинки всё равно отвечаем по тексту
            print(f"assistant: картинка не скачалась ({str(e)[:80]})", flush=True)
    try:
        out = ai(SYSTEM, hist, incoming, known, image=img) if img else ai(SYSTEM, hist, incoming, known)
    except Exception as e:  # noqa: BLE001
        print(f"assistant: ИИ ошибка {str(e)[:120]}", flush=True)
        db.execute("DELETE FROM msgs WHERE rowid=(SELECT MAX(rowid) FROM msgs WHERE chat=?)", (cid,))   # шаблон запишет сам
        db.commit()
        return "ai_failed"
    kind, reply = out["kind"], out["reply"]
    if known and kind != "greeting":                  # знакомым — только ответ на поздравление/салом
        return "contact_quiet"
    first_today = not (row and row["replied_at"] and _ago(row["replied_at"], now) < REPLY_EVERY)
    if reply and first_today and "ёрдамчи" not in reply.lower() and "помощник" not in reply.lower():
        reply = "🤖 Озод Жамолнинг ИИ-ёрдамчиси:\n" + reply
    if reply:
        try:
            api("sendMessage", chat_id=cid, business_connection_id=c["id"], text=reply[:3500])
        except RuntimeError:
            raise
        _log(db, cid, "ai", reply, now)
    name = " ".join(x for x in (frm.get("first_name"), frm.get("last_name")) if x) or "—"
    db.execute("INSERT INTO chats(chat, replied_at, kind, name) VALUES(?,?,?,?) ON CONFLICT(chat) DO UPDATE SET "
               "replied_at=COALESCE(excluded.replied_at, chats.replied_at), kind=excluded.kind, name=excluded.name",
               (cid, now.isoformat() if reply else None, kind, name))
    db.commit()
    # владельцу: новый человек — первое обращение за сутки; реклама — каждый раз
    if c["owner_chat"] and not known and (first_today or kind == "ad"):
        head = {"ad": "📣 РЕКЛАМА", "greeting": "🤝 Салом/табрик", "personal": "👤 Личное"}.get(kind, "💬 Сообщение")
        user = f" (@{frm['username']})" if frm.get("username") else ""
        try:
            api("sendMessage", chat_id=c["owner_chat"],
                text=f"{head} · {name}{user}\n—\n{incoming[:600] or '(медиа)'}\n—\n🤖 {reply[:400] or '(промолчал)'}")
        except Exception as e:  # noqa: BLE001
            print(f"assistant: уведомление не ушло ({e})", flush=True)
    return kind


STRANGER_START = """Ассалому алайкум!
Бу — Озод Жамолнинг ИИ-ёрдамчиси 🤖
Реклама ва бошқа масалалар бўйича тўғридан-тўғри @Ozodjamol га ёзинг — ёрдамчи дарҳол жавоб беради."""


def start_text(db, msg: dict) -> str:
    """18.10: бот только для владельца. Владелец — уведомления; посторонний — короткая подсказка написать @Ozodjamol."""
    owners = {r[0] for r in db.execute("SELECT owner FROM conn")}
    if (msg.get("from") or {}).get("id") in owners:
        return "🤖 ИИ-ассистент Озод Жамола. Сюда приходят уведомления о новых обращениях."
    return STRANGER_START


def api_for(token: str):
    def api(method: str, **p):
        data = urllib.parse.urlencode({k: (json.dumps(v) if isinstance(v, (list, dict)) else v) for k, v in p.items()}).encode()
        try:
            with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/{method}", data=data, timeout=70) as r:
                out = json.loads(r.read())
        except urllib.error.HTTPError as e:
            out = json.loads(e.read() or b"{}")
        if not out.get("ok"):
            raise RuntimeError(f"{method}: {out.get('description')}")
        return out["result"]

    def download(file_id: str) -> bytes:
        """30.10: файл из сообщения (картинка для ИИ). Токен в ошибки не попадает."""
        path = api("getFile", file_id=file_id).get("file_path")
        if not path:
            return b""
        with urllib.request.urlopen(f"https://api.telegram.org/file/bot{token}/{path}", timeout=30) as r:
            return r.read(IMG_MAX + 1)
    api.download = download
    return api


def loop() -> None:
    token = os.environ["ASSISTANT_BOT_TOKEN"]
    db = connect(os.environ.get("PAPA_ASSISTANT_DB", "/var/lib/papa-assistant/assistant.sqlite3"))
    api = api_for(token)
    me = api("getMe")
    print(f"ИИ-ассистент @{me['username']} запущен", flush=True)
    off = int((db.execute("SELECT v FROM kv WHERE k='offset'").fetchone() or ["0"])[0])
    while True:
        try:
            ups = api("getUpdates", offset=off, timeout=50,
                      allowed_updates=["business_connection", "business_message", "message"])
        except Exception as e:  # noqa: BLE001
            print(f"assistant: getUpdates {e}", flush=True)
            time.sleep(10)
            continue
        for u in ups:
            off = u["update_id"] + 1
            try:
                if u.get("message", {}).get("text", "").startswith("/start"):
                    api("sendMessage", chat_id=u["message"]["chat"]["id"], text=start_text(db, u["message"]))
                else:
                    res = handle(db, u, api)
                    if res not in ("skip", "quiet", "owner"):
                        print(f"assistant: {res}", flush=True)
            except Exception as e:  # noqa: BLE001
                print(f"assistant: ошибка {e}", flush=True)
            db.execute("INSERT OR REPLACE INTO kv VALUES('offset', ?)", (str(off),))
            db.commit()


if __name__ == "__main__":
    loop()
