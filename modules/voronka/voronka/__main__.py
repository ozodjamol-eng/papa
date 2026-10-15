"""PAPA Voronka.
  python -m voronka status        — токен, посты под наблюдением, статистика
  python -m voronka poll          — один проход по комментариям Instagram
  python -m voronka bot           — один проход по заявкам Telegram
  python -m voronka loop          — постоянная работа (для службы)
  python -m voronka refresh       — продлить токен Instagram (60 дней)
  python -m voronka invite NAME   — создать ссылку-приглашение с заявкой в каждый канал
"""
from __future__ import annotations

import datetime as dt
import os
import sys
import time
import tomllib
from pathlib import Path

from . import engine, joins, store
from .api import ApiError, Bot, Instagram

CONFIG = Path(os.environ.get("PAPA_VORONKA_CONFIG", Path(__file__).resolve().parent.parent / "config.toml"))
DB = os.environ.get("PAPA_VORONKA_DB", "/var/lib/papa-voronka/voronka.sqlite3")
IG_ENV = Path(os.environ.get("PAPA_VORONKA_IG_ENV", "/etc/papa-voronka/instagram.env"))


def cfg() -> dict:
    c = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
    c["dm_text"] = c["dm_text"].replace("{page}", c.get("page_url", ""))
    return c


def read_env(p: Path) -> dict:
    return dict(l.split("=", 1) for l in p.read_text().splitlines() if "=" in l and not l.startswith("#"))


def ig() -> Instagram:
    e = read_env(IG_ENV)
    return Instagram(e["IG_TOKEN"], e["IG_USER_ID"])


def bot() -> Bot:
    t = os.environ.get("VORONKA_BOT_TOKEN") or os.environ.get("PAPA_TEST_BOT_TOKEN")
    if not t:
        raise SystemExit("NO_BOT_TOKEN (VORONKA_BOT_TOKEN)")
    return Bot(t)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def refresh(db) -> None:
    r = ig().refresh_token()
    e = read_env(IG_ENV)
    e["IG_TOKEN"] = r["access_token"]
    tmp = IG_ENV.with_suffix(".tmp")
    old = os.umask(0o077)
    try:
        tmp.write_text("".join(f"{k}={v}\n" for k, v in e.items()))
    finally:
        os.umask(old)
    os.replace(tmp, IG_ENV)
    store.kv_set(db, "token_refreshed", now_iso())
    print(f"токен продлён на {int(r.get('expires_in', 0)) // 86400} дн.")


def status(db, c: dict) -> None:
    i = ig()
    print(f"режим: {'ПРОВЕРКА (ничего не отправляет)' if c.get('dry_run', True) else 'РАБОТА'}; "
          f"ответ: {'всем' if c.get('mode') == 'all' else 'по словам ' + ', '.join(c.get('keywords', []))}; "
          f"предел {c.get('max_per_hour')}/час")
    media = engine.target_media(i, c, engine.utcnow())
    print(f"постов под наблюдением: {len(media)}")
    for m in media:
        print(f"  {m['timestamp'][:16]}  комментариев {m.get('comments_count')}  {m.get('permalink')}")
    for row in db.execute("SELECT action, COUNT(*) n FROM comments GROUP BY action ORDER BY n DESC"):
        print(f"  {row['action']}: {row['n']}")
    n = db.execute("SELECT COUNT(*), SUM(welcomed), SUM(approved) FROM joins").fetchone()
    print(f"заявок в Telegram: {n[0]} (приветствий {n[1] or 0}, одобрено {n[2] or 0})")
    print(f"токен продлевался: {store.kv_get(db, 'token_refreshed', 'ещё нет')}")
    print(f"последний проход: {store.kv_get(db, 'last_run', 'ещё не было')}")
    for m in media:  # что видит API (без токенов)
        for cm in i.comments(m["id"], limit=10):
            u = cm.get("from") or {}
            print(f"  комментарий {cm['id']} от @{u.get('username')} (id {u.get('id')}): {(cm.get('text') or '')[:30]!r}")
    for row in db.execute("SELECT at, username, action, detail FROM comments ORDER BY at DESC LIMIT 5"):
        print(f"  {row['at'][:19]} @{row['username']} {row['action']} {row['detail'] or ''}")


def loop(db, c: dict) -> None:
    b = bot() if c.get("channels") else None
    next_ig = 0.0
    while True:
        if time.time() >= next_ig:
            try:
                last = store.kv_get(db, "token_refreshed")
                if not last:  # новый токен: продлевать можно не раньше чем через сутки
                    store.kv_set(db, "token_refreshed", now_iso())
                elif dt.datetime.fromisoformat(last) < dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7):
                    refresh(db)
                s = engine.run_once(ig(), db, cfg())
                if s["new"] or s["error"]:
                    print(f"IG: {s}", flush=True)
            except (ApiError, OSError) as e:
                print(f"IG ошибка: {e}", flush=True)
            next_ig = time.time() + int(c.get("poll_seconds", 120))
        if b:
            try:
                joins.poll_once(b, db, cfg(), now_iso(), timeout=min(25, int(c.get("poll_seconds", 120))))
            except (ApiError, OSError) as e:
                print(f"TG ошибка: {e}", flush=True)
                time.sleep(10)
        else:
            time.sleep(5)


def main(argv: list[str]) -> None:
    cmd = argv[0] if argv else "status"
    c = cfg()
    db = store.connect(DB)
    if cmd == "status":
        status(db, c)
    elif cmd == "poll":
        print(engine.run_once(ig(), db, c))
    elif cmd == "bot":
        print(f"обработано: {joins.poll_once(bot(), db, c, now_iso(), timeout=5)}")
    elif cmd == "loop":
        loop(db, c)
    elif cmd == "refresh":
        refresh(db)
    elif cmd == "invite" and len(argv) > 1:
        b = bot()
        for ch in c.get("channels", []):
            print(f"{ch.get('title')}: {joins.make_invite(b, ch['chat_id'], argv[1])}")
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
