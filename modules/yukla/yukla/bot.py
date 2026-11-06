"""«Хўжаобод Юкла ⚡» (@XojaobodYuklaBot, 03.11.2026) — Instagram/TikTok/YouTube видео ва MP3.

Владелец: «такой же бот для себя» (образец @Chaqqon_Robot). Мақсад — Xo'jaobod City учун обуначи: юклашдан олдин
каналга обуна (SUB_CHAT). Ҳар бир юкланган файл Telegram'да file_id билан хотирада қолади — шу ҳаволани кейинги
одамга дарҳол қайта юборади (Instagram'га қайта мурожаат йўқ). Двигатель — yt-dlp (YUKLA_YTDLP), прокси — YUKLA_PROXY
(ихтиёрий, 03.11: аввал проксисиз синов). Пульт фақат владелецга: ҳисобот, реклама матни, рассылка (✅ билан).
Фақат стандарт кутубхона: long polling + SQLite + ThreadPool.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
import sqlite3
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import texts as T

TZ = dt.timezone(dt.timedelta(hours=5))
MAX_BYTES = 49 * 1024 * 1024          # Bot API: юклаш чегараси 50 МБ
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (uid INTEGER PRIMARY KEY, first TEXT, username TEXT, created TEXT, last TEXT,
    blocked INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, url TEXT, kind TEXT, video TEXT, audio TEXT, hits INTEGER NOT NULL DEFAULT 0,
    created TEXT);
CREATE TABLE IF NOT EXISTS log (id INTEGER PRIMARY KEY AUTOINCREMENT, uid INTEGER, platform TEXT, result TEXT, ts TEXT);
CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS saved (uid INTEGER, rid INTEGER, ts TEXT, PRIMARY KEY (uid, rid));
CREATE TABLE IF NOT EXISTS subs (chat TEXT PRIMARY KEY, until TEXT, joins INTEGER NOT NULL DEFAULT 0, added TEXT,
    pos INTEGER NOT NULL DEFAULT 0);
"""
LINK_RE = re.compile(r"https?://[^\s]+", re.I)
PLATFORMS = (("instagram", re.compile(r"(?:^|\.)instagram\.com$")), ("tiktok", re.compile(r"(?:^|\.)tiktok\.com$")),
             ("youtube", re.compile(r"(?:^|\.)(?:youtube\.com|youtu\.be)$")),
             ("facebook", re.compile(r"(?:^|\.)(?:facebook\.com|fb\.watch|fb\.com)$")))   # 03.11 владелец: «многие сидят в Фейсбуке»


def now() -> str:
    return dt.datetime.now(TZ).isoformat(timespec="seconds")


def esc(s) -> str:
    return html.escape(str(s or ""), quote=False)


def platform_of(url: str) -> str | None:
    host = re.sub(r"^https?://", "", url, flags=re.I).split("/")[0].split("?")[0].lower()
    return next((name for name, rx in PLATFORMS if rx.search(host)), None)


def norm_key(url: str) -> str:
    """Бир видео — бир калит: ?igsh=, ?si= каби қўшимчалар ташланади."""
    u = re.sub(r"^https?://(www\.|m\.)?", "", url.strip(), flags=re.I)
    base, _, query = u.partition("?")
    host, _, path = base.rstrip("/").partition("/")
    base = host.lower() + "/" + path                       # коди катта-кичик ҳарфга сезгир — фақат домен кичик
    if platform_of(url) == "youtube":
        m = re.search(r"(?:v=)([\w-]{6,})", query) or re.search(r"(?:youtu\.be/|shorts/)([\w-]{6,})", base)
        return "yt:" + m.group(1) if m else base
    m = re.search(r"instagram\.com/(?:reel|reels|p|tv)/([\w-]+)", base, re.I)
    if m:
        return "ig:" + m.group(1)
    return base


def connect(path: str) -> sqlite3.Connection:
    db = sqlite3.connect(path, timeout=15, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    cols = {r[1] for r in db.execute("PRAGMA table_info(cache)")}
    for c in ("descr", "doc"):                    # 04.11: «📝 Тавсиф» ва «💾 Сақлаш» (Chaqqon каби)
        if c not in cols:
            db.execute(f"ALTER TABLE cache ADD COLUMN {c} TEXT")
    db.commit()
    return db


NAMAZ_JSON = Path(os.environ.get("PAPA_NAMAZ_JSON", "/var/lib/papa-namaz/namaz.json"))
N_KEYS = (("bomdod", "🌅 Бомдод"), ("peshin", "☀️ Пешин"), ("asr", "🌤 Аср"), ("shom", "🌇 Шом"), ("xufton", "🌙 Хуфтон"))
WEEK = ("Душанба", "Сешанба", "Чоршанба", "Пайшанба", "Жума", "Шанба", "Якшанба")


OBOI = Path(os.environ.get("PAPA_NAMAZ_OBOI", "/var/lib/papa-namaz/oboi"))


def oboi_current(base: Path = OBOI) -> tuple[str, list[Path], str] | None:
    """03.11: 5 та обои + тайёр матн («Намоз маркази» дан, papa-namaz-export чизади)."""
    try:
        key = (base / "CURRENT").read_text(encoding="utf-8").strip()
        d = base / key
        files = sorted(f for f in d.iterdir() if f.suffix == ".jpg")
        cap = (d / "caption.txt").read_text(encoding="utf-8")
    except OSError:
        return None
    return (key, files, cap) if 1 <= len(files) <= 10 else None      # 06.11: шаблонов может быть больше/меньше 5


TOP_ROWS = [[{"text": T.GROUP_BTN}, {"text": T.DESC_BTN}], [{"text": T.MP3_BTN}, {"text": T.SAVE_BTN}]]   # 04.11 владелец: 4 кнопки Chaqqon сверху


def user_kb() -> dict:
    return {"keyboard": TOP_ROWS + [[{"text": T.NAMAZ_BTN}]], "resize_keyboard": True, "is_persistent": True}


def namaz_text(path: Path = NAMAZ_JSON, today: dt.datetime | None = None) -> str | None:
    """«🕌 Намоз маркази»: владелец PAPA'га киритган вақт (ягона манба)."""
    try:
        sched = json.loads(path.read_text(encoding="utf-8"))["schedule"]
    except (OSError, ValueError, KeyError):
        return None
    t = today or dt.datetime.now(TZ)
    rows = [r for r in sched if r.get("day", "") <= t.date().isoformat()]
    if not rows:
        return None
    r = rows[-1]
    hm = t.strftime("%H:%M")
    nxt = next((k for k, _ in N_KEYS if r.get(k, "") > hm), None)
    lines = [f"{'➡️ ' if k == nxt else ''}{label} — <b>{r.get(k, '—')}</b>" for k, label in N_KEYS]
    return T.NAMAZ.format(date=f"{t:%d.%m.%Y} · {WEEK[t.weekday()]}", rows="\n".join(lines))


def owner_kb() -> dict:
    return {"keyboard": [[{"text": T.O_STATS}, {"text": T.O_SUBS}], [{"text": T.O_AD}, {"text": T.O_SEND}],
                         [{"text": T.O_PREVIEW}]], "resize_keyboard": True}


class Downloader:
    """yt-dlp орқали. Тест учун алмаштирилади."""

    def __init__(self, ytdlp: str = "yt-dlp", proxy: str | None = None):
        self.ytdlp, self.proxy = ytdlp, proxy

    def fetch(self, url: str, audio: bool = False) -> Path | None:
        out = Path(tempfile.mkdtemp(prefix="yukla-"))
        cmd = [self.ytdlp, "--no-playlist", "--no-warnings", "-q", "--max-filesize", str(MAX_BYTES),
               "-o", str(out / "f.%(ext)s"), "--socket-timeout", "20", "--retries", "2"]
        if self.proxy:
            cmd += ["--proxy", self.proxy]
        if audio:
            cmd += ["-x", "--audio-format", "mp3", "--audio-quality", "5"]
        else:
            cmd += ["--print-to-file", "%(description)s", str(out / "desc.txt")]   # 04.11: «📝 Тавсиф»
            cmd += ["-f", "best[ext=mp4][filesize<49M]/bv*[ext=mp4]+ba[ext=m4a]/best[filesize<49M]/best",
                    "--merge-output-format", "mp4"]
        try:
            subprocess.run(cmd + [url], timeout=150, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                           stderr=subprocess.PIPE, check=False)
        except subprocess.TimeoutExpired:
            return None
        except OSError as e:                      # 04.11: yt-dlp не запускается (права) — не молчим, а «не удалось»
            print(f"fetch: {type(e).__name__}: {e}", flush=True)
            return None
        files = [f for f in out.iterdir() if f.is_file() and not f.name.endswith((".part", ".txt"))]
        return max(files, key=lambda f: f.stat().st_size) if files else None


class Bot:
    def __init__(self, db, api, owners: list[int], username: str = "XojaobodYuklaBot",
                 sub_chat: str | None = "@kattadavrauz,@xojaobodcity24",
                 downloader: Downloader | None = None, upload=None, workers: int = 2, sync: bool = False):
        self.db, self.api, self.owners, self.username, self.sub_chat = db, api, owners, username, sub_chat
        self.dl = downloader or Downloader()
        self.upload = upload                  # upload(method, chat, field, path, caption, kb) -> message dict
        self.upload_group = None              # upload_group(chat, files, caption) -> [message]
        self.lock = threading.RLock()
        self.busy: set[int] = set()
        self.sync = sync                      # тестда — навбатсиз, дарҳол
        self.pool = None if sync else ThreadPoolExecutor(max_workers=workers)
        self.bot_id = None
        if sub_chat and not self.q("SELECT 1 FROM subs LIMIT 1", one=True) and not self.kv("subs_seeded"):
            for i, c in enumerate(x.strip() for x in sub_chat.split(",") if x.strip()):   # бошланғич: муддатсиз
                self.q("INSERT OR IGNORE INTO subs(chat, until, added, pos) VALUES (?,?,?,?)", (c, None, now(), i))
            self.kv("subs_seeded", now())
        if not self.kv("subs_v2"):                       # 03.11: КАТТА ДАВРА — асосий (сервердаги эски .env'да фақат Xo'jaobod эди)
            self.kv("subs_v2", now())
            if not self.q("SELECT 1 FROM subs WHERE chat='@kattadavrauz'", one=True):
                self.q("INSERT INTO subs(chat, until, added, pos) VALUES ('@kattadavrauz', NULL, ?, -1)", (now(),))

    # ---------- ёрдамчилар ----------
    def q(self, sql: str, args=(), one=False):
        with self.lock:
            cur = self.db.execute(sql, args)
            self.db.commit()
            return cur.fetchone() if one else cur.fetchall()

    def kv(self, k: str, v: str | None = None) -> str | None:
        if v is None:
            r = self.q("SELECT v FROM kv WHERE k=?", (k,), one=True)
            return r["v"] if r else None
        self.q("INSERT OR REPLACE INTO kv(k, v) VALUES (?, ?)", (k, v))
        return v

    def preview(self, uid: int) -> bool:
        return uid in self.owners and self.kv(f"preview:{uid}") == "1"

    def say(self, chat: int, text: str, kb: dict | None = None, reply_to: int | None = None):
        if chat < 0:                              # 04.11: гуруҳда пастки тугмалар йўқ — фақат хабар (ва инлайн тугмалар)
            return self.api("sendMessage", chat_id=chat, text=text, parse_mode="HTML", reply_markup=kb,
                            disable_web_page_preview=True, reply_to_message_id=reply_to)
        if kb is None:
            if chat in self.owners and not self.preview(chat):
                kb = owner_kb()
            elif chat in self.owners:
                kb = {"keyboard": TOP_ROWS + [[{"text": T.NAMAZ_BTN}], [{"text": T.O_BACK}]], "resize_keyboard": True}
            else:
                kb = user_kb()
        return self.api("sendMessage", chat_id=chat, text=text, parse_mode="HTML", reply_markup=kb,
                        disable_web_page_preview=True)

    def submit(self, fn, *a):
        if self.sync:
            return fn(*a)
        return self.pool.submit(self._safe, fn, *a)

    def _safe(self, fn, *a):
        try:
            fn(*a)
        except Exception as e:  # noqa: BLE001 — бир ҳавола ботни йиқитмасин
            print(f"worker: {type(e).__name__}: {e}", flush=True)

    def seen(self, frm: dict):
        self.q("""INSERT INTO users(uid, first, username, created, last) VALUES (?,?,?,?,?)
                  ON CONFLICT(uid) DO UPDATE SET first=excluded.first, username=excluded.username, last=excluded.last, blocked=0""",
               (frm["id"], frm.get("first_name"), frm.get("username"), now(), now()))

    def active_subs(self) -> list:
        """Муддати тугаганларни олиб ташлаб (владелецга хабар), фаол каналлар рўйхати."""
        for r in self.q("SELECT * FROM subs WHERE until IS NOT NULL AND until<?", (now(),)):
            self.q("DELETE FROM subs WHERE chat=?", (r["chat"],))
            for o in self.owners:
                self.say(o, T.O_SUB_EXPIRED.format(chat=esc(r["chat"])))
                self.say(o, self.sponsor_report(r))           # тайёр ҳисобот — ҳомийга юбориш учун
        return self.q("SELECT * FROM subs ORDER BY pos, added")

    def missing(self, uid: int) -> list[str]:
        """Обуна бўлинмаган каналлар. Текшириб бўлмаса — ўтказамиз, владелецга бир марта айтамиз."""
        if uid in self.owners and not self.preview(uid):
            return []
        out = []
        for r in self.active_subs():
            try:
                m = self.api("getChatMember", chat_id=r["chat"], user_id=uid)
                if m.get("status") not in ("member", "administrator", "creator", "restricted"):
                    out.append(r["chat"])
            except Exception as e:  # noqa: BLE001
                if not self.kv(f"sub_warned:{r['chat']}"):
                    self.kv(f"sub_warned:{r['chat']}", now())
                    for o in self.owners:
                        self.say(o, T.O_SUB_WARN.format(err=esc(f"{r['chat']}: {str(e)[:60]}")))
        return out

    def subscribed(self, uid: int) -> bool:
        return not self.missing(uid)

    @staticmethod
    def link(chat: str) -> str:
        return f"https://t.me/{chat.lstrip('@')}" if chat.startswith("@") else ""

    def sub_link(self) -> str:
        r = self.q("SELECT chat FROM subs ORDER BY pos, added LIMIT 1", one=True)
        return self.link(r["chat"]) if r else ""

    def row_id(self, key: str, url: str) -> int:
        self.q("INSERT OR IGNORE INTO cache(key, url, kind, created) VALUES (?,?,?,?)", (key, url, platform_of(url), now()))
        return self.q("SELECT rowid FROM cache WHERE key=?", (key,), one=True)[0]

    def last(self, uid: int) -> int | None:
        v = self.kv(f"last:{uid}")
        return int(v) if v and v.isdigit() else None

    def bottom(self, uid: int, chat: int, text: str) -> str | None:
        """Пастки 4 тугма — охирги юкланган видео учун (видео остидаги тугмалар билан бир хил)."""
        if text == T.GROUP_BTN:
            self.say(chat, T.GROUP_HOW, {"inline_keyboard": [[{"text": T.GROUP_ADD, "url": f"https://t.me/{self.username}?startgroup=true"}]]})
            return "group_how"
        if text not in (T.DESC_BTN, T.MP3_BTN, T.SAVE_BTN):
            return None
        rid = self.last(uid)
        if rid is None:
            self.say(chat, T.NEED_LAST); return "need_last"
        fake = {"id": "0", "from": {"id": uid}, "data": {T.DESC_BTN: "d:", T.MP3_BTN: "a:", T.SAVE_BTN: "s:"}[text] + str(rid),
                "message": {"chat": {"id": chat}, "message_id": 0}}
        return self.callback(fake)

    def media_kb(self, rid: int) -> dict:
        """04.11 владелец: «панель как в Chaqqon бот» (скриншот): ➕ Гуруҳда ишлатиш / 📝 Тавсиф · 🎵 MP3 / 📁 Сақлаш · ❌ Ўчириш."""
        return {"inline_keyboard": [[{"text": T.GROUP_BTN, "url": f"https://t.me/{self.username}?startgroup=true"}],
                                    [{"text": T.DESC_BTN, "callback_data": f"d:{rid}"}, {"text": T.MP3_BTN, "callback_data": f"a:{rid}"}],
                                    [{"text": T.SAVE_BTN, "callback_data": f"s:{rid}"}, {"text": T.DEL_BTN, "callback_data": "x"}]]}

    def caption(self) -> str:
        return T.CAPTION.format(bot=self.username)

    def send_ad(self, chat: int):
        """04.11 (как в Chaqqon): реклама — отдельным сообщением сразу после видео."""
        ad = self.kv("ad") or ""
        if ad:
            try:
                self.api("sendMessage", chat_id=chat, text=ad, parse_mode="HTML", disable_web_page_preview=True)
            except Exception as e:  # noqa: BLE001
                print(f"ad: {type(e).__name__}: {e}", flush=True)

    def namaz(self) -> str | None:
        return namaz_text()

    def oboi(self):
        return oboi_current()

    def send_oboi(self, chat: int) -> bool:
        """Альбом: 5 обои, остида тайёр матн. Биринчи марта юклаб, кейин file_id билан — дарҳол."""
        cur = self.oboi()
        if not cur:
            return False
        key, files, cap = cur
        ids = json.loads(self.kv(f"oboi:{key}") or "[]")
        if len(ids) == 5:
            media = [{"type": "photo", "media": fid} for fid in ids]
            media[0].update(caption=cap, parse_mode="HTML")
            try:
                self.api("sendMediaGroup", chat_id=chat, media=media)
                return True
            except Exception:  # noqa: BLE001 — file_id эскирган бўлса — қайта юклаймиз
                pass
        res = self.upload_group(chat, files, cap) if self.upload_group else None
        if not res:
            return False
        ids = [max(m["photo"], key=lambda p: p.get("file_size", 0))["file_id"] for m in res if m.get("photo")]
        if len(ids) == 5:
            self.kv(f"oboi:{key}", json.dumps(ids))
        return True

    # ---------- кириш ----------
    def handle(self, upd: dict) -> str | None:
        if "callback_query" in upd:
            return self.callback(upd["callback_query"])
        m = upd.get("message")
        if not m:
            return None
        if m["chat"]["type"] in ("group", "supergroup"):     # 04.11: «👥 Гуруҳда ишлатиш» — гуруҳдаги ҳаволани ўзи юклайди
            return self.group(m)
        if m["chat"]["type"] != "private":
            return None
        frm, chat = m["from"], m["chat"]["id"]
        text = (m.get("text") or m.get("caption") or "").strip()
        self.seen(frm)
        if frm["id"] in self.owners and text in (T.O_BACK, "/panel"):
            self.kv(f"preview:{chat}", "0")
            self.say(chat, T.O_HELLO); return "o_panel"
        if frm["id"] in self.owners and not self.preview(frm["id"]):
            r = self.owner(frm, chat, m, text)
            if r:
                return r
        if text.startswith("/start"):
            self.say(chat, T.START)
            return "start"
        r = self.bottom(frm["id"], chat, text)
        if r:
            return r
        if text in ("/saqlangan", "/saved", T.SAVED_BTN):
            return self.saved_list(chat, frm["id"])
        if text == T.NAMAZ_BTN or text in ("/namoz", "/namaz"):
            if self.send_oboi(chat):
                return "namaz_oboi"
            nt = self.namaz()
            more = {"inline_keyboard": [[{"text": T.NAMAZ_MORE, "url": f"https://t.me/{T.CITY24_BOT}"}]]}
            self.say(chat, nt or T.NAMAZ_NONE, more if nt else None)
            return "namaz"
        link = LINK_RE.search(text)
        if not link or not platform_of(link.group()):
            self.say(chat, T.BAD_LINK)
            return "bad"
        url = link.group().rstrip(").,")
        miss = self.missing(frm["id"])
        if miss:
            self.kv(f"pending:{frm['id']}", url)
            self.kv(f"miss:{frm['id']}", ",".join(miss))          # кейин «қайси канал обуначи келтирди» ҳисоби
            return self.gate(chat, miss)
        return self.start_job(frm["id"], chat, url)

    def group(self, m: dict) -> str | None:
        text = (m.get("text") or m.get("caption") or "").strip()
        link = LINK_RE.search(text)
        if not link or not platform_of(link.group()):
            return None                           # гуруҳда бошқа гапларга жавоб бермаймиз
        url = link.group().rstrip(").,")
        return self.start_job(m["from"]["id"], m["chat"]["id"], url, reply_to=m["message_id"])

    def saved_list(self, chat: int, uid: int) -> str:
        rows = self.q("SELECT c.rowid AS rid, c.kind, c.url FROM saved s JOIN cache c ON c.rowid=s.rid "
                      "WHERE s.uid=? AND c.video IS NOT NULL ORDER BY s.ts DESC LIMIT 20", (uid,))
        if not rows:
            self.say(chat, T.SAVED_NONE); return "saved_empty"
        kb = [[{"text": f"▶️ {i}. {(r['kind'] or '').capitalize()}", "callback_data": f"v:{r['rid']}"}] for i, r in enumerate(rows, 1)]
        self.say(chat, T.SAVED_HEAD.format(n=len(rows)), {"inline_keyboard": kb})
        return "saved"

    def gate(self, chat: int, miss: list[str]) -> str:
        rows = [[{"text": f"📢 {c}", "url": self.link(c)}] for c in miss if self.link(c)]
        self.say(chat, T.NEED_SUB, {"inline_keyboard": rows + [[{"text": T.CHECK_BTN, "callback_data": "chk"}]]})
        return "need_sub"

    def start_job(self, uid: int, chat: int, url: str, reply_to: int | None = None) -> str:
        key = norm_key(url)
        hit = self.q("SELECT * FROM cache WHERE key=? AND video IS NOT NULL", (key,), one=True)
        if hit:                                   # хотирадан — дарҳол
            self.q("UPDATE cache SET hits=hits+1 WHERE key=?", (key,))
            self.kv(f"last:{uid}", str(self.row_id(key, url)))
            self.api("sendVideo", chat_id=chat, video=hit["video"], caption=self.caption(), parse_mode="HTML",
                     reply_markup=self.media_kb(self.row_id(key, url)), reply_to_message_id=reply_to)
            self.send_ad(chat)
            self.q("INSERT INTO log(uid, platform, result, ts) VALUES (?,?,?,?)", (uid, platform_of(url), "cache", now()))
            return "cache"
        with self.lock:
            if uid in self.busy:
                self.say(chat, T.BUSY)
                return "busy"
            self.busy.add(uid)
        wait = self.say(chat, T.WAIT, reply_to=reply_to) or {}
        self.submit(self.job, uid, chat, url, key, wait.get("message_id"))
        return "job"

    def job(self, uid: int, chat: int, url: str, key: str, wait_id):
        res = "fail"
        try:
            f = self.dl.fetch(url)
            if f and f.stat().st_size > MAX_BYTES:
                self.say(chat, T.TOO_BIG); res = "big"
            elif f:
                d = f.parent / "desc.txt"
                if d.exists():
                    txt = d.read_text(encoding="utf-8", errors="replace").strip()
                    if txt and txt not in ("NA", "None"):
                        self.row_id(key, url)
                        self.q("UPDATE cache SET descr=? WHERE key=?", (txt[:3500], key))
                msg = self.upload("sendVideo", chat, "video", f, self.caption(), self.media_kb(self.row_id(key, url))) or {}
                fid = (msg.get("video") or msg.get("document") or {}).get("file_id")
                if fid:
                    self.q("UPDATE cache SET video=? WHERE key=?", (fid, key))
                self.kv(f"last:{uid}", str(self.row_id(key, url)))
                self.send_ad(chat)
                res = "ok"
            else:
                self.say(chat, T.FAIL)
        except Exception as e:  # noqa: BLE001 — 04.11: человек всегда получает ответ, а не тишину
            print(f"job: {type(e).__name__}: {e}", flush=True)
            try:
                self.say(chat, T.FAIL)
            except Exception:  # noqa: BLE001
                pass
        finally:
            with self.lock:
                self.busy.discard(uid)
            if wait_id:
                try:
                    self.api("deleteMessage", chat_id=chat, message_id=wait_id)
                except Exception:  # noqa: BLE001
                    pass
            self.q("INSERT INTO log(uid, platform, result, ts) VALUES (?,?,?,?)", (uid, platform_of(url), res, now()))

    def doc_job(self, chat: int, rid: str):
        """💾 Сақлаш: видео файл сифатида (сиқилмайди — галереяга асл сифатда сақланади)."""
        row = self.q("SELECT rowid, * FROM cache WHERE rowid=?", (int(rid) if rid.isdigit() else -1,), one=True)
        if not row:
            self.say(chat, T.FAIL); return
        if row["doc"]:
            self.api("sendDocument", chat_id=chat, document=row["doc"], caption=self.caption(), parse_mode="HTML"); return
        f = self.dl.fetch(row["url"])
        if not f:
            self.say(chat, T.FAIL); return
        msg = self.upload("sendDocument", chat, "document", f, self.caption(), None) or {}
        fid = (msg.get("document") or {}).get("file_id")
        if fid:
            self.q("UPDATE cache SET doc=? WHERE rowid=?", (fid, row["rowid"]))

    def audio_job(self, chat: int, rid: str):
        row = self.q("SELECT rowid, * FROM cache WHERE rowid=?", (int(rid) if rid.isdigit() else -1,), one=True)
        if not row:
            self.say(chat, T.FAIL); return
        if row["audio"]:
            self.api("sendAudio", chat_id=chat, audio=row["audio"], caption=self.caption(), parse_mode="HTML"); return
        f = self.dl.fetch(row["url"], audio=True)
        if not f:
            self.say(chat, T.FAIL); return
        msg = self.upload("sendAudio", chat, "audio", f, self.caption(), None) or {}
        fid = (msg.get("audio") or msg.get("document") or {}).get("file_id")
        if fid:
            self.q("UPDATE cache SET audio=? WHERE rowid=?", (fid, row["rowid"]))

    def callback(self, cq: dict) -> str | None:
        if cq.get("id") == "0":                   # пастки тугмадан (ҳақиқий callback эмас) — answerCallbackQuery ўрнига хабар
            api0 = self.api
            def _api(method, **p):
                if method == "answerCallbackQuery":
                    if p.get("show_alert") and p.get("text"):
                        return api0("sendMessage", chat_id=cq["message"]["chat"]["id"], text=p["text"])
                    return None
                return api0(method, **p)
            self.api = _api
            try:
                return self._callback(cq)
            finally:
                self.api = api0
        return self._callback(cq)

    def _callback(self, cq: dict) -> str | None:
        data, uid = cq.get("data") or "", cq["from"]["id"]
        chat = cq["message"]["chat"]["id"] if cq.get("message") else uid
        if data == "chk":
            if self.missing(uid):
                self.api("answerCallbackQuery", callback_query_id=cq["id"], text=T.NOT_YET, show_alert=True)
                return "not_yet"
            self.api("answerCallbackQuery", callback_query_id=cq["id"], text="✅")
            for c in (self.kv(f"miss:{uid}") or "").split(","):    # шу каналга бот олиб келган обуначи
                if c:
                    self.q("UPDATE subs SET joins=joins+1 WHERE chat=?", (c,))
            self.kv(f"miss:{uid}", "")
            url = self.kv(f"pending:{uid}")
            return self.start_job(uid, chat, url) if url else "ok"
        if data.startswith("a:"):
            self.api("answerCallbackQuery", callback_query_id=cq["id"], text="🎵")
            self.submit(self.audio_job, chat, data[2:])
            return "mp3"
        if data.startswith("d:"):                                  # 📝 Тавсиф — асл пост матни
            self.api("answerCallbackQuery", callback_query_id=cq["id"])
            row = self.q("SELECT descr FROM cache WHERE rowid=?", (int(data[2:]) if data[2:].isdigit() else -1,), one=True)
            t = (row["descr"] if row else None) or ""
            self.say(chat, f"📝 <b>{T.DESC_HEAD}</b>\n\n{esc(t)}" if t else T.DESC_NONE, {"inline_keyboard": []} if chat > 0 else None)
            return "desc"
        if data.startswith("s:"):                                  # 📁 Сақлаш — «📁 Сақланганлар» рўйхатига (/saqlangan)
            rid = int(data[2:]) if data[2:].isdigit() else -1
            self.q("INSERT OR IGNORE INTO saved(uid, rid, ts) VALUES (?,?,?)", (uid, rid, now()))
            self.api("answerCallbackQuery", callback_query_id=cq["id"], text=T.SAVED_OK, show_alert=True)
            return "save"
        if data == "x":                                            # ❌ Ўчириш — видеони чатдан олиб ташлаш
            self.api("answerCallbackQuery", callback_query_id=cq["id"])
            try:
                self.api("deleteMessage", chat_id=chat, message_id=cq["message"]["message_id"])
            except Exception:  # noqa: BLE001
                pass
            return "del"
        if data.startswith("v:"):                                  # сақланган видеони қайта юбориш
            self.api("answerCallbackQuery", callback_query_id=cq["id"])
            row = self.q("SELECT rowid, * FROM cache WHERE rowid=?", (int(data[2:]) if data[2:].isdigit() else -1,), one=True)
            if row and row["video"]:
                self.api("sendVideo", chat_id=chat, video=row["video"], caption=self.caption(), parse_mode="HTML",
                         reply_markup=self.media_kb(row["rowid"]))
            else:
                self.say(chat, T.FAIL)
            return "resend"
        if uid in self.owners and data.startswith("sd:"):          # каналнии олиб ташлаш
            self.api("answerCallbackQuery", callback_query_id=cq["id"])
            self.q("DELETE FROM subs WHERE chat=?", (data[3:],))
            self.say(chat, T.O_SUB_REMOVED.format(chat=esc(data[3:])))
            return self.o_subs(chat)
        if uid in self.owners and data.startswith("sr:"):          # ҳомийга юбориладиган ҳисобот
            self.api("answerCallbackQuery", callback_query_id=cq["id"])
            r = self.q("SELECT * FROM subs WHERE chat=?", (data[3:],), one=True)
            if r:
                self.say(chat, self.sponsor_report(r), {"inline_keyboard": []})
            return "o_sponsor_report"
        if uid in self.owners and data == "sa":
            self.api("answerCallbackQuery", callback_query_id=cq["id"])
            self.kv(f"ostep:{chat}", "sub")
            self.say(chat, T.O_SUB_ASK)
            return "o_sub_ask"
        if uid in self.owners and data in ("bc_yes", "bc_no"):
            self.api("answerCallbackQuery", callback_query_id=cq["id"])
            src = self.kv("bc_src")
            if data == "bc_no" or not src:
                self.say(chat, "❌ Бекор қилинди."); return "bc_no"
            self.kv("bc_src", "")
            from_chat, mid = (int(x) for x in src.split(":"))
            self.say(chat, T.O_SENDING)
            self.submit(self.broadcast, chat, from_chat, mid)
            return "bc_yes"
        return None

    # ---------- пульт ----------
    def owner(self, frm: dict, chat: int, m: dict, text: str) -> str | None:
        step = self.kv(f"ostep:{chat}") or ""
        if text in ("/start", "/panel") and not step:
            self.say(chat, T.O_HELLO); return "o_panel"
        if text == T.O_STATS:
            self.say(chat, self.stats()); return "o_stats"
        if text == T.O_AD:
            self.kv(f"ostep:{chat}", "ad")
            self.say(chat, T.O_ASK_AD.format(cur=esc(self.kv("ad") or "—"))); return "o_ad"
        if text == T.O_SUBS:
            return self.o_subs(chat)
        if text == T.O_PREVIEW:
            self.kv(f"preview:{chat}", "1")
            self.say(chat, T.O_PREVIEW_ON); return "o_preview"
        if step == "sub" and text:
            self.kv(f"ostep:{chat}", "")
            return self.o_sub_add(chat, text)
        if text == T.O_SEND:
            self.kv(f"ostep:{chat}", "bc")
            self.say(chat, T.O_ASK_SEND); return "o_send"
        if step == "ad" and text:
            self.kv(f"ostep:{chat}", "")
            self.kv("ad", "" if text == "-" else text[:300])
            self.say(chat, T.O_AD_SET); return "o_ad_set"
        if step == "bc":
            self.kv(f"ostep:{chat}", "")
            n = self.q("SELECT count(*) c FROM users WHERE blocked=0", one=True)["c"]
            self.kv("bc_src", f"{chat}:{m['message_id']}")
            self.api("copyMessage", chat_id=chat, from_chat_id=chat, message_id=m["message_id"])
            self.say(chat, T.O_CONFIRM.format(n=n), {"inline_keyboard": [[{"text": "✅ Юбориш", "callback_data": "bc_yes"},
                                                                          {"text": "❌ Йўқ", "callback_data": "bc_no"}]]})
            return "o_bc_preview"
        return None

    def sponsor_report(self, r) -> str:
        start = (r["added"] or now())[:10]
        end = (r["until"] or now())[:10]
        left = ""
        if r["until"] and r["until"] > now():
            left = f" (яна {(dt.datetime.fromisoformat(r['until']) - dt.datetime.now(TZ)).days + 1} кун)"
        fmt = lambda d: f"{d[8:10]}.{d[5:7]}"
        return T.SPONSOR_REPORT.format(chat=esc(r["chat"]), start=fmt(start), end=fmt(end), left=left,
                                       joins=f"{r['joins']:,}".replace(",", " "), bot=self.username)

    def o_subs(self, chat: int) -> str:
        rows = self.active_subs()
        lines = [T.O_SUBS_HEAD] if rows else [T.O_SUBS_EMPTY]
        btn = []
        for r in rows:
            until = f"до {r['until'][:10]}" if r["until"] else "муддатсиз"
            lines.append(f"• {esc(r['chat'])} · {until} · бот келтирди: {r['joins']}")
            btn.append([{"text": f"📄 {r['chat']}", "callback_data": f"sr:{r['chat']}"[:64]},
                        {"text": "🗑", "callback_data": f"sd:{r['chat']}"[:64]}])
        btn.append([{"text": "➕ Канал қўшиш", "callback_data": "sa"}])
        self.say(chat, "\n".join(lines), {"inline_keyboard": btn})
        return "o_subs"

    def o_sub_add(self, chat: int, text: str) -> str:
        m = re.match(r"^\s*(?:https?://t\.me/)?@?([A-Za-z0-9_]{4,32})\s*(\d{1,3})?\s*$", text)
        if not m:
            self.say(chat, T.O_SUB_ASK); return "o_sub_bad"
        c, days = "@" + m.group(1), int(m.group(2) or 0)
        try:
            me = self.bot_id or self.api("getMe")["id"]
            st = self.api("getChatMember", chat_id=c, user_id=me).get("status")
        except Exception:  # noqa: BLE001
            st = None
        if st not in ("administrator", "creator"):
            self.say(chat, T.O_SUB_NOT_ADMIN.format(chat=esc(c))); return "o_sub_not_admin"
        until = (dt.datetime.now(TZ) + dt.timedelta(days=days)).isoformat(timespec="seconds") if days else None
        pos = (self.q("SELECT max(pos) m FROM subs", one=True)["m"] or 0) + 1
        self.q("INSERT OR REPLACE INTO subs(chat, until, joins, added, pos) VALUES (?,?,COALESCE((SELECT joins FROM subs WHERE chat=?),0),?,?)",
               (c, until, c, now(), pos))
        self.say(chat, T.O_SUB_ADDED.format(chat=esc(c), until=f" — {days} кун" if days else " — муддатсиз"))
        n = len(self.active_subs())
        if n > 2:
            self.say(chat, T.O_SUB_MANY.format(n=n))
        return self.o_subs(chat)

    def broadcast(self, owner_chat: int, from_chat: int, mid: int, pause: float = 0.05):
        ok = fail = 0
        for r in self.q("SELECT uid FROM users WHERE blocked=0"):
            try:
                self.api("copyMessage", chat_id=r["uid"], from_chat_id=from_chat, message_id=mid)
                ok += 1
            except Exception:  # noqa: BLE001 — ботни блоклаган
                fail += 1
                self.q("UPDATE users SET blocked=1 WHERE uid=?", (r["uid"],))
            time.sleep(pause)
        self.say(owner_chat, T.O_SENT.format(ok=ok, fail=fail))

    def stats(self) -> str:
        day = dt.datetime.now(TZ).date().isoformat()
        users = self.q("SELECT count(*) c FROM users", one=True)["c"]
        new = self.q("SELECT count(*) c FROM users WHERE created>=?", (day,), one=True)["c"]
        rows = self.q("SELECT platform, result, count(*) c FROM log WHERE ts>=? GROUP BY platform, result", (day,))
        tot = {r["result"]: 0 for r in rows}
        by = {}
        for r in rows:
            tot[r["result"]] = tot.get(r["result"], 0) + r["c"]
            by.setdefault(r["platform"] or "?", {})[r["result"]] = r["c"]
        lines = [f"📊 <b>ҲИСОБОТ</b> (бугун)", f"👥 Фойдаланувчилар: {users} (бугун янги: {new})",
                 f"⬇️ Юклашлар: {sum(tot.values())} · ✅ {tot.get('ok', 0)} · ⚡ хотирадан {tot.get('cache', 0)} · "
                 f"❌ {tot.get('fail', 0)}"]
        for p, d in sorted(by.items()):
            lines.append(f"• {p}: ✅ {d.get('ok', 0) + d.get('cache', 0)} · ❌ {d.get('fail', 0)}")
        return "\n".join(lines)


# ---------- ишга тушириш ----------
def make_api(token: str):
    def api(method: str, **params):
        data = json.dumps({k: v for k, v in params.items() if v is not None}).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/{method}", data=data,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                out = json.loads(r.read())
        except urllib.error.HTTPError as e:
            out = json.loads(e.read() or b"{}")
        if not out.get("ok"):
            raise RuntimeError(f"{method}: {out.get('description')}")
        return out["result"]
    return api


def make_upload(token: str):
    def upload(method: str, chat: int, field: str, path: Path, caption: str, kb: dict | None):
        b = uuid.uuid4().hex
        parts = []
        fields = {"chat_id": str(chat), "caption": caption[:1024], "parse_mode": "HTML"}
        if method == "sendVideo":
            fields["supports_streaming"] = "true"
        if kb:
            fields["reply_markup"] = json.dumps(kb, ensure_ascii=False)
        for k, v in fields.items():
            parts.append(f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
        parts.append(f"--{b}\r\nContent-Disposition: form-data; name=\"{field}\"; filename=\"{path.name}\"\r\n"
                     f"Content-Type: application/octet-stream\r\n\r\n".encode() + path.read_bytes() + b"\r\n")
        parts.append(f"--{b}--\r\n".encode())
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/{method}", data=b"".join(parts),
                                     headers={"Content-Type": f"multipart/form-data; boundary={b}"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read()).get("result")
        finally:
            try:
                for f in path.parent.iterdir():
                    f.unlink()
                path.parent.rmdir()
            except OSError:
                pass
    return upload


def make_upload_group(token: str):
    def upload_group(chat: int, files: list[Path], caption: str):
        b = uuid.uuid4().hex
        media = [{"type": "photo", "media": f"attach://f{i}"} for i in range(len(files))]
        media[0].update(caption=caption[:1024], parse_mode="HTML")
        parts = [f"--{b}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat}\r\n".encode(),
                 f"--{b}\r\nContent-Disposition: form-data; name=\"media\"\r\n\r\n{json.dumps(media, ensure_ascii=False)}\r\n".encode()]
        for i, f in enumerate(files):
            parts.append(f"--{b}\r\nContent-Disposition: form-data; name=\"f{i}\"; filename=\"{f.name}\"\r\n"
                         f"Content-Type: image/jpeg\r\n\r\n".encode() + f.read_bytes() + b"\r\n")
        parts.append(f"--{b}--\r\n".encode())
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMediaGroup", data=b"".join(parts),
                                     headers={"Content-Type": f"multipart/form-data; boundary={b}"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read()).get("result")
    return upload_group


def main():
    tok = os.environ["YUKLA_BOT_TOKEN"]
    api = make_api(tok)
    owners = [int(x) for x in os.environ.get("OWNER_IDS", "").split(",") if x.strip()]
    try:
        me = api("getMe")
        uname, bid = me["username"], me["id"]
    except Exception:  # noqa: BLE001
        uname, bid = "XojaobodYuklaBot", None
    dl = Downloader(os.environ.get("YUKLA_YTDLP", "yt-dlp"), os.environ.get("YUKLA_PROXY") or None)
    bot = Bot(connect(os.environ.get("YUKLA_DB", "yukla.sqlite3")), api, owners, uname,
              os.environ.get("YUKLA_SUB_CHAT", "@kattadavrauz,@xojaobodcity24") or None, dl, make_upload(tok))
    bot.bot_id = bid
    bot.upload_group = make_upload_group(tok)
    try:                                          # 04.11: «Меню» как в Chaqqon — команды бота
        api("setMyCommands", commands=[{"command": "start", "description": "Бошлаш"},
                                       {"command": "saqlangan", "description": "📁 Сақланганлар"},
                                       {"command": "namoz", "description": "🕌 Намоз вақтлари"}])
    except Exception as e:  # noqa: BLE001
        print(f"commands: {e}", flush=True)
    off = 0
    print(f"yukla: запущен @{uname}", flush=True)
    while True:
        try:
            for u in api("getUpdates", offset=off, timeout=30, allowed_updates=["message", "callback_query"]):
                off = u["update_id"] + 1
                try:
                    bot.handle(u)
                except Exception as e:  # noqa: BLE001
                    print(f"handle: {type(e).__name__}: {e}", flush=True)
            bot.active_subs()                     # муддати тугаган ҳомийни ўзи олиб ташлайди
        except Exception as e:  # noqa: BLE001
            print(f"poll: {type(e).__name__}: {e}", flush=True)
            time.sleep(5)
