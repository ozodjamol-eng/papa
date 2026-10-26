"""@ShodiyonaMebelUzBot — бот мебельного центра Shodiyona (клиент OZOD DIGITAL). Утверждено владельцем 24.10.2026.

Покупатель: каталог · буюртма по размерам · «арзонроқ топамиз» (фото чужой мебели) · «хонангизда кўринг»
(фото комнаты; ИИ — когда шеф оплатит) · бесплатный замер с днём и временем · «буюртмам қаерда?» (этапы и фото из цеха)
· адреса · контакты.
Менеджер (OWNER_IDS + MANAGER_IDS): карточка каждой заявки с кнопками, напоминание через 15 минут, буюртма → этапы,
фото из цеха уходит покупателю, каталог пополняется прямо из Telegram (/admin).
Только стандартная библиотека Python: long polling Bot API + SQLite. Бот ничего не публикует в каналы."""
from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import os
import re
import sqlite3
import time
import tomllib
import urllib.error
import uuid
import urllib.request
from pathlib import Path

from . import texts as T

TZ = dt.timezone(dt.timedelta(hours=5))
HERE = Path(__file__).resolve().parent.parent
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (uid INTEGER PRIMARY KEY, first TEXT, username TEXT, phone TEXT, src TEXT,
    step TEXT, data TEXT, updated TEXT);
CREATE TABLE IF NOT EXISTS leads (n INTEGER PRIMARY KEY, uid INTEGER NOT NULL, kind TEXT NOT NULL, phone TEXT,
    details TEXT, photos TEXT, src TEXT, status TEXT NOT NULL DEFAULT 'new', created TEXT NOT NULL,
    reminded INTEGER NOT NULL DEFAULT 0, cards TEXT, log TEXT);
CREATE TABLE IF NOT EXISTS orders (n INTEGER PRIMARY KEY, lead INTEGER, uid INTEGER NOT NULL, title TEXT,
    stage INTEGER NOT NULL DEFAULT 0, created TEXT NOT NULL, updated TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, cat TEXT NOT NULL, title TEXT NOT NULL, info TEXT,
    photo TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT NOT NULL);
"""
PHONE_RE = re.compile(r"\+?\d[\d\s\-()]{7,}\d")


def now() -> dt.datetime:
    return dt.datetime.now(TZ)


def esc(s) -> str:
    return html.escape(str(s or ""), quote=False)


def load_cfg(path: str | Path | None = None) -> dict:
    return tomllib.loads(Path(path or HERE / "config.toml").read_text(encoding="utf-8"))


def connect(path: str) -> sqlite3.Connection:
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    if path != ":memory:":
        db.execute("PRAGMA journal_mode=WAL")
    db.executescript(SCHEMA)
    return db


def norm_phone(text: str) -> str | None:
    m = PHONE_RE.search(text or "")
    if not m:
        return None
    d = re.sub(r"\D", "", m.group())
    if len(d) == 9:
        d = "998" + d
    if len(d) < 11 or len(d) > 13:
        return None
    return "+" + d


def day_label(d: dt.date) -> str:
    return f"{T.WEEKDAYS[d.weekday()]}, {d.day} {T.MONTHS[d.month - 1]}"


class Api:
    def __init__(self, token: str):
        self.base = f"https://api.telegram.org/bot{token}"

    def upload(self, method: str, field: str, data: bytes, **p) -> dict:
        """Отправка с файлом (multipart): фирменная картинка один раз, дальше — по file_id."""
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
        req = urllib.request.Request(f"{self.base}/{method}", data=json.dumps(p, ensure_ascii=False).encode(),
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
    def __init__(self, api, db, admins: set[int], cfg: dict, clock=now, managers: set[int] | None = None):
        """admins = владельцы (OWNER_IDS): всё, включая ⚙️ Созламалар. managers — получают заявки и ведут заказы."""
        self.api, self.db, self.owners, self.cfg, self.clock = api, db, set(admins), cfg, clock
        self.env_managers = set(managers or ())
        self.cats = [tuple(c) for c in cfg.get("categories", [])]

    # ---------- настройки: ⚙️ Созламалар поверх config.toml ----------
    def kv(self, k: str, default=None):
        r = self.db.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
        return r[0] if r else default

    def kv_set(self, k: str, v) -> None:
        if v is None:
            self.db.execute("DELETE FROM kv WHERE k=?", (k,))
        else:
            self.db.execute("INSERT OR REPLACE INTO kv VALUES (?,?)", (k, str(v)))
        self.db.commit()

    def conf(self, key: str) -> str:
        v = self.kv(f"set:{key}")
        return v if v is not None else str(self.cfg.get(key, "") or "")

    def feat(self, name: str) -> bool:
        v = self.kv(f"feat:{name}")
        return v == "1" if v is not None else bool(self.cfg.get("features", {}).get(name, name != "gate"))

    def managers(self) -> dict:
        return {int(k): v for k, v in json.loads(self.kv("managers", "{}")).items()}

    @property
    def admins(self) -> set[int]:
        return self.owners | self.env_managers | set(self.managers())

    def channel_url(self) -> str:
        ch = self.conf("channel").lstrip("@")
        return f"https://t.me/{ch}" if ch else self.conf("telegram_channel")

    # ---------- хранение ----------
    def user(self, uid: int) -> dict:
        r = self.db.execute("SELECT * FROM users WHERE uid=?", (uid,)).fetchone()
        if not r:
            return {"uid": uid, "step": None, "data": {}, "phone": None, "src": None, "first": "", "username": ""}
        d = dict(r)
        d["data"] = json.loads(d["data"] or "{}")
        return d

    def save(self, uid: int, **kw) -> None:
        u = self.user(uid)
        u.update(kw)
        self.db.execute("INSERT OR REPLACE INTO users (uid, first, username, phone, src, step, data, updated) "
                        "VALUES (?,?,?,?,?,?,?,?)",
                        (uid, u.get("first"), u.get("username"), u.get("phone"), u.get("src"), u.get("step"),
                         json.dumps(u.get("data") or {}, ensure_ascii=False), self.clock().isoformat()))
        self.db.commit()

    def step(self, uid: int, step: str | None, fresh: bool = False, **data) -> None:
        """fresh=True — новый сценарий: данные прошлого сценария не тянем (чужой адрес/категория в заявке)."""
        u = self.user(uid)
        d = {} if step is None else dict({} if fresh else u["data"], **data)
        self.save(uid, step=step, data=d)

    # ---------- отправка ----------
    def send(self, chat: int, text: str, kb: dict | None = None) -> dict | None:
        p = {"chat_id": chat, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
        if kb:
            p["reply_markup"] = kb
        try:
            return self.api("sendMessage", **p)
        except Exception as e:  # noqa: BLE001 — человек заблокировал бота и т.п.
            print(f"send {chat}: {e}", flush=True)
            return None

    def menu_kb(self) -> dict:
        f = self.feat
        items = [(T.MENU_CATALOG, f("catalog")), (T.MENU_ORDER, f("order")),
                 (T.MENU_CHEAPER, f("cheaper")), (T.MENU_ROOM, f("room")),
                 (T.MENU_MEASURE, f("measure")), (T.MENU_TRACK, f("tracking")),
                 (T.MENU_PLACES, True), (T.MENU_CONTACT, True)]
        btn = [{"text": t} for t, on in items if on]
        return {"keyboard": [btn[i:i + 2] for i in range(0, len(btn), 2)], "resize_keyboard": True,
                "is_persistent": True}

    def cancel_kb(self, extra: list | None = None) -> dict:
        rows = [extra] if extra else []
        return {"keyboard": rows + [[{"text": T.CANCEL}]], "resize_keyboard": True}

    def cats_kb(self, prefix: str, counts: dict | None = None) -> dict:
        btn = []
        for key, title in self.cats:
            if counts is not None:
                if not counts.get(key):
                    continue
                title = f"{title} ({counts[key]})"
            btn.append({"text": title, "callback_data": f"{prefix}:{key}"})
        return {"inline_keyboard": [btn[i:i + 2] for i in range(0, len(btn), 2)]}

    def cat_title(self, key: str) -> str:
        return dict(self.cats).get(key, key)

    # ---------- вход ----------
    def handle(self, upd: dict) -> None:
        if "chat_join_request" in upd:
            self.on_join(upd["chat_join_request"])
        elif "message" in upd:
            self.on_message(upd["message"])
        elif "callback_query" in upd:
            self.on_callback(upd["callback_query"])

    def on_message(self, msg: dict) -> None:
        chat = msg["chat"]
        if chat.get("type") != "private":
            return
        uid = chat["id"]
        fr = msg.get("from") or {}
        u = self.user(uid)
        if u.get("first") != fr.get("first_name") or u.get("username") != fr.get("username"):
            self.save(uid, first=fr.get("first_name") or "", username=fr.get("username") or "")
            u = self.user(uid)
        text = (msg.get("text") or msg.get("caption") or "").strip()
        if text.startswith("/start"):
            payload = text[6:].strip().lower()
            src = "Instagram" if payload.startswith("insta") else (payload or u.get("src") or "Telegram")
            self.save(uid, src=src, step=None, data={})
            if self.gate_blocks(uid):
                return
            self.welcome(uid, fr.get("first_name") or "")
            return
        if text in ("/admin", "/a") and uid in self.admins:
            self.step(uid, None)
            self.admin_menu(uid)
            return
        if text == T.CANCEL or text == "/cancel":
            self.step(uid, None)
            self.send(uid, T.CANCELLED, self.menu_kb())
            return
        menu = {T.MENU_CATALOG: self.catalog, T.MENU_ORDER: self.order_start, T.MENU_CHEAPER: self.cheaper_start,
                T.MENU_ROOM: self.room_start, T.MENU_MEASURE: self.measure_start, T.MENU_TRACK: self.track,
                T.MENU_PLACES: self.places, T.MENU_CONTACT: self.contact}
        if text in menu:
            self.step(uid, None)
            if uid not in self.admins and self.gate_blocks(uid):
                return
            menu[text](uid)
            return
        st = u.get("step")
        if st:
            self.on_step(uid, st, msg, text)
            return
        ph = self.photo_id(msg)
        if ph:  # 26.10: реклама «расмини ботга юборинг» — фото без кнопки = заявка «Арзонроқ топамиз»
            if uid not in self.admins and self.gate_blocks(uid):
                return
            self.step(uid, "phone", fresh=True, kind="cheaper", details=text, photos=[ph])
            self.send(uid, T.PHOTO_DIRECT)
            self.ask_phone(uid)
            return
        self.send(uid, T.UNKNOWN, self.menu_kb())

    @staticmethod
    def photo_id(msg: dict) -> str | None:
        if msg.get("photo"):
            return msg["photo"][-1]["file_id"]
        doc = msg.get("document") or {}
        if (doc.get("mime_type") or "").startswith("image/"):
            return doc["file_id"]
        return None

    def on_step(self, uid: int, st: str, msg: dict, text: str) -> None:
        u = self.user(uid)
        d = u["data"]
        ph = self.photo_id(msg)
        if st == "order_details":
            if not text and not ph:
                self.send(uid, T.ORDER_DETAILS, self.cancel_kb())
                return
            self.step(uid, "phone", details=text, photos=d.get("photos", []) + ([ph] if ph else []))
            self.ask_phone(uid)
        elif st == "cheaper_photo":
            if not ph:
                self.send(uid, T.CHEAPER_NEED_PHOTO, self.cancel_kb())
                return
            self.step(uid, "phone", details=text, photos=[ph])
            self.ask_phone(uid)
        elif st == "room_photo":
            if not ph:
                self.send(uid, T.ROOM_NEED_PHOTO, self.cancel_kb())
                return
            if d.get("product"):
                self.step(uid, "phone", photos=[ph], details=(text + "\n" if text else "") + d.get("details", ""))
                self.ask_phone(uid)
                return
            self.step(uid, "room_what", photos=[ph], details=text)
            self.send(uid, T.ROOM_WHAT, self.cats_kb("r"))
        elif st == "room_what":
            if not text:
                self.send(uid, T.ROOM_WHAT, self.cats_kb("r"))
                return
            self.step(uid, "phone", details=((d.get("details") or "") + "\n" + text).strip())
            self.ask_phone(uid)
        elif st == "measure_address":
            loc = msg.get("location")
            if loc:
                addr = f"📍 https://maps.google.com/?q={loc['latitude']},{loc['longitude']}"
            elif text:
                addr = text
            else:
                self.send(uid, T.MEASURE_ADDRESS, self.cancel_kb([{"text": T.SEND_LOCATION, "request_location": True}]))
                return
            self.step(uid, "phone", address=addr)
            self.ask_phone(uid)
        elif st == "phone":
            c = msg.get("contact")
            phone = norm_phone(c["phone_number"]) if c and c.get("phone_number") else norm_phone(text)
            if not phone:
                self.send(uid, T.PHONE_BAD, self.phone_kb())
                return
            self.save(uid, phone=phone)
            self.finish(uid)
        elif st.startswith("set:") and uid in self.owners:
            key = st[4:]
            val = text.strip()
            if key == "channel" and val and not val.startswith("@"):
                val = "@" + val.rsplit("/", 1)[-1]
            self.kv_set(f"set:{key}", "" if val in ("-", "—") else val)
            self.step(uid, None)
            self.send(uid, T.SET_SAVED, self.menu_kb())
            self.settings(uid)
        elif st.startswith("add_") and uid in self.admins:
            self.admin_step(uid, st, msg, text, ph)
        elif st.startswith("ordphoto:") and uid in self.admins:
            self.order_photo(uid, int(st.split(":")[1]), ph)
        else:
            self.send(uid, T.UNKNOWN, self.menu_kb())

    # ---------- сценарии покупателя ----------
    def order_start(self, uid: int) -> None:
        self.step(uid, "order_cat", fresh=True, kind="order")
        self.send(uid, T.ORDER_CAT, self.cats_kb("o"))

    def cheaper_start(self, uid: int) -> None:
        self.step(uid, "cheaper_photo", fresh=True, kind="cheaper")
        self.send(uid, T.CHEAPER_PHOTO, self.cancel_kb())

    def room_start(self, uid: int, product: dict | None = None) -> None:
        extra = {"product": product["id"], "details": f"Каталог №{product['id']}: {product['title']}"} if product else {}
        self.step(uid, "room_photo", fresh=True, kind="room", **extra)
        self.send(uid, T.ROOM_PHOTO, self.cancel_kb())

    def measure_start(self, uid: int) -> None:
        self.step(uid, "measure_day", fresh=True, kind="measure")
        today = self.clock().date()
        btn = []
        for i in range(1, int(self.cfg.get("measure", {}).get("days_ahead", 6)) + 1):
            d = today + dt.timedelta(days=i)
            btn.append({"text": day_label(d), "callback_data": f"m:d:{d.isoformat()}"})
        self.send(uid, T.MEASURE_DAY, {"inline_keyboard": [btn[i:i + 2] for i in range(0, len(btn), 2)]})

    def phone_kb(self) -> dict:
        return self.cancel_kb([{"text": T.SEND_PHONE, "request_contact": True}])

    def ask_phone(self, uid: int) -> None:
        u = self.user(uid)
        if u.get("phone"):
            self.send(uid, T.PHONE_KNOWN.format(phone=esc(u["phone"])),
                      {"inline_keyboard": [[{"text": "✅ Ҳа", "callback_data": "p:yes"},
                                            {"text": "✏️ Бошқа рақам", "callback_data": "p:new"}]]})
        else:
            self.send(uid, T.PHONE_ASK, self.phone_kb())

    def finish(self, uid: int) -> None:
        """Телефон есть — заявка менеджеру, покупателю «раҳмат»."""
        u = self.user(uid)
        d = u["data"]
        kind = d.get("kind", "order")
        parts = []
        if d.get("cat"):
            parts.append(f"Тур: {self.cat_title(d['cat'])}")
        if d.get("details"):
            parts.append(d["details"])
        if kind == "measure":
            parts.append(f"Ўлчов: {d.get('day_label')}, {d.get('time')}")
            parts.append(f"Манзил: {d.get('address')}")
        n = self.new_lead(uid, kind, u["phone"], "\n".join(p for p in parts if p), d.get("photos", []))
        self.step(uid, None)
        if kind == "measure":
            self.send(uid, T.MEASURE_DONE.format(day=esc(d.get("day_label")), time=esc(d.get("time")), n=n,
                                                 phone=esc(u["phone"])), self.menu_kb())
        elif kind == "room" and not self.feat("room_ai"):
            self.send(uid, f"{T.ROOM_DONE_NO_AI}\n\nАриза №{n}.", self.menu_kb())
        else:
            self.send(uid, T.LEAD_DONE.format(n=n, phone=esc(u["phone"])), self.menu_kb())
        self.offer_channel(uid)

    # ---------- заявки (менеджер) ----------
    def new_lead(self, uid: int, kind: str, phone: str, details: str, photos: list) -> int:
        u = self.user(uid)
        cur = self.db.execute("INSERT INTO leads (uid, kind, phone, details, photos, src, created) VALUES (?,?,?,?,?,?,?)",
                              (uid, kind, phone, details, json.dumps(photos), u.get("src") or "Telegram",
                               self.clock().isoformat()))
        self.db.commit()
        n = cur.lastrowid
        self.notify_lead(n)
        return n

    def who(self, uid: int) -> str:
        u = self.user(uid)
        name = esc(u.get("first") or "Мижоз")
        link = f'<a href="tg://user?id={uid}">{name}</a>'
        return link + (f" (@{esc(u['username'])})" if u.get("username") else "")

    def lead_text(self, n: int) -> str:
        r = self.db.execute("SELECT * FROM leads WHERE n=?", (n,)).fetchone()
        details = f"📝 {esc(r['details'])}\n" if r["details"] else ""
        t = T.LEAD_CARD.format(n=n, kind=T.KIND.get(r["kind"], r["kind"]), who=self.who(r["uid"]), phone=esc(r["phone"]),
                               details=details, src=esc(r["src"]),
                               time=dt.datetime.fromisoformat(r["created"]).astimezone(TZ).strftime("%d.%m %H:%M"))
        for line in json.loads(r["log"] or "[]"):
            t += f"\n{esc(line)}"
        return t

    def lead_kb(self, n: int, status: str) -> dict | None:
        if status in ("won", "lost"):
            return None
        row = [] if status == "called" else [{"text": T.LEAD_CALLED, "callback_data": f"l:called:{n}"}]
        return {"inline_keyboard": ([row] if row else []) + [[{"text": T.LEAD_WON, "callback_data": f"l:won:{n}"},
                                                              {"text": T.LEAD_LOST, "callback_data": f"l:lost:{n}"}]]}

    def notify_lead(self, n: int) -> None:
        r = self.db.execute("SELECT * FROM leads WHERE n=?", (n,)).fetchone()
        photos = json.loads(r["photos"] or "[]")
        cards = {}
        for a in self.admins:
            for p in photos[:5]:
                try:
                    self.api("sendPhoto", chat_id=a, photo=p, caption=f"Ариза №{n}")
                except Exception as e:  # noqa: BLE001
                    print(f"photo → {a}: {e}", flush=True)
            m = self.send(a, self.lead_text(n), self.lead_kb(n, "new"))
            if m:
                cards[str(a)] = m["message_id"]
        self.db.execute("UPDATE leads SET cards=? WHERE n=?", (json.dumps(cards), n))
        self.db.commit()

    def refresh_cards(self, n: int) -> None:
        r = self.db.execute("SELECT status, cards FROM leads WHERE n=?", (n,)).fetchone()
        for a, mid in json.loads(r["cards"] or "{}").items():
            p = {"chat_id": int(a), "message_id": mid, "text": self.lead_text(n), "parse_mode": "HTML",
                 "disable_web_page_preview": True}
            kb = self.lead_kb(n, r["status"])
            if kb:
                p["reply_markup"] = kb
            try:
                self.api("editMessageText", **p)
            except Exception as e:  # noqa: BLE001
                print(f"edit card {n}: {e}", flush=True)

    def set_lead(self, n: int, status: str, by: dict) -> None:
        r = self.db.execute("SELECT * FROM leads WHERE n=?", (n,)).fetchone()
        if not r or r["status"] in ("won", "lost"):
            return
        log = json.loads(r["log"] or "[]")
        log.append(f"{T.LEAD_STATUS[status]} — {by.get('first_name', '')} {self.clock().strftime('%d.%m %H:%M')}")
        self.db.execute("UPDATE leads SET status=?, log=? WHERE n=?", (status, json.dumps(log, ensure_ascii=False), n))
        self.db.commit()
        if status == "won":
            self.new_order(r)
        self.refresh_cards(n)

    def remind(self) -> int:
        """Заявку 15 минут никто не взял — напомнить менеджерам (днём; ночные — утром)."""
        rc = self.cfg.get("remind", {})
        t = self.clock()
        if not rc.get("day_start", 8) <= t.hour < rc.get("day_end", 21):
            return 0
        edge = (t - dt.timedelta(minutes=int(rc.get("minutes", 15)))).isoformat()
        rows = self.db.execute("SELECT * FROM leads WHERE status='new' AND reminded=0 AND created<=?", (edge,)).fetchall()
        for r in rows:
            m = int((t - dt.datetime.fromisoformat(r["created"])).total_seconds() // 60)
            for a in self.admins:
                self.send(a, T.REMIND.format(n=r["n"], kind=T.KIND.get(r["kind"], r["kind"]), m=m,
                                             who=self.who(r["uid"]), phone=esc(r["phone"])))
            self.db.execute("UPDATE leads SET reminded=1 WHERE n=?", (r["n"],))
        self.db.commit()
        return len(rows)

    # ---------- буюртмалар: этапы и фото из цеха ----------
    def new_order(self, lead) -> int:
        title = T.KIND.get(lead["kind"], lead["kind"])
        first = (lead["details"] or "").split("\n")[0][:60]
        if first:
            title = first
        ts = self.clock().isoformat()
        cur = self.db.execute("INSERT INTO orders (lead, uid, title, created, updated) VALUES (?,?,?,?,?)",
                              (lead["n"], lead["uid"], title, ts, ts))
        self.db.commit()
        n = cur.lastrowid
        if self.feat("tracking"):
            self.send(lead["uid"], T.ORDER_CREATED_CLIENT.format(n=n))
        for a in self.admins:
            self.send(a, self.order_text(n), self.order_kb(n))
        return n

    def order_text(self, n: int) -> str:
        o = self.db.execute("SELECT * FROM orders WHERE n=?", (n,)).fetchone()
        phone = (self.db.execute("SELECT phone FROM leads WHERE n=?", (o["lead"],)).fetchone() or {"phone": ""})["phone"]
        return T.ORDER_CARD.format(n=n, title=esc(o["title"]), who=self.who(o["uid"]), phone=esc(phone),
                                   stage=T.STAGES[o["stage"]])

    def order_kb(self, n: int) -> dict:
        o = self.db.execute("SELECT stage FROM orders WHERE n=?", (n,)).fetchone()
        nxt = [{"text": T.STAGES[i], "callback_data": f"s:{n}:{i}"} for i in range(o["stage"] + 1, len(T.STAGES))]
        rows = [nxt[i:i + 2] for i in range(0, len(nxt), 2)]
        rows.append([{"text": "📷 Мижозга расм юбориш", "callback_data": f"s:{n}:ph"}])
        return {"inline_keyboard": rows}

    def set_stage(self, cq: dict, n: int, stage: int) -> None:
        o = self.db.execute("SELECT * FROM orders WHERE n=?", (n,)).fetchone()
        if not o or stage <= o["stage"]:
            return
        self.db.execute("UPDATE orders SET stage=?, updated=? WHERE n=?", (stage, self.clock().isoformat(), n))
        self.db.commit()
        if self.feat("tracking"):
            self.send(o["uid"], T.STAGE_CLIENT.format(n=n, stage=T.STAGES[stage]))
        m = cq.get("message") or {}
        try:
            self.api("editMessageText", chat_id=m["chat"]["id"], message_id=m["message_id"], text=self.order_text(n),
                     parse_mode="HTML", reply_markup=self.order_kb(n), disable_web_page_preview=True)
        except Exception as e:  # noqa: BLE001
            print(f"edit order {n}: {e}", flush=True)

    def order_photo(self, uid: int, n: int, ph: str | None) -> None:
        if not ph:
            self.send(uid, T.ORDER_PHOTO_ASK.format(n=n))
            return
        o = self.db.execute("SELECT * FROM orders WHERE n=?", (n,)).fetchone()
        self.api("sendPhoto", chat_id=o["uid"], photo=ph, parse_mode="HTML",
                 caption=T.ORDER_PHOTO_CLIENT.format(n=n, stage=T.STAGES[o["stage"]]))
        self.step(uid, None)
        self.send(uid, T.ORDER_PHOTO_SENT.format(n=n))

    def track(self, uid: int) -> None:
        rows = self.db.execute("SELECT * FROM orders WHERE uid=? ORDER BY n DESC LIMIT 5", (uid,)).fetchall()
        if not rows:
            self.send(uid, T.TRACK_NONE, self.menu_kb())
            return
        out = [T.TRACK_ITEM.format(n=r["n"], title=esc(r["title"]), stage=T.STAGES[r["stage"]],
                                   date=dt.datetime.fromisoformat(r["updated"]).astimezone(TZ).strftime("%d.%m.%Y"))
               for r in rows]
        self.send(uid, "\n\n".join(out), self.menu_kb())

    # ---------- каталог ----------
    def counts(self) -> dict:
        return {r[0]: r[1] for r in self.db.execute("SELECT cat, COUNT(*) FROM products WHERE active=1 GROUP BY cat")}

    def go_kb(self) -> dict:
        row = []
        if self.feat("order"):
            row.append({"text": T.MENU_ORDER, "callback_data": "g:order"})
        if self.feat("cheaper"):
            row.append({"text": T.MENU_CHEAPER, "callback_data": "g:cheaper"})
        return {"inline_keyboard": [row]} if row else None

    def catalog(self, uid: int) -> None:
        c = self.counts()
        if not c:
            self.send(uid, T.CATALOG_EMPTY, self.go_kb())
            return
        self.send(uid, T.CATALOG, self.cats_kb("c", c))

    def products(self, cat: str) -> list:
        return self.db.execute("SELECT * FROM products WHERE cat=? AND active=1 ORDER BY id", (cat,)).fetchall()

    def product_view(self, uid: int, p, i: int, total: int) -> tuple[str, dict]:
        lines = "\n".join(esc(x) for x in (p["info"] or "").split("\n") if x.strip())
        cap = T.PRODUCT_CAPTION.format(title=esc(p["title"]), lines=lines, phone=esc(self.conf("phone")))
        nav = []
        if total > 1:
            nav = [{"text": "◀️", "callback_data": f"c:{p['cat']}:{(i - 1) % total}"},
                   {"text": f"{i + 1}/{total}", "callback_data": "noop"},
                   {"text": "▶️", "callback_data": f"c:{p['cat']}:{(i + 1) % total}"}]
        rows = [nav] if nav else []
        rows.append([{"text": T.PRODUCT_ORDER, "callback_data": f"b:{p['id']}"}])
        if self.feat("room"):
            rows.append([{"text": T.PRODUCT_ROOM, "callback_data": f"rm:{p['id']}"}])
        rows.append([{"text": T.BACK_CATS, "callback_data": "cats"}])
        if uid in self.admins:
            rows.append([{"text": "🙈 Каталогдан олиш (админ)", "callback_data": f"h:{p['id']}"}])
        return cap, {"inline_keyboard": rows}

    def show_product(self, uid: int, cat: str, i: int, edit: dict | None = None) -> None:
        ps = self.products(cat)
        if not ps:
            self.send(uid, T.CATEGORY_EMPTY, self.go_kb())
            return
        i %= len(ps)
        cap, kb = self.product_view(uid, ps[i], i, len(ps))
        if edit:
            try:
                self.api("editMessageMedia", chat_id=edit["chat"]["id"], message_id=edit["message_id"],
                         media={"type": "photo", "media": ps[i]["photo"], "caption": cap, "parse_mode": "HTML"},
                         reply_markup=kb)
                return
            except Exception as e:  # noqa: BLE001 — старое сообщение: шлём новое
                print(f"editMedia: {e}", flush=True)
        self.api("sendPhoto", chat_id=uid, photo=ps[i]["photo"], caption=cap, parse_mode="HTML", reply_markup=kb)

    # ---------- адреса и контакты ----------
    def places(self, uid: int) -> None:
        self.send(uid, T.PLACES + (f"\n🕐 {esc(self.conf('hours'))}" if self.conf("hours") else ""), self.menu_kb())
        for loc in self.cfg.get("locations", []):
            try:
                self.api("sendVenue", chat_id=uid, latitude=loc["lat"], longitude=loc["lon"], title=loc["title"],
                         address=loc.get("address", ""))
            except Exception as e:  # noqa: BLE001
                print(f"venue: {e}", flush=True)

    def contact(self, uid: int) -> None:
        c = self.conf
        t = T.CONTACT.format(name=esc(c("name")), phone=esc(c("phone")))
        if c("hours"):
            t += f"\n🕐 {esc(c('hours'))}"
        if c("delivery"):
            t += f"\n🚚 {esc(c('delivery'))}"
        rows = []
        if c("manager"):
            rows.append([{"text": T.WRITE_MANAGER, "url": f"https://t.me/{c('manager').lstrip('@')}"}])
        if c("instagram"):
            rows.append([{"text": "📸 Instagram", "url": c("instagram")}])
        if self.channel_url():
            rows.append([{"text": "📢 Telegram канал", "url": self.channel_url()}])
        self.send(uid, t, {"inline_keyboard": rows} if rows else self.menu_kb())

    # ---------- фирменное приветствие и канал ----------
    BANNER = HERE / "assets" / "welcome.jpg"

    def banner_key(self) -> str:
        """file_id привязан к содержимому картинки: новая welcome.jpg — загружается заново (26.10: смена номера)."""
        if not self.BANNER.exists():
            return "banner_id"
        return "banner_id:" + hashlib.sha1(self.BANNER.read_bytes()).hexdigest()[:10]

    def welcome(self, uid: int, first: str) -> None:
        """Фирменная картинка (кремовый фон, логотип, #1F3A28/#B8814A, Inter Display) + приветствие + меню."""
        cap = T.START.format(first=esc(first), name=esc(self.conf("name")))
        key = self.banner_key()
        fid = self.kv(key)
        try:
            if fid:
                self.api("sendPhoto", chat_id=uid, photo=fid, caption=cap, parse_mode="HTML", reply_markup=self.menu_kb())
            elif self.BANNER.exists():
                r = self.api.upload("sendPhoto", "photo", self.BANNER.read_bytes(), chat_id=uid, caption=cap,
                                    parse_mode="HTML", reply_markup=self.menu_kb())
                if r and r.get("photo"):
                    self.kv_set(key, r["photo"][-1]["file_id"])
            else:
                self.send(uid, cap, self.menu_kb())
        except Exception as e:  # noqa: BLE001 — картинка не ушла: приветствие текстом
            print(f"banner: {e}", flush=True)
            self.kv_set(key, None)
            self.send(uid, cap, self.menu_kb())
        self.welcome_channel(uid)

    def welcome_channel(self, uid: int) -> None:
        """24.10 владелец: в приветствии сразу зовём в канал (публичный канал не даёт «одним нажатием в оба»)."""
        if self.channel_url() and self.is_member(uid) is not True:
            self.send(uid, T.CHANNEL_WELCOME, self.channel_kb())
            self.kv_set(f"offered:{uid}", "1")

    def is_member(self, uid: int) -> bool | None:
        ch = self.conf("channel")
        if not ch:
            return None
        try:
            r = self.api("getChatMember", chat_id=ch, user_id=uid)
        except Exception as e:  # noqa: BLE001 — бот не админ / сеть: не мешаем человеку
            print(f"getChatMember: {e}", flush=True)
            return None
        return r.get("status") in ("member", "administrator", "creator", "restricted")

    def channel_kb(self, check: bool = False) -> dict:
        rows = [[{"text": T.CHANNEL_BTN, "url": self.channel_url()}]]
        if check:
            rows.append([{"text": T.GATE_CHECK, "callback_data": "gate"}])
        return {"inline_keyboard": rows}

    def gate_blocks(self, uid: int) -> bool:
        """🔒 Жёсткая подписка — только если владелец включил (по умолчанию выкл). Не узнали — пропускаем."""
        if not self.feat("gate") or not self.channel_url():
            return False
        if self.is_member(uid) is False:
            self.send(uid, T.GATE, self.channel_kb(check=True))
            return True
        return False

    def offer_channel(self, uid: int) -> None:
        """Мягко: после заявки, один раз, только тем, кто ещё не в канале."""
        if not self.channel_url() or self.kv(f"offered:{uid}"):
            return
        if self.is_member(uid) is False:
            self.send(uid, T.CHANNEL_OFFER, self.channel_kb())
            self.kv_set(f"offered:{uid}", "1")

    def on_join(self, j: dict) -> None:
        """Заявка в канал (ссылка из Instagram): сразу пишем в личку (у бота 5 минут) и одобряем — человек в канале и в боте."""
        fr = j.get("from") or {}
        uid = fr.get("id")
        chat = j.get("chat") or {}
        if not uid:
            return
        ch = self.conf("channel").lstrip("@").lower()
        if ch and (chat.get("username") or "").lower() != ch:
            return
        name = ((j.get("invite_link") or {}).get("name") or "").lower()
        src = "Instagram" if name.startswith("insta") else "Канал"
        u = self.user(uid)
        self.save(uid, first=fr.get("first_name") or "", username=fr.get("username") or "", src=u.get("src") or src)
        dm = j.get("user_chat_id") or uid
        self.welcome(dm, fr.get("first_name") or "")
        try:
            self.api("approveChatJoinRequest", chat_id=chat["id"], user_id=uid)
            self.kv_set("joins", int(self.kv("joins", "0")) + 1)
        except Exception as e:  # noqa: BLE001
            print(f"approve {uid}: {e}", flush=True)

    def instagram_link(self) -> str | None:
        link = self.kv("link:instagram")
        if link or not self.conf("channel"):
            return link
        try:
            r = self.api("createChatInviteLink", chat_id=self.conf("channel"), name="Instagram", creates_join_request=True)
            link = r.get("invite_link")
            if link:
                self.kv_set("link:instagram", link)
        except Exception as e:  # noqa: BLE001 — нет права «Добавление участников»
            print(f"invite link: {e}", flush=True)
        return link

    # ---------- ⚙️ Созламалар и 📊 Статистика (владелец) ----------
    def settings(self, uid: int) -> None:
        e = lambda k: esc(self.conf(k)) or T.SET_EMPTY  # noqa: E731
        mg = ", ".join(esc(v) for v in self.managers().values()) or T.SET_EMPTY
        self.send(uid, T.SET_MENU.format(phone=e("phone"), hours=e("hours"), delivery=e("delivery"), channel=e("channel"),
                                         managers=mg), {"inline_keyboard": [
            [{"text": "☎️ Телефон", "callback_data": "set:e:phone"}, {"text": "🕐 Иш вақти", "callback_data": "set:e:hours"}],
            [{"text": "🚚 Етказиб бериш", "callback_data": "set:e:delivery"}, {"text": "📢 Канал", "callback_data": "set:e:channel"}],
            [{"text": "🔘 Тугмалар", "callback_data": "set:f"}, {"text": "👥 Менежерлар", "callback_data": "set:m"}],
            [{"text": "🔗 Instagram ҳаволаси", "callback_data": "set:l"}, {"text": "📊 Статистика", "callback_data": "a:stats"}]]})

    def features_kb(self) -> dict:
        return {"inline_keyboard": [[{"text": ("✅ " if self.feat(k) else "⬜ ") + t, "callback_data": f"set:t:{k}"}]
                                    for k, t in T.FEATURES] + [[{"text": "⬅️ Созламалар", "callback_data": "a:set"}]]}

    def settings_cb(self, cq: dict, uid: int, part: list) -> None:
        if part[1] == "e":
            self.step(uid, f"set:{part[2]}", fresh=True)
            self.send(uid, T.SET_ASK[part[2]] + "\n(ўчириш учун: -)", self.cancel_kb())
        elif part[1] == "f":
            self.send(uid, T.SET_FEATURES, self.features_kb())
        elif part[1] == "t":
            self.kv_set(f"feat:{part[2]}", "0" if self.feat(part[2]) else "1")
            m = cq.get("message") or {}
            try:
                self.api("editMessageReplyMarkup", chat_id=m["chat"]["id"], message_id=m["message_id"],
                         reply_markup=self.features_kb())
            except Exception:  # noqa: BLE001
                self.send(uid, T.SET_FEATURES, self.features_kb())
            self.send(uid, T.SET_SAVED, self.menu_kb())
        elif part[1] == "m":
            rows = [[{"text": f"❌ {v}", "callback_data": f"set:mr:{k}"}] for k, v in self.managers().items()]
            rows.append([{"text": "➕ Қўшиш", "callback_data": "set:mp"}])
            self.send(uid, T.SET_MANAGERS, {"inline_keyboard": rows})
        elif part[1] == "mp":
            rows = self.db.execute("SELECT uid, first, username FROM users ORDER BY updated DESC LIMIT 15").fetchall()
            btn = [[{"text": f"{r['first'] or ''} @{r['username'] or ''}".strip(), "callback_data": f"set:ma:{r['uid']}"}]
                   for r in rows if r["uid"] not in self.admins][:8]
            self.send(uid, T.SET_PICK if btn else "Ҳали ҳеч ким ёзмаган.", {"inline_keyboard": btn} if btn else None)
        elif part[1] == "ma":
            m = self.managers()
            u = self.user(int(part[2]))
            m[int(part[2])] = (u.get("first") or "") + (f" @{u['username']}" if u.get("username") else "")
            self.kv_set("managers", json.dumps({str(k): v for k, v in m.items()}, ensure_ascii=False))
            self.send(uid, T.SET_SAVED)
            self.send(int(part[2]), "✅ Сиз Shodiyona менежери этиб тайинландингиз. Аризалар шу ерга келади. Бошқарув: /admin")
        elif part[1] == "mr":
            m = self.managers()
            m.pop(int(part[2]), None)
            self.kv_set("managers", json.dumps({str(k): v for k, v in m.items()}, ensure_ascii=False))
            self.send(uid, T.SET_SAVED)
        elif part[1] == "l":
            self.send(uid, T.SET_LINK.format(link=esc(self.instagram_link() or "— (ботга каналда «Қўшиш» ҳуқуқини беринг)")))

    def stats(self, uid: int) -> None:
        t = self.clock()
        d1 = t.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        d7 = (t - dt.timedelta(days=7)).isoformat()
        q = lambda sql, *a: self.db.execute(sql, a).fetchall()  # noqa: E731
        cnt = lambda since: q("SELECT COUNT(*) FROM leads WHERE created>=?", since)[0][0]  # noqa: E731
        won = lambda since: q("SELECT COUNT(*) FROM orders WHERE created>=?", since)[0][0]  # noqa: E731
        kinds = ", ".join(f"{T.KIND.get(k, k)} {n}" for k, n in q("SELECT kind, COUNT(*) FROM leads WHERE created>=? GROUP BY kind", d7)) or "—"
        srcs = ", ".join(f"{k} {n}" for k, n in q("SELECT src, COUNT(*) FROM leads WHERE created>=? GROUP BY src", d7)) or "—"
        self.send(uid, T.STATS.format(d1=cnt(d1), w1=won(d1), d7=cnt(d7), w7=won(d7), kinds=esc(kinds), srcs=esc(srcs),
                                      joins=self.kv("joins", "0"), users=q("SELECT COUNT(*) FROM users")[0][0]))

    # ---------- админ: каталог ----------
    def admin_menu(self, uid: int) -> None:
        rows = [[{"text": "➕ Маҳсулот", "callback_data": "a:add"}, {"text": "📊 Статистика", "callback_data": "a:stats"}],
                [{"text": "📥 Очиқ аризалар", "callback_data": "a:leads"},
                 {"text": "📦 Буюртмалар", "callback_data": "a:orders"}]]
        if uid in self.owners:
            rows.append([{"text": "⚙️ Созламалар", "callback_data": "a:set"}])
        self.send(uid, T.ADMIN_MENU, {"inline_keyboard": rows})

    def admin_step(self, uid: int, st: str, msg: dict, text: str, ph: str | None) -> None:
        d = self.user(uid)["data"]
        if st == "add_photo":
            if not ph:
                self.send(uid, T.ADD_PHOTO, self.cancel_kb())
                return
            self.step(uid, "add_text", photo=ph)
            if text:                                   # подпись к фото = сразу данные
                self.admin_step(uid, "add_text", msg, text, None)
                return
            self.send(uid, T.ADD_TEXT, self.cancel_kb())
        elif st == "add_text":
            lines = [x.strip() for x in text.split("\n") if x.strip()]
            if not lines:
                self.send(uid, T.ADD_TEXT, self.cancel_kb())
                return
            info = "\n".join([f"📏 {lines[1]}" if len(lines) > 1 else "", f"🪵 {lines[2]}" if len(lines) > 2 else "",
                              f"💰 {lines[3]}" if len(lines) > 3 else ""]).strip()
            cur = self.db.execute("INSERT INTO products (cat, title, info, photo, created) VALUES (?,?,?,?,?)",
                                  (d["cat"], lines[0], info, d["photo"], self.clock().isoformat()))
            self.db.commit()
            self.step(uid, None)
            self.send(uid, T.ADD_DONE.format(id=cur.lastrowid), self.menu_kb())

    # ---------- кнопки ----------
    def on_callback(self, cq: dict) -> None:
        uid = cq["from"]["id"]
        data = cq.get("data") or ""
        try:
            self.api("answerCallbackQuery", callback_query_id=cq["id"])
        except Exception:  # noqa: BLE001
            pass
        u = self.user(uid)
        st = u.get("step")
        part = data.split(":")
        admin = uid in self.admins
        if data == "noop":
            return
        if data == "gate":
            if self.is_member(uid) is False:
                self.send(uid, T.GATE_NOT_YET, self.channel_kb(check=True))
            else:
                self.welcome(uid, cq["from"].get("first_name") or "")
            return
        if part[0] == "set" and uid in self.owners:
            self.settings_cb(cq, uid, part)
            return
        if part[0] == "o" and st == "order_cat":
            self.step(uid, "order_details", cat=part[1])
            self.send(uid, f"{self.cat_title(part[1])} ✅\n\n{T.ORDER_DETAILS}", self.cancel_kb())
        elif part[0] == "r" and st == "room_what":
            self.step(uid, "phone", cat=part[1])
            self.ask_phone(uid)
        elif part[0] == "m" and part[1] == "d" and st == "measure_day":
            d = dt.date.fromisoformat(part[2])
            self.step(uid, "measure_time", day=part[2], day_label=day_label(d))
            times = self.cfg.get("measure", {}).get("times", [])
            btn = [{"text": t, "callback_data": f"m:t:{t}"} for t in times]
            self.send(uid, f"{day_label(d)} ✅\n\n{T.MEASURE_TIME}",
                      {"inline_keyboard": [btn[i:i + 3] for i in range(0, len(btn), 3)]})
        elif part[0] == "m" and part[1] == "t" and st == "measure_time":
            t = ":".join(part[2:])
            self.step(uid, "measure_address", time=t)
            self.send(uid, f"{t} ✅\n\n{T.MEASURE_ADDRESS}",
                      self.cancel_kb([{"text": T.SEND_LOCATION, "request_location": True}]))
        elif part[0] == "p" and st == "phone":
            if part[1] == "yes" and u.get("phone"):
                self.finish(uid)
            else:
                self.send(uid, T.PHONE_ASK, self.phone_kb())
        elif data == "cats":
            self.catalog(uid)
        elif part[0] == "c" and len(part) == 2:
            self.show_product(uid, part[1], 0)
        elif part[0] == "c" and len(part) == 3:
            self.show_product(uid, part[1], int(part[2]), edit=cq.get("message"))
        elif part[0] == "b":
            p = self.db.execute("SELECT * FROM products WHERE id=?", (int(part[1]),)).fetchone()
            if p:
                self.step(uid, "phone", fresh=True, kind="product", cat=p["cat"], details=f"Каталог №{p['id']}: {p['title']}",
                          photos=[p["photo"]])
                self.ask_phone(uid)
        elif part[0] == "rm":
            p = self.db.execute("SELECT * FROM products WHERE id=?", (int(part[1]),)).fetchone()
            if p:
                self.room_start(uid, dict(p))
        elif part[0] == "g":
            {"order": self.order_start, "cheaper": self.cheaper_start}.get(part[1], self.catalog)(uid)
        elif part[0] == "l" and admin:
            self.set_lead(int(part[2]), part[1], cq["from"])
        elif part[0] == "s" and admin:
            if part[2] == "ph":
                self.step(uid, f"ordphoto:{part[1]}", fresh=True)
                self.send(uid, T.ORDER_PHOTO_ASK.format(n=part[1]), self.cancel_kb())
            else:
                self.set_stage(cq, int(part[1]), int(part[2]))
        elif part[0] == "h" and admin:
            self.db.execute("UPDATE products SET active=0 WHERE id=?", (int(part[1]),))
            self.db.commit()
            self.send(uid, T.HIDDEN.format(id=part[1]))
        elif part[0] == "a" and admin:
            self.admin_cb(uid, part)

    def admin_cb(self, uid: int, part: list) -> None:
        if part[1] == "set" and uid in self.owners:
            self.settings(uid)
        elif part[1] == "stats":
            self.stats(uid)
        elif part[1] == "add":
            self.step(uid, "add_cat", fresh=True)
            self.send(uid, T.ADD_CAT, self.cats_kb("a:cat"))
        elif part[1] == "cat":
            self.step(uid, "add_photo", cat=part[2])
            self.send(uid, f"{self.cat_title(part[2])} ✅\n\n{T.ADD_PHOTO}", self.cancel_kb())
        elif part[1] == "leads":
            rows = self.db.execute("SELECT n FROM leads WHERE status IN ('new','called') ORDER BY n DESC LIMIT 10").fetchall()
            if not rows:
                self.send(uid, T.NO_OPEN_LEADS)
            for r in reversed(rows):
                st = self.db.execute("SELECT status FROM leads WHERE n=?", (r["n"],)).fetchone()["status"]
                self.send(uid, self.lead_text(r["n"]), self.lead_kb(r["n"], st))
        elif part[1] == "orders":
            rows = self.db.execute(f"SELECT n FROM orders WHERE stage<{len(T.STAGES) - 1} ORDER BY n DESC LIMIT 10").fetchall()
            if not rows:
                self.send(uid, T.NO_ORDERS)
            for r in reversed(rows):
                self.send(uid, self.order_text(r["n"]), self.order_kb(r["n"]))


def run() -> None:
    api = Api(os.environ["SHODIYONA_BOT_TOKEN"])
    db = connect(os.environ.get("SHODIYONA_DB", "/var/lib/papa-shodiyona/shodiyona.sqlite3"))
    ids = lambda k: {int(x) for x in os.environ.get(k, "").split(",") if x.strip()}  # noqa: E731
    bot = Bot(api, db, ids("OWNER_IDS"), load_cfg(os.environ.get("SHODIYONA_CONFIG")), managers=ids("MANAGER_IDS"))
    me = api("getMe")
    for m, p in (("setMyCommands", {"commands": [{"command": "start", "description": "Асосий меню"}]}),
                 ("setMyDescription", {"description": T.BOT_DESCRIPTION}),
                 ("setMyShortDescription", {"short_description": T.BOT_SHORT})):
        try:
            api(m, **p)
        except Exception as e:  # noqa: BLE001
            print(f"{m}: {e}", flush=True)
    link = bot.instagram_link()
    print(f"SHODIYONA @{me['username']} запущен, менеджеров {len(bot.admins)}, канал {bot.conf('channel')}, "
          f"ссылка для Instagram: {link or 'нет (нужно право «Добавление участников»)'}", flush=True)
    off = int((db.execute("SELECT v FROM kv WHERE k='offset'").fetchone() or [0])[0])
    last_tick = 0.0
    while True:
        if time.time() - last_tick > 60:
            try:
                bot.remind()
            except Exception as e:  # noqa: BLE001
                print(f"remind: {e}", flush=True)
            last_tick = time.time()
        try:
            ups = api("getUpdates", offset=off, timeout=30, allowed_updates=["message", "callback_query", "chat_join_request"])
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
