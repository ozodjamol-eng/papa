"""PAPA Razvedka.
  python -m razvedka login            — вход в Telegram (интерактивно, на сервере)
  python -m razvedka collect          — собрать посты
  python -m razvedka report [--send]  — отчёт в консоль (и в PAPA TEST GROUP с --send)
  python -m razvedka send             — отчёт в консоль и в «PAPA ОТЧЁТЫ» (картинками, 18.10)
  python -m razvedka cards            — только нарисовать картинки отчёта (проверка, без Telegram)
  python -m razvedka dossier [--send] — досье больших каналов + сравнение с нашими (по понедельникам — само в run)
  python -m razvedka run              — collect + send (для ежедневного таймера)
  python -m razvedka publish          — только обновить отчёт для Pult (без отправки в Telegram)
  python -m razvedka curate           — агент-куратор: лучшее из папок PAPA·… → карточки в пульты каналов
  python -m razvedka pain            — «боль аудитории», этап А: комментарии под сильными постами → вопросы/жалобы/просьбы
  python -m razvedka trend daily|market [--send] (trend-auto / trend-now — для таймера и установки) — 🎬 Тренд-разведка: AI-видео тренды (ежедневно) и рынок «панелей» (по понедельникам)
  python -m razvedka github [--send] (github-auto — для таймера) — 🧭 GitHub-разведка: новые полезные инструменты (раз в неделю)
  python -m razvedka sources          — 📡 отбор каналов-источников (белый список, 26.10) → таблица в главный пульт
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


def dossier_text() -> str:
    from . import dossier
    c = cfg()
    return dossier.render(dossier.build(store.connect(DB), int(c.get("dossier_days", 14)), int(c.get("dossier_big", 6)),
                                        own_usernames=c.get("own_channels", []), watch=c.get("dossier_watch", dossier.WATCH)))


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
        "text": text[:40000],
    }
    tmp = d / ".latest.json.tmp"
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.chmod(tmp, 0o640)
    os.replace(tmp, d / "latest.json")
    return str(d / "latest.json")


def dt_now():
    import datetime as _dt
    return _dt.datetime.now(analyze.TZ)


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


async def _send_daily(a: dict, text: str) -> None:
    """18.10, владелец: отчёт картинками «как в Excel». Не вышло (нет Pillow и т.п.) — прежний текст."""
    try:
        if cfg().get("report_format", "cards") != "cards":
            raise RuntimeError("text format")
        from .cards import caption, render_cards
        images, cap = render_cards(a), caption(a)
    except Exception as e:
        print(f"CARDS_SKIP: {type(e).__name__}: {e}", flush=True)
        await _send(text)
        return
    from .telegram import client_from_env, send_report_cards
    c = client_from_env()
    await c.connect()
    try:
        ok = await send_report_cards(c, images, cap)
        print(f"CARDS_SENT {len(images)}" if ok else "CARDS_NOT_SENT", flush=True)
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
        res = await run(c, Path(PUB) / "curator", log=lambda s: print(s, flush=True))
        from . import sklad                      # 26.10: 📦 склады владельца → 📦 запас пультов (сам по сетке, с вето)
        from .telegram import send_report
        try:
            from .telegram import bot_send, pult_bot

            async def notify(text: str, channel: str) -> None:     # «склад почти пуст» — в пульт своего канала
                tok, ids = pult_bot(channel)
                if not (tok and ids and all(bot_send(tok, o, text) for o in ids)):
                    await send_report(c, text)
            res["склад"] = await sklad.run(c, Path(PUB) / "curator", log=lambda s: print(s, flush=True), notify=notify)
        except Exception as e:  # noqa: BLE001 — склад не роняет куратора
            res["склад"] = f"ошибка: {type(e).__name__}: {e}"[:200]
        return res
    finally:
        await c.disconnect()


async def _sources(inside_run: bool = False) -> dict:
    import subprocess
    busy = [u for u in ("hunt", "collect", "curate", "pain") + (() if inside_run else ("run",)) if subprocess.run(
        ["systemctl", "is-active", "-q", f"papa-razvedka@{u}.service"]).returncode == 0]
    if busy:                                   # один профиль — одна задача за раз
        return {"пропуск": f"профиль занят: {', '.join(busy)}"}
    from . import sources
    from .telegram import client_from_env, send_report
    c = client_from_env()
    await c.connect()
    if not await c.is_user_authorized():
        raise SystemExit("NOT_AUTHORIZED")
    try:
        res = await sources.run(c, Path(PUB) / "sources", log=lambda s: print(s, flush=True))
        cards = res.pop("cards")
        if cards:                                 # 26.10: карточка выбора — в пульт СВОЕГО канала (кнопки ловит genplan)
            from .telegram import bot_send_kb, owner_bot, pult_bot
            tok, ids = owner_bot()
            if tok and ids:
                res["отправлено"] = all(bot_send_kb(pult_bot(ch)[0], o, t, kb) for ch, t, kb in cards for o in ids)
            else:
                for _, t, _ in cards:
                    await send_report(c, t + "\n\n(кнопки выбора работают только в пультах)")
                res["отправлено"] = "без кнопок — нет PAPA ШТАБ"
            for _, t, _ in cards:
                print(t, flush=True)
        else:
            res["отправлено"] = "нет — карточки на этой неделе уже были, кадры ещё проверяются"
        return res
    finally:
        await c.disconnect()


async def _pain() -> dict:
    import subprocess
    busy = [u for u in ("hunt", "collect", "run", "curate") if subprocess.run(
        ["systemctl", "is-active", "-q", f"papa-razvedka@{u}.service"]).returncode == 0]
    if busy:                                   # один профиль — одна задача за раз
        return {"пропуск": f"профиль занят: {', '.join(busy)}"}
    from . import pain
    from .telegram import client_from_env
    c = client_from_env()
    await c.connect()
    if not await c.is_user_authorized():
        raise SystemExit("NOT_AUTHORIZED")
    db = store.connect(DB)
    try:
        stat = await pain.run(c, db, log=lambda s: print(s, flush=True))
        print(pain.render(stat, pain.summary(db), db), flush=True)
        return stat
    finally:
        await c.disconnect()


def main(argv: list[str]) -> None:
    cmd = argv[0] if argv else "report"
    if cmd == "pain-report":                   # только база, Telegram не трогаем
        from . import pain
        db = pain.connect(store.connect(DB))
        s = pain.summary(db)
        print(f"В базе: {s['total']} · полезных: {s['useful']} ({s['useful_pct']}%) · " +
              " · ".join(f"{k}: {v}" for k, v in s["kinds"].items()))
        for k, t in (("request", "Просьбы"), ("complaint", "Жалобы"), ("question", "Вопросы")):
            for x in pain.samples(db, k, 5):
                print(f"  [{t}] {x}")
        print("PAIN_REPORT_DONE")
        return
    if cmd in ("trend-auto", "trend-now"):     # для systemd (без пробелов в имени экземпляра)
        argv = ["trend", "auto"] if cmd == "trend-auto" else ["trend", "daily", "market", "--send"]
        cmd = "trend"
    if cmd == "trend":                         # только веб-поиск через Anthropic; Telegram — лишь для отправки отчёта
        from . import trend
        modes = [a for a in argv[1:] if a in ("daily", "market", "auto")] or ["daily"]
        if modes == ["auto"]:                  # таймер: каждый день daily, по понедельникам ещё и market
            modes = ["daily"] + (["market"] if dt_now().weekday() == 0 else [])
        out = Path(PUB) / "trend"
        out.mkdir(parents=True, exist_ok=True)
        for m in modes:
            try:
                text = trend.run(m, out)
            except trend.TrendError as e:
                text = f"🎬 Тренд-разведка ({m}): ошибка — {e}"
            print(text, flush=True)
            if "--send" in argv or argv[1:2] == ["auto"]:
                asyncio.run(_send(text))
                print("TREND_SENT", m)
        print("TREND_DONE")
        return
    if cmd in ("github", "github-auto"):       # 🧭 только GitHub API + Anthropic; Telegram — лишь для отправки отчёта
        from . import github
        out = Path(PUB) / "github"
        out.mkdir(parents=True, exist_ok=True)
        try:
            text = github.run(out)
        except Exception as e:                  # отчёт об ошибке тоже уходит владельцу, сервис не падает молча
            text = f"🧭 GitHub-разведка: ошибка — {type(e).__name__}: {e}"
        print(text, flush=True)
        if cmd == "github-auto" or "--send" in argv:
            asyncio.run(_send(text))
            print("GITHUB_SENT")
        # 28.10 владелец: + «Новинки сервисов» (ElevenLabs, Google, Kling…) — тем же недельным заходом, отдельным сообщением
        from . import novinki
        try:
            ntext = novinki.run(out)
        except Exception as e:
            ntext = f"🆕 Новинки сервисов: ошибка — {type(e).__name__}: {e}"
        print(ntext, flush=True)
        if cmd == "github-auto" or "--send" in argv:
            asyncio.run(_send(ntext))
            print("NOVINKI_SENT")
        print("GITHUB_DONE")
        return
    if cmd == "pain":
        print("PAIN_DONE", asyncio.run(_pain()))
        return
    if cmd == "sources":
        print("SOURCES_DONE", asyncio.run(_sources()))
        return
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
            asyncio.run(_send_daily(a, text))
            print("REPORT_SENT")
            import datetime as _dt
            if _dt.datetime.now(analyze.TZ).weekday() == 0:          # досье — раз в неделю, по понедельникам
                asyncio.run(_send(dossier_text()))
                print("DOSSIER_SENT")
            # 26.10: белый список — по понедельникам заново, в другие дни — пока не добран (лимит Gemini)
            if _dt.datetime.now(analyze.TZ).weekday() == 0 or (Path(PUB) / "sources" / "pending").exists() \
                    or not (Path(PUB) / "sources" / "sent_week").exists():
                print("SOURCES_DONE", asyncio.run(_sources(inside_run=True)))
    elif cmd == "dossier":
        text = dossier_text()
        print(text)
        if "--send" in argv:
            asyncio.run(_send(text))
            print("DOSSIER_SENT")
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
            asyncio.run(_send_daily(a, text))
            print("REPORT_SENT")
    elif cmd == "cards":                       # только нарисовать (проверка, без Telegram)
        from .cards import caption, render_cards
        _, a = build()
        imgs = render_cards(a)
        print(caption(a))
        print("CARDS_OK", [len(x) for x in imgs])
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv[1:])
