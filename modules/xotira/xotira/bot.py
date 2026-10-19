"""@XotiraMarkaziBot — бесплатные посты памяти для ХОТИРА КАНАЛИ ХЎЖАОБОД (@XOTIRAXOJAOBOD).

Человек: /start → фото → «ФИО 1942-2005» (1–2 строки) → предпросмотр → ✅ Юбориш.
Владелец: карточка с фото → ✅ Жойлаш (пост уходит в канал) / ❌ Рад этиш. Без одобрения владельца ничего не публикуется.
Только стандартная библиотека Python: long polling Bot API + SQLite."""
from __future__ import annotations

import datetime as dt
import json
import os
import sqlite3
import time
import urllib.error
import urllib.request
import uuid

from . import core, photo as ph

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
N_AUTO = "✂️ Скриншот: лишнее обрезано автоматически (↩️ Оригинал — вернуть)"

KB_FLOW = {"inline_keyboard": [[{"text": "⬅️ Орқага", "callback_data": "u:back"},
                                {"text": "❌ Бекор қилиш", "callback_data": "u:cancel"}]]}
KB_PREVIEW = {"inline_keyboard": [[{"text": "✅ Юбориш", "callback_data": "u:send"}],
                                  [{"text": "✏️ Ўзгартириш", "callback_data": "u:edit"},
                                   {"text": "❌ Бекор қилиш", "callback_data": "u:cancel"}]]}


def kb_owner(n: int, status: str = "pending") -> dict:
    top = ([{"text": "✅ Жойлаш", "callback_data": f"o:ok:{n}"}, {"text": "❌ Рад этиш", "callback_data": f"o:no:{n}"}]
           if status == "pending" else [{"text": "✅ Всё равно жойлаш", "callback_data": f"o:ok:{n}"}])
    rows = [top]
    if ph.available():
        rows.append([{"text": "✂️ Авто-обрезка", "callback_data": f"o:crop:{n}"},
                     {"text": "👤 По лицу", "callback_data": f"o:face:{n}"}])
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
    return db


def index_post(db, msg_id: int, text: str, date: str | None = None) -> int:
    """Пост канала → в базу повторов. Возвращает, сколько людей нашлось в подписи."""
    people = core.extract(text)
    for p in people:
        db.execute("INSERT OR REPLACE INTO posts VALUES (?,?,?,?,?,?)",
                   (msg_id, p["name"], core.key(p["name"]), p["born"], p["died"], date or now()))
    db.commit()
    return len(people)


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
        dup, lines, links = self.check(people)
        status = "duplicate" if dup and links else "pending"
        cropped = self.try_photo(ph.auto, u["photo"])              # скриншот → лишнее срезаем сразу
        if cropped:
            lines.append(N_AUTO)
        cur = self.db.execute("INSERT INTO subs(uid, who, photo, caption, created, status, report, photo_orig) "
                              "VALUES (?,?,?,?,?,?,?,?)",
                              (chat, who, u["photo"], cap, now(), status, "\n".join(lines), u["photo"]))
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

    def check(self, people: list[dict]) -> tuple[bool, list[str], list[str]]:
        """→ (все люди — точный повтор?, строки отчёта владельцу, ссылки на найденные посты)."""
        n_posts = self.db.execute("SELECT COUNT(DISTINCT msg_id) FROM posts").fetchone()[0]
        lines, links, all_same = [], [], True
        for p in people:
            found_same, found_sim = [], []
            for r in self.db.execute("SELECT * FROM posts WHERE died BETWEEN ? AND ?", (p["died"] - 1, p["died"] + 1)):
                c = core.compare(p, dict(r))
                (found_same if c == "same" else found_sim if c == "similar" else []).append(r)
            if not found_same:                                   # то же имя, но годы другие — тоже показать
                k = core.key(p["name"])
                found_sim += [r for r in self.db.execute("SELECT * FROM posts WHERE key=?", (k,))
                              if r["msg_id"] not in {x["msg_id"] for x in found_sim}]
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
                for r in found_sim[:2]:
                    lines.append(f"🔎 Похоже: {r['name']} {r['born']}-{r['died']} 👉 {self.link(r['msg_id'])}")
        head = f"📋 Проверено постов канала: {n_posts}" if n_posts else "📋 База канала ещё не загружена — проверить повторы нельзя"
        if not any(x.startswith(("⚠️", "🔎")) for x in lines) and n_posts:
            lines.append("✅ Повторов нет")
        return all_same and bool(people), [head] + lines, links

    # ---------- владелец ----------
    def owner_card(self, s) -> str:
        rep = s["report"] if "report" in s.keys() and s["report"] else ""
        if not all(core.name_ok(p["name"]) for p in core.extract(s["caption"]) or [{"name": ""}]):
            rep = (rep + "\n" if rep else "") + "⛔ НЕТ ИМЕНИ: в посте нет исм-фамилии — не жойлайте, ответьте человеку"
        tail = "⏳ Ждёт вашего одобрения" if s["status"] == "pending" else (
            "🚫 Человеку ответили «уже есть». Если это другой человек — «Всё равно жойлаш»" if s["status"] == "duplicate" else "")
        return f"🕊 №{s['id']} · ариза: {s['who']}\n\n{s['caption']}\n\n{rep}\n{tail}".strip()

    def notify_owners(self, n: int, data: bytes | None = None) -> None:
        s = self.db.execute("SELECT * FROM subs WHERE id=?", (n,)).fetchone()
        sent, pid = {}, s["photo"]
        for o in self.owners:
            try:
                kb = kb_owner(n, s["status"])
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

    def decide(self, cq: dict, ok: bool, n: int) -> str:
        s = self.db.execute("SELECT * FROM subs WHERE id=?", (n,)).fetchone()
        if s is None or s["status"] not in ("pending", "duplicate"):
            self.api("answerCallbackQuery", callback_query_id=cq["id"], text="Аввал кўриб чиқилган")
            return "dup"
        # сначала отмечаем — двойное нажатие не опубликует дважды
        self.db.execute("UPDATE subs SET status=?, decided=? WHERE id=? AND status IN ('pending','duplicate')",
                        ("working" if ok else "rejected", now(), n))
        self.db.commit()
        mark = "❌ РАД ЭТИЛДИ"
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
            link = f"https://t.me/{self.channel.lstrip('@')}/{r['message_id']}"
            mark = f"✅ ЖОЙЛАНДИ\n{link}"
            self.tell(s["uid"], T_DONE.format(n=n, ch=self.channel, link=link))
        else:
            self.tell(s["uid"], T_REJECT.format(n=n))
        for o, mid in json.loads(s["owner_msgs"] or "{}").items():
            try:
                self.api("editMessageCaption", chat_id=int(o), message_id=mid,
                         caption=(self.owner_card(s)[:900] + "\n\n" + mark))
            except Exception:  # noqa: BLE001
                pass
        self.api("answerCallbackQuery", callback_query_id=cq["id"], text="Жойланди ✅" if ok else "Рад этилди")
        return "published" if ok else "rejected"

    def tell(self, chat: int, text: str) -> None:
        try:
            self.api("sendMessage", chat_id=chat, text=text, disable_web_page_preview=False)
        except Exception as e:  # noqa: BLE001 — человек заблокировал бота
            print(f"tell {chat}: {e}", flush=True)

    # ---------- фото: скриншоты и обрезка (19.10) ----------
    def try_photo(self, fn, file_id: str) -> bytes | None:
        """Скачать фото и прогнать обработку. Любая ошибка → None (бот работает дальше без обрезки)."""
        if not ph.available() or not hasattr(self.api, "download"):
            return None
        try:
            return fn(self.api.download(file_id))
        except Exception as e:  # noqa: BLE001
            print(f"photo {fn.__name__}: {type(e).__name__}: {e}", flush=True)
            return None

    def warn_screenshot(self, chat: int, file_id: str) -> None:
        if self.try_photo(ph.auto, file_id):
            self.api("sendMessage", chat_id=chat, text=T_SCREEN)

    def set_photo(self, n: int, data: bytes | None = None, file_id: str | None = None) -> None:
        """Новое фото заявки → в базу и во все карточки владельца (кнопки остаются)."""
        s = self.db.execute("SELECT * FROM subs WHERE id=?", (n,)).fetchone()
        cap, kb = self.owner_card(s)[:1024], kb_owner(n, s["status"])
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
            if act in ("crop", "face", "orig", "own"):
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
