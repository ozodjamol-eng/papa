"""Бот VOLIDAM × Safo Marva Tour — приём заявок на Умру (клиент Нодирбек Ҳайитов). Утверждено владельцем 02.11.2026.

Паломник: 🕋 пакеты и цены · ✍️ заявка (пакет → дата → хона → неча киши → телефон) · 🌐 страница · 📞 алоқа.
Ссылки со страницы: ?start=site_<пакет>_<ддмм>_<4|3|2> — пакет, дата и хона уже выбраны.
Менеджеры (OWNER_IDS + зарегистрированные по ссылке ?start=mgr_<MANAGER_CODE>): карточка каждой заявки,
кнопки «✅ Олдим / 📞 Боғланилди / 🤝 Шартнома / ✖️ Рад», напоминание через 15 минут.
Пакеты/даты/цены — data.json страницы (единый источник), запасная копия рядом. Только стандартная библиотека.
Филиалы (04.11, владелец: «филиалов может быть много») — [[branch]] в config.toml: своя ссылка ?start=br_<id>,
свои менеджеры (?start=mgr_<MANAGER_CODE>_<id>) видят только заявки своего филиала, своя группа: приветствие
новичка с кнопкой «ариза», чистка чужих ссылок, посты в группу по «✅» владельца. Новый филиал = одна запись."""
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

TZ = dt.timezone(dt.timedelta(hours=5))
HERE = Path(__file__).resolve().parent.parent
MONTHS = ["январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август", "сентябрь", "октябрь", "ноябрь",
          "декабрь"]
ROOMS = ["4", "3", "2"]
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (uid INTEGER PRIMARY KEY, first TEXT, username TEXT, phone TEXT, src TEXT,
    step TEXT, data TEXT, updated TEXT);
CREATE TABLE IF NOT EXISTS leads (n INTEGER PRIMARY KEY, uid INTEGER NOT NULL, phone TEXT, details TEXT, src TEXT,
    status TEXT NOT NULL DEFAULT 'new', created TEXT NOT NULL, reminded INTEGER NOT NULL DEFAULT 0, cards TEXT, log TEXT);
CREATE TABLE IF NOT EXISTS managers (uid INTEGER PRIMARY KEY, name TEXT, added TEXT);
CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT NOT NULL);
"""
MIGRATE = {"users": "branch", "leads": "branch", "managers": "branch"}   # 04.11: филиалы
PHONE_RE = re.compile(r"\+?\d[\d\s\-()]{7,}\d")

M_PACKS, M_ORDER, M_SITE, M_CONTACT = "🕋 Пакетлар ва нархлар", "✍️ Жой банд қилиш", "🌐 Сайтни очиш", "📞 Алоқа"
M_FAQ = "❓ Савол-жавоб"
M_POST = "📣 Пост юбориш"
M_POST_OLD = "📣 Каналга пост"
LINK_RE = re.compile(r"(https?://|t\.me/|telegram\.me/|www\.)", re.I)
# Ответы — только из официального сайта Safo Marva (safomarvaumra.uz), ничего не выдумываем.
FAQ = [
    ("Пакет нархига нималар киради?", "✈️ Авиабилет ва виза\n🏨 Макка ва Мадинада меҳмонхона\n🍽 Овқатланиш (2–3 маҳал)\n🚄 Трансфер (тезюрар поезд ёки автобус)\n🕌 Равзага кириш ва экскурсиялар\n👨‍⚕️ Малакали элликбоши ва ҳамшира\n🌊 Қизил денгизга саёҳат\n🎁 Бонус: Зам-зам 5 л, нимча, сумка, бейжик, абая"),
    ("Қайси авиакомпаниялар?", "Flynas, Fly One, Centrum Air. Йўналиш пакетга қараб: Тошкент → Мадина ёки Тошкент → Жидда."),
    ("Сафар неча кун?", "10 кунлик (9 кеча) — Tawaf пакетлари.\n14 кунлик — Comfort Plus ва Standart."),
    ("Нарх нимага боғлиқ?", "Пакетга ва хонадаги кишилар сонига: 4, 3 ёки 2 кишилик. Кўп кишилик хона — арзонроқ. Нарх бир кишига, АҚШ долларида."),
    ("Меҳмонхоналар Ҳарамга яқинми?", "Ҳа, барча меҳмонхоналар 4–5 юлдузли, Маккада Ҳарамга, Мадинада Масжид Набавийга яқин. Масалан, Anjum Makkah — Ҳарамгача 250 м."),
    ("Жой қандай банд қилинади?", "«✍️ Жой банд қилиш» тугмасини босинг: пакет, сана ва хонани танланг, рақамингизни қолдиринг — мутахассисимиз ўзи қўнғироқ қилади."),
]
CANCEL = "⬅️ Бекор қилиш"
STATUS = {"taken": "✅ Олди", "called": "📞 Боғланилди", "won": "🤝 Шартнома", "lost": "✖️ Рад"}


def now() -> dt.datetime:
    return dt.datetime.now(TZ)


def esc(s) -> str:
    return html.escape(str(s or ""), quote=False)


def load_cfg(path=None) -> dict:
    return tomllib.loads(Path(path or HERE / "config.toml").read_text(encoding="utf-8"))


def connect(path: str) -> sqlite3.Connection:
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    if path != ":memory:":
        db.execute("PRAGMA journal_mode=WAL")
    db.executescript(SCHEMA)
    for table, col in MIGRATE.items():
        if col not in {r[1] for r in db.execute(f"PRAGMA table_info({table})")}:
            db.execute(f"ALTER TABLE {table} ADD COLUMN {col} TEXT")
    db.commit()
    return db


def norm_phone(text: str) -> str | None:
    m = PHONE_RE.search(text or "")
    if not m:
        return None
    d = re.sub(r"\D", "", m.group())
    if len(d) == 9:
        d = "998" + d
    if not 11 <= len(d) <= 13:
        return None
    return "+" + d


def to_date(s: str, today: dt.date) -> dt.date:
    """«12.11» → ближайшая такая дата (если давно прошла — следующий год)."""
    d, m = (int(x) for x in s.split("."))
    x = dt.date(today.year, m, d)
    if x < today and (today - x).days > 200:
        x = dt.date(today.year + 1, m, d)
    return x


def fmt(d: dt.date) -> str:
    return f"{d.day}-{MONTHS[d.month - 1]}"


def parse_start(payload: str) -> dict:
    """site_<пакет>_<ддмм>_<хона> / mgr_<код> / br_<филиал> / insta… / yt… → что выбрано."""
    p = (payload or "").strip()
    low = p.lower()
    if low.startswith("mgr_"):
        return {"mgr": p[4:]}
    if low.startswith("br_"):
        return {"src": "Филиал", "branch": low[3:]}
    if low.startswith("site"):
        parts = low.split("_")
        out = {"src": "Сайт"}
        if len(parts) > 1 and parts[1]:
            out["pkg"] = parts[1]
        if len(parts) > 2 and re.fullmatch(r"\d{4}", parts[2]):
            out["date"] = f"{parts[2][:2]}.{parts[2][2:]}"
        if len(parts) > 3 and parts[3] in ROOMS:
            out["room"] = parts[3]
        return out
    if low.startswith("insta"):
        return {"src": "Instagram"}
    if low.startswith(("yt", "youtube")):
        return {"src": "YouTube"}
    return {"src": p[:30] or "Telegram"}


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
    def __init__(self, api, db, owners: set[int], cfg: dict, data: dict | None = None, clock=now,
                 mgr_code: str = "", fetch=None):
        self.api, self.db, self.owners, self.cfg, self.clock = api, db, set(owners), cfg, clock
        self.mgr_code = mgr_code or ""
        self._data, self._data_t = data, (time.time() if data else 0.0)
        self._fetch = fetch
        self.username = cfg.get("bot_username", "VolidamUmraBot")
        self.branches = {b["id"]: b for b in cfg.get("branch", [])}
        self._admins: dict[int, tuple[float, set[int]]] = {}

    # ---------- данные: пакеты с сайта (кэш 30 мин), запасная копия рядом ----------
    def data(self) -> dict:
        if self._data and (self._fetch is None or time.time() - self._data_t < 1800):
            return self._data
        d = None
        if self._fetch:
            try:
                d = self._fetch()
            except Exception as e:  # noqa: BLE001
                print(f"data.json с сайта: {e}", flush=True)
        if not d and not self._data:
            d = json.loads((HERE / "data.json").read_text(encoding="utf-8"))
        if d:
            self._data, self._data_t = d, time.time()
        return self._data

    def pkg(self, pid: str) -> dict | None:
        return next((p for p in self.data()["packages"] if p["id"] == pid), None)

    def dates(self, p: dict) -> list[dt.date]:
        t = self.clock().date()
        return sorted(x for x in (to_date(s, t) for s in p["dates"]) if x >= t)

    # ---------- пользователи ----------
    def user(self, uid: int) -> dict:
        r = self.db.execute("SELECT * FROM users WHERE uid=?", (uid,)).fetchone()
        if not r:
            return {"uid": uid, "data": {}}
        u = dict(r)
        u["data"] = json.loads(u.get("data") or "{}")
        return u

    def save(self, uid: int, **kw) -> None:
        u = self.user(uid)
        u.update(kw)
        self.db.execute("INSERT OR REPLACE INTO users (uid, first, username, phone, src, step, data, updated, branch) "
                        "VALUES (?,?,?,?,?,?,?,?,?)",
                        (uid, u.get("first"), u.get("username"), u.get("phone"), u.get("src"), u.get("step"),
                         json.dumps(u.get("data") or {}, ensure_ascii=False), self.clock().isoformat(),
                         u.get("branch")))
        self.db.commit()

    def step(self, uid: int, st: str | None, fresh: bool = False, **data) -> None:
        d = {} if fresh else self.user(uid)["data"]
        d.update(data)
        self.save(uid, step=st, data=d)

    @property
    def managers(self) -> set[int]:
        """Все, кто видит хоть какие-то заявки (владельцы, главные и филиальные менеджеры)."""
        return self.owners | {r[0] for r in self.db.execute("SELECT uid FROM managers")}

    def recipients(self, branch: str | None) -> set[int]:
        """Кому идёт заявка: владельцы + главные менеджеры (Нодирбек) + менеджеры её филиала."""
        main = {r[0] for r in self.db.execute("SELECT uid FROM managers WHERE branch IS NULL OR branch=''")}
        br = {r[0] for r in self.db.execute("SELECT uid FROM managers WHERE branch=?", (branch,))} if branch else set()
        return self.owners | main | br

    def mgr_branch(self, uid: int) -> str | None:
        """Филиал менеджера; None — главный (видит всё)."""
        if uid in self.owners:
            return None
        r = self.db.execute("SELECT branch FROM managers WHERE uid=?", (uid,)).fetchone()
        return (r[0] or None) if r else None

    def branch_of_payload(self, payload: str) -> str | None:
        low = (payload or "").strip().lower()
        if low.startswith("br_") and low[3:] in self.branches:
            return low[3:]
        for bid, b in self.branches.items():
            if low in [x.lower() for x in b.get("starts", [])]:
                return bid
        return None

    def send(self, chat: int, text: str, kb: dict | None = None) -> dict | None:
        p = {"chat_id": chat, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
        if kb:
            p["reply_markup"] = kb
        try:
            return self.api("sendMessage", **p)
        except Exception as e:  # noqa: BLE001
            print(f"send {chat}: {e}", flush=True)
            return None

    # ---------- клавиатуры ----------
    def menu_kb(self, uid: int | None = None) -> dict:
        rows = [[{"text": M_PACKS}], [{"text": M_ORDER}], [{"text": M_FAQ}, {"text": M_CONTACT}]]
        if self.cfg.get("site"):
            rows.insert(2, [{"text": M_SITE, "web_app": {"url": self.cfg["site"]}}])
        if uid in self.owners and self.post_targets():
            rows.append([{"text": M_POST}])
        return {"keyboard": rows, "resize_keyboard": True}

    def cancel_kb(self, extra: list | None = None) -> dict:
        rows = ([extra] if extra else []) + [[{"text": CANCEL}]]
        return {"keyboard": rows, "resize_keyboard": True}

    # ---------- вход ----------
    def handle(self, upd: dict) -> None:
        if "message" in upd:
            self.on_message(upd["message"])
        elif "callback_query" in upd:
            self.on_callback(upd["callback_query"])

    def on_message(self, msg: dict) -> None:
        if msg.get("chat", {}).get("type") in ("group", "supergroup"):
            self.on_group(msg)
            return
        if msg.get("chat", {}).get("type") != "private":
            return
        uid = msg["chat"]["id"]
        fr = msg.get("from") or {}
        u = self.user(uid)
        if u.get("first") != fr.get("first_name") or u.get("username") != fr.get("username"):
            self.save(uid, first=fr.get("first_name") or "", username=fr.get("username") or "")
        text = (msg.get("text") or "").strip()
        if text.startswith("/start"):
            self.on_start(uid, text[6:].strip(), fr)
            return
        if text in ("/paketlar", M_PACKS):
            self.step(uid, None)
            self.packages(uid)
            return
        if text in ("/ariza", M_ORDER):
            self.order_start(uid)
            return
        if text in ("/savol", M_FAQ):
            self.step(uid, None)
            self.faq(uid)
            return
        if text in ("/aloqa", M_CONTACT):
            self.step(uid, None)
            self.contact(uid)
            return
        if text in (CANCEL, "/cancel"):
            self.step(uid, None)
            self.send(uid, "Бекор қилинди. Асосий меню 👇", self.menu_kb(uid))
            return
        if text in ("/post", M_POST, M_POST_OLD) and uid in self.owners and self.post_targets():
            self.step(uid, "post", fresh=True)
            where = ", ".join(f"<b>{esc(n)}</b>" for _, n, _ in self.post_targets())
            self.send(uid, f"📣 Пост юборинг (расм/видео + матн ёки фақат матн) — {where}.\n"
                           "Тайёр постни шу ерга узатсангиз ҳам бўлади. Кўриниши олдин шу ерда кўрсатилади, "
                           "«✅» тугмасисиз ҳеч нарса чиқмайди.", self.cancel_kb())
            return
        if text == "/mgrlink" and uid in self.owners:         # ссылки для менеджеров (код не выходит в чат с ИИ)
            if not self.mgr_code:
                self.send(uid, "MANAGER_CODE ўрнатилмаган.")
                return
            base = f"https://t.me/{self.username}?start=mgr_{self.mgr_code}"
            lines = ["🔑 <b>Менежер ҳаволалари</b> — фақат ўша одамга юборинг:", "", f"Бош менежер (ҳамма аризалар):\n{base}"]
            lines += [f"\n{esc(b['name'])} (фақат шу филиал):\n{base}_{bid}" for bid, b in self.branches.items()]
            self.send(uid, "\n".join(lines))
            return
        if text == "/leads" and uid in self.managers:
            self.open_leads(uid)
            return
        u = self.user(uid)
        if u.get("step") == "post" and uid in self.owners:
            self.post_preview(uid, msg)
            return
        if u.get("step") == "phone":
            ph = norm_phone((msg.get("contact") or {}).get("phone_number") or text)
            if not ph:
                self.send(uid, "Рақамни тўғри ёзинг, масалан: <b>+998 90 123 45 67</b> — ёки пастдаги тугмани босинг 👇",
                          self.phone_kb())
                return
            self.save(uid, phone=ph)
            self.finish(uid)
            return
        if u.get("step") == "name":
            self.step(uid, "phone", name=text[:60])
            self.ask_phone(uid)
            return
        self.send(uid, "Қуйидаги тугмалардан бирини танланг 👇", self.menu_kb())

    def on_start(self, uid: int, payload: str, fr: dict) -> None:
        s = parse_start(payload)
        if "mgr" in s:
            br = "-"
            if self.mgr_code and s["mgr"] == self.mgr_code:
                br = None
            elif self.mgr_code:
                for bid in self.branches:
                    if s["mgr"] == f"{self.mgr_code}_{bid}":
                        br = bid
            if br != "-":
                name = (fr.get("first_name") or "") + (f" @{fr['username']}" if fr.get("username") else "")
                self.db.execute("INSERT OR REPLACE INTO managers (uid, name, added, branch) VALUES (?,?,?,?)",
                                (uid, name, self.clock().isoformat(), br))
                self.db.commit()
                where = f" — <b>{esc(self.branches[br]['name'])}</b>" if br else ""
                self.send(uid, f"✅ Сиз менежер сифатида қўшилдингиз{where}. Энди ҳар бир янги ариза шу ерга келади."
                               "\n\nОчиқ аризалар: /leads", self.menu_kb())
                for o in self.owners:
                    if o != uid:
                        self.send(o, f"👤 Янги менежер қўшилди: {esc(name)}{where}")
            else:
                self.send(uid, "Ҳавола эскирган ёки нотўғри.", self.menu_kb())
            return
        br = self.branch_of_payload(payload)
        src = self.branches[br]["name"] + (" · Instagram" if "insta" in payload.lower() else "") if br else None
        self.save(uid, src=src or s.get("src") or "Telegram", step=None, data={},
                  branch=br or self.user(uid).get("branch"))
        self.welcome(uid, fr.get("first_name") or "")
        p = self.pkg(s["pkg"]) if s.get("pkg") else None
        if p:
            self.step(uid, None, fresh=True, pkg=p["id"])
            if s.get("date"):
                self.step(uid, None, date=s["date"])
                if s.get("room"):
                    self.step(uid, None, room=s["room"])
                    self.ask_people(uid)
                    return
                self.ask_room(uid)
                return
            self.ask_date(uid)

    def welcome(self, uid: int, first: str) -> None:
        cap = (f"Ассалому алайкум{', ' + esc(first) if first else ''}! 🤍\n\n"
               "<b>VOLIDAM × Safo Marva Tour</b> — Умра зиёрати 2026.\n\n"
               "🕋 Пакетлар, саналар ва нархларни кўринг\n✍️ Ўзингизга қулай санага жой банд қилинг — "
               "мутахассисимиз ўзи сизга қўнғироқ қилади.\n\nПастдаги тугмани танланг 👇")
        ph = self.cfg.get("welcome_photo")
        if ph:
            try:
                self.api("sendPhoto", chat_id=uid, photo=ph, caption=cap, parse_mode="HTML",
                         reply_markup=self.menu_kb(uid))
                return
            except Exception as e:  # noqa: BLE001
                print(f"welcome photo: {e}", flush=True)
        self.send(uid, cap, self.menu_kb(uid))

    # ---------- пакеты ----------
    def packages(self, uid: int) -> None:
        rows = [[{"text": f"{p['title']} — ${p['prices'][0]} дан", "callback_data": f"p:{p['id']}"}]
                for p in self.data()["packages"]]
        if self.cfg.get("site"):
            rows.append([{"text": "🌐 Батафсил — сайтда (расмлар билан)", "web_app": {"url": self.cfg["site"]}}])
        self.send(uid, "🕋 <b>Умра пакетлари</b>\nНарх — бир кишига, хонадаги кишилар сонига қараб (4 / 3 / 2 кишилик).",
                  {"inline_keyboard": rows})

    def pkg_text(self, p: dict) -> str:
        ds = self.dates(p)
        lines = [f"🕋 <b>{esc(p['title'])}</b> · {esc(p['label'])}"]
        if p.get("badge"):
            lines.append(f"⭐️ {esc(p['badge'])}")
        lines += ["", f"✈️ {esc(p['route'])}", f"🏨 Мадина: {esc(p['madina'])}", f"🏨 Макка: {esc(p['makka'])}",
                  f"🍽 {esc(p['meals'])}", f"🚄 {esc(p['transfer'])}", "",
                  f"💵 <b>${p['prices'][0]}</b> (4 киш.) · <b>${p['prices'][1]}</b> (3 киш.) · <b>${p['prices'][2]}</b> (2 киш.)"]
        if p.get("note"):
            lines.append(f"⚠️ {esc(p['note'])}")
        lines.append("")
        lines.append("📅 Саналар: " + (", ".join(fmt(d) for d in ds) if ds else "янги саналар тез орада — сўранг"))
        return "\n".join(lines)

    # ---------- заявка ----------
    def order_start(self, uid: int) -> None:
        self.step(uid, None, fresh=True)
        rows = [[{"text": p["title"], "callback_data": f"o:{p['id']}"}] for p in self.data()["packages"]]
        rows.append([{"text": "🤔 Ҳали билмайман — маслаҳат керак", "callback_data": "o:-"}])
        self.send(uid, "✍️ <b>Жой банд қилиш</b>\n\n1/4 · Қайси пакет?", {"inline_keyboard": rows})

    def ask_date(self, uid: int) -> None:
        p = self.pkg(self.user(uid)["data"].get("pkg") or "")
        ds = self.dates(p) if p else []
        btn = [{"text": fmt(d), "callback_data": f"d:{d.strftime('%d.%m')}"} for d in ds]
        rows = [btn[i:i + 3] for i in range(0, len(btn), 3)]
        rows.append([{"text": "📅 Санани кейин келишамиз", "callback_data": "d:-"}])
        title = f" — <b>{esc(p['title'])}</b>" if p else ""
        self.send(uid, f"2/4 · Қайси санага{title}?", {"inline_keyboard": rows})

    def ask_room(self, uid: int) -> None:
        p = self.pkg(self.user(uid)["data"].get("pkg") or "")
        row = [{"text": f"{r} кишилик" + (f" · ${p['prices'][i]}" if p else ""), "callback_data": f"r:{r}"}
               for i, r in enumerate(ROOMS)]
        self.send(uid, "3/4 · Хонада неча киши бўлади?\n<i>Кўп кишилик хона — арзонроқ.</i>",
                  {"inline_keyboard": [row[:2], row[2:], [{"text": "🤔 Маслаҳат керак", "callback_data": "r:-"}]]})

    def ask_people(self, uid: int) -> None:
        row = [{"text": str(i), "callback_data": f"n:{i}"} for i in range(1, 6)]
        self.send(uid, "4/4 · Неча киши сафарга боради?", {"inline_keyboard": [row, [{"text": "6 ва ундан кўп",
                                                                                          "callback_data": "n:6+"}]]})

    def phone_kb(self) -> dict:
        return self.cancel_kb([{"text": "📱 Рақамимни юбориш", "request_contact": True}])

    def ask_phone(self, uid: int) -> None:
        u = self.user(uid)
        if u.get("phone"):
            self.send(uid, f"Сиз билан шу рақам орқали боғланайликми: <b>{esc(u['phone'])}</b>?",
                      {"inline_keyboard": [[{"text": "✅ Ҳа", "callback_data": "ph:yes"},
                                            {"text": "✏️ Бошқа рақам", "callback_data": "ph:new"}]]})
        else:
            self.step(uid, "phone")
            self.send(uid, "📞 Телефон рақамингизни юборинг — мутахассисимиз ўзи қўнғироқ қилади.\n"
                           "Пастдаги тугмани босинг ёки рақамни ёзинг 👇", self.phone_kb())

    def summary(self, d: dict) -> str:
        p = self.pkg(d.get("pkg") or "")
        lines = [f"🕋 Пакет: <b>{esc(p['title']) if p else 'маслаҳат керак'}</b>"]
        if d.get("date"):
            t = to_date(d["date"], self.clock().date())
            back = t + dt.timedelta(days=p["nights"]) if p else None
            lines.append(f"📅 Сана: <b>{fmt(t)}</b>" + (f" → {fmt(back)}" if back else ""))
        elif d.get("pkg"):
            lines.append("📅 Сана: келишилади")
        if d.get("room"):
            i = ROOMS.index(d["room"])
            lines.append(f"🛏 Хона: <b>{d['room']} кишилик</b>" + (f" — ${p['prices'][i]} / киши" if p else ""))
        if d.get("people"):
            lines.append(f"👥 Кишилар: <b>{esc(d['people'])}</b>")
        return "\n".join(lines)

    def finish(self, uid: int) -> None:
        u = self.user(uid)
        d = u["data"]
        details = self.summary(d)
        cur = self.db.execute("INSERT INTO leads (uid, phone, details, src, created, branch) VALUES (?,?,?,?,?,?)",
                              (uid, u["phone"], details, u.get("src") or "Telegram", self.clock().isoformat(),
                               u.get("branch")))
        self.db.commit()
        n = cur.lastrowid
        self.step(uid, None, fresh=True)
        ph = " / ".join(x["show"] for x in self.phones(u.get("branch")))
        self.send(uid, f"✅ <b>Ариза №{n} қабул қилинди!</b>\n\n{details}\n📞 {esc(u['phone'])}\n\n"
                       f"Мутахассисимиз тез орада сизга қўнғироқ қилади. Шошилинч бўлса: {esc(ph)}\n\n"
                       "Аллоҳ зиёратингизни қабул қилсин 🤲", self.menu_kb())
        rows = self.write_rows(u.get("branch"))
        if rows:
            self.send(uid, "Саволингиз бўлса — Умра бўйича мутахассисимизга тўғридан-тўғри ёзинг 👇",
                      {"inline_keyboard": rows})
        self.notify(n)
        self.offer_channel(uid)

    # ---------- менеджеры ----------
    def who(self, uid: int) -> str:
        u = self.user(uid)
        link = f'<a href="tg://user?id={uid}">{esc(u.get("first") or "Мижоз")}</a>'
        return link + (f" (@{esc(u['username'])})" if u.get("username") else "")

    def lead_text(self, n: int) -> str:
        r = self.db.execute("SELECT * FROM leads WHERE n=?", (n,)).fetchone()
        t = (f"🆕 <b>АРИЗА №{n}</b> · {dt.datetime.fromisoformat(r['created']).astimezone(TZ).strftime('%d.%m %H:%M')}\n"
             f"👤 {self.who(r['uid'])}\n📞 <b>{esc(r['phone'])}</b>\n\n{r['details']}\n\n🔗 Манба: {esc(r['src'])}")
        if r["branch"] and r["branch"] in self.branches:
            t += f"\n🏢 Филиал: <b>{esc(self.branches[r['branch']]['name'])}</b>"
        for line in json.loads(r["log"] or "[]"):
            t += f"\n{esc(line)}"
        return t

    def lead_kb(self, n: int, status: str) -> dict | None:
        if status in ("won", "lost"):
            return None
        rows = []
        if status == "new":
            rows.append([{"text": "✅ Олдим", "callback_data": f"l:taken:{n}"}])
        elif status == "taken":
            rows.append([{"text": "📞 Боғланилди", "callback_data": f"l:called:{n}"}])
        rows.append([{"text": "🤝 Шартнома", "callback_data": f"l:won:{n}"},
                     {"text": "✖️ Рад", "callback_data": f"l:lost:{n}"}])
        return {"inline_keyboard": rows}

    def notify(self, n: int) -> None:
        cards = {}
        br = self.db.execute("SELECT branch FROM leads WHERE n=?", (n,)).fetchone()[0]
        for a in self.recipients(br):
            m = self.send(a, self.lead_text(n), self.lead_kb(n, "new"))
            if m:
                cards[str(a)] = m["message_id"]
        self.db.execute("UPDATE leads SET cards=? WHERE n=?", (json.dumps(cards), n))
        self.db.commit()

    def set_lead(self, n: int, status: str, by: dict) -> None:
        r = self.db.execute("SELECT * FROM leads WHERE n=?", (n,)).fetchone()
        if not r or r["status"] in ("won", "lost"):
            return
        log = json.loads(r["log"] or "[]")
        log.append(f"{STATUS[status]} — {by.get('first_name', '')} {self.clock().strftime('%d.%m %H:%M')}")
        self.db.execute("UPDATE leads SET status=?, log=? WHERE n=?", (status, json.dumps(log, ensure_ascii=False), n))
        self.db.commit()
        for a, mid in json.loads(r["cards"] or "{}").items():
            p = {"chat_id": int(a), "message_id": mid, "text": self.lead_text(n), "parse_mode": "HTML",
                 "disable_web_page_preview": True}
            kb = self.lead_kb(n, status)
            if kb:
                p["reply_markup"] = kb
            try:
                self.api("editMessageText", **p)
            except Exception as e:  # noqa: BLE001
                print(f"edit {n}: {e}", flush=True)

    def remind(self) -> int:
        rc = self.cfg.get("remind", {})
        t = self.clock()
        if not rc.get("day_start", 8) <= t.hour < rc.get("day_end", 21):
            return 0
        edge = (t - dt.timedelta(minutes=int(rc.get("minutes", 15)))).isoformat()
        rows = self.db.execute("SELECT * FROM leads WHERE status='new' AND reminded=0 AND created<=?", (edge,)).fetchall()
        for r in rows:
            m = int((t - dt.datetime.fromisoformat(r["created"])).total_seconds() // 60)
            for a in self.recipients(r["branch"]):
                self.send(a, f"⏰ <b>Ариза №{r['n']}</b> {m} дақиқадан бери кутяпти!\n👤 {self.who(r['uid'])} · "
                             f"📞 <b>{esc(r['phone'])}</b>")
            self.db.execute("UPDATE leads SET reminded=1 WHERE n=?", (r["n"],))
        self.db.commit()
        return len(rows)

    def open_leads(self, uid: int) -> None:
        br = self.mgr_branch(uid)
        q = "SELECT n, status FROM leads WHERE status IN ('new','taken','called')"
        rows = self.db.execute(q + (" AND branch=?" if br else "") + " ORDER BY n DESC LIMIT 10",
                               (br,) if br else ()).fetchall()
        if not rows:
            self.send(uid, "Очиқ ариза йўқ ✅")
        for r in reversed(rows):
            self.send(uid, self.lead_text(r["n"]), self.lead_kb(r["n"], r["status"]))

    # ---------- пост в канал (только владелец, по кнопке) ----------
    def post_preview(self, uid: int, msg: dict) -> None:
        mid = msg["message_id"]
        try:
            rows = [[{"text": f"✅ {name}", "callback_data": f"pub:{mid}:{key}"}] for key, name, _ in self.post_targets()]
            self.api("copyMessage", chat_id=uid, from_chat_id=uid, message_id=mid, reply_markup={"inline_keyboard":
                     rows + [[{"text": "✖️ Бекор қилиш", "callback_data": "pub:x"}]]})
        except Exception as e:  # noqa: BLE001
            self.send(uid, f"Кўриниш хатоси: {esc(e)}")
            return
        self.step(uid, None)
        self.send(uid, "👆 Шундай кўринади. Қаерга жойлаймиз?", self.menu_kb(uid))

    def post_targets(self) -> list[tuple[str, str, str | int]]:
        """(ключ, подпись кнопки, chat_id): канал Нодирбека + группы филиалов."""
        out = []
        if self.cfg.get("channel_id"):
            out.append(("ch", "Каналга", self.cfg["channel_id"]))
        for bid, b in self.branches.items():
            g = self.group_chat(bid)
            if g:
                out.append((bid, f"{b['name']} гуруҳига", g))
        return out

    def publish(self, uid: int, mid: int, target: str = "ch") -> None:
        t = next((x for x in self.post_targets() if x[0] == target), None)
        if not t:
            self.send(uid, "❌ Бу манзил топилмади.")
            return
        ch = t[2]
        key = f"pub:{uid}:{mid}" + ("" if target == "ch" else f":{target}")
        if self.db.execute("SELECT 1 FROM kv WHERE k=?", (key,)).fetchone():
            self.send(uid, "Бу пост аллақачон жойланган ✅")
            return
        try:
            r = self.api("copyMessage", chat_id=ch, from_chat_id=uid, message_id=mid)
        except Exception as e:  # noqa: BLE001
            self.send(uid, f"❌ Жойлаб бўлмади: {esc(e)}\nБот у ерда админ ва пост юбориш ҳуқуқи борми?")
            return
        self.db.execute("INSERT OR REPLACE INTO kv VALUES (?,?)", (key, str(r.get("message_id"))))
        self.db.commit()
        link = f"https://t.me/{ch.lstrip('@')}/{r.get('message_id')}" if str(ch).startswith("@") else ""
        self.send(uid, f"✅ Жойланди — {esc(t[1])}. {link}".strip(), self.menu_kb(uid))

    def faq(self, uid: int) -> None:
        rows = [[{"text": q, "callback_data": f"q:{i}"}] for i, (q, _) in enumerate(FAQ)]
        self.send(uid, "❓ <b>Савол-жавоб</b>\nСаволни танланг 👇", {"inline_keyboard": rows})

    def offer_channel(self, uid: int) -> None:
        ch = self.cfg.get("channel")
        if ch:
            self.send(uid, "📢 Янги саналар, нархлар ва зиёратчилар фикрларини биринчи бўлиб кўриш учун "
                           "каналимизга қўшилинг 👇", {"inline_keyboard": [[{"text": "✈️ VOLIDAM канали", "url": ch}]]})

    def phones(self, branch: str | None) -> list[dict]:
        """Телефоны; у клиента филиала — номер его филиала первым."""
        ps = list(self.data().get("phones", []))
        lab = self.branches.get(branch or "", {}).get("phone_label")
        return sorted(ps, key=lambda p: p.get("label") != lab) if lab else ps

    def write_rows(self, branch: str | None) -> list:
        rows = []
        b = self.branches.get(branch or "")
        if b and b.get("manager"):
            rows.append([{"text": b.get("write", "✍️ Филиалга ёзиш"), "url": f"https://t.me/{b['manager'].lstrip('@')}"}])
        if self.cfg.get("manager"):
            rows.append([{"text": "✍️ Нодирбекка ёзиш", "url": f"https://t.me/{self.cfg['manager'].lstrip('@')}"}])
        return rows

    def contact(self, uid: int) -> None:
        br = self.user(uid).get("branch")
        lines = ["📞 <b>Алоқа</b>", ""] + [f"<b>{esc(p['label'])}:</b> {esc(p['show'])}" for p in self.phones(br)]
        lines += ["", "🕋 Safo Marva Tour расмий ҳамкори"]
        rows = self.write_rows(br)
        if self.cfg.get("youtube"):
            rows.append([{"text": "▶️ YouTube — VOLIDAM", "url": self.cfg["youtube"]}])
        if self.cfg.get("instagram"):
            rows.append([{"text": "📸 Instagram", "url": self.cfg["instagram"]}])
        if self.cfg.get("channel"):
            rows.append([{"text": "✈️ Telegram канал", "url": self.cfg["channel"]}])
        self.send(uid, "\n".join(lines), {"inline_keyboard": rows} if rows else None)

    # ---------- кнопки ----------
    def on_callback(self, cq: dict) -> None:
        uid = cq["from"]["id"]
        data = cq.get("data") or ""
        try:
            self.api("answerCallbackQuery", callback_query_id=cq["id"])
        except Exception:  # noqa: BLE001
            pass
        kind, _, val = data.partition(":")
        if kind == "pub" and uid in self.owners:
            mid, _, target = val.partition(":")
            if mid.isdigit():
                self.publish(uid, int(mid), target or "ch")
            else:
                self.send(uid, "Бекор қилинди.", self.menu_kb(uid))
            return
        if kind == "p":
            p = self.pkg(val)
            if p:
                self.send(uid, self.pkg_text(p), {"inline_keyboard": [
                    [{"text": "✍️ Шу пакетга жой банд қилиш", "callback_data": f"o:{p['id']}"}],
                    [{"text": "⬅️ Барча пакетлар", "callback_data": "back:packs"}]]})
        elif kind == "q" and val.isdigit() and int(val) < len(FAQ):
            q, a = FAQ[int(val)]
            self.send(uid, f"❓ <b>{esc(q)}</b>\n\n{esc(a)}", {"inline_keyboard": [
                [{"text": "✍️ Жой банд қилиш", "callback_data": "o:start"}],
                [{"text": "⬅️ Бошқа саволлар", "callback_data": "back:faq"}]]})
        elif kind == "back" and val == "faq":
            self.faq(uid)
        elif kind == "o" and val == "start":
            self.order_start(uid)
        elif kind == "back":
            self.packages(uid)
        elif kind == "o":
            self.step(uid, None, fresh=True, pkg=None if val == "-" else val)
            if val == "-":
                self.step(uid, "name")
                self.send(uid, "Мутахассисимиз сизга маслаҳат беради 🤝\nИсмингизни ёзинг:", self.cancel_kb())
            else:
                self.ask_date(uid)
        elif kind == "d":
            self.step(uid, None, date=None if val == "-" else val)
            self.ask_room(uid)
        elif kind == "r":
            self.step(uid, None, room=None if val == "-" else val)
            self.ask_people(uid)
        elif kind == "n":
            self.step(uid, "phone", people=val)
            self.ask_phone(uid)
        elif kind == "ph":
            if val == "yes" and self.user(uid).get("phone"):
                self.finish(uid)
            else:
                self.step(uid, "phone")
                self.send(uid, "📞 Янги рақамни юборинг 👇", self.phone_kb())
        elif kind == "l" and uid in self.managers:
            st, _, n = val.partition(":")
            if st in STATUS and n.isdigit():
                r = self.db.execute("SELECT branch FROM leads WHERE n=?", (int(n),)).fetchone()
                if r and uid in self.recipients(r[0]):
                    self.set_lead(int(n), st, cq["from"])

    # ---------- группы филиалов ----------
    def group_chat(self, bid: str):
        r = self.db.execute("SELECT v FROM kv WHERE k=?", (f"group:{bid}",)).fetchone()
        if r:
            return int(r[0])
        g = self.branches.get(bid, {}).get("group")
        return f"@{g.lstrip('@')}" if g else None

    def group_branch(self, chat: dict) -> str | None:
        cid, uname = chat.get("id"), (chat.get("username") or "").lower()
        for bid, b in self.branches.items():
            r = self.db.execute("SELECT v FROM kv WHERE k=?", (f"group:{bid}",)).fetchone()
            if (r and int(r[0]) == cid) or (uname and uname == (b.get("group") or "").lstrip("@").lower()):
                return bid
        return None

    def is_admin(self, chat_id: int, uid: int) -> bool:
        if uid in self.managers:
            return True
        t, ids = self._admins.get(chat_id, (0.0, set()))
        if time.time() - t > 600:
            try:
                ids = {a["user"]["id"] for a in self.api("getChatAdministrators", chat_id=chat_id)}
            except Exception as e:  # noqa: BLE001
                print(f"admins {chat_id}: {e}", flush=True)
            self._admins[chat_id] = (time.time(), ids)
        return uid in ids

    def delete(self, chat_id: int, mid: int) -> None:
        try:
            self.api("deleteMessage", chat_id=chat_id, message_id=mid)
        except Exception as e:  # noqa: BLE001
            print(f"delete {chat_id}/{mid}: {e}", flush=True)

    @staticmethod
    def has_link(msg: dict) -> bool:
        ents = (msg.get("entities") or []) + (msg.get("caption_entities") or [])
        if any(e.get("type") in ("url", "text_link") for e in ents):
            return True
        if LINK_RE.search((msg.get("text") or "") + " " + (msg.get("caption") or "")):
            return True
        fo = msg.get("forward_origin") or {}
        return fo.get("type") == "channel" or (msg.get("forward_from_chat") or {}).get("type") == "channel"

    def on_group(self, msg: dict) -> None:
        chat = msg["chat"]
        cid = chat["id"]
        fr = msg.get("from") or {}
        uid = fr.get("id")
        text = (msg.get("text") or "").strip()
        if text.startswith("/bind") and uid in self.owners:      # привязать группу к филиалу: /bind xojaobod
            bid = text.split()[1].lower() if len(text.split()) > 1 else ""
            self.delete(cid, msg["message_id"])
            if bid in self.branches:
                self.db.execute("INSERT OR REPLACE INTO kv VALUES (?,?)", (f"group:{bid}", str(cid)))
                self.db.commit()
                self.send(uid, f"✅ «{esc(chat.get('title'))}» гуруҳи — <b>{esc(self.branches[bid]['name'])}</b>га боғланди.")
            else:
                self.send(uid, "Филиал номи: " + ", ".join(self.branches) if self.branches else "Филиаллар йўқ.")
            return
        bid = self.group_branch(chat)
        if not bid:
            return
        if msg.get("new_chat_members"):
            people = [m for m in msg["new_chat_members"] if not m.get("is_bot")]
            self.delete(cid, msg["message_id"])
            if people:
                self.group_welcome(cid, bid, people)
            return
        if msg.get("left_chat_member"):
            self.delete(cid, msg["message_id"])
            return
        if fr.get("is_bot") or not uid:
            return
        sc = msg.get("sender_chat") or {}
        if sc.get("id") == cid:          # анонимный админ группы
            return
        if self.has_link(msg) and not self.is_admin(cid, uid):
            self.delete(cid, msg["message_id"])

    def group_welcome(self, cid: int, bid: str, people: list) -> None:
        b = self.branches[bid]
        names = ", ".join(esc(p.get("first_name") or "") for p in people[:3]) + (" ва бошқалар" if len(people) > 3 else "")
        text = (f"Ассалому алайкум, {names}! 🤍\n<b>VOLIDAM Умра · {esc(b['name'])}</b> гуруҳига хуш келибсиз.\n\n"
                "🕋 Пакетлар, саналар ва жой банд қилиш — ботимиз орқали, 1 дақиқада 👇")
        kb = {"inline_keyboard": [[{"text": "🕋 Умрага ариза қолдириш",
                                    "url": f"https://t.me/{self.username}?start=br_{bid}"}]]}
        old = self.db.execute("SELECT v FROM kv WHERE k=?", (f"welcome:{cid}",)).fetchone()
        if old:
            self.delete(cid, int(old[0]))       # одно приветствие на группу — без мусора
        m = self.send(cid, text, kb)
        if m:
            self.db.execute("INSERT OR REPLACE INTO kv VALUES (?,?)", (f"welcome:{cid}", str(m["message_id"])))
            self.db.commit()


def fetch_site(url: str):
    def f() -> dict:
        with urllib.request.urlopen(url.rstrip("/") + "/data.json", timeout=20) as r:
            return json.loads(r.read())
    return f


def run() -> None:
    api = Api(os.environ["VOLIDAM_BOT_TOKEN"])
    db = connect(os.environ.get("VOLIDAM_DB", "/var/lib/papa-volidam/volidam.sqlite3"))
    owners = {int(x) for x in os.environ.get("OWNER_IDS", "").split(",") if x.strip()}
    cfg = load_cfg(os.environ.get("VOLIDAM_CONFIG"))
    bot = Bot(api, db, owners, cfg, mgr_code=os.environ.get("MANAGER_CODE", ""),
              fetch=fetch_site(cfg["site"]) if cfg.get("site") else None)
    me = api("getMe")
    bot.username = me["username"]
    cmds = [{"command": "start", "description": "Бошлаш"}, {"command": "paketlar", "description": "Умра пакетлари ва нархлар"},
            {"command": "ariza", "description": "Жой банд қилиш"}, {"command": "savol", "description": "Савол-жавоб"},
            {"command": "aloqa", "description": "Алоқа рақамлари"}]
    try:
        api("setMyCommands", commands=cmds)
    except Exception as e:  # noqa: BLE001
        print(f"setMyCommands: {e}", flush=True)
    print(f"VOLIDAM @{me['username']} запущен, менеджеров {len(bot.managers)}, пакетов {len(bot.data()['packages'])}",
          flush=True)
    off = int((db.execute("SELECT v FROM kv WHERE k='offset'").fetchone() or [0])[0])
    last = 0.0
    while True:
        if time.time() - last > 60:
            try:
                bot.remind()
            except Exception as e:  # noqa: BLE001
                print(f"remind: {e}", flush=True)
            last = time.time()
        try:
            ups = api("getUpdates", offset=off, timeout=30, allowed_updates=["message", "callback_query"])
        except Exception as e:  # noqa: BLE001
            print(f"getUpdates: {e}", flush=True)
            time.sleep(10)
            continue
        for u in ups:
            try:
                bot.handle(u)
            except Exception as e:  # noqa: BLE001
                print(f"update: {type(e).__name__}: {e}", flush=True)
            off = u["update_id"] + 1
            db.execute("INSERT OR REPLACE INTO kv VALUES ('offset', ?)", (str(off),))
            db.commit()
