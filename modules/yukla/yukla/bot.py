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
"""
LINK_RE = re.compile(r"https?://[^\s]+", re.I)
PLATFORMS = (("instagram", re.compile(r"(?:^|\.)instagram\.com$")), ("tiktok", re.compile(r"(?:^|\.)tiktok\.com$")),
             ("youtube", re.compile(r"(?:^|\.)(?:youtube\.com|youtu\.be)$")))


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
    db.commit()
    return db


def owner_kb() -> dict:
    return {"keyboard": [[{"text": T.O_STATS}, {"text": T.O_AD}], [{"text": T.O_SEND}]], "resize_keyboard": True}


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
            cmd += ["-f", "best[ext=mp4][filesize<49M]/bv*[ext=mp4]+ba[ext=m4a]/best[filesize<49M]/best",
                    "--merge-output-format", "mp4"]
        try:
            subprocess.run(cmd + [url], timeout=150, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                           stderr=subprocess.PIPE, check=False)
        except subprocess.TimeoutExpired:
            return None
        files = [f for f in out.iterdir() if f.is_file() and not f.name.endswith(".part")]
        return max(files, key=lambda f: f.stat().st_size) if files else None


class Bot:
    def __init__(self, db, api, owners: list[int], username: str = "XojaobodYuklaBot", sub_chat: str | None = "@xojaobodcity24",
                 downloader: Downloader | None = None, upload=None, workers: int = 2, sync: bool = False):
        self.db, self.api, self.owners, self.username, self.sub_chat = db, api, owners, username, sub_chat
        self.dl = downloader or Downloader()
        self.upload = upload                  # upload(method, chat, field, path, caption, kb) -> message dict
        self.lock = threading.RLock()
        self.busy: set[int] = set()
        self.sync = sync                      # тестда — навбатсиз, дарҳол
        self.pool = None if sync else ThreadPoolExecutor(max_workers=workers)
        self.sub_title = None

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

    def say(self, chat: int, text: str, kb: dict | None = None):
        if kb is None and chat in self.owners:
            kb = owner_kb()
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

    def subscribed(self, uid: int) -> bool:
        if not self.sub_chat or uid in self.owners:
            return True
        try:
            m = self.api("getChatMember", chat_id=self.sub_chat, user_id=uid)
            return m.get("status") in ("member", "administrator", "creator", "restricted")
        except Exception as e:  # noqa: BLE001 — бот админ бўлмаса: текширмасдан ўтказамиз, владелецга бир марта айтамиз
            if not self.kv("sub_warned"):
                self.kv("sub_warned", now())
                for o in self.owners:
                    self.say(o, T.O_SUB_WARN.format(err=esc(str(e)[:80])))
            return True

    def sub_link(self) -> str:
        return f"https://t.me/{self.sub_chat.lstrip('@')}" if self.sub_chat and self.sub_chat.startswith("@") else ""

    def row_id(self, key: str, url: str) -> int:
        self.q("INSERT OR IGNORE INTO cache(key, url, kind, created) VALUES (?,?,?,?)", (key, url, platform_of(url), now()))
        return self.q("SELECT rowid FROM cache WHERE key=?", (key,), one=True)[0]

    def media_kb(self, rid: int) -> dict:
        row = [{"text": T.MP3_BTN, "callback_data": f"a:{rid}"}]   # callback_data ≤ 64 байт — калит эмас, рақам
        if self.sub_link():
            row.append({"text": T.CHANNEL_BTN, "url": self.sub_link()})
        return {"inline_keyboard": [row]}

    def caption(self) -> str:
        ad = self.kv("ad") or ""
        return T.CAPTION.format(bot=self.username) + (f"\n\n{ad}" if ad else "")

    # ---------- кириш ----------
    def handle(self, upd: dict) -> str | None:
        if "callback_query" in upd:
            return self.callback(upd["callback_query"])
        m = upd.get("message")
        if not m or m["chat"]["type"] != "private":
            return None
        frm, chat = m["from"], m["chat"]["id"]
        text = (m.get("text") or m.get("caption") or "").strip()
        self.seen(frm)
        if frm["id"] in self.owners:
            r = self.owner(frm, chat, m, text)
            if r:
                return r
        if text.startswith("/start"):
            self.say(chat, T.START)
            return "start"
        link = LINK_RE.search(text)
        if not link or not platform_of(link.group()):
            self.say(chat, T.BAD_LINK)
            return "bad"
        url = link.group().rstrip(").,")
        if not self.subscribed(frm["id"]):
            self.kv(f"pending:{frm['id']}", url)
            kb = {"inline_keyboard": [[{"text": T.SUB_BTN, "url": self.sub_link()}],
                                      [{"text": T.CHECK_BTN, "callback_data": "chk"}]]}
            self.say(chat, T.NEED_SUB.format(title=esc(self.sub_chat)), kb)
            return "need_sub"
        return self.start_job(frm["id"], chat, url)

    def start_job(self, uid: int, chat: int, url: str) -> str:
        key = norm_key(url)
        hit = self.q("SELECT * FROM cache WHERE key=? AND video IS NOT NULL", (key,), one=True)
        if hit:                                   # хотирадан — дарҳол
            self.q("UPDATE cache SET hits=hits+1 WHERE key=?", (key,))
            self.api("sendVideo", chat_id=chat, video=hit["video"], caption=self.caption(), parse_mode="HTML",
                     reply_markup=self.media_kb(self.row_id(key, url)))
            self.q("INSERT INTO log(uid, platform, result, ts) VALUES (?,?,?,?)", (uid, platform_of(url), "cache", now()))
            return "cache"
        with self.lock:
            if uid in self.busy:
                self.say(chat, T.BUSY)
                return "busy"
            self.busy.add(uid)
        wait = self.say(chat, T.WAIT) or {}
        self.submit(self.job, uid, chat, url, key, wait.get("message_id"))
        return "job"

    def job(self, uid: int, chat: int, url: str, key: str, wait_id):
        res = "fail"
        try:
            f = self.dl.fetch(url)
            if f and f.stat().st_size > MAX_BYTES:
                self.say(chat, T.TOO_BIG); res = "big"
            elif f:
                msg = self.upload("sendVideo", chat, "video", f, self.caption(), self.media_kb(self.row_id(key, url))) or {}
                fid = (msg.get("video") or msg.get("document") or {}).get("file_id")
                if fid:
                    self.q("UPDATE cache SET video=? WHERE key=?", (fid, key))
                res = "ok"
            else:
                self.say(chat, T.FAIL)
        finally:
            with self.lock:
                self.busy.discard(uid)
            if wait_id:
                try:
                    self.api("deleteMessage", chat_id=chat, message_id=wait_id)
                except Exception:  # noqa: BLE001
                    pass
            self.q("INSERT INTO log(uid, platform, result, ts) VALUES (?,?,?,?)", (uid, platform_of(url), res, now()))

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
        data, uid = cq.get("data") or "", cq["from"]["id"]
        chat = cq["message"]["chat"]["id"] if cq.get("message") else uid
        if data == "chk":
            if not self.subscribed(uid):
                self.api("answerCallbackQuery", callback_query_id=cq["id"], text=T.NOT_YET, show_alert=True)
                return "not_yet"
            self.api("answerCallbackQuery", callback_query_id=cq["id"], text="✅")
            url = self.kv(f"pending:{uid}")
            return self.start_job(uid, chat, url) if url else "ok"
        if data.startswith("a:"):
            self.api("answerCallbackQuery", callback_query_id=cq["id"], text="🎵")
            self.submit(self.audio_job, chat, data[2:])
            return "mp3"
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


def main():
    tok = os.environ["YUKLA_BOT_TOKEN"]
    api = make_api(tok)
    owners = [int(x) for x in os.environ.get("OWNER_IDS", "").split(",") if x.strip()]
    try:
        uname = api("getMe")["username"]
    except Exception:  # noqa: BLE001
        uname = "XojaobodYuklaBot"
    dl = Downloader(os.environ.get("YUKLA_YTDLP", "yt-dlp"), os.environ.get("YUKLA_PROXY") or None)
    bot = Bot(connect(os.environ.get("YUKLA_DB", "yukla.sqlite3")), api, owners, uname,
              os.environ.get("YUKLA_SUB_CHAT", "@xojaobodcity24") or None, dl, make_upload(tok))
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
        except Exception as e:  # noqa: BLE001
            print(f"poll: {type(e).__name__}: {e}", flush=True)
            time.sleep(5)
