"""@ShodiyonaMebelUzBot — бот мебельного центра Shodiyona (клиент OZOD DIGITAL). Утверждено владельцем 24.10.2026.

Покупатель: каталог · буюртма по размерам · «арзонроқ топамиз» (фото чужой мебели) · «хонангизда кўринг»
(фото комнаты; ИИ — когда шеф оплатит) · бесплатный замер с днём и временем · «буюртмам қаерда?» (этапы и фото из цеха)
· адреса · контакты.
Менеджер (OWNER_IDS + MANAGER_IDS): карточка каждой заявки с кнопками, напоминание через 15 минут, буюртма → этапы,
фото из цеха уходит покупателю, каталог пополняется прямо из Telegram (/admin).
Только стандартная библиотека Python: long polling Bot API + SQLite. Бот ничего не публикует в каналы."""
from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
import sqlite3
import time
import tomllib
import urllib.error
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
    def __init__(self, api, db, admins: set[int], cfg: dict, clock=now):
        self.api, self.db, self.admins, self.cfg, self.clock = api, db, admins, cfg, clock
        self.f = cfg.get("features", {})
        self.cats = [tuple(c) for c in cfg.get("categories", [])]

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
        f = self.f
        items = [(T.MENU_CATALOG, f.get("catalog", True)), (T.MENU_ORDER, f.get("order", True)),
                 (T.MENU_CHEAPER, f.get("cheaper", True)), (T.MENU_ROOM, f.get("room", True)),
                 (T.MENU_MEASURE, f.get("measure", True)), (T.MENU_TRACK, f.get("tracking", True)),
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
        if "message" in upd:
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
            self.send(uid, T.START.format(first=esc(fr.get("first_name") or ""), name=esc(self.cfg["name"])),
                      self.menu_kb())
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
            menu[text](uid)
            return
        st = u.get("step")
        if st:
            self.on_step(uid, st, msg, text)
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
        elif kind == "room" and not self.f.get("room_ai"):
            self.send(uid, f"{T.ROOM_DONE_NO_AI}\n\nАриза №{n}.", self.menu_kb())
        else:
            self.send(uid, T.LEAD_DONE.format(n=n, phone=esc(u["phone"])), self.menu_kb())

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
        if self.f.get("tracking", True):
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
        if self.f.get("tracking", True):
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
        if self.f.get("order", True):
            row.append({"text": T.MENU_ORDER, "callback_data": "g:order"})
        if self.f.get("cheaper", True):
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
        cap = T.PRODUCT_CAPTION.format(title=esc(p["title"]), lines=lines, phone=esc(self.cfg["phone"]))
        nav = []
        if total > 1:
            nav = [{"text": "◀️", "callback_data": f"c:{p['cat']}:{(i - 1) % total}"},
                   {"text": f"{i + 1}/{total}", "callback_data": "noop"},
                   {"text": "▶️", "callback_data": f"c:{p['cat']}:{(i + 1) % total}"}]
        rows = [nav] if nav else []
        rows.append([{"text": T.PRODUCT_ORDER, "callback_data": f"b:{p['id']}"}])
        if self.f.get("room", True):
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
        self.send(uid, T.PLACES + (f"\n🕐 {esc(self.cfg['hours'])}" if self.cfg.get("hours") else ""), self.menu_kb())
        for loc in self.cfg.get("locations", []):
            try:
                self.api("sendVenue", chat_id=uid, latitude=loc["lat"], longitude=loc["lon"], title=loc["title"],
                         address=loc.get("address", ""))
            except Exception as e:  # noqa: BLE001
                print(f"venue: {e}", flush=True)

    def contact(self, uid: int) -> None:
        c = self.cfg
        t = T.CONTACT.format(name=esc(c["name"]), phone=esc(c["phone"]))
        if c.get("hours"):
            t += f"\n🕐 {esc(c['hours'])}"
        if c.get("delivery"):
            t += f"\n🚚 {esc(c['delivery'])}"
        rows = []
        if c.get("instagram"):
            rows.append([{"text": "📸 Instagram", "url": c["instagram"]}])
        if c.get("telegram_channel"):
            rows.append([{"text": "📢 Telegram канал", "url": c["telegram_channel"]}])
        self.send(uid, t, {"inline_keyboard": rows} if rows else self.menu_kb())

    # ---------- админ: каталог ----------
    def admin_menu(self, uid: int) -> None:
        self.send(uid, T.ADMIN_MENU, {"inline_keyboard": [
            [{"text": "➕ Маҳсулот", "callback_data": "a:add"}],
            [{"text": "📥 Очиқ аризалар", "callback_data": "a:leads"},
             {"text": "📦 Буюртмалар", "callback_data": "a:orders"}]]})

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
        if part[1] == "add":
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
    ids = os.environ.get("OWNER_IDS", "") + "," + os.environ.get("MANAGER_IDS", "")
    admins = {int(x) for x in ids.split(",") if x.strip()}
    bot = Bot(api, db, admins, load_cfg(os.environ.get("SHODIYONA_CONFIG")))
    me = api("getMe")
    for m, p in (("setMyCommands", {"commands": [{"command": "start", "description": "Асосий меню"}]}),
                 ("setMyDescription", {"description": T.BOT_DESCRIPTION}),
                 ("setMyShortDescription", {"short_description": T.BOT_SHORT})):
        try:
            api(m, **p)
        except Exception as e:  # noqa: BLE001
            print(f"{m}: {e}", flush=True)
    print(f"SHODIYONA @{me['username']} запущен, менеджеров {len(admins)}", flush=True)
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
            ups = api("getUpdates", offset=off, timeout=30, allowed_updates=["message", "callback_query"])
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
