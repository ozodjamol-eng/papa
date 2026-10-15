"""Fabrika — обработчик заданий (отдельная служба papa-fabrika, чтобы тяжёлая работа не тормозила бота).

link: ссылка Instagram / TikTok / YouTube Shorts →
      1) скачать видео и оригинальный текст (yt-dlp);
      2) наложить логотип канала (постоянная метка + плывущий логотип);
      3) переписать текст ИИ (если есть ключ), иначе — оригинал;
      4) положить в PAPA HUB, показать владельцу готовое видео и карточку (рубрика / срочно / в запас).
ai:   переписать текст существующего материала ИИ и прислать новую карточку."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
import uuid
import urllib.request
from pathlib import Path

from . import ai, hub, media, store

LINK = re.compile(r"https?://(?:www\.|m\.|vm\.|vt\.)?(?:instagram\.com/(?:reel|reels|p|tv)/|tiktok\.com/|"
                  r"youtube\.com/shorts/|youtu\.be/|facebook\.com/(?:reel|watch)|fb\.watch/)\S+", re.I)
STATE = Path(os.environ.get("PAPA_GENPLAN_STATE", "/var/lib/papa-genplan"))
MAX_UPLOAD = 49 * 1024 * 1024


def find_link(text: str) -> str | None:
    m = LINK.search(text or "")
    return m.group(0).rstrip(").,") if m else None


def logo_path(channel: str, root: Path = STATE) -> Path:
    return root / f"logo-{channel}.png"


def download(url: str, work: Path) -> tuple[Path, str]:
    work.mkdir(parents=True, exist_ok=True)
    cmd = ["yt-dlp", "--no-playlist", "--no-progress", "--no-warnings", "--max-filesize", "300M",
           "-f", "bv*[height<=1280][ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b", "--merge-output-format", "mp4",
           "--write-info-json", "-o", str(work / "src.%(ext)s"), url]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    vids = [p for p in work.glob("src.*") if p.suffix in (".mp4", ".mkv", ".webm", ".mov")]
    if r.returncode != 0 or not vids:
        err = (r.stderr or r.stdout or "").strip().splitlines()[-1:] or ["неизвестная ошибка"]
        raise RuntimeError(f"не удалось скачать: {err[0][:200]}")
    info = {}
    for j in work.glob("src*.info.json"):
        info = json.loads(j.read_text(encoding="utf-8"))
    return vids[0], (info.get("description") or info.get("title") or "").strip()


def upload_video(token: str, chat: int, path: Path, caption: str) -> dict:
    boundary = uuid.uuid4().hex
    parts = []
    for k, v in (("chat_id", str(chat)), ("caption", caption[:1024]), ("supports_streaming", "true")):
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="video"; filename="video.mp4"\r\n'
                 f"Content-Type: video/mp4\r\n\r\n".encode() + path.read_bytes() + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendVideo", data=b"".join(parts),
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.loads(r.read())
    if not data.get("ok"):
        raise RuntimeError(f"Telegram: {data.get('description')}")
    return data["result"]


def process_link(bot, db, cfg: dict, env: dict, p: dict, work_root: Path = STATE / "work") -> str:
    owner = int(p["owner_chat"])
    channel = p.get("channel") or cfg.get("default_channel") or next(iter(cfg["channels"]))
    ch = cfg["channels"][channel]
    work = work_root / uuid.uuid4().hex[:10]
    notes = []
    try:
        src, original = download(p["url"], work)
        mark = ch.get("watermark") or "@" + ch["username"]            # водяной знак — @юзернейм канала
        logo = media.text_logo(mark, work / "wm.png")
        out = media.watermark_video(src, logo, work / "out.mp4")
        if out.stat().st_size > MAX_UPLOAD:
            out = media.watermark_video(src, logo, work / "out2.mp4", crf=30)
        if out.stat().st_size > MAX_UPLOAD:
            raise RuntimeError("видео больше 50 МБ даже после сжатия")
        text = original
        if ai.available():
            try:
                text = ai.rewrite(db, original, ch["title"])
                notes.append("🤖 Текст переписан ИИ — проверьте")
            except ai.AIError as e:
                notes.append(f"🤖 ИИ: {e} — оставлен оригинал")
        hub_chat = int(env["HUB_CHAT_ID"])
        res = upload_video(env["GENPLAN_BOT_TOKEN"], hub_chat, out, text)
        v = res.get("video") or res.get("document") or {}
        shown = bot("copyMessage", chat_id=owner, from_chat_id=hub_chat, message_id=res["message_id"])
        msg = {"message_id": shown["message_id"], "caption": text,
               "video": {"file_id": v.get("file_id"), "file_unique_id": v.get("file_unique_id")}}
        hub.intake(bot, db, cfg, {owner}, hub_chat, [res["message_id"]], [msg], reply_chat=owner, notes=notes)
        return "ok"
    finally:
        shutil.rmtree(work, ignore_errors=True)


def process_ai(bot, db, cfg: dict, p: dict) -> str:
    m = store.get(db, int(p["mid"]))
    text = ai.rewrite(db, m["text"], cfg["channels"][m["channel"]]["title"])
    store.update(db, m["id"], text=text)
    t, kb = hub.card(db, cfg, m["id"])
    r = bot("sendMessage", chat_id=int(p["owner_chat"]), text="🤖 Текст переписан ИИ — проверьте:\n\n" + t,
            reply_markup=kb, disable_web_page_preview=True)
    store.update(db, m["id"], owner_msg=r["message_id"])
    return "ok"


def run_once(bot, db, cfg: dict, env: dict) -> bool:
    j = store.job_take(db)
    if not j:
        return False
    p = json.loads(j["payload"])
    try:
        (process_link(bot, db, cfg, env, p) if j["kind"] == "link" else process_ai(bot, db, cfg, p))
        store.job_done(db, j["id"])
    except Exception as e:  # noqa: BLE001 — любая ошибка → владельцу понятным текстом
        store.job_done(db, j["id"], str(e)[:300])
        try:
            bot("sendMessage", chat_id=int(p["owner_chat"]), text=f"❌ Fabrika: {e}"[:1000])
        except Exception:  # noqa: BLE001
            pass
    return True


def loop(bot, db, cfg_fn, env: dict) -> None:
    (STATE / "work").mkdir(parents=True, exist_ok=True)
    print("FABRIKA запущена", flush=True)
    while True:
        if not run_once(bot, db, cfg_fn(), env):
            time.sleep(3)
