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
    urgency TEXT, rating INTEGER, reminded INTEGER NOT NULL DEFAULT 0, obj TEXT);
CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT NOT NULL);
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
    for col, typ in (("urgency", "TEXT"), ("rating", "INTEGER"), ("reminded", "INTEGER NOT NULL DEFAULT 0"), ("obj", "TEXT")):
        if col not in have:
            db.execute(f"ALTER TABLE leads ADD COLUMN {col} {typ}")
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
    rows = [[{"text": T.KINDS[k][0]}] for k in T.KINDS] + [[{"text": T.CONTACT}]]
    return {"keyboard": rows, "resize_keyboard": True}


class Bot:
    def __init__(self, db, api, owners: list[int]):
        self.db, self.api, self.owners = db, api, owners

    # ---------- состояние ----------
    def user(self, frm: dict, src: str | None = None):
        uid = frm["id"]
        r = self.db.execute("SELECT * FROM users WHERE uid=?", (uid,)).fetchone()
        t = now().isoformat()
        if not r:
            self.db.execute("INSERT INTO users(uid, first, username, src, step, data, created, updated) VALUES (?,?,?,?,?,?,?,?)",
                            (uid, frm.get("first_name"), frm.get("username"), src, "", "{}", t, t))
        elif src and not r["src"]:
            self.db.execute("UPDATE users SET src=? WHERE uid=?", (src, uid))
        self.db.commit()
        return self.db.execute("SELECT * FROM users WHERE uid=?", (uid,)).fetchone()

    def set_step(self, uid: int, step: str, data: dict | None = None):
        self.db.execute("UPDATE users SET step=?, data=?, updated=? WHERE uid=?",
                        (step, json.dumps(data or {}, ensure_ascii=False), now().isoformat(), uid))
        self.db.commit()

    def say(self, chat: int, text: str, kb: dict | None = None):
        return self.api("sendMessage", chat_id=chat, text=text, reply_markup=kb or main_kb(), parse_mode="HTML",
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
        step, data = u["step"] or "", json.loads(u["data"] or "{}")
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

    def phone_kb(self) -> dict:
        return {"keyboard": [[{"text": T.SEND_PHONE, "request_contact": True}], [{"text": T.BACK}]], "resize_keyboard": True}

    def ask_phone(self, chat: int):
        self.say(chat, T.ASK_PHONE, self.phone_kb())

    def finish(self, frm: dict, chat: int, data: dict, phone: str) -> str:
        u = self.db.execute("SELECT src FROM users WHERE uid=?", (frm["id"],)).fetchone()
        cur = self.db.execute("INSERT INTO leads(uid, kind, details, place, phone, photos, src, created, urgency, obj)"
                              " VALUES (?,?,?,?,?,?,?,?,?,?)",
                              (frm["id"], data.get("kind", "?"), data.get("details"), data.get("place"), phone,
                               json.dumps(data.get("photos") or []), u["src"] if u else None, now().isoformat(),
                               data.get("urgency"), data.get("obj")))
        self.db.commit()
        n = cur.lastrowid
        self.set_step(frm["id"], "")
        self.say(chat, T.DONE.format(n=n))
        self.notify(n, frm)
        return "lead"

    def card(self, r, frm: dict | None = None) -> str:
        who = esc((frm or {}).get("first_name") or "")
        un = (frm or {}).get("username")
        st = {"new": "🆕 янги", "done": "✅ боғланилди", "no": "❌ бекор", "fin": "🏁 иш битди"}.get(r["status"], r["status"])
        if r["rating"]:
            st += " · " + "⭐" * r["rating"]
        when = T.WHEN.get(r["urgency"] or "", r["urgency"] or "—")
        obj = f" · {T.OBJ.get(r['obj'], r['obj'])}" if r["obj"] else ""
        return (f"📥 <b>Ариза №{r['n']}</b> · {T.KINDS.get(r['kind'], (r['kind'],))[0]}{obj}\n"
                f"👤 {who}{(' @' + un) if un else ''}\n📞 {esc(r['phone'])}\n📍 {esc(r['place'])}\n"
                f"⏱ {esc(when)}\n📝 {esc(r['details'])}\n🔗 манба: {esc(r['src'] or '—')}\n{st}")

    def notify(self, n: int, frm: dict):
        r = self.db.execute("SELECT * FROM leads WHERE n=?", (n,)).fetchone()
        kb = {"inline_keyboard": [[{"text": "✅ Боғландим", "callback_data": f"ok:{n}"},
                                   {"text": "❌ Бекор", "callback_data": f"no:{n}"}]]}
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
        if q["from"]["id"] not in self.owners:
            return None
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
    bot = Bot(connect(os.environ.get("USTA_DB", "usta.sqlite3")), api, owners)
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
