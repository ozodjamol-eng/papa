"""🛡 Страж рекламы GENPLAN 5 (Лондон, до перевода Хўжаобода на PAPA). Только чтение базы.
Каждые 10 минут 06:00–23:00: (1) две активные кампании на одно время — одна будет пропущена;
(2) рекламный пост сегодня пропущен/с ошибкой/время прошло, а не вышел. Тревога — владельцу от бота GENPLAN 5,
один раз на каждую беду (без спама). Стандартная библиотека Python."""
from __future__ import annotations

import datetime as dt
import json
import re
import sqlite3
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

G = Path("/opt/xojaobod-genplan-v5")
DB = G / "data/genplan_v3_production.db"
ENV = G / ".env.production"
STATE = Path("/var/lib/papa-genplan5-guard/state.json")


def env_token(path: Path = ENV) -> str:
    vals = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("BOT_TOKEN", "TELEGRAM_BOT_TOKEN", "GENPLAN_BOT_TOKEN", "TG_BOT_TOKEN"):
        if vals.get(k):
            return vals[k]
    return next((v for k, v in vals.items() if "TOKEN" in k and re.fullmatch(r"\d{6,12}:[\w-]{30,}", v)), "")


def check(db, now: dt.datetime) -> list[tuple[str, str]]:
    """[(ключ, текст)] — беды на сейчас. now — местное время Ташкента (как в базе)."""
    out = []
    today = now.date().isoformat()
    by_slot = defaultdict(list)
    for r in db.execute("SELECT id, name, slot_time FROM campaigns WHERE active=1 AND deleted_at IS NULL AND coalesce(slot_time,'')<>''"):
        by_slot[r["slot_time"]].append(r)
    for slot, rows in by_slot.items():
        if len(rows) > 1:
            names = ", ".join(f"«{r['name']}»" for r in rows)
            out.append((f"clash:{today}:{slot}:{'-'.join(str(r['id']) for r in rows)}",
                        f"🚨 РЕКЛАМА Хўжаобод (GENPLAN 5): {names} стоят на одно время {slot} — выйдет только одна, "
                        "остальные будут пропущены! Разведите по времени."))
    late = (now - dt.timedelta(minutes=7)).strftime("%Y-%m-%dT%H:%M:%S")
    for r in db.execute("SELECT p.id, p.status, p.scheduled_at, p.last_error, c.name FROM scheduled_posts p "
                        "LEFT JOIN campaigns c ON p.slot_key = 'campaign_' || c.id || '_' || substr(p.scheduled_at,1,10) "
                        "WHERE p.rubric='ad' AND substr(p.scheduled_at,1,10)=? AND "
                        "(p.status IN ('skipped','failed') OR (p.status='pending' AND p.scheduled_at < ?))", (today, late)):
        what = {"skipped": "ПРОПУЩЕНА системой", "failed": "не вышла (ошибка)"}.get(r["status"], "время прошло — не вышла")
        out.append((f"ad:{r['id']}:{r['status']}",
                    f"🚨 РЕКЛАМА Хўжаобод (GENPLAN 5) «{r['name'] or 'без имени'}» {r['scheduled_at'][11:16]} — {what}"
                    + (f": {(r['last_error'] or '')[:120]}" if r["last_error"] else "") + ". Опубликуйте вручную или скажите мне."))
    return out


def tg(token: str, method: str, **p) -> dict:
    data = urllib.parse.urlencode(p).encode()
    try:
        with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/{method}", data=data, timeout=20) as r:
            return json.loads(r.read())
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "description": type(e).__name__}


def main(send: bool = True) -> int:
    now = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=5)).replace(tzinfo=None)
    db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=15)
    db.row_factory = sqlite3.Row
    problems = check(db, now)
    owners = [str(r[0]) for r in db.execute("SELECT user_id FROM users WHERE active=1")]
    db.close()
    try:
        state = json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    new = [(k, t) for k, t in problems if k not in state]
    for k, t in problems:
        print(t)
    if not problems:
        print("страж GENPLAN 5: реклама в порядке")
    if send and new:
        tok = env_token()
        text = "\n\n".join(t for _, t in new)[:4000]
        sent = any(tg(tok, "sendMessage", chat_id=o, text=text).get("ok") for o in owners) if tok else False
        print("тревога отправлена владельцу" if sent else "НЕ СМОГ ОТПРАВИТЬ ТРЕВОГУ (бот/владелец)")
        if sent:
            for k, _ in new:
                state[k] = now.isoformat()
    cut = (now - dt.timedelta(days=3)).isoformat()
    state = {k: v for k, v in state.items() if v >= cut}
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main("--no-send" not in sys.argv))
