"""@XotiraMarkaziBot — бесплатные посты памяти для ХОТИРА КАНАЛИ ХЎЖАОБОД (@XOTIRAXOJAOBOD).

Человек: /start → фото → «ФИО 1942-2005» (1–2 строки) → предпросмотр → ✅ Юбориш.
Владелец: карточка с фото → ✅ Жойлаш (пост уходит в канал) / ❌ Рад этиш. Без одобрения владельца ничего не публикуется.
Только стандартная библиотека Python: long polling Bot API + SQLite."""
from __future__ import annotations

import datetime as dt
import json
import re
import os
import sqlite3
import time
import urllib.error
import urllib.request
import uuid

from . import core, photo as ph

try:
    import numpy as np
except Exception:  # noqa: BLE001
    np = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (uid INTEGER PRIMARY KEY, step TEXT, photo TEXT, people TEXT, updated TEXT);
CREATE TABLE IF NOT EXISTS subs (
    id INTEGER PRIMARY KEY, uid INTEGER NOT NULL, who TEXT, photo TEXT NOT NULL, caption TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', created TEXT NOT NULL, decided TEXT, channel_msg INTEGER, owner_msgs TEXT);
CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT NOT NULL);
-- 18.10: база канала для проверки повторов (история — профилем Разведки, новые посты — сам бот)
CREATE TABLE IF NOT EXISTS posts (msg_id INTEGER NOT NULL, name TEXT NOT NULL, key TEXT NOT NULL, born INTEGER,
    died INTEGER, date TEXT, PRIMARY KEY (msg_id, key));
CREATE INDEX IF NOT EXISTS idx_posts_died ON posts(died);
-- 21.10: отпечатки фото канала — повтор узнаём по самому фото, даже если ФИО и годы изменили
CREATE TABLE IF NOT EXISTS prints (msg_id INTEGER PRIMARY KEY, fp BLOB NOT NULL, date TEXT);
-- 21.10: лица с фото канала — тот же человек на ДРУГОМ фото
CREATE TABLE IF NOT EXISTS faces (msg_id INTEGER NOT NULL, i INTEGER NOT NULL, vec BLOB NOT NULL, PRIMARY KEY (msg_id, i));
CREATE TABLE IF NOT EXISTS faced (msg_id INTEGER PRIMARY KEY);
"""
DAY_LIMIT = 5

T_START = ("🕊 Ассалому алайкум!\n\nЯқинларингиз хотирасини мангу сақланг. Хотира пости бепул тайёрланади ва "
           "{ch} каналига жойланади.\n\n1️⃣ Марҳумнинг расмини юборинг.\n2️⃣ Кейин маълумотни намунадагидек ёзинг:\n\n"
           "Қосимов Қўчқарвой 1942-2005\n\nИкки киши бўлса — ҳар бири алоҳида қаторда. Ёш автоматик ҳисобланади.")
T_ASK_TEXT = ("Расм қабул қилинди ✅\n\nЭнди маълумотни намунадагидек ёзинг: ФИО 1942-2005\n"
              "Бир киши — битта қатор; икки киши — иккита қатор.\n\nМасалан:\nҚосимов Қўчқарвой 1942-2005\n"
              "Қосимова Мўътабархон 1942-2026")
T_ASK_PHOTO = "Маълумот қабул қилинди ✅\n\nЭнди марҳумнинг расмини юборинг (сурат сифатида)."
T_NEED_PHOTO = "Расмни сурат (фото) сифатида юборинг — файл ёки видео эмас."
T_PREVIEW = "👆 Пост шундай чиқади. Текшириб, «✅ Юбориш»ни босинг."
T_SENT = "✅ №{n} аризангиз қабул қилинди. Текширувдан сўнг {ch} каналига жойланади."
T_DONE = "🕊 №{n} хотира пости {ch} каналига жойланди:\n{link}\n\nАллоҳ раҳмат қилсин."
T_REJECT = "№{n} аризангиз жойланмади. Маълумотни текшириб, қайта юборишингиз мумкин: /start"
T_LIMIT = "Бугун учун ариза чегараси тўлди. Эртага қайта юборинг ёки админга ёзинг: @Ozodjamol"
T_CANCEL = "❌ Бекор қилинди. Янгидан бошлаш учун: /start"
T_EXISTS = ("🕊 Бу хотира {ch} каналида аввал жойланган:\n{links}\n\nАгар бу бошқа инсон бўлса — админ кўриб чиқади, "
            "сизга хабар келади.")

T_SCREEN = ("📱 Бу скриншотга ўхшайди. Иложи бўлса, асл расмни (галереядан) юборинг.\n"
            "Асли бўлмаса — давом этаверинг, ортиқча жойларини ўзимиз қирқиб тўғрилаймиз.")
T_BAD = {
    "blur": ("📷 Кечирасиз, расм хира чиққан — марҳумнинг юзи аниқ кўринмаяпти.\n\nХотира пости чиройли чиқиши учун "
             "тиниқроқ расм юборинг: иложи бўлса, асл расмни ёки юзи яқиндан, аниқ тушган суратни."),
    "small": ("📷 Кечирасиз, расмда юз жуда кичик — аниқ кўринмаяпти.\n\nЮзи яқинроқдан, тиниқ кўринадиган расм "
              "юборинг."),
    "noface": ("📷 Кечирасиз, бу расмда марҳумнинг юзи кўринмаяпти.\n\nЮзи аниқ кўринадиган расм юборинг."),
}
T_BAD_OWNER = ("Ассалому алайкум! №{n} аризангиз учун катта раҳмат 🤲\n\n"
               "Юборган расмингиз бироз хира ёки скриншот бўлиб чиқди — марҳумнинг юзи аниқ кўринмаяпти. "
               "Хотира пости марҳумга муносиб ва чиройли чиқиши учун, илтимос, асл расмни юборинг: галереядаги "
               "расмнинг ўзини ёки қоғоз расмни ёруғ жойда, яқиндан суратга олиб.\n\n{tail}\n\nАллоҳ раҳмат қилсин.")
T_BAD_KEEP = "Маълумотлар сақланди ✅ Фақат янги расмни юборсангиз кифоя."
T_BAD_NEW = "Қайта юбориш учун: /start"
T_PHOTO_OK = "✅ Расмингиз қабул қилинди."
T_WAIT = "⏳ Расм қабул қилинди. Админ кўриб чиқмоқда — жавоб шу ерга келади, бир оз кутинг."
T_REFUSE = ("Ассалому алайкум! Аризангиз учун катта раҳмат 🤲\n\n"
            "Афсуски, бу расмда марҳумнинг юзи аниқ кўринмаяпти, шу сабабли хотира постини муносиб тайёрлаб бўлмайди. "
            "Асл ёки тиниқроқ расм топилса, ҳар доим қайта юборишингиз мумкин: /start\n\nАллоҳ раҳмат қилсин.")
T_HAS = ("Ассалому алайкум! Аризангиз учун катта раҳмат 🤲\n\n"
         "Сиз юборган марҳум ҳақидаги хотира пости каналимизда аллақачон жойлаштирилган:\n{links}\n\n"
         "Шу сабабли уни қайта жойлаштирмаймиз. Тушунганингиз учун раҳмат.\n"
         "Аллоҳ марҳумни Ўз раҳматига олсин 🤲")
N_BAD = {"blur": "фото размытое", "small": "лицо слишком мелкое", "noface": "бот не нашёл лицо"}
# 20.10: бот сомневается в фото → сначала решает владелец (3 кнопки), человеку бот сам не отказывает
N_DONE = {"pok": "✅ ПРИНЯТО — человек продолжает с этим фото",
          "pnew": "🔄 Попросили у человека другое фото",
          "pno": "🙏 Вежливо отказано",
          "self": "📷 Человек сам прислал другое фото — эта карточка закрыта"}
N_AUTO = "✂️ Скриншот: лишнее обрезано автоматически (↩️ Оригинал — вернуть)"

KB_FLOW = {"inline_keyboard": [[{"text": "⬅️ Орқага", "callback_data": "u:back"},
                                {"text": "❌ Бекор қилиш", "callback_data": "u:cancel"}]]}
KB_PREVIEW = {"inline_keyboard": [[{"text": "✅ Юбориш", "callback_data": "u:send"}],
                                  [{"text": "✏️ Ўзгартириш", "callback_data": "u:edit"},
                                   {"text": "❌ Бекор қилиш", "callback_data": "u:cancel"}]]}


def report_links(report: str | None) -> list[str]:
    """Ссылки на уже опубликованные посты из отчёта проверки (⚠️ ПОВТОР / 🔎 Похоже)."""
    return list(dict.fromkeys(re.findall(r"https://t\.me/\S+", report or "")))


def kb_owner(n: int, status: str = "pending", report: str | None = None) -> dict:
    no = {"text": "❌ Рад этиш", "callback_data": f"o:no:{n}"}
    if status == "duplicate":                     # точный повтор: публиковать нельзя, только закрыть заявку
        return {"inline_keyboard": [[no]]}
    rows = [[{"text": "✅ Жойлаш", "callback_data": f"o:ok:{n}"}, no]]
    if report_links(report):                      # 21.10: бот нашёл похожий пост — вежливо «уже есть в канале»
        rows.append([{"text": "🙏 Уже есть в канале — вежливо отказать", "callback_data": f"o:has:{n}"}])
    rows.append([{"text": "🙏 Вежливо отказать — попросить другое фото", "callback_data": f"o:bad:{n}"}])
    if ph.available():
        rows.append([{"text": "✂️ Авто-обрезка", "callback_data": f"o:crop:{n}"},
                     {"text": "👤 По лицу", "callback_data": f"o:face:{n}"}])
        rows.append([{"text": "✨ Улучшить", "callback_data": f"o:enh:{n}"},
                     {"text": "↩️ Оригинал", "callback_data": f"o:orig:{n}"}])
        rows.append([{"text": "📎 Своё фото", "callback_data": f"o:own:{n}"}])
    else:
        rows.append([{"text": "↩️ Оригинал", "callback_data": f"o:orig:{n}"},
                     {"text": "📎 Своё фото", "callback_data": f"o:own:{n}"}])
    return {"inline_keyboard": rows}


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def connect(path: str) -> sqlite3.Connection:
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    if "report" not in {r[1] for r in db.execute("PRAGMA table_info(subs)")}:
        db.execute("ALTER TABLE subs ADD COLUMN report TEXT")
    if "photo_orig" not in {r[1] for r in db.execute("PRAGMA table_info(subs)")}:
        db.execute("ALTER TABLE subs ADD COLUMN photo_orig TEXT")      # 19.10: что прислал человек (для «↩️ Оригинал»)
    if "people" not in {r[1] for r in db.execute("PRAGMA table_info(subs)")}:
        db.execute("ALTER TABLE subs ADD COLUMN people TEXT")          # 19.10: ФИО и годы — при «🙏» просим только фото
    if "enh" not in {r[1] for r in db.execute("PRAGMA table_info(subs)")}:
        db.execute("ALTER TABLE subs ADD COLUMN enh TEXT")             # 19.10: file_id уже улучшенного фото (не улучшать дважды)
    return db


def index_post(db, msg_id: int, text: str, date: str | None = None) -> int:
    """Пост канала → в базу повторов. Возвращает, сколько людей нашлось в подписи."""
    people = core.extract(text)
    for p in people:
        db.execute("INSERT OR REPLACE INTO posts VALUES (?,?,?,?,?,?)",
                   (msg_id, p["name"], core.key(p["name"]), p["born"], p["died"], date or now()))
    db.commit()
    return len(people)


def index_print(db, msg_id: int, data: bytes, date: str | None = None) -> bool:
    """Фото поста канала → отпечаток в базу. False — фото не разобрать (или нет OpenCV)."""
    if not ph.available():
        return False
    try:
        fp = ph.fingerprint(data)
    except Exception as e:  # noqa: BLE001
        print(f"print {msg_id}: {type(e).__name__}: {e}", flush=True)
        return False
    if fp:
        db.execute("INSERT OR REPLACE INTO prints VALUES (?,?,?)", (msg_id, fp, date or now()))
    if ph.face_ready():
        try:
            fs = ph.faces(data)
        except Exception as e:  # noqa: BLE001
            print(f"faces {msg_id}: {type(e).__name__}: {e}", flush=True)
            fs = None
        if fs is not None:
            db.execute("DELETE FROM faces WHERE msg_id=?", (msg_id,))
            db.executemany("INSERT INTO faces VALUES (?,?,?)", [(msg_id, i, v) for i, v in enumerate(fs)])
            db.execute("INSERT OR REPLACE INTO faced VALUES (?)", (msg_id,))
    db.commit()
    return bool(fp)


class FaceIndex:
    """Все лица канала в памяти (матрица N×128, ~0.3 МБ на 600 фото); перечитывается, когда в базе прибавилось."""
    def __init__(self):
        self.n, self.ids, self.m = -1, [], None

    def load(self, db):
        n = db.execute("SELECT COUNT(*) FROM faces").fetchone()[0]
        if n != self.n:
            rows = db.execute("SELECT msg_id, vec FROM faces").fetchall()
            self.ids = [r["msg_id"] for r in rows]
            self.m = np.stack([ph.vec(r["vec"]) for r in rows]) if rows else None
            self.n = n
        return self

    def hits(self, db, data: bytes) -> list[tuple[int, float]]:
        """→ [(msg_id, сходство лица)] ≥ порога «похоже», лучшие сначала (по одному на пост)."""
        if not ph.face_ready() or not data:
            return []
        try:
            fs = ph.faces(data)
        except Exception:  # noqa: BLE001
            return []
        self.load(db)
        if not fs or self.m is None:
            return []
        best: dict[int, float] = {}
        for f in fs:
            sims = self.m @ ph.vec(f)
            for i in np.nonzero(sims >= ph.MAYBE_FACE)[0]:
                mid = self.ids[int(i)]
                best[mid] = max(best.get(mid, 0.0), float(sims[i]))
        return sorted(best.items(), key=lambda x: -x[1])


def photo_hits(db, data: bytes, cache: dict | None = None, skip: int | None = None) -> list[tuple[int, int]]:
    """→ [(msg_id, совпавших точек)] постов канала с ТЕМ ЖЕ фото, лучшие сначала."""
    if not ph.available() or not data:
        return []
    try:
        fp = ph.fingerprint(data)
    except Exception:  # noqa: BLE001
        return []
    if not fp:
        return []
    me = ph.unpack(fp)
    cache = {} if cache is None else cache
    hits = []
    for r in db.execute("SELECT msg_id, fp FROM prints"):
        if r["msg_id"] == skip:
            continue
        other = cache.get(r["msg_id"])
        if other is None:
            other = cache[r["msg_id"]] = ph.unpack(r["fp"])
        n = ph.match(me, other)
        if n >= ph.MAYBE_POINTS:
            hits.append((r["msg_id"], n))
    return sorted(hits, key=lambda x: -x[1])


class Api:
    def __init__(self, token: str):
        self.base = f"https://api.telegram.org/bot{token}"
        self.files = f"https://api.telegram.org/file/bot{token}"

    def download(self, file_id: str) -> bytes:
        f = self("getFile", file_id=file_id)
        with urllib.request.urlopen(f"{self.files}/{f['file_path']}", timeout=60) as r:
            return r.read()

    def upload(self, method: str, field: str, data: bytes, **p) -> dict:
        """Отправка с файлом (multipart). Картинку кладём в поле field."""
        b = uuid.uuid4().hex
        out = []
        for k, v in p.items():
            v = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)
            out.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        out.append(f'--{b}\r\nContent-Disposition: form-data; name="{field}"; filename="photo.jpg"\r\n'
                   f"Content-Type: image/jpeg\r\n\r\n".encode() + data + b"\r\n")
        out.append(f"--{b}--\r\n".encode())
        req = urllib.request.Request(f"{self.base}/{method}", data=b"".join(out),
                                     headers={"Content-Type": f"multipart/form-data; boundary={b}"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                res = json.loads(r.read())
        except urllib.error.HTTPError as e:
            res = json.loads(e.read() or b"{}")
        if not res.get("ok"):
            raise RuntimeError(f"{method}: {res.get('description')}")
        return res["result"]

    def __call__(self, method: str, **p) -> dict:
        req = urllib.request.Request(f"{self.base}/{method}", data=json.dumps(p).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                res = json.loads(r.read())
        except urllib.error.HTTPError as e:
            res = json.loads(e.read() or b"{}")
        if not res.get("ok"):
            raise RuntimeError(f"{method}: {res.get('description')}")
        return res["result"]


class Bot:
    def __init__(self, api, db, owners: set[int], channel: str, today=None):
        self.api, self.db, self.owners, self.channel = api, db, owners, channel
        self.today = today or dt.date.today
        self._fp_cache: dict = {}
        self._faces = FaceIndex()                             # отпечатки фото канала в памяти (~8 МБ)

    # ---------- состояние ----------
    def user(self, uid: int) -> dict:
        r = self.db.execute("SELECT * FROM users WHERE uid=?", (uid,)).fetchone()
        return dict(r) if r else {"uid": uid, "step": "", "photo": None, "people": None}

    def save(self, uid: int, **kw) -> None:
        u = self.user(uid)
        u.update(kw)
        self.db.execute("INSERT OR REPLACE INTO users VALUES (?,?,?,?,?)",
                        (uid, u["step"], u["photo"], u["people"], now()))
        self.db.commit()

    def reset(self, uid: int) -> None:
        self.save(uid, step="photo", photo=None, people=None)

    # ---------- человек ----------
    def start(self, chat: int) -> None:
        self.reset(chat)
        self.api("sendMessage", chat_id=chat, text=T_START.format(ch=self.channel))

    def on_message(self, msg: dict) -> str:
        if msg.get("chat", {}).get("type") != "private":
            return "skip"
        chat = msg["chat"]["id"]
        txt = (msg.get("text") or "").strip()
        if txt.startswith("/start"):
            self.db.execute("DELETE FROM kv WHERE k=?", (f"wait:{chat}",))
            self.start(chat)
            return "start"
        if txt.startswith("/navbat") and chat in self.owners:
            return self.queue(chat)
        if chat in self.owners and "photo" in msg:
            n = self.waiting(chat, msg)
            if n:
                return self.replace_own(chat, n, msg["photo"][-1]["file_id"])
        u = self.user(chat)
        if "photo" in msg:
            photo = msg["photo"][-1]["file_id"]
            bad = self.try_photo(ph.quality, photo)
            if bad:                                        # сомнительное фото → решает владелец
                return self.bad_photo(chat, msg, photo, bad)
            self.warn_screenshot(chat, photo)
            cap = (msg.get("caption") or "").strip()
            people = u["people"]
            if cap:
                try:
                    people = json.dumps(core.parse(cap, self.today()), ensure_ascii=False)
                except core.BadInput as e:
                    self.save(chat, step="text", photo=photo, people=None)
                    self.api("sendMessage", chat_id=chat, text=f"⚠️ {e}\n\n{T_ASK_TEXT}", reply_markup=KB_FLOW)
                    return "bad"
            if self.db.execute("SELECT 1 FROM kv WHERE k=?", (f"bad:{chat}",)).fetchone():
                self.close_bad(chat, "self")               # прислал другое фото сам — старая карточка закрыта
            self.save(chat, photo=photo, people=people)
            if people:
                return self.preview(chat)
            self.save(chat, step="text")
            self.api("sendMessage", chat_id=chat, text=T_ASK_TEXT, reply_markup=KB_FLOW)
            return "photo"
        if any(k in msg for k in ("document", "video", "animation", "sticker")):
            self.api("sendMessage", chat_id=chat, text=T_NEED_PHOTO)
            return "need_photo"
        if not txt:
            return "skip"
        try:
            people = core.parse(txt, self.today())
        except core.BadInput as e:
            self.api("sendMessage", chat_id=chat, text=f"⚠️ {e}", reply_markup=KB_FLOW)
            return "bad"
        self.save(chat, people=json.dumps(people, ensure_ascii=False))
        if not u["photo"]:
            self.save(chat, step="photo")
            self.api("sendMessage", chat_id=chat, text=T_ASK_PHOTO, reply_markup=KB_FLOW)
            return "text"
        return self.preview(chat)

    def preview(self, chat: int) -> str:
        u = self.user(chat)
        cap = core.caption(json.loads(u["people"]), self.channel)
        self.save(chat, step="confirm")
        self.api("sendPhoto", chat_id=chat, photo=u["photo"], caption=cap)
        self.api("sendMessage", chat_id=chat, text=T_PREVIEW, reply_markup=KB_PREVIEW)
        return "preview"

    def submit(self, chat: int, who: str) -> str:
        u = self.user(chat)
        if u["step"] != "confirm" or not u["photo"] or not u["people"]:
            self.start(chat)
            return "stale"
        since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1)).isoformat()
        n_today = self.db.execute("SELECT COUNT(*) FROM subs WHERE uid=? AND created>=?", (chat, since)).fetchone()[0]
        if n_today >= DAY_LIMIT and chat not in self.owners:
            self.api("sendMessage", chat_id=chat, text=T_LIMIT)
            return "limit"
        people = json.loads(u["people"])
        cap = core.caption(people, self.channel)
        raw = self.fetch(u["photo"])
        dup, lines, links = self.check(people, raw)
        status = "duplicate" if dup and links else "pending"
        cropped = self.safe(ph.auto, raw)                          # скриншот → лишнее срезаем сразу
        if cropped:
            lines.append(N_AUTO)
        cur = self.db.execute("INSERT INTO subs(uid, who, photo, caption, created, status, report, photo_orig, people) "
                              "VALUES (?,?,?,?,?,?,?,?,?)",
                              (chat, who, u["photo"], cap, now(), status, "\n".join(lines), u["photo"], u["people"]))
        n = cur.lastrowid
        self.db.commit()
        self.reset(chat)
        self.notify_owners(n, cropped)
        if status == "duplicate":
            self.api("sendMessage", chat_id=chat, text=T_EXISTS.format(ch=self.channel, links="\n".join(dict.fromkeys(links))))
            return "duplicate"
        self.api("sendMessage", chat_id=chat, text=T_SENT.format(n=n, ch=self.channel))
        return "sent"

    # ---------- проверка повторов ----------
    def link(self, msg_id: int) -> str:
        return f"https://t.me/{self.channel.lstrip('@')}/{msg_id}"

    def check(self, people: list[dict], data: bytes | None = None) -> tuple[bool, list[str], list[str]]:
        """→ (все люди — точный повтор?, строки отчёта владельцу, ссылки на найденные посты).
        21.10: сравниваем со ВСЕМИ постами (годы могли изменить) и само фото — с фото канала."""
        n_posts = self.db.execute("SELECT COUNT(DISTINCT msg_id) FROM posts").fetchone()[0]
        n_prints = self.db.execute("SELECT COUNT(*) FROM prints").fetchone()[0]
        lines, links, all_same = [], [], True
        hits = photo_hits(self.db, data, self._fp_cache) if n_prints else []
        for msg_id, n in hits[:2]:
            links.append(self.link(msg_id))
            lines.append(f"📸 ЭТО ФОТО уже было в канале 👉 {self.link(msg_id)}" if n >= ph.SAME_POINTS else
                         f"📸 Возможно, то же фото (проверьте) 👉 {self.link(msg_id)}")
        seen = {m for m, _ in hits[:2]}
        for msg_id, sim in [h for h in self._faces.hits(self.db, data) if h[0] not in seen][:2]:
            links.append(self.link(msg_id))
            lines.append(f"👤 ТОТ ЖЕ ЧЕЛОВЕК по лицу ({sim:.2f}) 👉 {self.link(msg_id)}" if sim >= ph.SAME_FACE else
                         f"👤 Лицо похоже ({sim:.2f}) — проверьте 👉 {self.link(msg_id)}")
        for p in people:
            found_same, found_sim = [], []
            for r in self.db.execute("SELECT * FROM posts"):
                c = core.compare(p, dict(r))
                (found_same if c == "same" else found_sim if c == "similar" else []).append(r)
            found_sim.sort(key=lambda r: abs((r["died"] or 0) - p["died"]) + abs((r["born"] or 0) - p["born"]))
            for s in self.db.execute("SELECT id, caption FROM subs WHERE status IN ('pending','working')"):
                if any(core.compare(p, q) == "same" for q in core.extract(s["caption"])):
                    found_same.append({"msg_id": None, "sub": s["id"], "name": p["name"], "born": p["born"], "died": p["died"]})
            who = f"{p['name']} {p['born']}-{p['died']}"
            if found_same:
                r = found_same[0]
                if r["msg_id"]:
                    links.append(self.link(r["msg_id"]))
                    lines.append(f"⚠️ ПОВТОР: {who} — уже в канале 👉 {self.link(r['msg_id'])}")
                else:
                    lines.append(f"⚠️ ПОВТОР: {who} — уже ждёт одобрения (№{r['sub']})")
            else:
                all_same = False
                for r in found_sim[:3]:
                    lines.append(f"🔎 Похоже: {r['name']} {r['born']}-{r['died']} 👉 {self.link(r['msg_id'])}")
        head = f"📋 Проверено постов канала: {n_posts}" if n_posts else "📋 База канала ещё не загружена — проверить повторы нельзя"
        if n_prints:
            head += f" · фото: {n_prints}"
            n_faces = self.db.execute("SELECT COUNT(*) FROM faced").fetchone()[0]
            if n_faces and ph.face_ready():
                head += f" · лица: {n_faces}"
        if not any(x.startswith(("⚠️", "🔎", "📸", "👤")) for x in lines) and n_posts:
            lines.append("✅ Повторов нет")
        return all_same and bool(people), [head] + lines, links

    # ---------- владелец ----------
    def owner_card(self, s) -> str:
        rep = s["report"] if "report" in s.keys() and s["report"] else ""
        if not all(core.name_ok(p["name"]) for p in core.extract(s["caption"]) or [{"name": ""}]):
            rep = (rep + "\n" if rep else "") + "⛔ НЕТ ИМЕНИ: в посте нет исм-фамилии — не жойлайте, ответьте человеку"
        tail = "⏳ Ждёт вашего одобрения" if s["status"] == "pending" else (
            "🚫 Точный повтор — человеку уже ответили «уже есть». Нажмите «❌ Рад этиш», чтобы закрыть заявку" if s["status"] == "duplicate" else "")
        return f"🕊 №{s['id']} · ариза: {s['who']}\n\n{s['caption']}\n\n{rep}\n{tail}".strip()

    def notify_owners(self, n: int, data: bytes | None = None) -> None:
        s = self.db.execute("SELECT * FROM subs WHERE id=?", (n,)).fetchone()
        sent, pid = {}, s["photo"]
        for o in self.owners:
            try:
                kb = kb_owner(n, s["status"], s["report"])
                cap = self.owner_card(s)[:1024]
                if data:                                          # обрезанное фото — загружаем один раз
                    r = self.api.upload("sendPhoto", "photo", data, chat_id=o, caption=cap, reply_markup=kb)
                    pid, data = r["photo"][-1]["file_id"], None
                    self.db.execute("UPDATE subs SET photo=? WHERE id=?", (pid, n))
                    self.db.commit()
                else:
                    r = self.api("sendPhoto", chat_id=o, photo=pid, caption=cap, reply_markup=kb)
                sent[str(o)] = r["message_id"]
            except Exception as e:  # noqa: BLE001 — владелец не нажал «Старт» в боте
                print(f"owner {o}: {e}", flush=True)
        self.db.execute("UPDATE subs SET owner_msgs=? WHERE id=?", (json.dumps(sent), n))
        self.db.commit()

    def queue(self, chat: int) -> str:
        rows = self.db.execute("SELECT id FROM subs WHERE status='pending' ORDER BY id").fetchall()
        if not rows:
            self.api("sendMessage", chat_id=chat, text="Навбатда ариза йўқ ✅")
        for r in rows:
            self.notify_owners(r["id"])
        return "queue"

    def decide(self, cq: dict, ok: bool, n: int, bad: bool = False, has: bool = False) -> str:
        s = self.db.execute("SELECT * FROM subs WHERE id=?", (n,)).fetchone()
        if s is None or s["status"] not in ("pending", "duplicate"):
            self.api("answerCallbackQuery", callback_query_id=cq["id"], text="Аввал кўриб чиқилган")
            return "dup"
        if ok and s["status"] == "duplicate":               # старая кнопка «Всё равно жойлаш» — повтор не публикуем
            self.api("answerCallbackQuery", callback_query_id=cq["id"], show_alert=True,
                     text="Бу аниқ такрор — каналда бор. Жойлаб бўлмайди, «❌ Рад этиш» босинг")
            return "blocked"
        # сначала отмечаем — двойное нажатие не опубликует дважды
        self.db.execute("UPDATE subs SET status=?, decided=? WHERE id=? AND status IN ('pending','duplicate')",
                        ("working" if ok else "rejected", now(), n))
        self.db.commit()
        links = report_links(s["report"]) if has else []
        if has and not links:
            self.db.execute("UPDATE subs SET status=? WHERE id=?", (s["status"], n))
            self.db.commit()
            self.api("answerCallbackQuery", callback_query_id=cq["id"], show_alert=True, text="Каналда ўхшаш пост топилмади")
            return "nolink"
        mark = ("🙏 ВЕЖЛИВО ОТКАЗАНО — человеку отправлена ссылка: уже есть в канале" if has else
                "🙏 ВЕЖЛИВО ОТКАЗАНО — человека попросили прислать другое фото" if bad else "❌ РАД ЭТИЛДИ")
        if ok:
            try:
                r = self.api("sendPhoto", chat_id=self.channel, photo=s["photo"], caption=s["caption"])
            except Exception as e:  # noqa: BLE001
                self.db.execute("UPDATE subs SET status=? WHERE id=?", (s["status"], n))
                self.db.commit()
                self.api("answerCallbackQuery", callback_query_id=cq["id"], show_alert=True,
                         text=f"Каналга юбориб бўлмади: бот {self.channel} да админми? ({e})"[:190])
                return "fail"
            self.db.execute("UPDATE subs SET status='published', channel_msg=? WHERE id=?", (r["message_id"], n))
            self.db.commit()
            index_post(self.db, r["message_id"], s["caption"])
            data = self.fetch(s["photo"])
            if data:
                index_print(self.db, r["message_id"], data)
            link = f"https://t.me/{self.channel.lstrip('@')}/{r['message_id']}"
            mark = f"✅ ЖОЙЛАНДИ\n{link}"
            self.tell(s["uid"], T_DONE.format(n=n, ch=self.channel, link=link))
        elif has:
            self.tell(s["uid"], T_HAS.format(links="\n".join(links)))
        elif bad:
            people = s["people"] if "people" in s.keys() else None
            if not people:                                  # старые заявки — восстановить ФИО и годы из подписи
                try:
                    people = json.dumps(core.parse("\n".join(f"{p['name']} {p['born']}-{p['died']}"
                                                              for p in core.extract(s["caption"])), self.today()),
                                        ensure_ascii=False)
                except core.BadInput:
                    people = None
            if people:                                      # человеку остаётся прислать только фото → сразу предпросмотр
                self.save(s["uid"], step="photo", photo=None, people=people)
            self.tell(s["uid"], T_BAD_OWNER.format(n=n, tail=T_BAD_KEEP if people else T_BAD_NEW))
        elif s["status"] != "duplicate":                     # при повторе человеку уже ответили «бор»
            self.tell(s["uid"], T_REJECT.format(n=n))
        for o, mid in json.loads(s["owner_msgs"] or "{}").items():
            try:
                self.api("editMessageCaption", chat_id=int(o), message_id=mid,
                         caption=(self.owner_card(s)[:900] + "\n\n" + mark))
            except Exception:  # noqa: BLE001
                pass
        self.api("answerCallbackQuery", callback_query_id=cq["id"], text="Жойланди ✅" if ok else "🙏 Вежливо отправлено" if bad or has else "Рад этилди")
        return "published" if ok else "exists" if has else "bad_photo" if bad else "rejected"

    def tell(self, chat: int, text: str) -> None:
        try:
            self.api("sendMessage", chat_id=chat, text=text, disable_web_page_preview=False)
        except Exception as e:  # noqa: BLE001 — человек заблокировал бота
            print(f"tell {chat}: {e}", flush=True)

    # ---------- фото: скриншоты и обрезка (19.10) ----------
    def fetch(self, file_id: str) -> bytes | None:
        """Скачать фото (для обрезки и проверки по фото). Ошибка → None."""
        if not ph.available() or not hasattr(self.api, "download") or not file_id:
            return None
        try:
            return self.api.download(file_id)
        except Exception as e:  # noqa: BLE001
            print(f"download: {type(e).__name__}: {e}", flush=True)
            return None

    @staticmethod
    def safe(fn, data: bytes | None) -> bytes | None:
        if not data:
            return None
        try:
            return fn(data)
        except Exception as e:  # noqa: BLE001
            print(f"photo {fn.__name__}: {type(e).__name__}: {e}", flush=True)
            return None

    def try_photo(self, fn, file_id: str) -> bytes | None:
        """Скачать фото и прогнать обработку. Любая ошибка → None (бот работает дальше без обрезки)."""
        if not ph.available() or not hasattr(self.api, "download"):
            return None
        try:
            return fn(self.api.download(file_id))
        except Exception as e:  # noqa: BLE001
            print(f"photo {fn.__name__}: {type(e).__name__}: {e}", flush=True)
            return None

    def bad_photo(self, chat: int, msg: dict, photo: str, why: str) -> str:
        """Бот сомневается в фото. Человеку — «ждите», владельцу — простая карточка с 3 кнопками. Решает владелец."""
        cap = (msg.get("caption") or "").strip()
        f = msg.get("from") or {}
        who = ((f.get("first_name") or "") + (f" @{f['username']}" if f.get("username") else "")).strip() or "—"
        people = None
        try:
            people = core.parse(cap, self.today()) if cap else json.loads(self.user(chat)["people"] or "null")
        except core.BadInput:
            pass
        whom = "\n".join(f"{p['name']} {p['born']}-{p['died']}" for p in people) if people else "пока не написал"
        card = (f"📋 Хотира — новая заявка\n\nПрислал: {who}\nЗа кого: {whom}\n\n"
                f"⚠️ Бот сомневается в фото: {N_BAD[why]}\n\nЧеловек ждёт вашего ответа.")
        kb = {"inline_keyboard": [[{"text": "✅ Принять", "callback_data": f"o:pok:{chat}"},
                                   {"text": "🔄 Другое фото", "callback_data": f"o:pnew:{chat}"}],
                                  [{"text": "🙏 Вежливо отказать", "callback_data": f"o:pno:{chat}"}]]}
        sent = {}
        for o in self.owners:
            if o == chat:
                continue
            try:
                sent[str(o)] = self.api("sendPhoto", chat_id=o, photo=photo, caption=card, reply_markup=kb)["message_id"]
            except Exception as e:  # noqa: BLE001
                print(f"owner {o}: {e}", flush=True)
        kv = {f"bad:{chat}": photo, f"badwhy:{chat}": why, f"badcard:{chat}": json.dumps({"c": card, "m": sent})}
        if cap:
            kv[f"badcap:{chat}"] = cap
        self.db.executemany("INSERT OR REPLACE INTO kv VALUES (?,?)", kv.items())
        self.db.commit()
        self.api("sendMessage", chat_id=chat, text=T_WAIT)
        return "bad_photo"

    def close_bad(self, uid: int, act: str) -> str | None:
        """Снять заявку «сомнительное фото»: обновить карточки владельца, убрать кнопки. → фото или None."""
        keys = [f"{k}:{uid}" for k in ("bad", "badcap", "badwhy", "badcard")]
        got = dict(self.db.execute(f"SELECT k, v FROM kv WHERE k IN ({','.join('?' * 4)})", keys).fetchall())
        self.db.execute(f"DELETE FROM kv WHERE k IN ({','.join('?' * 4)})", keys)
        self.db.commit()
        card = json.loads(got.get(f"badcard:{uid}") or '{"c": "", "m": {}}')
        for o, mid in card["m"].items():
            try:
                self.api("editMessageCaption", chat_id=int(o), message_id=mid,
                         caption=f"{card['c']}\n\n{N_DONE[act]}"[:1024], reply_markup={"inline_keyboard": []})
            except Exception:  # noqa: BLE001
                pass
        self._badcap, self._badwhy = got.get(f"badcap:{uid}"), got.get(f"badwhy:{uid}")
        return got.get(f"bad:{uid}")

    def answer_bad(self, cq: dict, act: str, uid: int) -> str:
        """Кнопки владельца по сомнительному фото: pok / pnew / pno."""
        say = lambda t: self.api("answerCallbackQuery", callback_query_id=cq["id"], text=t)  # noqa: E731
        photo = self.close_bad(uid, act)
        if not photo:
            say("Уже неактуально — человек прислал другое фото")
            return "stale"
        if act == "pnew":
            self.tell(uid, T_BAD.get(self._badwhy or "", T_BAD["noface"]))
            say("🔄 Попросили другое фото")
            return "ask_new"
        if act == "pno":
            self.reset(uid)
            self.tell(uid, T_REFUSE)
            say("🙏 Вежливо отказано")
            return "refused"
        self.tell(uid, T_PHOTO_OK)
        people = self.user(uid)["people"]
        if self._badcap:
            try:
                people = json.dumps(core.parse(self._badcap, self.today()), ensure_ascii=False)
            except core.BadInput:
                pass
        self.save(uid, photo=photo, people=people)
        say("✅ Принято")
        if people:
            return self.preview(uid)
        self.save(uid, step="text")
        self.api("sendMessage", chat_id=uid, text=T_ASK_TEXT, reply_markup=KB_FLOW)
        return "photo_ok"

    def warn_screenshot(self, chat: int, file_id: str) -> None:
        if self.try_photo(ph.auto, file_id):
            self.api("sendMessage", chat_id=chat, text=T_SCREEN)

    def set_photo(self, n: int, data: bytes | None = None, file_id: str | None = None) -> str | None:
        """Новое фото заявки → в базу и во все карточки владельца (кнопки остаются)."""
        s = self.db.execute("SELECT * FROM subs WHERE id=?", (n,)).fetchone()
        cap, kb = self.owner_card(s)[:1024], kb_owner(n, s["status"], s["report"])
        for o, mid in json.loads(s["owner_msgs"] or "{}").items():
            try:
                if data:
                    r = self.api.upload("editMessageMedia", "p", data, chat_id=int(o), message_id=mid, reply_markup=kb,
                                        media={"type": "photo", "media": "attach://p", "caption": cap})
                    file_id, data = r["photo"][-1]["file_id"], None
                else:
                    self.api("editMessageMedia", chat_id=int(o), message_id=mid, reply_markup=kb,
                             media={"type": "photo", "media": file_id, "caption": cap})
            except Exception as e:  # noqa: BLE001 — одна карточка не мешает
                print(f"card {o}: {e}", flush=True)
        if data and not file_id:                                   # карточек нет — загрузим владельцу заново
            o = next(iter(self.owners))
            r = self.api.upload("sendPhoto", "photo", data, chat_id=o, caption=cap, reply_markup=kb)
            file_id = r["photo"][-1]["file_id"]
        if file_id:
            self.db.execute("UPDATE subs SET photo=? WHERE id=?", (file_id, n))
            self.db.commit()
        return file_id

    def edit_photo(self, cq: dict, act: str, n: int) -> str:
        s = self.db.execute("SELECT * FROM subs WHERE id=?", (n,)).fetchone()
        say = lambda t, alert=False: self.api("answerCallbackQuery", callback_query_id=cq["id"], text=t,  # noqa: E731
                                              show_alert=alert)
        if s is None or s["status"] not in ("pending", "duplicate"):
            say("Аввал кўриб чиқилган")
            return "dup"
        orig = s["photo_orig"] or s["photo"]
        if act == "own":
            self.db.execute("INSERT OR REPLACE INTO kv VALUES (?,?)", (f"wait:{cq['from']['id']}", str(n)))
            self.db.commit()
            say("Жду фото")
            self.api("sendMessage", chat_id=cq["from"]["id"],
                     text=f"📎 Отправьте фото для №{n}.\nМожно обрезать прямо в Telegram: выберите фото → ✏️ → обрезка → отправить.")
            return "wait"
        if act == "orig":
            if s["photo"] == orig:
                say("Уже оригинал")
                return "same"
            self.set_photo(n, file_id=orig)
            say("↩️ Оригинал")
            return "orig"
        if act == "enh":                                          # улучшаем то, что сейчас в карточке (после обрезки)
            if s["enh"] and s["enh"] == s["photo"]:
                say("Уже улучшено. Не нравится — «↩️ Оригинал»")
                return "same"
            out = self.try_photo(ph.enhance, s["photo"])
            if not out:
                say("Не получилось обработать фото", True)
                return "none"
            fid = self.set_photo(n, data=out)
            self.db.execute("UPDATE subs SET enh=? WHERE id=?", (fid, n))
            self.db.commit()
            say("✨ Готово")
            return "enh"
        out = self.try_photo(ph.auto if act == "crop" else ph.face, orig)
        if not out:
            say("Лишнего не найдено — фото и так чистое" if act == "crop" else "Лицо не найдено — попробуйте «📎 Своё фото»", True)
            return "none"
        self.set_photo(n, data=out)
        say("✂️ Готово" if act == "crop" else "👤 Готово")
        return act

    def waiting(self, chat: int, msg: dict) -> int | None:
        """Владелец ждёт замену фото (кнопка «📎») или ответил фото на карточку → номер заявки."""
        r = self.db.execute("SELECT v FROM kv WHERE k=?", (f"wait:{chat}",)).fetchone()
        if r:
            return int(r[0])
        reply = (msg.get("reply_to_message") or {}).get("message_id")
        if reply:
            for s in self.db.execute("SELECT id, owner_msgs FROM subs WHERE status IN ('pending','duplicate')"):
                if json.loads(s["owner_msgs"] or "{}").get(str(chat)) == reply:
                    return s["id"]
        return None

    def replace_own(self, chat: int, n: int, file_id: str) -> str:
        self.db.execute("DELETE FROM kv WHERE k=?", (f"wait:{chat}",))
        self.db.commit()
        s = self.db.execute("SELECT status FROM subs WHERE id=?", (n,)).fetchone()
        if s is None or s["status"] not in ("pending", "duplicate"):
            self.api("sendMessage", chat_id=chat, text=f"№{n} уже рассмотрена — фото не заменено.")
            return "dup"
        self.set_photo(n, file_id=file_id)
        self.api("sendMessage", chat_id=chat, text=f"✅ Фото №{n} заменено. Карточка выше обновлена — можно «✅ Жойлаш».")
        return "replaced"

    # ---------- кнопки ----------
    def on_callback(self, cq: dict) -> str:
        data = cq.get("data") or ""
        uid = cq["from"]["id"]
        if data.startswith("o:"):
            if uid not in self.owners:
                self.api("answerCallbackQuery", callback_query_id=cq["id"], text="Фақат админ учун")
                return "denied"
            _, act, n = data.split(":")
            if act in ("pok", "pnew", "pno"):
                return self.answer_bad(cq, act, int(n))
            if act == "bad":
                return self.decide(cq, False, int(n), bad=True)
            if act == "has":
                return self.decide(cq, False, int(n), has=True)
            if act in ("crop", "face", "orig", "own", "enh"):
                return self.edit_photo(cq, act, int(n))
            return self.decide(cq, act == "ok", int(n))
        self.api("answerCallbackQuery", callback_query_id=cq["id"])
        chat = cq["message"]["chat"]["id"]
        if data == "u:send":
            f = cq["from"]
            who = (f.get("first_name") or "") + (f" @{f['username']}" if f.get("username") else f" (id {f['id']})")
            return self.submit(chat, who.strip())
        if data == "u:cancel":
            self.reset(chat)
            self.api("sendMessage", chat_id=chat, text=T_CANCEL)
            return "cancel"
        if data == "u:edit":
            self.save(chat, step="text", people=None)
            self.api("sendMessage", chat_id=chat, text=T_ASK_TEXT, reply_markup=KB_FLOW)
            return "edit"
        self.start(chat)                                   # «Орқага» и кнопки старого бота — начать заново
        return "start"

    def on_channel_post(self, post: dict) -> str | None:
        """Пост в канале Хотира (через бота или вручную владельцем) → в базу повторов."""
        if (post.get("chat", {}).get("username") or "").lower() != self.channel.lstrip("@").lower():
            return None
        text = post.get("caption") or post.get("text") or ""
        if post.get("photo"):                                   # 21.10: и фото — в базу отпечатков
            data = self.fetch(post["photo"][-1]["file_id"])
            if data:
                index_print(self.db, post["message_id"], data)
        return f"indexed:{index_post(self.db, post['message_id'], text)}"

    def handle(self, upd: dict) -> str | None:
        for k in ("channel_post", "edited_channel_post"):
            if k in upd:
                return self.on_channel_post(upd[k])
        if "message" in upd:
            return self.on_message(upd["message"])
        if "callback_query" in upd:
            return self.on_callback(upd["callback_query"])
        return None


def run() -> None:
    api = Api(os.environ["XOTIRA_BOT_TOKEN"])
    db = connect(os.environ.get("XOTIRA_DB", "/var/lib/papa-xotira/xotira.sqlite3"))
    owners = {int(x) for x in os.environ.get("OWNER_IDS", "").split(",") if x.strip()}
    bot = Bot(api, db, owners, os.environ.get("XOTIRA_CHANNEL", "@XOTIRAXOJAOBOD"))
    me = api("getMe")
    try:
        api("setMyCommands", commands=[{"command": "start", "description": "Хотира пости яратиш"}])
    except Exception:  # noqa: BLE001
        pass
    print(f"XOTIRA @{me['username']} запущен, канал {bot.channel}, владельцев {len(owners)}", flush=True)
    off = int((db.execute("SELECT v FROM kv WHERE k='offset'").fetchone() or [0])[0])
    while True:
        try:
            ups = api("getUpdates", offset=off, timeout=30, allowed_updates=["message", "callback_query", "channel_post", "edited_channel_post"])
        except Exception as e:  # noqa: BLE001
            print(f"getUpdates: {e}", flush=True)
            time.sleep(10)
            continue
        for u in ups:
            try:
                bot.handle(u)
            except Exception as e:  # noqa: BLE001 — одно сообщение не роняет бота
                print(f"update: {type(e).__name__}: {e}", flush=True)
            off = u["update_id"] + 1
            db.execute("INSERT OR REPLACE INTO kv VALUES ('offset', ?)", (str(off),))
            db.commit()
