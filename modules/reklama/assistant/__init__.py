"""ИИ-ассистент личного Telegram владельца (@Ozodjamol) через Telegram Business (решение 17.10).

30.10 (утверждено: «все пункты нормальные, одобряю»): первый раз (после паузы больше часа) или на любое «салом» — «Ассалому алайкум ва
раҳматуллоҳи ва барокатуҳ! Мен — Озод Жамолнинг ИИ-ёрдамчисиман» + 3 кнопки (📣 Реклама / 🎬 Бошқа иш / 👤 Шахсий);
поздравление — сначала ответное поздравление, потом меню; ясная просьба — приветствие и сразу ответ по делу; кнопки не
прошли — меню цифрами 1/2/3. Отвечает ВСЕГДА, на каждое сообщение, и знакомым тоже (владелец: «хоть 5 раз, хоть 10»);
молчит только 30 мин после живого ответа владельца в этом чате. Альбом — один ответ.

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

REPLY_EVERY = dt.timedelta(hours=1)         # 30.10: пауза больше часа = новый разговор → снова приветствие + меню (было 24 ч)
HELLO_WORDS = ("салом", "салам", "ассалом", "assalom", "salom", "привет", "здравств", "хорманг", "hormang", "яхшимисиз",
               "yaxshimisiz", "қалайсиз", "qalaysiz")
MENU_AGAIN = dt.timedelta(minutes=10)       # «салом» → меню заново, но не чаще раза в 10 мин (без спама меню)
OWNER_QUIET = dt.timedelta(minutes=30)      # 30.10: молчит, только пока владелец сам ведёт живой разговор (было 24 ч)
SHORT_TEXT = "Хабарингизни Озод Жамолга етказдим 🙏 Тез орада ўзи жавоб беради."

PRICE = """📣 XO'JAOBOD CITY 24 — РЕКЛАМА
1) 1 кун — 50 000 сўм
2) 3 кун (ҳар куни 1 марта) — 130 000 сўм
3) 7 кун (ҳар куни 1 марта) — 280 000 сўм
4) Кечки вақт (18:00–20:00) — +10 000 сўм
5) Тепада қадаб қўйиш (1 кун) — +20 000 сўм
6) «Дам олиш кунлари қаерга борамиз?» жума подборкасида жой — 50 000 сўм (ҳафтасига 3 та жой)
Реклама 10 дақиқа энг тепада туради.

🎬 Моушн-реклама пакети — 500 000 сўм (замонавий моушн-видео + 1 ҳафта ҳар куни XO'JAOBOD CITY 24 да)
🎥 Реклама видеоролик (моушн / ИИ) — нархи иш ҳажмига қараб, Озод Жамол ўзи айтади
💻 Сайт, Telegram-бот — нархи келишилади
Буюртма: @Ozodjamol"""   # 30.10 утверждено владельцем («согласен»); 31.10 + п.6 подборка выходных (владелец: 50 000, 3 места)

# 30.10 (утверждено владельцем): тёплое приветствие + меню из 3 кнопок вместо «пустого» шаблона.
GREETING_HEAD = """Ассалому алайкум ва раҳматуллоҳи ва барокатуҳ! 🤝
Мен — Озод Жамолнинг ИИ-ёрдамчисиман."""
GREETING = GREETING_HEAD + "\nСизга қайси масалада ёрдам бера оламан? 👇"
MENU = (("📣 Реклама бўйича", "ad"), ("🎬 Бошқа иш юзасидан (видео, сайт, бот)", "work"), ("👤 Шахсий масала", "me"))
MENU_MARK = "[МЕНЮ]"
MENU_NUMBERS = "\n\n" + "\n".join(f"{n} {t.split(' ', 1)[1]}" for n, (t, _) in zip(("1️⃣", "2️⃣", "3️⃣"), MENU)) + "\n\nКеракли рақамни ёзинг 🙂"
BRANCH = {
    "ad": """Реклама «Хўжаобод Сити 24» каналида чиқади:
▫️ 1 кун — 50 000 сўм
▫️ 3 кун — 130 000 сўм
▫️ 7 кун — 280 000 сўм
▫️ Кечки вақт (18:00–20:00) — +10 000
▫️ 1 кунга юқорига қадаш — +20 000
▫️ «Дам олиш кунлари қаерга борамиз?» подборкасида жой — 50 000 (ҳафтасига 3 та)
▫️ Моушн-видео + 1 ҳафта реклама — 500 000

Реклама матни, расм ёки видеони юборинг — тайёрлаб, Озод Жамолга тасдиққа бераман ✅""",
    "work": "Ажойиб! Қисқача ёзинг: нима керак, қайси соҳа ва қачонгача. Озод Жамол ўзи сиз билан боғланади 🤝",
    "me": "Хабарингизни шу ерга ёзиб қолдиринг — Озод Жамолга албатта етказаман, у ўзи жавоб беради 🙏",
}
BRANCH_KIND = {"ad": "ad", "work": "work", "me": "personal"}
PICK_NUM = {"1": "ad", "1️⃣": "ad", "2": "work", "2️⃣": "work", "3": "me", "3️⃣": "me"}

AD_TEXT = GREETING_HEAD + """

""" + PRICE + """

Нимани реклама қилмоқчи эканингизни ёзиб, матн ва расм/видеони юборинг — Озод Жамол тез орада боғланади. Раҳмат!"""

PERSONAL_TEXT = GREETING_HEAD + """
Хабарингизни унга етказдим — тез орада ўзи сиз билан боғланади. Раҳмат!"""


def _who(frm: dict) -> tuple[str, str]:
    name = " ".join(x for x in (frm.get("first_name"), frm.get("last_name")) if x) or "—"
    return name, (f" (@{frm['username']})" if frm.get("username") else "")


def send_menu(db, api, c, cid: int, now: dt.datetime) -> None:
    """Приветствие + 3 кнопки. Кнопки не прошли (не ошибка прав) — то же меню цифрами 1/2/3."""
    kb = {"inline_keyboard": [[{"text": t, "callback_data": "m:" + k}] for t, k in MENU]}
    try:
        api("sendMessage", chat_id=cid, business_connection_id=c["id"], text=GREETING, reply_markup=kb)
    except RuntimeError as e:
        if "PEER_INVALID" in str(e) or "not enough rights" in str(e).lower():
            raise
        print(f"assistant: кнопки не прошли ({str(e)[:80]}) — меню цифрами", flush=True)
        api("sendMessage", chat_id=cid, business_connection_id=c["id"], text=GREETING + MENU_NUMBERS)
    _log(db, cid, "ai", MENU_MARK + " " + GREETING + MENU_NUMBERS, now)


def last_was_menu(db, cid: int, now: dt.datetime) -> bool:
    r = db.execute("SELECT text FROM msgs WHERE chat=? AND role='ai' AND at>=? ORDER BY at DESC, rowid DESC LIMIT 1",
                   (cid, (now - HISTORY_FOR).isoformat())).fetchone()
    return bool(r and (r[0] or "").startswith(MENU_MARK))


def menu_recent(db, cid: int, now: dt.datetime) -> bool:
    return bool(db.execute("SELECT 1 FROM msgs WHERE chat=? AND role='ai' AND text LIKE ? AND at>=? LIMIT 1",
                           (cid, MENU_MARK + "%", (now - MENU_AGAIN).isoformat())).fetchone())


def choose(db, api, c, cid: int, frm: dict, branch: str, now: dt.datetime) -> str:
    """Человек выбрал пункт меню (кнопкой или цифрой) → ответ ветки + уведомление владельцу."""
    last = db.execute("SELECT v FROM kv WHERE k=?", (f"pick:{cid}",)).fetchone()
    if last and last[0].split("|")[0] == branch and now - dt.datetime.fromisoformat(last[0].split("|")[1]) < dt.timedelta(minutes=2):
        return "pick_dup"                                  # двойное нажатие — второй раз не отвечаем
    api("sendMessage", chat_id=cid, business_connection_id=c["id"], text=BRANCH[branch])
    _log(db, cid, "ai", BRANCH[branch], now)
    kind = BRANCH_KIND[branch]
    name, user = _who(frm)
    db.execute("INSERT OR REPLACE INTO kv VALUES (?,?)", (f"pick:{cid}", f"{branch}|{now.isoformat()}"))
    db.execute("INSERT INTO chats(chat, replied_at, kind, name) VALUES(?,?,?,?) ON CONFLICT(chat) DO UPDATE SET "
               "replied_at=excluded.replied_at, kind=excluded.kind, name=excluded.name", (cid, now.isoformat(), kind, name))
    db.commit()
    if c["owner_chat"]:
        label = dict((k, t) for t, k in MENU)[branch]
        try:
            api("sendMessage", chat_id=c["owner_chat"], text=f"{label} · {name}{user}\n—\n🤖 Выбрал пункт меню, ассистент ведёт дальше.")
        except Exception as e:  # noqa: BLE001
            print(f"assistant: уведомление не ушло ({e})", flush=True)
    return "pick_" + branch


def handle_callback(db, q: dict, api, now: dt.datetime) -> str:
    data = q.get("data") or ""
    try:
        api("answerCallbackQuery", callback_query_id=q["id"])
    except Exception:  # noqa: BLE001
        pass
    if data.startswith("o:"):
        return order_callback(db, q, api, now)
    if not data.startswith("m:") or data[2:] not in BRANCH:
        return "skip"
    m = q.get("message") or {}
    cid = (m.get("chat") or {}).get("id")
    bcid = m.get("business_connection_id")
    c = db.execute("SELECT * FROM conn WHERE id=?", (bcid,)).fetchone() if bcid else None
    c = c or db.execute("SELECT * FROM conn WHERE enabled=1 LIMIT 1").fetchone()
    if not c or not c["enabled"] or not cid:
        return "no_connection"
    return choose(db, api, c, cid, q.get("from") or {}, data[2:], now)

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
CREATE TABLE IF NOT EXISTS ad_media (chat INTEGER NOT NULL, kind TEXT NOT NULL, file_id TEXT NOT NULL, at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS orders (chat INTEGER NOT NULL, at TEXT NOT NULL, summary TEXT);
CREATE TABLE IF NOT EXISTS packs (id INTEGER PRIMARY KEY, chat INTEGER NOT NULL, bc TEXT, name TEXT, at TEXT NOT NULL,
                                  order_json TEXT, media TEXT, state TEXT NOT NULL DEFAULT 'new');
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
    if upd.get("callback_query"):
        return handle_callback(db, upd["callback_query"], api, now)
    bc = upd.get("business_connection")
    if bc:
        db.execute("INSERT OR REPLACE INTO conn VALUES (?,?,?,?)",
                   (bc["id"], bc["user"]["id"], bc.get("user_chat_id"), int(bc.get("is_enabled", True))))
        db.commit()
        can_reply = can_reply_of(bc)
        print(f"assistant: подключение · ответ разрешён: {can_reply}", flush=True)
        if bc.get("is_enabled", True) and bc.get("user_chat_id"):
            api("sendMessage", chat_id=bc["user_chat_id"],
                text=("✅ ИИ-ассистент подключён к вашему Telegram.\nНовому человеку — приветствие и меню "
                      "(Реклама / Бошқа иш / Шахсий), дальше веду разговор; знакомым — только ответ на поздравления. "
                      "Обращения пересылаю вам сюда.")
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
    mg = m.get("media_group_id")                         # альбом = несколько сообщений — отвечаем один раз
    if mg:
        if db.execute("SELECT 1 FROM kv WHERE k=?", (f"mg:{mg}",)).fetchone():
            _log(db, chat["id"], "user", _incoming(m), now)
            save_media(db, chat["id"], m, now)
            return "album_dup"
        db.execute("INSERT OR REPLACE INTO kv VALUES (?,?)", (f"mg:{mg}", now.isoformat()))
        db.commit()
    pick = PICK_NUM.get(text.strip())
    if pick and not (o is not None and o < OWNER_QUIET) and last_was_menu(db, chat["id"], now):
        _log(db, chat["id"], "user", text.strip(), now)
        return choose(db, api, c, chat["id"], frm, pick, now)
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
        if res not in ("ai_failed", "limit"):
            return res
        print(f"assistant: ИИ не ответил ({res}) — шаблон", flush=True)
    if o is not None and o < OWNER_QUIET:
        return "quiet"
    kind = kind_of(text)
    try:
        hello = any(w in text.lower() for w in HELLO_WORDS) and len(text) < 60
        if r is not None and r < REPLY_EVERY and (menu_recent(db, chat["id"], now) or not hello):   # в разговоре — коротко
            api("sendMessage", chat_id=chat["id"], business_connection_id=c["id"], text=AD_TEXT if kind == "ad" else SHORT_TEXT)
        elif kind == "ad":
            api("sendMessage", chat_id=chat["id"], business_connection_id=c["id"], text=AD_TEXT)
        else:
            send_menu(db, api, c, chat["id"], now)          # 30.10: вместо «передал» — приветствие и меню
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
AI_PER_CHAT_DAY = 40            # не больше ответов ИИ одному человеку в сутки
AI_PER_DAY = 300                # общий предел в сутки (бесплатный лимит Gemini)
HISTORY = 12                    # сколько последних сообщений помнит
HISTORY_FOR = dt.timedelta(hours=48)
KINDS = ("greeting", "congrats", "ad", "work", "personal", "other")

SYSTEM = """Ты — ИИ-ёрдамчи (ИИ-помощник) Озод Жамола в его личном Telegram (@Ozodjamol).
Озод Жамол — блогер и медиа-владелец из Хўжаобода (Андижон): Telegram-каналы XO'JAOBOD CITY 24, КАТТА ДАВРА, PaparazziUZ,
Instagram @paparazzi.uz. Ты отвечаешь людям, пока он занят.

КАК ОТВЕЧАТЬ: коротко (1–3 предложения), тепло и уважительно (на «сиз»), как воспитанный узбек. Язык — как у собеседника:
узбекский — ТОЛЬКО кириллицей (даже если человек пишет латиницей), русский — по-русски. Ты не Озод Жамол и не выдаёшь себя
за него; если спросят — ты его ИИ-ёрдамчи. Не повторяй одно и то же, учитывай переписку.

ПРИВЕТСТВИЕ И МЕНЮ отправляет сам бот: «Ассалому алайкум ва раҳматуллоҳи ва барокатуҳ! Мен — Озод Жамолнинг
ИИ-ёрдамчисиман» + кнопки «📣 Реклама бўйича / 🎬 Бошқа иш юзасидан (видео, сайт, бот) / 👤 Шахсий масала». Ты не
представляйся заново и не перечисляй меню. Если человек выбрал пункт — продолжай разговор по нему.

ПРАВИЛА:
1) Поздравления и дуо (Жума муборак, байрам, туғилган кун, тилаклар, пересланные открытки/посты с поздравлением) —
   ответь искренним ответным поздравлением и дуо от имени Озод Жамола («Озод Жамол номидан ҳам…»). kind=congrats.
2) Просто салом / как дела без просьбы — короткое ответное приветствие. kind=greeting.
2б) Бошқа иш (заказать видеоролик, моушн, сайт, Telegram-бот): узнай коротко, что нужно, соҳа и срок; цену не называй —
   «нархини Озод Жамол ўзи айтади», он сам свяжется. kind=work.
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

8) Заказ рекламы готов, когда клиент дал: что рекламирует, текст рекламы, хотя бы одно фото/видео ([photo]/[video] в
   переписке), число дней (1/3/7) и дату. Тогда order.ready=true, скажи клиенту, что заказ передан Озод Жамолу и он
   подтвердит время и оплату. Иначе order.ready=false и спрашивай недостающее по одному.

Ответ — ТОЛЬКО JSON: {"reply": "текст или пусто", "kind": "greeting|congrats|ad|work|personal|other",
 "order": {"ready": false, "what": "", "days": 1, "evening": false, "pin": false, "date": "", "total": 0,
           "ad_text": "текст рекламы клиента дословно"}}"""


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
    # 30.10: с картинкой основная модель «думала» дольше 40 с → шаблон. Теперь: основная 60 с, потом быстрая lite 30 с.
    models = list(dict.fromkeys([os.environ.get("GEMINI_MODEL", "gemini-flash-latest"), "gemini-flash-lite-latest"]))
    data, last = None, None
    for i, model in enumerate(models):
        req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                     data=json.dumps(body).encode(),
                                     headers={"content-type": "application/json", "x-goog-api-key": os.environ["GEMINI_API_KEY"]})
        try:
            with urllib.request.urlopen(req, timeout=60 if i == 0 else 30) as r:
                data = json.loads(r.read())
            break
        except urllib.error.HTTPError as e:
            last = f"gemini {model} {e.code}"
            if e.code not in (500, 503, 404, 429, 400):
                raise RuntimeError(last) from None
        except Exception as e:  # noqa: BLE001 — таймаут/сеть: пробуем быструю модель
            last = f"gemini {model} {type(e).__name__}"
    if data is None:
        raise RuntimeError(last or "gemini: нет ответа")
    parts = ((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
    raw = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
    raw = raw[raw.find("{"): raw.rfind("}") + 1] if "{" in raw else raw
    out = json.loads(raw)
    return {"reply": str(out.get("reply") or "").strip(), "kind": out.get("kind") if out.get("kind") in KINDS else "other",
            "order": out.get("order") if isinstance(out.get("order"), dict) else {}}


def save_media(db, chat: int, m: dict, now: dt.datetime) -> None:
    """30.10: фото/видео клиента — для готового заказа рекламы."""
    if m.get("photo"):
        db.execute("INSERT INTO ad_media VALUES (?,?,?,?)", (chat, "photo", m["photo"][-1]["file_id"], now.isoformat()))
    for k in ("video", "animation", "document"):
        if m.get(k) and (k != "document" or (m[k].get("mime_type") or "").startswith(("image/", "video/"))):
            db.execute("INSERT INTO ad_media VALUES (?,?,?,?)", (chat, k, m[k]["file_id"], now.isoformat()))
    db.commit()


def send_order(db, api, owner_chat: int, chat: int, name: str, username: str | None, order: dict,
               now: dt.datetime, bc: str | None = None) -> bool:
    """💰 30.10 «реклама под ключ», этап 1: готовый заказ — владельцу одним пакетом (сводка + реклама как есть),
    чтобы переслать в пульт Хўжаобода. Один заказ от человека — не чаще раза в 6 ч."""
    last = db.execute("SELECT at FROM orders WHERE chat=? ORDER BY at DESC LIMIT 1", (chat,)).fetchone()
    if last and now - dt.datetime.fromisoformat(last[0]) < dt.timedelta(hours=6):
        return False
    since = (now - dt.timedelta(days=2)).isoformat()
    media = db.execute("SELECT kind, file_id FROM ad_media WHERE chat=? AND at>=? ORDER BY at DESC LIMIT 3",
                       (chat, since)).fetchall()
    opts = [f"{int(order.get('days') or 1)} кун"] + (["кечки вақт"] if order.get("evening") else []) + \
           (["тепада қадаб"] if order.get("pin") else [])
    total = int(order.get("total") or 0)
    who = name + (f" (@{username})" if username else "")
    head = (f"💰 ЗАКАЗ РЕКЛАМЫ · {who}\n—\n📦 {order.get('what') or '—'}\n🗓 {order.get('date') or 'дата не указана'} · "
            + " · ".join(opts) + (f"\n💵 по прайсу: {total:,} сўм".replace(",", " ") if total else "")
            + "\n—\nНиже — реклама как есть. Перешлите её в пульт Хўжаобода → 📣 Реклама → время → ✅."
            + "\nОплату и время клиенту подтверждаете вы.")
    text = (order.get("ad_text") or "").strip()[:1000]
    cur = db.execute("INSERT INTO packs(chat, bc, name, at, order_json, media) VALUES(?,?,?,?,?,?)",
                     (chat, bc, who, now.isoformat(), json.dumps(order, ensure_ascii=False),
                      json.dumps([list(x) for x in reversed(media)])))
    pid = cur.lastrowid
    head = head.replace("\nНиже — реклама как есть. Перешлите её в пульт Хўжаобода → 📣 Реклама → время → ✅.",
                        "\nНиже — реклама как есть. ✅ — сам положу её в пульт Хўжаобода, останется выбрать время.")
    api("sendMessage", chat_id=owner_chat, text=head[:4000], reply_markup={"inline_keyboard": [[
        {"text": "✅ В пульт Хўжаобода", "callback_data": f"o:ok:{pid}"}, {"text": "❌ Не берём", "callback_data": f"o:no:{pid}"}]]})
    sent_media = False
    for k, fid in reversed(media):
        method = {"photo": "sendPhoto", "video": "sendVideo", "animation": "sendAnimation"}.get(k, "sendDocument")
        field = {"photo": "photo", "video": "video", "animation": "animation"}.get(k, "document")
        try:
            api(method, chat_id=owner_chat, **{field: fid}, caption=text if not sent_media else "")
            sent_media = True
        except Exception as e:  # noqa: BLE001
            print(f"assistant: медиа заказа не ушло ({str(e)[:80]})", flush=True)
    if not sent_media and text:
        api("sendMessage", chat_id=owner_chat, text=text)
    db.execute("INSERT INTO orders VALUES (?,?,?)", (chat, now.isoformat(), head[:500]))
    db.commit()
    return True


ADS_INBOX = os.environ.get("PAPA_ADS_INBOX", "/var/lib/papa-ads-inbox")
FILE_MAX = 20 * 1024 * 1024                 # предел Bot API на скачивание


def order_callback(db, q: dict, api, now: dt.datetime, inbox: str | None = None) -> str:
    """💰 31.10 «реклама под ключ», этап 2: владелец жмёт ✅ под заказом → пакет (текст + файлы) кладётся в папку,
    GENPLAN сам открывает его в пульте Хўжаобода экраном «📣 когда выпустить?». ❌ — заказ закрыт, клиенту ничего не шлём."""
    _, act, pid = (q.get("data") or "o:x:0").split(":", 2)
    owners = {r[0] for r in db.execute("SELECT owner FROM conn")}
    if (q.get("from") or {}).get("id") not in owners:
        return "skip"
    p = db.execute("SELECT * FROM packs WHERE id=?", (int(pid) if pid.isdigit() else 0,)).fetchone()
    m = q.get("message") or {}
    chat_id, mid = (m.get("chat") or {}).get("id"), m.get("message_id")

    def mark(note: str) -> None:
        try:
            api("editMessageReplyMarkup", chat_id=chat_id, message_id=mid, reply_markup={"inline_keyboard": [[
                {"text": note, "callback_data": "o:x:0"}]]})
        except Exception:  # noqa: BLE001
            pass
    if not p or p["state"] != "new":
        mark("✔️ уже сделано")
        return "order_done"
    if act == "no":
        db.execute("UPDATE packs SET state='no' WHERE id=?", (p["id"],)); db.commit()
        mark("❌ Не берём")
        return "order_no"
    if act != "ok":
        return "skip"
    base = os.path.join(inbox or ADS_INBOX, f"order-{p['id']}")
    os.makedirs(base, exist_ok=True)
    os.chmod(base, 0o2770)                                    # GENPLAN (группа папки) читает и удаляет
    files = []
    for i, (kind, fid) in enumerate(json.loads(p["media"] or "[]")):
        try:
            data = api.download(fid, FILE_MAX) if hasattr(api, "download") else b""
        except Exception as e:  # noqa: BLE001
            print(f"assistant: файл заказа не скачался ({str(e)[:80]})", flush=True)
            data = b""
        if not data or len(data) > FILE_MAX:
            continue
        ext = {"photo": "jpg", "video": "mp4", "animation": "mp4"}.get(kind, "bin")
        fn = f"{i}.{ext}"
        with open(os.path.join(base, fn), "wb") as f:
            f.write(data)
        os.chmod(os.path.join(base, fn), 0o660)
        files.append({"kind": kind, "file": fn})
    order = json.loads(p["order_json"] or "{}")
    meta = {"id": p["id"], "client_chat": p["chat"], "bc": p["bc"], "client": p["name"], "at": now.isoformat(),
            "text": (order.get("ad_text") or "").strip()[:1000], "media": files, "days": int(order.get("days") or 1),
            "evening": bool(order.get("evening")), "pin": bool(order.get("pin")), "what": order.get("what") or "",
            "date": order.get("date") or ""}
    tmp = os.path.join(base, "meta.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)
    os.chmod(tmp, 0o660)
    os.replace(tmp, os.path.join(base, "meta.json"))          # meta.json — последним: GENPLAN не возьмёт половину
    db.execute("UPDATE packs SET state='sent' WHERE id=?", (p["id"],)); db.commit()
    mark("⏳ Ушло в пульт Хўжаобода — выберите там время")
    return "order_ok"


DONE_TEXT = """✅ Рекламангиз «Хўжаобод Сити 24» да чиқди!
{link}
Ишончингиз учун раҳмат 🤝 Яна реклама керак бўлса — шу ерга ёзинг."""


def client_reports(db, api, inbox: str | None = None) -> int:
    """💰 31.10: GENPLAN выпустил рекламу из заказа → клиенту в его чат (через Telegram Business) «чиқди ✅» + ссылка.
    Не вышло отправить (клиент давно не писал — Telegram не даёт) — владельцу готовый текст, чтобы переслал сам."""
    base = inbox or ADS_INBOX
    try:
        names = sorted(n for n in os.listdir(base) if n.startswith("done-") and n.endswith(".json"))
    except OSError:
        return 0
    n = 0
    for name in names:
        path = os.path.join(base, name)
        try:
            d = json.load(open(path, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        text = DONE_TEXT.format(link=d.get("link") or "")
        try:
            api("sendMessage", chat_id=d["client_chat"], business_connection_id=d.get("bc"), text=text)
            note = f"✅ Клиенту {d.get('client') or ''} сообщил: реклама вышла · {d.get('link') or ''}"
        except Exception as e:  # noqa: BLE001
            note = (f"⚠️ Клиенту {d.get('client') or ''} не смог написать ({str(e)[:60]}). Перешлите ему сами:\n\n" + text)
        owner = db.execute("SELECT owner_chat FROM conn WHERE id=?", (d.get("bc"),)).fetchone() or \
            db.execute("SELECT owner_chat FROM conn WHERE enabled=1 LIMIT 1").fetchone()
        if owner and owner[0]:
            try:
                api("sendMessage", chat_id=owner[0], text=note[:4000])
            except Exception:  # noqa: BLE001
                pass
        os.remove(path)
        n += 1
    return n


def ai_turn(db, c, m: dict, chat: dict, frm: dict, row, api, ai, now: dt.datetime) -> str:
    """Один ход ИИ. Возвращает kind / 'contact_quiet' / 'limit' / 'ai_failed'."""
    cid = chat["id"]
    incoming = _incoming(m)
    known = bool(row and row["owner_at"])             # владелец с этим человеком уже переписывался
    hist = _history(db, cid, now)
    _log(db, cid, "user", incoming, now)
    save_media(db, cid, m, now)
    if _count(db, cid, now) >= AI_PER_CHAT_DAY or _count(db, None, now) >= AI_PER_DAY:
        return "limit"
    try:                                              # «печатает…» — человек видит, что ответ готовится
        api("sendChatAction", chat_id=cid, business_connection_id=c["id"], action="typing")
    except Exception:  # noqa: BLE001
        pass
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
    # 30.10 (владелец: «всегда надо отвечать, хоть 5 раз, хоть 10»): знакомым тоже отвечаем — ограничение «знакомый» убрано
    first_today = not (row and row["replied_at"] and _ago(row["replied_at"], now) < REPLY_EVERY)
    menu = False
    if not first_today and kind in ("greeting", "other") and not menu_recent(db, cid, now):
        reply, menu = "", True                        # 30.10: «салом» посреди дня — тоже начинаем заново: приветствие + меню
    elif first_today:                                 # 30.10: первый раз за сутки — тёплое приветствие
        if kind in ("greeting", "other") or not reply:
            reply, menu = "", True                    # просто салом / непонятно → приветствие + меню
        elif kind == "congrats":
            menu = True                               # сначала ответное поздравление, потом меню
        elif "ёрдамчи" not in reply.lower() and "помощник" not in reply.lower():
            reply = GREETING_HEAD + "\n\n" + reply     # ясная просьба → приветствие и сразу ответ по делу
    if reply:
        try:
            api("sendMessage", chat_id=cid, business_connection_id=c["id"], text=reply[:3500])
        except RuntimeError:
            raise
        _log(db, cid, "ai", reply, now)
    if menu:
        send_menu(db, api, c, cid, now)
        reply = reply or "(приветствие + меню)"
    name = " ".join(x for x in (frm.get("first_name"), frm.get("last_name")) if x) or "—"
    if kind == "ad" and (out.get("order") or {}).get("ready") and c["owner_chat"]:
        send_order(db, api, c["owner_chat"], cid, name, frm.get("username"), out["order"], now, bc=c["id"])
    db.execute("INSERT INTO chats(chat, replied_at, kind, name) VALUES(?,?,?,?) ON CONFLICT(chat) DO UPDATE SET "
               "replied_at=COALESCE(excluded.replied_at, chats.replied_at), kind=excluded.kind, name=excluded.name",
               (cid, now.isoformat() if reply else None, kind, name))
    db.commit()
    # владельцу: новый человек — первое обращение за сутки; реклама — каждый раз
    if c["owner_chat"] and (first_today or kind == "ad"):
        head = {"ad": "📣 РЕКЛАМА", "greeting": "🤝 Салом", "congrats": "🤝 Табрик", "work": "🎬 Работа (видео/сайт/бот)",
                "personal": "👤 Личное"}.get(kind, "💬 Сообщение")
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

    def download(file_id: str, limit: int = IMG_MAX) -> bytes:
        """30.10: файл из сообщения (картинка для ИИ; 31.10 — и файлы заказа). Токен в ошибки не попадает."""
        path = api("getFile", file_id=file_id).get("file_path")
        if not path:
            return b""
        with urllib.request.urlopen(f"https://api.telegram.org/file/bot{token}/{path}", timeout=120) as r:
            return r.read(limit + 1)
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
            ups = api("getUpdates", offset=off, timeout=25,
                      allowed_updates=["business_connection", "business_message", "message", "callback_query"])
        except Exception as e:  # noqa: BLE001
            print(f"assistant: getUpdates {e}", flush=True)
            time.sleep(10)
            continue
        try:
            client_reports(db, api)
        except Exception as e:  # noqa: BLE001
            print(f"assistant: отчёт клиенту {e}", flush=True)
        for u in ups:
            off = u["update_id"] + 1
            try:
                if u.get("message", {}).get("text", "").startswith("/start"):
                    api("sendMessage", chat_id=u["message"]["chat"]["id"], text=start_text(db, u["message"]))
                else:
                    res = handle(db, u, api)
                    if res not in ("skip", "quiet", "owner", "pick_dup"):
                        print(f"assistant: {res}", flush=True)
            except Exception as e:  # noqa: BLE001
                print(f"assistant: ошибка {e}", flush=True)
            db.execute("INSERT OR REPLACE INTO kv VALUES('offset', ?)", (str(off),))
            db.commit()


if __name__ == "__main__":
    loop()
