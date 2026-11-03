#!/usr/bin/env python3
"""«🕌 Намоз маркази» (03.11.2026), Лондон: берёт время намаза у PAPA (шлюз Франкфурта, /api/runner/namaz — токен
исполнителя, только чтение) и записывает его туда, откуда его читает бот XOJAOBOD CITY 24 (prayer_schedules, confirmed=1).
Пишет только если время изменилось; перед первой записью — копия базы. Код бота не трогает.
"""
import datetime as dt
import json
import os
import shutil
import sqlite3
import ssl
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from papa_runner import TailnetHTTPS  # noqa: E402

NAMES = ("bomdod", "peshin", "asr", "shom", "xufton")
BK = Path("/opt/xojaobodcity24bot/deploy-backups")


def fetch(url: str, addr: str, token: str) -> list[dict]:
    host = url[len("https://"):].split("/", 1)[0]
    h, _, port = host.partition(":")
    c = TailnetHTTPS(h, addr, int(port or 443), ssl.create_default_context())
    try:
        c.request("GET", "/api/runner/namaz", headers={"Authorization": "Bearer " + token, "X-Device-ID": "london-runner"})
        r = c.getresponse()
        body = r.read(262144)
        if r.status != 200:
            raise RuntimeError(f"http_{r.status}")
        return json.loads(body)["schedule"]
    finally:
        c.close()


def city24_db() -> Path:
    out = subprocess.run(["sudo", "-u", "xojaobodbot", "/opt/xojaobodcity24bot/venv/bin/python", "-c",
                          "import os;os.environ.setdefault('BOT_TOKEN','0:x');from bot.handlers import prayer as P;print(P.GENPLAN_PRAYER_DB)"],
                         cwd="/opt/xojaobodcity24bot/app", capture_output=True, text=True, timeout=60)
    return Path(out.stdout.strip())


def apply(db_path: Path, schedule: list[dict], backup_dir: Path | None = BK) -> list[str]:
    ok = lambda t: isinstance(t, str) and len(t) == 5 and t[2] == ":" and t[:2].isdigit() and t[3:].isdigit()
    since = (dt.date.today() - dt.timedelta(days=21)).isoformat()
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    cols = db.execute("PRAGMA table_info(prayer_schedules)").fetchall()
    changed, backed = [], False
    for s in schedule:
        day = s.get("day", "")
        if day < since and s is not schedule[-1]:
            continue
        if not all(ok(s.get(n)) for n in NAMES):
            continue
        cur = db.execute(f"SELECT {', '.join(NAMES)} FROM prayer_schedules WHERE confirmed=1 AND effective_date=? "
                         "ORDER BY id DESC LIMIT 1", (day,)).fetchone()
        if cur and all(cur[n] == s[n] for n in NAMES):
            continue
        if backup_dir and not backed:
            backup_dir.mkdir(parents=True, exist_ok=True)
            f = backup_dir / f"namaz-{dt.datetime.now():%Y%m%d-%H%M%S}.db"
            shutil.copy2(db_path, f)
            (backup_dir / "namaz-LAST").write_text(str(f) + "\n")
            backed = True
        now = dt.datetime.now().isoformat(timespec="seconds")
        val = {"effective_date": day, "valid_until": None, "confirmed": 1, **{n: s[n] for n in NAMES}}
        for c in cols:
            n = c["name"]
            if n in val or c["pk"]:
                continue
            if c["notnull"] and c["dflt_value"] is None:
                val[n] = now if any(k in n.lower() for k in ("at", "time", "date")) else ("papa-namaz-markazi" if str(c["type"]).upper().startswith("TEXT") else 0)
            elif n == "source":
                val[n] = "papa-namaz-markazi"
        keys = list(val)
        db.execute(f"INSERT INTO prayer_schedules ({','.join(keys)}) VALUES ({','.join('?' * len(keys))})", [val[k] for k in keys])
        changed.append(f"{day}: " + " ".join(s[n] for n in NAMES))
    db.commit()
    db.close()
    return changed


def main() -> int:
    url, token = os.getenv("NEXUS_GATEWAY_URL", "").rstrip("/"), os.getenv("PAPA_RUNNER_TOKEN", "")
    if not url.startswith("https://") or len(token) < 32:
        print("нет NEXUS_GATEWAY_URL / PAPA_RUNNER_TOKEN"); return 2
    sched = fetch(url, os.getenv("NEXUS_GATEWAY_ADDR", ""), token)
    ch = apply(city24_db(), sched)
    print("намоз: " + ("обновлено → " + "; ".join(ch) if ch else "без изменений"), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
