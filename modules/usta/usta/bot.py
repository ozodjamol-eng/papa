"""Бот заявок «уй ва таъмир» (31.10.2026, владелец: «сделать бота, опрос в группе — кто откликнется, те реальные клиенты»).
Эксперимент на 1 неделю, одна цифра — число заявок. Человек: услуга → детали → место → фото (необязательно) → телефон.
Владельцу (OWNER_IDS) — карточка заявки с кнопками. Источник — ссылка t.me/<бот>?start=<метка> (группа, канал, Instagram).
Только стандартная библиотека: long polling Bot API + SQLite. В каналы ничего не публикует."""
from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
import sqlite3
import time
import urllib.error
import urllib.request

from . import texts as T

TZ = dt.timezone(dt.timedelta(hours=5))
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (uid INTEGER PRIMARY KEY, first TEXT, username TEXT, src TEXT, step TEXT, data TEXT,
    created TEXT, updated TEXT);
CREATE TABLE IF NOT EXISTS leads (n INTEGER PRIMARY KEY, uid INTEGER NOT NULL, kind TEXT NOT NULL, details TEXT,
    place TEXT, phone TEXT, photos TEXT, src TEXT, status TEXT NOT NULL DEFAULT 'new', created TEXT NOT NULL,
    urgency TEXT, rating INTEGER, reminded INTEGER NOT NULL DEFAULT 0, obj TEXT, master INTEGER);
CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS masters (id INTEGER PRIMARY KEY, uid INTEGER NOT NULL UNIQUE, username TEXT, trade TEXT NOT NULL,
    name TEXT, area TEXT, exp TEXT, phone TEXT, face TEXT, works TEXT, status TEXT NOT NULL DEFAULT 'pending',
    created TEXT NOT NULL, jobs INTEGER NOT NULL DEFAULT 0, paid_out INTEGER NOT NULL DEFAULT 0);
"""
PHONE_RE = re.compile(r"\+?\d[\d\s\-()]{7,}\d")


def now() -> dt.datetime:
    return dt.datetime.now(TZ)


def esc(s) -> str:
    return html.escape(str(s or ""), quote=False)


def connect(path: str) -> sqlite3.Connection:
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    have = {r[1] for r in db.execute("PRAGMA table_info(leads)")}
    for col, typ in (("urgency", "TEXT"), ("rating", "INTEGER"), ("reminded", "INTEGER NOT NULL DEFAULT 0"), ("obj", "TEXT"), ("master", "INTEGER"), ("ref", "INTEGER"), ("paid", "INTEGER")):
        if col not in have:
            db.execute(f"ALTER TABLE leads ADD COLUMN {col} {typ}")
    mh = {r[1] for r in db.execute("PRAGMA table_info(masters)")}
    if "paid_out" not in mh:
        db.execute("ALTER TABLE masters ADD COLUMN paid_out INTEGER NOT NULL DEFAULT 0")
    db.commit()
    return db


def norm_phone(text: str) -> str | None:
    m = PHONE_RE.search(text or "")
    if not m:
        return None
    d = re.sub(r"\D", "", m.group())
    if len(d) == 9:
        d = "998" + d
    return "+" + d if 11 <= len(d) <= 13 else None


def main_kb() -> dict:
    rows = [[{"text": T.KINDS[k][0], "web_app": {"url": T.MINIAPP_URL}} if k == "dizayn" else {"text": T.KINDS[k][0]}]
            for k in T.KINDS] + [[{"text": T.M_BTN}], [{"text": T.CONTACT}]]
    return {"keyboard": rows, "resize_keyboard": True}


def owner_kb() -> dict:
    return {"keyboard": [[{"text": T.O_STATS}, {"text": T.O_LEADS}], [{"text": T.O_MASTERS}, {"text": T.O_PENDING}],
                         [{"text": T.O_MONEY}, {"text": T.O_CLIENT}]], "resize_keyboard": True}


class Bot:
    def __init__(self, db, api, owners: list[int], username: str = "ozodjamoldizaynbot"):
        self.db, self.api, self.owners, self.username = db, api, owners, username

    # ---------- состояние ----------
    def user(self, frm: dict, src: str | None = None):
        uid = frm["id"]
        r = self.db.execute("SELECT * FROM users WHERE uid=?", (uid,)).fetchone()
        t = now().isoformat()
        if not r:
            self.db.execute("INSERT INTO users(uid, first, username, src, step, data, created, updated) VALUES (?,?,?,?,?,?,?,?)",
                            (uid, frm.get("first_name"), frm.get("username"), src, "", "{}", t, t))
        elif src and (not r["src"] or (src[:1] == "r" and src[1:].isdigit() and not (r["src"] or "")[1:].isdigit())):
            # 31.10: ҳавола устаники бўлса — умумий манбадан устун (биринчи келтирган уста ўзгармайди)
            self.db.execute("UPDATE users SET src=? WHERE uid=?", (src, uid))
        self.db.commit()
        return self.db.execute("SELECT * FROM users WHERE uid=?", (uid,)).fetchone()

    def set_step(self, uid: int, step: str, data: dict | None = None):
        self.db.execute("UPDATE users SET step=?, data=?, updated=? WHERE uid=?",
                        (step, json.dumps(data or {}, ensure_ascii=False), now().isoformat(), uid))
        self.db.commit()

    def say(self, chat: int, text: str, kb: dict | None = None):
        if kb is None:
            kb = owner_kb() if chat in self.owners else main_kb()
        return self.api("sendMessage", chat_id=chat, text=text, reply_markup=kb, parse_mode="HTML",
                        disable_web_page_preview=True)

    # ---------- сообщения ----------
    def handle(self, upd: dict) -> str | None:
        if "callback_query" in upd:
            return self.callback(upd["callback_query"])
        m = upd.get("message")
        if not m or m["chat"]["type"] != "private":
            return None
        frm, chat = m["from"], m["chat"]["id"]
        text = (m.get("text") or "").strip()
        if frm["id"] in self.owners:
            r = self.owner(frm, chat, text)
            if r:
                return r
        if text in ("/usta", "/start usta", T.M_BTN):
            self.user(frm, "usta")
            return self.m_begin(frm, chat)
        if text == "/menim":
            return self.m_mine(frm, chat)
        if frm["id"] in self.owners and text.startswith(("/tolandi", "/berildi")):
            self.say(chat, self.money_cmd(text))
            return "money"
        if text == "/ustalar" and frm["id"] in self.owners:
            self.say(chat, self.m_list())
            return "ustalar"
        if m.get("web_app_data"):                    # Mini App (кнопка клавиатуры): JSON с объектом, м², стилем
            try:
                d = json.loads(m["web_app_data"].get("data") or "{}")
            except ValueError:
                d = {}
            return self.dz_begin(frm, chat, d.get("obj"), d.get("m2"), d.get("style"))
        if text.startswith("/start d_"):              # Mini App из меню/ссылки: /start d_<obj>_<m2>_<style>
            parts = text.split(maxsplit=1)[1].split("_")
            if len(parts) == 4:
                self.user(frm)
                return self.dz_begin(frm, chat, parts[1], parts[2], parts[3])
        if text.startswith("/start"):
            src = text.split(maxsplit=1)[1][:32] if " " in text else None
            self.user(frm, src)
            self.set_step(frm["id"], "")
            self.say(chat, T.GREETING.format(name=esc(frm.get("first_name") or "")))
            return "start"
        if text == "/stats" and frm["id"] in self.owners:
            self.say(chat, self.stats())
            return "stats"
        u = self.user(frm)
        if text == T.BACK:
            self.set_step(frm["id"], "")
            self.say(chat, T.UNKNOWN)
            return "back"
        if text == T.CONTACT:
            self.say(chat, T.CONTACT_TEXT)
            return "contact"
        step, data = u["step"] or "", json.loads(u["data"] or "{}")
        if step.startswith("m_"):                    # уста рўйхатдан ўтмоқда — касб тугмалари мижоз тугмаларига ўхшайди
            return self.m_step(frm, chat, m, text, step, data)
        kind = next((k for k, (btn, _) in T.KINDS.items() if text == btn), None)
        if kind:
            if kind in T.OBJ_KINDS:
                self.set_step(frm["id"], "obj", {"kind": kind})
                self.say(chat, T.ASK_OBJ, {"keyboard": [[{"text": v}] for v in T.OBJ.values()] + [[{"text": T.BACK}]],
                                           "resize_keyboard": True})
            else:
                self.set_step(frm["id"], "details", {"kind": kind})
                self.say(chat, T.KINDS[kind][1], {"keyboard": [[{"text": T.BACK}]], "resize_keyboard": True})
            return "kind"
        if step == "obj" and text:
            obj = next((k for k, v in T.OBJ.items() if v == text), None)
            if not obj:
                self.say(chat, T.UNKNOWN, {"keyboard": [[{"text": v}] for v in T.OBJ.values()] + [[{"text": T.BACK}]],
                                           "resize_keyboard": True})
                return "badobj"
            data["obj"] = obj
            self.set_step(frm["id"], "details", data)
            q = T.KINDS[data["kind"]][1] + ("\n\n" + T.FASAD_NOTE if data["kind"] == "fasad" else "")
            self.say(chat, q, {"keyboard": [[{"text": T.BACK}]], "resize_keyboard": True})
            return "obj"
        if step == "details" and text:
            data["details"] = text[:500]
            self.set_step(frm["id"], "when", data)
            self.say(chat, T.ASK_WHEN, {"keyboard": [[{"text": v} for v in T.WHEN.values()], [{"text": T.BACK}]],
                                        "resize_keyboard": True})
            return "details"
        if step == "when" and text:
            data["urgency"] = next((k for k, v in T.WHEN.items() if v == text), text[:40])
            self.set_step(frm["id"], "place", data)
            self.say(chat, T.ASK_PLACE, {"keyboard": [[{"text": T.BACK}]], "resize_keyboard": True})
            return "when"
        if step == "place" and text:
            data["place"] = text[:200]
            self.set_step(frm["id"], "photo", data)
            self.say(chat, T.ASK_PHOTO, {"keyboard": [[{"text": T.SKIP}], [{"text": T.BACK}]], "resize_keyboard": True})
            return "place"
        if step == "photo":
            ph = m.get("photo") or []
            doc = m.get("document")
            if ph or doc:
                data.setdefault("photos", []).append({"chat": chat, "id": m["message_id"]})
                self.set_step(frm["id"], "photo", data)
                if len(data["photos"]) == 1:
                    self.ask_phone(chat)
                return "photo"
            if text == T.SKIP or (data.get("photos") and not m.get("contact") and not norm_phone(text)):
                self.set_step(frm["id"], "phone", data)
                self.ask_phone(chat)
                return "skip"
        if step in ("photo", "phone"):
            contact = m.get("contact")
            phone = norm_phone(contact["phone_number"]) if contact else norm_phone(text)
            if not phone:
                if step == "phone":
                    self.say(chat, T.BAD_PHONE, self.phone_kb())
                return "badphone"
            return self.finish(frm, chat, data, phone)
        self.say(chat, T.UNKNOWN)
        return "unknown"

    def dz_begin(self, frm: dict, chat: int, obj, m2, style) -> str:
        """31.10: заявка на 3D дизайн из Mini App — объект, м², стиль уже выбраны, цена $3/м²; дальше обычный путь (когда → место → фото → телефон)."""
        try:
            m2 = int(float(m2))
        except (TypeError, ValueError):
            m2 = 0
        if obj not in T.OBJ or style not in T.STYLES or not 5 <= m2 <= 1000:
            self.say(chat, T.UNKNOWN)
            return "dz_bad"
        self.user(frm)
        price = m2 * T.PRICE_M2
        data = {"kind": "dizayn", "obj": obj,
                "details": f"{m2} м² · {T.STYLES[style]} · ${price} (Mini App)"}
        self.set_step(frm["id"], "when", data)
        self.say(chat, T.DZ_GOT.format(obj=T.OBJ[obj], m2=m2, style=T.STYLES[style], price=price),
                 {"keyboard": [[{"text": v} for v in T.WHEN.values()], [{"text": T.BACK}]], "resize_keyboard": True})
        return "dz"

    def phone_kb(self) -> dict:
        return {"keyboard": [[{"text": T.SEND_PHONE, "request_contact": True}], [{"text": T.BACK}]], "resize_keyboard": True}

    def ask_phone(self, chat: int):
        self.say(chat, T.ASK_PHONE, self.phone_kb())

    def finish(self, frm: dict, chat: int, data: dict, phone: str) -> str:
        u = self.db.execute("SELECT src FROM users WHERE uid=?", (frm["id"],)).fetchone()
        ref = None
        src = (u["src"] if u else None) or ""
        if src[:1] == "r" and src[1:].isdigit():
            row = self.db.execute("SELECT id FROM masters WHERE id=? AND status='ok'", (int(src[1:]),)).fetchone()
            ref = row["id"] if row else None
        cur = self.db.execute("INSERT INTO leads(uid, kind, details, place, phone, photos, src, created, urgency, obj, ref)"
                              " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                              (frm["id"], data.get("kind", "?"), data.get("details"), data.get("place"), phone,
                               json.dumps(data.get("photos") or []), u["src"] if u else None, now().isoformat(),
                               data.get("urgency"), data.get("obj"), ref))
        self.db.commit()
        n = cur.lastrowid
        self.set_step(frm["id"], "")
        self.say(chat, T.DONE.format(n=n))
        self.notify(n, frm)
        return "lead"

    def card(self, r, frm: dict | None = None) -> str:
        who = esc((frm or {}).get("first_name") or "")
        un = (frm or {}).get("username")
        st = {"new": "🆕 янги", "done": "✅ боғланилди", "no": "❌ бекор", "fin": "🏁 иш битди",
              "sent": "📤 устага юборилди", "taken": "👷 уста олди"}.get(r["status"], r["status"])
        if r["rating"]:
            st += " · " + "⭐" * r["rating"]
        when = T.WHEN.get(r["urgency"] or "", r["urgency"] or "—")
        obj = f" · {T.OBJ.get(r['obj'], r['obj'])}" if r["obj"] else ""
        if r["ref"]:
            mm = self.db.execute("SELECT name FROM masters WHERE id=?", (r["ref"],)).fetchone()
            st += f"\n🤝 реферал: {esc(mm['name'] if mm else r['ref'])}"
        if r["paid"]:
            st += f"\n💰 тўланди: {r['paid']:,} сўм".replace(",", " ")
        return (f"📥 <b>Ариза №{r['n']}</b> · {T.KINDS.get(r['kind'], (r['kind'],))[0]}{obj}\n"
                f"👤 {who}{(' @' + un) if un else ''}\n📞 {esc(r['phone'])}\n📍 {esc(r['place'])}\n"
                f"⏱ {esc(when)}\n📝 {esc(r['details'])}\n🔗 манба: {esc(r['src'] or '—')}\n{st}")

    def notify(self, n: int, frm: dict):
        r = self.db.execute("SELECT * FROM leads WHERE n=?", (n,)).fetchone()
        kb = self.lead_kb(r)
        for o in self.owners:
            try:
                self.api("sendMessage", chat_id=o, text=self.card(r, frm), reply_markup=kb, parse_mode="HTML")
                for p in json.loads(r["photos"] or "[]")[:5]:
                    self.api("copyMessage", chat_id=o, from_chat_id=p["chat"], message_id=p["id"])
            except Exception as e:  # noqa: BLE001 — уведомление не должно ронять бота
                print(f"notify: {type(e).__name__}: {e}", flush=True)

    def callback(self, q: dict) -> str | None:
        act, _, rest = (q.get("data") or "").partition(":")
        if act == "rate":  # мижоз баҳоси: rate:<n>:<1-5>
            n, _, k = rest.partition(":")
            r = self.db.execute("SELECT * FROM leads WHERE n=?", (int(n),)).fetchone() if n.isdigit() else None
            if not r or r["uid"] != q["from"]["id"] or not k.isdigit() or not 1 <= int(k) <= 5:
                return None
            self.db.execute("UPDATE leads SET rating=? WHERE n=?", (int(k), r["n"]))
            self.db.commit()
            self.api("answerCallbackQuery", callback_query_id=q["id"])
            self.say(q["from"]["id"], T.RATED)
            for o in self.owners:
                self.api("sendMessage", chat_id=o, text=f"⭐ Ариза №{r['n']}: мижоз баҳоси {'⭐' * int(k)}")
            return "rate"
        if act in ("mt", "ms"):                      # уста: mt:<n> оламан / ms:<n> ололмайман
            return self.m_answer(q, act, rest)
        if q["from"]["id"] not in self.owners:
            return None
        if act in ("lv", "mv", "pd", "po"):          # 31.10 пульт: просмотр заявки/мастера, оплата
            return self.o_callback(q, act, rest)
        if act in ("ma", "mr"):                      # владелец: ma:<id> тасдиқ / mr:<id> рад
            return self.m_decide(q, act, rest)
        if act == "go":                              # владелец: go:<n>:<master id> — заявка устага
            return self.m_send(q, rest)
        n = rest
        if act in ("ok", "no", "fin") and n.isdigit():
            self.db.execute("UPDATE leads SET status=? WHERE n=?", ({"ok": "done", "no": "no", "fin": "fin"}[act], int(n)))
            self.db.commit()
            r = self.db.execute("SELECT * FROM leads WHERE n=?", (int(n),)).fetchone()
            kb = {"inline_keyboard": [[{"text": "🏁 Иш битди", "callback_data": f"fin:{n}"}]]} if act == "ok" else None
            try:
                self.api("editMessageText", chat_id=q["message"]["chat"]["id"], message_id=q["message"]["message_id"],
                         text=self.card(r), parse_mode="HTML", reply_markup=kb)
            except Exception:  # noqa: BLE001
                pass
            if act == "fin":
                stars = {"inline_keyboard": [[{"text": "⭐" * i, "callback_data": f"rate:{n}:{i}"} for i in (1, 2, 3)],
                                             [{"text": "⭐" * i, "callback_data": f"rate:{n}:{i}"} for i in (4, 5)]]}
                self.api("sendMessage", chat_id=r["uid"], text=T.ASK_RATE.format(n=n), reply_markup=stars)
            self.api("answerCallbackQuery", callback_query_id=q["id"])
            return act
        return None

    # ---------- 🛠 усталар (31.10) ----------
    def trades_kb(self) -> dict:
        return {"keyboard": [[{"text": v}] for v in T.TRADES.values()] + [[{"text": T.BACK}]], "resize_keyboard": True}

    def m_begin(self, frm: dict, chat: int) -> str:
        self.set_step(frm["id"], "m_trade", {})
        self.say(chat, T.M_HELLO, self.trades_kb())
        return "m_begin"

    def m_step(self, frm, chat, m, text, step, data) -> str:
        back = {"keyboard": [[{"text": T.BACK}]], "resize_keyboard": True}
        if step == "m_trade":
            t = next((k for k, v in T.TRADES.items() if v == text), None)
            if not t:
                self.say(chat, T.UNKNOWN, self.trades_kb()); return "m_badtrade"
            data["trade"] = t; self.set_step(frm["id"], "m_name", data); self.say(chat, T.M_ASK_NAME, back); return "m_trade"
        if step == "m_name" and text:
            data["name"] = text[:80]; self.set_step(frm["id"], "m_area", data); self.say(chat, T.M_ASK_AREA, back); return "m_name"
        if step == "m_area" and text:
            data["area"] = text[:200]; self.set_step(frm["id"], "m_exp", data); self.say(chat, T.M_ASK_EXP, back); return "m_area"
        if step == "m_exp" and text:
            data["exp"] = text[:60]; self.set_step(frm["id"], "m_phone", data); self.say(chat, T.M_ASK_PHONE, self.phone_kb()); return "m_exp"
        if step == "m_phone":
            c = m.get("contact")
            phone = norm_phone(c["phone_number"]) if c else norm_phone(text)
            if not phone:
                self.say(chat, T.BAD_PHONE, self.phone_kb()); return "m_badphone"
            data["phone"] = phone; self.set_step(frm["id"], "m_face", data); self.say(chat, T.M_ASK_FACE, back); return "m_phone"
        if step == "m_face":
            if not m.get("photo"):
                self.say(chat, T.M_NEED_PHOTO, back); return "m_noface"
            data["face"] = {"chat": chat, "id": m["message_id"]}
            self.set_step(frm["id"], "m_work", data)
            self.say(chat, T.M_ASK_WORK, {"keyboard": [[{"text": T.M_READY}], [{"text": T.BACK}]], "resize_keyboard": True})
            return "m_face"
        if step == "m_work":
            if m.get("photo"):
                data.setdefault("works", []).append({"chat": chat, "id": m["message_id"]})
                self.set_step(frm["id"], "m_work", data); return "m_workphoto"
            if text == T.M_READY:
                if not data.get("works"):
                    self.say(chat, T.M_NEED_PHOTO); return "m_nowork"
                return self.m_submit(frm, chat, data)
        self.say(chat, T.UNKNOWN)
        return "m_unknown"

    def m_submit(self, frm, chat, data) -> str:
        t = now().isoformat()
        self.db.execute("INSERT INTO masters(uid, username, trade, name, area, exp, phone, face, works, status, created)"
                        " VALUES (?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(uid) DO UPDATE SET username=excluded.username,"
                        " trade=excluded.trade, name=excluded.name, area=excluded.area, exp=excluded.exp, phone=excluded.phone,"
                        " face=excluded.face, works=excluded.works, status='pending', created=excluded.created",
                        (frm["id"], frm.get("username"), data["trade"], data.get("name"), data.get("area"), data.get("exp"),
                         data.get("phone"), json.dumps(data.get("face")), json.dumps(data.get("works", [])[:3]), "pending", t))
        self.db.commit()
        self.set_step(frm["id"], "")
        self.say(chat, T.M_SENT)
        r = self.db.execute("SELECT * FROM masters WHERE uid=?", (frm["id"],)).fetchone()
        kb = {"inline_keyboard": [[{"text": "✅ Тасдиқлаш", "callback_data": f"ma:{r['id']}"},
                                   {"text": "❌ Рад этиш", "callback_data": f"mr:{r['id']}"}]]}
        for o in self.owners:
            try:
                for p in [json.loads(r["face"])] + json.loads(r["works"] or "[]"):
                    self.api("copyMessage", chat_id=o, from_chat_id=p["chat"], message_id=p["id"])
                self.api("sendMessage", chat_id=o, text=self.m_card(r), reply_markup=kb, parse_mode="HTML")
            except Exception as e:  # noqa: BLE001
                print(f"m_submit: {type(e).__name__}: {e}", flush=True)
        return "m_submit"

    def m_card(self, r) -> str:
        st = {"pending": "⏳ текширувда", "ok": "✅ рўйхатда", "no": "❌ рад этилди"}.get(r["status"], r["status"])
        un = f" @{r['username']}" if r["username"] else ""
        return (f"🛠 <b>Уста аризаси</b> · {T.TRADES.get(r['trade'], r['trade'])}\n👤 {esc(r['name'])}{un}\n"
                f"🆔 {r['uid']}\n📞 {esc(r['phone'])}\n📍 {esc(r['area'])}\n🧰 тажриба: {esc(r['exp'])}\n{st}")

    def m_decide(self, q, act, rest) -> str | None:
        if not rest.isdigit():
            return None
        st = "ok" if act == "ma" else "no"
        self.db.execute("UPDATE masters SET status=? WHERE id=?", (st, int(rest)))
        self.db.commit()
        r = self.db.execute("SELECT * FROM masters WHERE id=?", (int(rest),)).fetchone()
        try:
            self.api("editMessageText", chat_id=q["message"]["chat"]["id"], message_id=q["message"]["message_id"],
                     text=self.m_card(r), parse_mode="HTML")
        except Exception:  # noqa: BLE001
            pass
        self.say(r["uid"], T.M_OK.format(trade=T.TRADES.get(r["trade"], r["trade"])) if st == "ok" else T.M_NO)
        if st == "ok":
            self.say(r["uid"], T.M_LINK.format(link=self.ref_link(r["id"]), pct=T.REF_PCT))
        self.api("answerCallbackQuery", callback_query_id=q["id"])
        return act

    def dispatch_rows(self, r) -> list:
        """Карточка заявки владельцу: кнопки «→ уста» — подходящие по профессии, в списке (одобренные)."""
        trades = T.FOR_KIND.get(r["kind"], ())
        if not trades:
            return []
        ms = self.db.execute(f"SELECT * FROM masters WHERE status='ok' AND (trade IN ({','.join('?' * len(trades))}) OR id=?)"
                             " ORDER BY (id=?) DESC, jobs, id LIMIT 6", (*trades, r["ref"] or -1, r["ref"] or -1)).fetchall()
        return [[{"text": f"→ {m['name']} ({T.TRADES[m['trade']].split(' ', 1)[1].split(' (')[0]})",
                  "callback_data": f"go:{r['n']}:{m['id']}"}] for m in ms]

    def m_send(self, q, rest) -> str | None:
        n, _, mid = rest.partition(":")
        if not (n.isdigit() and mid.isdigit()):
            return None
        r = self.db.execute("SELECT * FROM leads WHERE n=?", (int(n),)).fetchone()
        ms = self.db.execute("SELECT * FROM masters WHERE id=? AND status='ok'", (int(mid),)).fetchone()
        if not r or not ms:
            return None
        card = (f"📥 Ариза №{r['n']} · {T.KINDS.get(r['kind'], (r['kind'],))[0]}\n📍 {esc(r['place'])}\n"
                f"⏱ {esc(T.WHEN.get(r['urgency'] or '', r['urgency'] or '—'))}\n📝 {esc(r['details'])}")
        kb = {"inline_keyboard": [[{"text": T.M_TAKE, "callback_data": f"mt:{r['n']}"},
                                   {"text": T.M_SKIP, "callback_data": f"ms:{r['n']}"}]]}
        self.api("sendMessage", chat_id=ms["uid"], text=T.M_JOB.format(card=card), reply_markup=kb, parse_mode="HTML")
        for p in json.loads(r["photos"] or "[]")[:5]:
            self.api("copyMessage", chat_id=ms["uid"], from_chat_id=p["chat"], message_id=p["id"])
        self.db.execute("UPDATE leads SET master=?, status='sent' WHERE n=?", (ms["id"], r["n"]))
        self.db.commit()
        self.api("answerCallbackQuery", callback_query_id=q["id"], text=f"→ {ms['name']}")
        for o in self.owners:
            self.api("sendMessage", chat_id=o, text=f"📤 Ариза №{r['n']} → уста {esc(ms['name'])} — жавобини кутамиз")
        return "go"

    def m_answer(self, q, act, n) -> str | None:
        ms = self.db.execute("SELECT * FROM masters WHERE uid=? AND status='ok'", (q["from"]["id"],)).fetchone()
        r = self.db.execute("SELECT * FROM leads WHERE n=?", (int(n),)).fetchone() if n.isdigit() else None
        if not ms or not r or r["master"] != ms["id"]:
            return None
        self.api("answerCallbackQuery", callback_query_id=q["id"])
        if act == "mt":
            self.db.execute("UPDATE leads SET status='taken' WHERE n=?", (r["n"],))
            self.db.execute("UPDATE masters SET jobs=jobs+1 WHERE id=?", (ms["id"],))
            self.db.commit()
            self.say(ms["uid"], T.M_TAKEN.format(phone=esc(r["phone"])))
            self.say(r["uid"], T.M_CLIENT.format(n=r["n"], name=esc(ms["name"])))
            note = f"✅ Ариза №{r['n']}: уста {esc(ms['name'])} олди"
        else:
            self.db.execute("UPDATE leads SET status='new', master=NULL WHERE n=?", (r["n"],))
            self.db.commit()
            note = f"❌ Ариза №{r['n']}: уста {esc(ms['name'])} ололмайди — бошқа уста танланг"
        for o in self.owners:
            self.api("sendMessage", chat_id=o, text=note, parse_mode="HTML")
        return act

    def m_list(self) -> str:
        rows = self.db.execute("SELECT * FROM masters ORDER BY trade, status, id").fetchall()
        if not rows:
            return "🛠 Усталар ҳали йўқ. Рўйхатга ёзилиш ҳаволаси: /start usta"
        out = ["🛠 <b>УСТАЛАР</b>"]
        for r in rows:
            st = {"pending": "⏳", "ok": "✅", "no": "❌"}.get(r["status"], "?")
            x = self.m_stats(r["id"])
            out.append(f"{st} #{r['id']} {T.TRADES.get(r['trade'], r['trade'])} — {esc(r['name'])} · {esc(r['phone'])}"
                       f" · иш: {r['jobs']} · 🤝 мижоз: {x['users']}, тўлов: {x['paid']} · қарз: {x['owed']:,}".replace(",", " "))
        return "\n".join(out)

    # ---------- 🤝 рефералка ----------
    def ref_link(self, mid: int) -> str:
        return f"https://t.me/{self.username}?start=r{mid}"

    def m_stats(self, mid: int) -> dict:
        users = self.db.execute("SELECT count(*) FROM users WHERE src=?", (f"r{mid}",)).fetchone()[0]
        leads = self.db.execute("SELECT count(*) FROM leads WHERE ref=?", (mid,)).fetchone()[0]
        paid, total = self.db.execute("SELECT count(paid), coalesce(sum(paid),0) FROM leads WHERE ref=? AND paid>0", (mid,)).fetchone()
        out = self.db.execute("SELECT paid_out FROM masters WHERE id=?", (mid,)).fetchone()[0]
        share = total * T.REF_PCT // 100
        return {"users": users, "leads": leads, "paid": paid, "sum": total, "share": share, "out": out, "owed": share - out}

    def m_mine(self, frm, chat) -> str:
        ms = self.db.execute("SELECT * FROM masters WHERE uid=? AND status='ok'", (frm["id"],)).fetchone()
        if not ms:
            self.say(chat, "Бу бўлим фақат рўйхатдаги усталар учун. Рўйхатдан ўтиш: /usta")
            return "mine_no"
        f = lambda x: f"{x:,}".replace(",", " ")
        st = self.m_stats(ms["id"])
        self.say(chat, T.M_MINE.format(pct=T.REF_PCT, **{k: (f(v) if k in ("sum", "share", "out", "owed") else v) for k, v in st.items()})
                 + "\n\n🔗 " + self.ref_link(ms["id"]))
        return "mine"

    def money_cmd(self, text: str) -> str:
        """Владелец: /tolandi <ариза №> <сўм> — мижоз дизайн учун тўлади; /berildi <уста id> <сўм> — устага улуш берилди."""
        p = text.split()
        if len(p) != 3 or not p[1].isdigit() or not p[2].replace(" ", "").isdigit():
            return "Формат: /tolandi 12 1500000  ёки  /berildi 3 150000"
        a, b = int(p[1]), int(p[2])
        return self.pay_lead(a, b) if p[0] == "/tolandi" else self.pay_out(a, b)

    def pay_lead(self, a: int, b: int) -> str:
        r = self.db.execute("SELECT * FROM leads WHERE n=?", (a,)).fetchone()
        if not r:
            return f"Ариза №{a} йўқ"
        self.db.execute("UPDATE leads SET paid=? WHERE n=?", (b, a)); self.db.commit()
        if r["ref"]:
            share = b * T.REF_PCT // 100
            ms = self.db.execute("SELECT * FROM masters WHERE id=?", (r["ref"],)).fetchone()
            self.say(ms["uid"], f"💰 Ариза №{a} тўланди. Сизнинг улушингиз: {share:,} сўм ({T.REF_PCT}%). Ҳисоб: /menim".replace(",", " "))
            return f"✅ Ариза №{a}: {b:,} сўм. Реферал {esc(ms['name'])}: {share:,} сўм".replace(",", " ")
        return f"✅ Ариза №{a}: {b:,} сўм (рефералсиз)".replace(",", " ")

    def pay_out(self, a: int, b: int) -> str:
        ms = self.db.execute("SELECT * FROM masters WHERE id=?", (a,)).fetchone()
        if not ms:
            return f"Уста #{a} йўқ"
        self.db.execute("UPDATE masters SET paid_out=paid_out+? WHERE id=?", (b, a)); self.db.commit()
        st = self.m_stats(a)
        self.say(ms["uid"], f"✅ Сизга {b:,} сўм тўланди. Қолдиқ: {st['owed']:,} сўм".replace(",", " "))
        return f"✅ {esc(ms['name'])}: +{b:,} сўм берилди, қолдиқ {st['owed']:,} сўм".replace(",", " ")

    # ---------- 👑 пульт владельца (31.10) ----------
    def owner(self, frm: dict, chat: int, text: str) -> str | None:
        uid = frm["id"]
        u = self.user(frm)
        step = u["step"] or ""
        if text in ("/start", "/panel", T.O_PANEL):
            self.set_step(uid, "")
            self.say(chat, T.O_HELLO, owner_kb())
            return "o_panel"
        if text == T.O_CLIENT:
            kb = main_kb(); kb["keyboard"] = kb["keyboard"] + [[{"text": T.O_PANEL}]]
            self.say(chat, "👀 Мижоз шундай кўради. Қайтиш — «👑 Бошқарув».", kb)
            return "o_client"
        if step.startswith("o_") and text and text not in T.O_BUTTONS:
            num = re.sub(r"\D", "", text)
            if not num:
                self.say(chat, T.O_BAD_NUM, {"keyboard": [[{"text": T.O_PANEL}]], "resize_keyboard": True})
                return "o_badnum"
            kind, _, ident = step.partition(":")
            self.set_step(uid, "")
            res = self.pay_lead(int(ident), int(num)) if kind == "o_pay" else self.pay_out(int(ident), int(num))
            self.say(chat, res, owner_kb())
            return "o_money"
        if text == T.O_STATS:
            self.say(chat, self.stats() + self.o_summary(), owner_kb()); return "o_stats"
        if text == T.O_LEADS:
            return self.o_leads(chat)
        if text == T.O_MASTERS:
            return self.o_masters(chat)
        if text == T.O_PENDING:
            return self.o_pending(chat)
        if text == T.O_MONEY:
            return self.o_money(chat)
        return None

    def o_summary(self) -> str:
        def c(table, st):
            return self.db.execute(f"SELECT count(*) FROM {table} WHERE status=?", (st,)).fetchone()[0]
        return (f"\n\n<b>Аризалар ҳолати:</b> 🆕 {c('leads', 'new')} · 📤 {c('leads', 'sent')} · "
                f"👷 {c('leads', 'taken')} · 🏁 {c('leads', 'fin')}\n"
                f"<b>Усталар:</b> ✅ {c('masters', 'ok')} · ⏳ {c('masters', 'pending')}")

    ST_ICON = {"new": "🆕", "done": "✅", "no": "❌", "fin": "🏁", "sent": "📤", "taken": "👷"}

    def o_leads(self, chat: int) -> str:
        rows = self.db.execute("SELECT * FROM leads ORDER BY n DESC LIMIT 15").fetchall()
        if not rows:
            self.say(chat, "📥 Аризалар ҳали йўқ.", owner_kb()); return "o_leads"
        lines = ["📥 <b>ОХИРГИ АРИЗАЛАР</b> (батафсил — рақамни босинг)"]
        btns = []
        for r in rows:
            lines.append(f"{self.ST_ICON.get(r['status'], '•')} №{r['n']} · {T.KINDS.get(r['kind'], (r['kind'],))[0]} · "
                         f"{esc((r['place'] or '')[:25])} · {r['created'][5:16].replace('T', ' ')}")
            btns.append({"text": f"№{r['n']}", "callback_data": f"lv:{r['n']}"})
        kb = {"inline_keyboard": [btns[i:i + 5] for i in range(0, len(btns), 5)]}
        self.say(chat, "\n".join(lines), kb)
        return "o_leads"

    def lead_kb(self, r) -> dict:
        rows = self.dispatch_rows(r) + [[{"text": "✅ Боғландим", "callback_data": f"ok:{r['n']}"},
                                         {"text": "❌ Бекор", "callback_data": f"no:{r['n']}"}],
                                        [{"text": "🏁 Иш битди", "callback_data": f"fin:{r['n']}"},
                                         {"text": "💰 Тўланди", "callback_data": f"pd:{r['n']}"}]]
        return {"inline_keyboard": rows}

    def o_masters(self, chat: int) -> str:
        rows = self.db.execute("SELECT * FROM masters WHERE status='ok' ORDER BY trade, id").fetchall()
        if not rows:
            self.say(chat, "🛠 Рўйхатда уста ҳали йўқ.\nТекширувдагилар — «⏳ Текширувда».\n"
                     f"Усталарни чақириш ҳаволаси:\nhttps://t.me/{self.username}?start=usta", owner_kb())
            return "o_masters"
        lines = ["🛠 <b>РЎЙХАТДАГИ УСТАЛАР</b> (батафсил — исмни босинг)"]
        btns = []
        for r in rows:
            x = self.m_stats(r["id"])
            lines.append(f"✅ {T.TRADES.get(r['trade'], r['trade'])} — {esc(r['name'])} · 📞 {esc(r['phone'])} · "
                         f"иш: {r['jobs']} · 🤝 {x['users']} · қарз: {x['owed']:,}".replace(",", " "))
            btns.append([{"text": f"{esc(r['name'])[:28]}", "callback_data": f"mv:{r['id']}"}])
        self.say(chat, "\n".join(lines), {"inline_keyboard": btns})
        return "o_masters"

    def o_pending(self, chat: int) -> str:
        rows = self.db.execute("SELECT * FROM masters WHERE status='pending' ORDER BY id").fetchall()
        if not rows:
            self.say(chat, "⏳ Текширувда ҳеч ким йўқ.", owner_kb()); return "o_pending"
        for r in rows:
            self.m_show(chat, r, {"inline_keyboard": [[{"text": "✅ Тасдиқлаш", "callback_data": f"ma:{r['id']}"},
                                                         {"text": "❌ Рад этиш", "callback_data": f"mr:{r['id']}"}]]})
        return "o_pending"

    def m_show(self, chat: int, r, kb: dict):
        try:
            for p in [json.loads(r["face"] or "null")] + json.loads(r["works"] or "[]"):
                if p:
                    self.api("copyMessage", chat_id=chat, from_chat_id=p["chat"], message_id=p["id"])
        except Exception as e:  # noqa: BLE001 — фото могли удалить, карточку всё равно показываем
            print(f"m_show: {e}", flush=True)
        self.api("sendMessage", chat_id=chat, text=self.m_card(r), reply_markup=kb, parse_mode="HTML")

    def o_money(self, chat: int) -> str:
        f = lambda x: f"{x:,}".replace(",", " ")
        paid = self.db.execute("SELECT count(*), coalesce(sum(paid),0) FROM leads WHERE paid>0").fetchone()
        lines = [f"💰 <b>ТЎЛОВЛАР</b>\nТўланган дизайнлар: {paid[0]} та · {f(paid[1])} сўм"]
        owed = []
        for r in self.db.execute("SELECT * FROM masters WHERE status='ok'").fetchall():
            x = self.m_stats(r["id"])
            if x["share"]:
                lines.append(f"🤝 {esc(r['name'])}: улуш {f(x['share'])} · берилди {f(x['out'])} · <b>қарз {f(x['owed'])}</b>")
                if x["owed"] > 0:
                    owed.append([{"text": f"💸 {r['name'][:20]} — бердим", "callback_data": f"po:{r['id']}"}])
        if len(lines) == 1:
            lines.append("Реферал улушлари ҳали йўқ.")
        lines.append("\nМижоз тўлаган бўлса — «📥 Аризалар» → ариза → «💰 Тўланди».")
        self.say(chat, "\n".join(lines), {"inline_keyboard": owed} if owed else owner_kb())
        return "o_money"

    def o_callback(self, q: dict, act: str, rest: str) -> str | None:
        chat = q["from"]["id"]
        self.user(q["from"])                         # строка владельца для шага ввода суммы
        self.api("answerCallbackQuery", callback_query_id=q["id"])
        if not rest.isdigit():
            return None
        if act == "lv":
            r = self.db.execute("SELECT * FROM leads WHERE n=?", (int(rest),)).fetchone()
            if not r:
                return None
            u = self.db.execute("SELECT first, username FROM users WHERE uid=?", (r["uid"],)).fetchone()
            frm = {"first_name": u["first"], "username": u["username"]} if u else None
            self.api("sendMessage", chat_id=chat, text=self.card(r, frm), reply_markup=self.lead_kb(r), parse_mode="HTML")
            for p in json.loads(r["photos"] or "[]")[:5]:
                try:
                    self.api("copyMessage", chat_id=chat, from_chat_id=p["chat"], message_id=p["id"])
                except Exception:  # noqa: BLE001
                    pass
            return "lv"
        if act == "mv":
            r = self.db.execute("SELECT * FROM masters WHERE id=?", (int(rest),)).fetchone()
            if not r:
                return None
            x = self.m_stats(r["id"])
            kb = {"inline_keyboard": [[{"text": "💸 Улуш бердим", "callback_data": f"po:{r['id']}"},
                                       {"text": "🚫 Рўйхатдан чиқариш", "callback_data": f"mr:{r['id']}"}]]}
            self.m_show(chat, r, kb)
            self.api("sendMessage", chat_id=chat, parse_mode="HTML",
                     text=(f"🤝 Ҳавола: {self.ref_link(r['id'])}\nКелганлар: {x['users']} · аризалар: {x['leads']} · "
                           f"тўловлар: {x['paid']} · қарз: {x['owed']:,} сўм").replace(",", " "))
            return "mv"
        if act == "pd":
            self.set_step(chat, f"o_pay:{rest}")
            self.say(chat, T.O_ASK_PAID.format(n=rest), {"keyboard": [[{"text": T.O_PANEL}]], "resize_keyboard": True})
            return "pd"
        if act == "po":
            r = self.db.execute("SELECT name FROM masters WHERE id=?", (int(rest),)).fetchone()
            if not r:
                return None
            self.set_step(chat, f"o_out:{rest}")
            self.say(chat, T.O_ASK_OUT.format(name=esc(r["name"])), {"keyboard": [[{"text": T.O_PANEL}]], "resize_keyboard": True})
            return "po"
        return None

    def remind(self, minutes: int = 30) -> int:
        """Заявка без ответа дольше 30 мин — напомнить владельцу один раз (днём 9–22)."""
        t = now()
        if not 9 <= t.hour < 22:
            return 0
        cut = (t - dt.timedelta(minutes=minutes)).isoformat()
        rows = self.db.execute("SELECT n FROM leads WHERE status='new' AND reminded=0 AND created<?", (cut,)).fetchall()
        for r in rows:
            for o in self.owners:
                try:
                    self.api("sendMessage", chat_id=o, text=T.REMIND.format(n=r["n"]))
                except Exception as e:  # noqa: BLE001
                    print(f"remind: {e}", flush=True)
            self.db.execute("UPDATE leads SET reminded=1 WHERE n=?", (r["n"],))
        self.db.commit()
        return len(rows)

    def stats(self) -> str:
        users = self.db.execute("SELECT count(*) FROM users").fetchone()[0]
        leads = self.db.execute("SELECT count(*) FROM leads").fetchone()[0]
        by_kind = self.db.execute("SELECT kind, count(*) c FROM leads GROUP BY kind ORDER BY c DESC").fetchall()
        by_src = self.db.execute("SELECT coalesce(src,'—') s, count(*) c FROM users GROUP BY s ORDER BY c DESC").fetchall()
        avg = self.db.execute("SELECT avg(rating), count(rating) FROM leads WHERE rating IS NOT NULL").fetchone()
        k = "\n".join(f"• {T.KINDS.get(r['kind'], (r['kind'],))[0]}: {r['c']}" for r in by_kind) or "—"
        s = "\n".join(f"• {esc(r['s'])}: {r['c']}" for r in by_src) or "—"
        rate = f"\nЎртача баҳо: {avg[0]:.1f} ⭐ ({avg[1]} та)" if avg[1] else ""
        return f"📊 Кирганлар: {users}\nАризалар: {leads}{rate}\n\n<b>Хизмат бўйича:</b>\n{k}\n\n<b>Қаердан келди:</b>\n{s}"


# ---------- запуск ----------
def make_api(token: str):
    def api(method: str, **params):
        data = json.dumps({k: v for k, v in params.items() if v is not None}).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/{method}", data=data,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                out = json.loads(r.read())
        except urllib.error.HTTPError as e:
            out = json.loads(e.read() or b"{}")
        if not out.get("ok"):
            raise RuntimeError(f"{method}: {out.get('description')}")
        return out["result"]
    return api


def main():
    api = make_api(os.environ["USTA_BOT_TOKEN"])
    owners = [int(x) for x in os.environ.get("OWNER_IDS", "").split(",") if x.strip()]
    try:
        uname = api("getMe")["username"]
    except Exception:  # noqa: BLE001
        uname = "ozodjamoldizaynbot"
    bot = Bot(connect(os.environ.get("USTA_DB", "usta.sqlite3")), api, owners, uname)
    try:  # 31.10: кнопка меню бота → Mini App 3D дизайна
        api("setChatMenuButton", menu_button={"type": "web_app", "text": T.MENU_BTN, "web_app": {"url": T.MINIAPP_URL}})
    except Exception as e:  # noqa: BLE001
        print(f"menu: {e}", flush=True)
    off = 0
    print("usta: запущен", flush=True)
    while True:
        try:
            for u in api("getUpdates", offset=off, timeout=30, allowed_updates=["message", "callback_query"]):
                off = u["update_id"] + 1
                try:
                    bot.handle(u)
                except Exception as e:  # noqa: BLE001
                    print(f"handle: {type(e).__name__}: {e}", flush=True)
            bot.remind()
        except Exception as e:  # noqa: BLE001
            print(f"poll: {type(e).__name__}: {e}", flush=True)
            time.sleep(5)
