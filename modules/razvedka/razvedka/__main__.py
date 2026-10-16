"""PAPA Razvedka.
  python -m razvedka login            — вход в Telegram (интерактивно, на сервере)
  python -m razvedka collect          — собрать посты
  python -m razvedka report [--send]  — отчёт в консоль (и в «Избранное» аккаунта с --send)
  python -m razvedka send             — отчёт в консоль и в «Избранное» аккаунта
  python -m razvedka run              — collect + send (для ежедневного таймера)
  python -m razvedka publish          — только обновить отчёт для Pult (без отправки в Telegram)
  python -m razvedka curate           — агент-куратор: лучшее из папок PAPA·… → карточки в пульты каналов
  python -m razvedka hunt             — найти утренние видео («Жума тонги»…) для утреннего блока GENPLAN
"""
from __future__ import annotations

import asyncio
import getpass
import os
import sys
import tomllib
from pathlib import Path

from . import analyze, report, store

CONFIG = Path(os.environ.get("PAPA_RAZVEDKA_CONFIG", Path(__file__).resolve().parent.parent / "config.toml"))
DB = os.environ.get("PAPA_RAZVEDKA_DB", "/var/lib/papa-razvedka/razvedka.sqlite3")
PUB = os.environ.get("PAPA_RAZVEDKA_PUB", "/var/lib/papa-razvedka-pub")


def build() -> tuple[str, dict]:
    a = analyze.analyze(store.connect(DB), int(cfg().get("report_days", 7)))
    return report.render(a), a


def publish(text: str, a: dict, pub_dir: str | None = None) -> str | None:
    """Отчёт для Pult (ChatGPT/Claude): latest.json в общем каталоге, без секретов."""
    import json
    d = Path(pub_dir or PUB)
    if not d.is_dir():
        return None
    data = {
        "generated": a["generated"], "days": a["days"], "posts_total": a["posts_total"],
        "channels_total": len(a["channels"]),
        "best_hours": sorted([h for h in a["hours"] if h["strength"] is not None],
                             key=lambda h: h["strength"], reverse=True)[:5],
        "top_channels": [{k: c[k] for k in ("title", "username", "folder", "is_own", "subscribers",
                                             "median_views", "err", "per_day", "ads_per_day")}
                         for c in a["channels"][:15]],
        "text": text[:15000],
    }
    tmp = d / ".latest.json.tmp"
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.chmod(tmp, 0o640)
    os.replace(tmp, d / "latest.json")
    return str(d / "latest.json")


def cfg() -> dict:
    return tomllib.loads(CONFIG.read_text(encoding="utf-8"))


async def _login(env_out: str) -> None:
    from telethon import TelegramClient
    from telethon.errors import SessionPasswordNeededError
    from telethon.sessions import StringSession
    print("Ключи берутся на https://my.telegram.org → API development tools.")
    api_id = int(input("api_id: ").strip())
    api_hash = getpass.getpass("api_hash (не отображается): ").strip()
    phone = input("номер телефона аккаунта (+998...): ").strip()
    c = TelegramClient(StringSession(), api_id, api_hash, device_model="PAPA Razvedka",
                       app_version="1.0", system_version="Linux")
    await c.connect()
    await c.send_code_request(phone)
    code = input("код из Telegram: ").strip()
    try:
        await c.sign_in(phone=phone, code=code)
    except SessionPasswordNeededError:
        await c.sign_in(password=getpass.getpass("облачный пароль Telegram (не отображается): "))
    me = await c.get_me()
    session = c.session.save()
    await c.disconnect()
    old = os.umask(0o077)
    try:
        Path(env_out).parent.mkdir(parents=True, exist_ok=True)
        Path(env_out).write_text(f"PAPA_TG_API_ID={api_id}\nPAPA_TG_API_HASH={api_hash}\nPAPA_TG_SESSION={session}\n")
    finally:
        os.umask(old)
    os.chmod(env_out, 0o600)
    print(f"LOGIN_OK: {me.first_name or ''} (id {me.id}). Сессия сохранена в {env_out}.")


async def _collect() -> dict:
    from .collect import collect
    from .telegram import TelethonSource, client_from_env
    db = store.connect(DB)
    c = client_from_env()
    await c.connect()
    if not await c.is_user_authorized():
        raise SystemExit("NOT_AUTHORIZED: выполните login")
    try:
        return await collect(TelethonSource(c), db, cfg())
    finally:
        await c.disconnect()


async def _send(text: str) -> None:
    from .telegram import client_from_env, send_report
    c = client_from_env()
    await c.connect()
    try:
        await send_report(c, text)
    finally:
        await c.disconnect()


async def _hunt() -> dict:
    from .hunt import hunt
    from .telegram import client_from_env
    c = client_from_env()
    await c.connect()
    if not await c.is_user_authorized():
        raise SystemExit("NOT_AUTHORIZED: выполните login")
    try:
        return await hunt(c, cfg(), Path(PUB) / "morning", log=lambda s: print(s, flush=True))
    finally:
        await c.disconnect()


async def _pool_latest() -> dict:
    """Последний пост с медиа в NEXUS MORNING POOL (то, что владелец положил вручную) → pub/morning/latest.json."""
    import json
    from .hunt import POOL_TITLES
    from .telegram import client_from_env
    c = client_from_env()
    await c.connect()
    try:
        async for d in c.iter_dialogs():
            if d.is_channel and any(t in (d.title or "").lower() for t in POOL_TITLES):
                async for m in c.iter_messages(d.entity, limit=20):
                    if m.media and not m.action:
                        out = {"pool_chat": int(f"-100{d.entity.id}"), "msg_id": m.id, "text": m.message or "",
                               "date": m.date.isoformat()}
                        p = Path(PUB) / "morning" / "latest.json"
                        p.parent.mkdir(parents=True, exist_ok=True)
                        p.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
                        return {"msg_id": m.id, "date": out["date"], "text": out["text"][:60]}
        raise SystemExit("NEXUS MORNING POOL не найден")
    finally:
        await c.disconnect()


async def _sklad_latest(n: int = 3) -> dict:
    """Последние n постов с медиа в PAPA СКЛАД (подготовил владелец) → pub/morning/sklad.json, по порядку (старый первым)."""
    import json
    from .telegram import client_from_env
    c = client_from_env()
    await c.connect()
    try:
        async for d in c.iter_dialogs():
            if d.is_channel and "papa склад" in (d.title or "").lower():
                items = []
                async for m in c.iter_messages(d.entity, limit=30):
                    if m.media and not m.action:
                        items.append({"chat": int(f"-100{d.entity.id}"), "msg_id": m.id, "text": m.message or "",
                                      "date": m.date.isoformat()})
                        if len(items) >= n:
                            break
                items.reverse()
                p = Path(PUB) / "morning" / "sklad.json"
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
                return {"items": [(i["msg_id"], i["text"][:40]) for i in items]}
        raise SystemExit("PAPA СКЛАД не найден")
    finally:
        await c.disconnect()


async def _sort_folders() -> dict:
    from .sortfolders import run
    from .telegram import client_from_env
    c = client_from_env()
    await c.connect()
    if not await c.is_user_authorized():
        raise SystemExit("NOT_AUTHORIZED")
    try:
        return await run(c, Path(PUB) / "morning", log=lambda s: print(s, flush=True))
    finally:
        await c.disconnect()


async def _curate() -> dict:
    import subprocess
    busy = [u for u in ("hunt", "collect", "run") if subprocess.run(
        ["systemctl", "is-active", "-q", f"papa-razvedka@{u}.service"]).returncode == 0]
    if busy:                                   # один профиль — одна задача за раз
        return {"пропуск": f"профиль занят: {', '.join(busy)}"}
    from .curate import run
    from .telegram import client_from_env
    c = client_from_env()
    await c.connect()
    if not await c.is_user_authorized():
        raise SystemExit("NOT_AUTHORIZED")
    try:
        return await run(c, Path(PUB) / "curator", log=lambda s: print(s, flush=True))
    finally:
        await c.disconnect()


def main(argv: list[str]) -> None:
    cmd = argv[0] if argv else "report"
    if cmd == "curate":
        print("CURATE_DONE", asyncio.run(_curate()))
        return
    if cmd == "sort-folders":
        print("FOLDERS_DONE", asyncio.run(_sort_folders()))
        return
    if cmd == "sklad-latest":
        print("SKLAD_LATEST", asyncio.run(_sklad_latest()))
        return
    if cmd == "pool-latest":
        print("POOL_LATEST", asyncio.run(_pool_latest()))
        return
    if cmd == "hunt":
        print("HUNT_DONE", asyncio.run(_hunt()))
        return
    if cmd == "login":
        asyncio.run(_login(argv[1] if len(argv) > 1 else "/etc/papa-razvedka/telegram.env"))
    elif cmd in ("collect", "run"):
        s = asyncio.run(_collect())
        print(f"COLLECT_DONE каналов={s['channels']} постов={s['posts']} ошибок={len(s['errors'])}")
        if cmd == "run":
            text, a = build()
            print("PUBLISHED", publish(text, a))
            asyncio.run(_send(text))
            print("REPORT_SENT")
    elif cmd == "publish":
        text, a = build()
        print("PUBLISHED", publish(text, a))
    elif cmd == "send":
        argv = ["report", "--send"]
        main(argv)
    elif cmd == "report":
        text, a = build()
        print(text)
        print("PUBLISHED", publish(text, a))
        if "--send" in argv:
            asyncio.run(_send(text))
            print("REPORT_SENT")
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv[1:])
