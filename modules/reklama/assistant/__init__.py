"""ИИ-ассистент личного Telegram владельца (@Ozodjamol) через Telegram Business (решение 17.10).

Отвечает ТОЛЬКО на первое сообщение человека (раз в сутки на чат), всегда представляется ИИ-ассистентом:
- 📣 реклама → готовый ответ с прайсом (50 000 сўм — пост сразу в трёх каналах);
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

AD_TEXT = """Ассалому алайкум!
Мен Озоджамолнинг ИИ-ёрдамчисиман 🤖
Реклама бўйича: 50 000 сўм — постингиз бир вақтда учта каналимизда чиқади:
📍 XO'JAOBOD CITY 24
🌍 КАТТА ДАВРА
🎵 PaparazziUZ
Нимани реклама қилмоқчи эканингизни ёзиб, матн ва расм/видеони юборинг — Озоджамол тез орада боғланади. Раҳмат!"""

PERSONAL_TEXT = """Ассалому алайкум!
Мен Озоджамолнинг ИИ-ёрдамчисиман 🤖
Хабарингизни унга етказдим — тез орада ўзи сиз билан боғланади. Раҳмат!"""

AD_WORDS = ("реклам", "reklam", "эълон", "элон", "e'lon", "eʼlon", "elon", "нарх", "narx", "прайс", "price",
            "цена", "стоимост", "сколько стоит", "қанча турад", "qancha tur", "жойла", "joyla", "размест", "тарқат",
            "tarqat")
WORD_RE = re.compile(r"[\s,.!?;:()\"«»]+")


def kind_of(text: str) -> str:
    """'ad' — обращение по рекламе, иначе 'personal'. Только ключевые слова — без ИИ (0 $)."""
    t = " " + WORD_RE.sub(" ", (text or "").lower()) + " "
    return "ad" if any(w in t for w in AD_WORDS) else "personal"


SCHEMA = """
CREATE TABLE IF NOT EXISTS conn (id TEXT PRIMARY KEY, owner INTEGER NOT NULL, owner_chat INTEGER, enabled INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS chats (chat INTEGER PRIMARY KEY, replied_at TEXT, owner_at TEXT, kind TEXT, name TEXT);
CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT);
"""


def connect(path: str) -> sqlite3.Connection:
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    return db


def _ago(ts: str | None, now: dt.datetime) -> dt.timedelta | None:
    return now - dt.datetime.fromisoformat(ts) if ts else None


def handle(db, upd: dict, api, now: dt.datetime | None = None) -> str:
    """Одно обновление Bot API → действие. api(method, **params). Возвращает, что сделано (для журнала/тестов)."""
    now = now or dt.datetime.now(dt.timezone.utc)
    bc = upd.get("business_connection")
    if bc:
        db.execute("INSERT OR REPLACE INTO conn VALUES (?,?,?,?)",
                   (bc["id"], bc["user"]["id"], bc.get("user_chat_id"), int(bc.get("is_enabled", True))))
        db.commit()
        if bc.get("is_enabled", True) and bc.get("user_chat_id"):
            api("sendMessage", chat_id=bc["user_chat_id"],
                text="✅ ИИ-ассистент подключён к вашему Telegram.\nОтвечаю только на первое сообщение человека "
                     "(реклама — прайс, остальное — «передал, скоро свяжется») и пересылаю вам сюда.")
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
        db.execute("INSERT INTO chats(chat, owner_at) VALUES(?,?) ON CONFLICT(chat) DO UPDATE SET owner_at=excluded.owner_at",
                   (chat["id"], now.isoformat()))
        db.commit()
        return "owner"
    o, r = (_ago(row["owner_at"], now), _ago(row["replied_at"], now)) if row else (None, None)
    if (o is not None and o < OWNER_QUIET) or (r is not None and r < REPLY_EVERY):
        return "quiet"
    text = m.get("text") or m.get("caption") or ""
    kind = kind_of(text)
    api("sendMessage", chat_id=chat["id"], business_connection_id=c["id"], text=AD_TEXT if kind == "ad" else PERSONAL_TEXT)
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
                    api("sendMessage", chat_id=u["message"]["chat"]["id"],
                        text="🤖 ИИ-ассистент Озоджамола. Сюда приходят уведомления о новых обращениях.")
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
