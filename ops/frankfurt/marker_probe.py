"""🏷 Маркировщик — ПРОБА (01.11). В каналы ничего не публикует.
Берёт посты из очереди каждого канала, решает «метить или нет» (genplan.marker.decide), на 1 видео + 1 фото
каждого канала рисует нашу метку и присылает владельцу в PAPA ШТАБ: «так будет выглядеть». Плюс сводка по очереди.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import tomllib
import urllib.request
import uuid
from collections import Counter
from pathlib import Path

GP = Path("/opt/papa/modules/genplan")
sys.path.insert(0, str(GP))
from genplan import marker  # noqa: E402

env = dict(os.environ)
cfg = tomllib.loads((GP / "config.toml").read_text(encoding="utf-8"))
db = sqlite3.connect("file:/var/lib/papa-genplan/genplan.sqlite3?mode=ro", uri=True)
db.row_factory = sqlite3.Row
HUB = str(env.get("HUB_CHAT_ID", ""))
SHTAB = env.get("SHTAB_BOT_TOKEN") or env["GENPLAN_BOT_TOKEN"]
OWNERS = [int(x) for x in str(env.get("OWNER_IDS", "")).split(",") if x.strip()]


def api(token: str, method: str, **kw) -> dict:
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/{method}", data=json.dumps(kw).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "description": str(e)}


def send_file(chat: int, path: Path, caption: str, kind: str) -> dict:
    field, method = ("photo", "sendPhoto") if kind == "photo" else ("video", "sendVideo")
    b = uuid.uuid4().hex
    parts = [f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
             for k, v in (("chat_id", chat), ("caption", caption[:1024]), ("supports_streaming", "true"))]
    parts.append(f"--{b}\r\nContent-Disposition: form-data; name=\"{field}\"; filename=\"{path.name}\"\r\n"
                 f"Content-Type: application/octet-stream\r\n\r\n".encode() + path.read_bytes() + b"\r\n")
    parts.append(f"--{b}--\r\n".encode())
    req = urllib.request.Request(f"https://api.telegram.org/bot{SHTAB}/{method}", data=b"".join(parts),
                                 headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())


def token_for(ch: dict, m) -> str:
    via = m["via"] if "via" in m.keys() else None
    if str(m["hub_chat"]) == HUB or not via or via == "main":
        return env["GENPLAN_BOT_TOKEN"]
    c = cfg["channels"].get(via) or {}
    return env.get(c.get("bot_token_env") or "") or env["GENPLAN_BOT_TOKEN"]


summary = []
for code, ch in cfg["channels"].items():
    rows = db.execute("SELECT * FROM materials WHERE channel=? AND status='queued' ORDER BY id DESC LIMIT 200",
                      (code,)).fetchall()
    why = Counter(marker.decide(ch, r)[1] for r in rows)
    summary.append(f"📺 {ch['title']} ({marker.mark_text(ch)}) — в очереди {len(rows)}: "
                   + ", ".join(f"{k} {v}" for k, v in why.most_common()))
    done = set()
    for r in rows:
        kind, _ = marker.decide(ch, r)
        grp = "photo" if kind == "photo" else "video"
        if not kind or grp in done:
            continue
        md = json.loads(r["media"])[0]
        tok = token_for(ch, r)
        info = api(tok, "getFile", file_id=md["file_id"])
        fp = (info.get("result") or {}).get("file_path")
        if not fp:
            print(f"  #{r['id']}: файл не скачать ({info.get('description', 'больше 20 МБ')})")
            continue
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / ("src.jpg" if kind == "photo" else "src.mp4")
            with urllib.request.urlopen(f"https://api.telegram.org/file/bot{tok}/{fp}", timeout=180) as f:
                src.write_bytes(f.read())
            try:
                out = marker.render(kind, src, Path(tmp) / "marked", marker.mark_text(ch))
            except Exception as e:  # noqa: BLE001
                print(f"  #{r['id']}: отрисовка не удалась: {e}")
                continue
            cap = f"🏷 ПРОБА МАРКИРОВКИ · {ch['title']} · пост #{r['id']} ({r['rubric']})\nВ канал НЕ ушло — только показ."
            for o in OWNERS:
                res = send_file(o, out, cap, kind)
                print(f"  #{r['id']} {kind} → владельцу: {'ok' if res.get('ok') else res.get('description')}")
        done.add(grp)
        if len(done) == 2:
            break

text = "🏷 МАРКИРОВЩИК · проба\n\n" + "\n".join(summary)
print(text)
for o in OWNERS:
    api(SHTAB, "sendMessage", chat_id=o, text=text)
print("== MARKER_PROBE_DONE")
