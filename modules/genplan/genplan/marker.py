"""🏷 МАРКИРОВЩИК (01.11.2026, владелец: «ты перестал маркировать… сделать одного агента, который только этим занимается»).

Один агент — одна работа: ставит НАШУ метку (@юзернейм канала) на видео и фото перед выходом в канал.
Политика — docs/MARKIROVKA.md. Здесь — решение «метить или нет» и сама отрисовка.

Видео: метка «подъём» (решение владельца): выходит снизу по центру, поднимается и растворяется до середины кадра,
повторяется раз в 15 с. Фото: небольшая метка в правом верхнем углу, полупрозрачная.
Без надписей-заголовков (23.10: «дёшево») — только @юзернейм.
"""
from __future__ import annotations

from pathlib import Path

from . import media as M

# Рубрики, которые НЕ метим никогда
NEVER_RUBRICS = ("реклама", "муфтий минбари")
# Уже наше (метка вшита при сборке) — второй раз не метим
OWN_SOURCES = ("fabrika", "digest", "дайжест")
KINDS = ("video", "animation", "photo")
MAX_BOT_FILE = 20 * 1024 * 1024        # Bot API скачивает до 20 МБ
MAX_UPLOAD = 50 * 1024 * 1024          # и отправляет до 50 МБ


def mark_text(ch: dict) -> str:
    return ch.get("watermark") or "@" + ch["username"]


def decide(ch: dict, m) -> tuple[str | None, str]:
    """(вид медиа или None, причина). None — пост выходит без метки, причина — для отчёта Штаба."""
    import json
    keys = m.keys()
    rubric = (m["rubric"] or "").lower()
    if not m["has_media"]:
        return None, "текст"
    if any(rubric.startswith(r) for r in NEVER_RUBRICS):
        return None, "реклама/Муфтий — не метим"
    src = (m["source"] if "source" in keys else "") or ""
    if any(s in src.lower() for s in OWN_SOURCES):
        return None, "уже с нашей меткой"
    try:
        media = json.loads(m["media"] or "[]") if "media" in keys else []
    except ValueError:
        media = []
    if len(media) > 1:
        return None, "альбом — пока без метки"
    kind = media[0].get("type") if media else None
    if kind not in KINDS:
        return None, "не видео/фото"
    return kind, "метим"


def render(kind: str, src: Path, dst: Path, text: str) -> Path:
    """Нарисовать метку. Видео — без сжатия качества (crf 20), звук как есть."""
    logo = M.text_logo(text, dst.with_suffix(".wm.png"))
    try:
        if kind == "photo":
            return M.watermark_photo(src, logo, dst.with_suffix(".jpg"))
        out = M.watermark_video(src, logo, dst.with_suffix(".mp4"), crf=20, style="rise")
        if out.stat().st_size > MAX_UPLOAD:
            out = M.watermark_video(src, logo, dst.with_suffix(".mp4"), crf=26, style="rise")
        return out
    finally:
        dst.with_suffix(".wm.png").unlink(missing_ok=True)


# ───────────── Живая работа (01.11, владелец: «да, включай всё») ─────────────
# Маркировщик сам, по одному посту: очередь каналов → скачать (бот до 20 МБ, больше — через аккаунт PAPA) →
# метка своего канала → загрузить на полку «<канал> · ГОТОВО» → пост выходит уже с полки. Банк остаётся чистым.
# Не успел пометить к выходу — пост выходит как раньше (сетка важнее).
import asyncio  # noqa: E402
import datetime as _dt  # noqa: E402
import json as _json  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402
import urllib.request  # noqa: E402

LOOKAHEAD_H = 30          # метим то, что выйдет в ближайшие 30 часов (и запас без времени)
MAX_TRIES = 2


def opts(cfg: dict) -> dict | None:
    o = cfg.get("marker") or {}
    return o if o.get("on") else None


def candidates(db, cfg: dict, now: _dt.datetime) -> list:
    o = opts(cfg)
    if not o:
        return []
    from . import store
    chans = [c for c in o.get("channels", []) if c in cfg["channels"]]
    if not chans:
        return []
    until = (now + _dt.timedelta(hours=LOOKAHEAD_H)).isoformat()
    q = ",".join("?" * len(chans))
    # сначала то, что уже стоит в сетке (по времени), потом 📦 запас — он выходит сам по часам сетки
    rows = db.execute(f"SELECT * FROM materials WHERE channel IN ({q}) AND ((status='queued' AND "
                      "(scheduled_at IS NULL OR scheduled_at<=?)) OR (status='draft' AND stock=1)) "
                      "ORDER BY CASE status WHEN 'queued' THEN 0 ELSE 1 END, COALESCE(scheduled_at,'9999'), created_at "
                      "LIMIT 120", (*chans, until)).fetchall()
    out = []
    for r in rows:
        if store.kv_get(db, f"marked_{r['id']}") or int(store.kv_get(db, f"markfail_{r['id']}") or 0) >= MAX_TRIES:
            continue
        from . import caption
        if caption.needs_caption(r):          # без своего текста — подпись ИИ делает при выходе по исходному файлу
            continue
        if decide(cfg["channels"][r["channel"]], r)[0]:
            out.append(r)
    # 14.11: рубрики «метка обязательна» (клипы, песни) — первыми среди запаса: без метки они в сетку не встанут
    out.sort(key=lambda r: not (r["status"] == "queued" or r["rubric"] in (cfg["channels"][r["channel"]].get("mark_must") or [])))
    return out


def _bot_download(pub, file_id: str, dst: Path) -> bool:
    info = pub.http("getFile", {"file_id": file_id})
    fp = ((info or {}).get("result") or {}).get("file_path")
    if not fp:
        return False
    with urllib.request.urlopen(pub.base.replace("/bot", "/file/bot", 1) + "/" + fp, timeout=300) as r:
        dst.write_bytes(r.read())
    return dst.stat().st_size > 0


def _video_attrs(path: Path):
    from telethon.tl.types import DocumentAttributeVideo
    i = M.probe(path)
    return [DocumentAttributeVideo(duration=int(i["dur"] or 1), w=i["w"] or 720, h=i["h"] or 1280,
                                   supports_streaming=True)]


def _thumb(path: Path) -> Path | None:
    t = path.with_suffix(".thumb.jpg")
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "1", "-i", str(path), "-frames:v", "1",
                        "-vf", "scale=320:-2", str(t)], capture_output=True, timeout=60)
    return t if r.returncode == 0 and t.exists() else None


async def ensure_shelf(acc, db, cfg: dict, pubs: dict, code: str) -> int:
    """Полка канала «<канал> · ГОТОВО»: частный канал аккаунта PAPA, боты канала — админы (публикуют копией оттуда)."""
    from . import store
    k = f"marker_shelf_{code}"
    got = store.kv_get(db, k)
    if got:
        return int(got)
    from telethon.tl.functions.channels import CreateChannelRequest, EditAdminRequest
    from telethon.tl.types import ChatAdminRights
    ch = cfg["channels"][code]
    res = await acc(CreateChannelRequest(title=f"{ch['title']} · ГОТОВО", megagroup=False,
                                         about="🏷 Маркировщик PAPA: видео с меткой канала, готовые к выходу. Вручную не бросать."))
    chan = res.chats[0]
    rights = ChatAdminRights(post_messages=True, edit_messages=True, delete_messages=True)
    for key in ("bot", f"bot:{code}"):
        p = pubs.get(key)
        if p is None:
            continue
        me = await asyncio.to_thread(p.http, "getMe", {})
        uname = ((me or {}).get("result") or {}).get("username")
        if uname:
            await acc(EditAdminRequest(chan, uname, rights, "PAPA"))
    sid = int(f"-100{chan.id}")
    store.kv_set(db, k, str(sid))
    return sid


_GRANTED: set = set()


async def grant(acc, cfg: dict, pubs: dict, code: str, shelf: int, log=print) -> bool:
    """02.11 разбор: посты КАТТА ДАВРА и PaparazziUZ с полки падали «chat not found» — бот, который публикует канал,
    не был админом своей полки (при создании полки права ставились не всем). Проверяем и доучиваем права; не вышло —
    False, и пост на полку не переезжает (выйдет как раньше, без метки)."""
    if (code, shelf) in _GRANTED:
        return True
    from telethon.tl.functions.channels import EditAdminRequest
    from telethon.tl.types import ChatAdminRights
    rights = ChatAdminRights(post_messages=True, edit_messages=True, delete_messages=True)
    if cfg["channels"][code]["publisher"] != "bot":
        keys = [k for k in (f"bot:{code}",) if k in pubs]        # группа: публикует аккаунт (он владелец полки)
    else:
        keys = [f"bot:{code}" if f"bot:{code}" in pubs else "bot"]
    ok = True
    for k in keys:
        p = pubs[k]
        try:
            me = (await asyncio.to_thread(p.http, "getMe", {})).get("result") or {}
            r = await asyncio.to_thread(p.http, "getChatMember", {"chat_id": shelf, "user_id": me.get("id")})
            if r.get("ok") and (r.get("result") or {}).get("status") in ("administrator", "creator"):
                continue
        except Exception:  # noqa: BLE001 — «chat not found» приходит ошибкой — значит, прав нет
            pass
        try:
            ent = await acc.get_entity(shelf)
            await acc(EditAdminRequest(ent, me.get("username"), rights, "PAPA"))
            await asyncio.sleep(0 if getattr(acc, "_fake", False) else 5)   # 02.11: Telegram применяет права с задержкой
            r = await asyncio.to_thread(p.http, "getChatMember", {"chat_id": shelf, "user_id": me.get("id")})
            if not (r.get("ok") and (r.get("result") or {}).get("status") in ("administrator", "creator")):
                raise RuntimeError(r.get("description") or "после назначения бот всё равно не админ")   # 02.11: проверяем, а не верим
            log(f"🏷 {code}: @{me.get('username')} — админ полки (права доставлены)")
        except Exception as e:  # noqa: BLE001
            ok = False
            log(f"🏷 {code}: @{me.get('username')} не стал админом полки — {type(e).__name__}: {str(e)[:150]}")
    if ok:
        _GRANTED.add((code, shelf))
    return ok


async def rehome(acc, db, env: dict, code: str, shelf: int, log=print) -> int:
    """02.11: полка есть, а публикующий бот её не видит (@PapaGenplanBot у КАТТА ДАВРА) — помеченные посты с полки
    переносим копией в PAPA HUB (главный бот там админ). Копия служебная (hubcopy_) — после выхода удаляется."""
    from . import store
    hub = str(env.get("HUB_CHAT_ID", ""))
    if not hub:
        return 0
    n = 0
    for m in db.execute("SELECT * FROM materials WHERE channel=? AND hub_chat=? AND status IN ('queued','draft')",
                        (code, shelf)).fetchall():
        try:
            sent = await acc.forward_messages(int(hub), int(m["hub_msg"]), from_peer=shelf, drop_author=True)
            sent = sent[0] if isinstance(sent, list) else sent
            store.kv_set(db, f"hubcopy_{int(sent.id)}", "1")
            store.update(db, m["id"], hub_chat=int(hub), hub_msg=int(sent.id), hub_msgs=_json.dumps([int(sent.id)]), via="main")
            n += 1
        except Exception as e:  # noqa: BLE001
            log(f"🏷 {code}: пост #{m['id']} с полки не перенести — {type(e).__name__}: {str(e)[:120]}")
    if n:
        log(f"🏷 {code}: бот не видит полку — {n} помеченных постов перенесены в PAPA HUB, выйдут с меткой")
    return n


async def step(acc, db, cfg: dict, env: dict, pubs: dict, db_path: str, log=print) -> bool:
    """Пометить один пост. True — что-то сделано (следующий сразу), False — работы нет."""
    from . import store
    from .service import pub_for
    from . import plan
    now = _dt.datetime.now(plan.TZ)
    rows = candidates(db, cfg, now)
    if not rows:
        return False
    m = rows[0]
    code, ch = m["channel"], cfg["channels"][m["channel"]]
    k_fail = f"markfail_{m['id']}"
    hub = str(env.get("HUB_CHAT_ID", ""))
    try:
        kind = decide(ch, m)[0]
        md = _json.loads(m["media"])[0]
        shelf = await ensure_shelf(acc, db, cfg, pubs, code)
        if not await grant(acc, cfg, pubs, code, shelf, log):
            raise RuntimeError("бот канала не админ полки — пост остаётся без метки")
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / ("src.jpg" if kind == "photo" else "src.mp4")
            ok = False
            if str(m["hub_chat"]) in (hub, str(shelf)):    # PAPA HUB аккаунт видит сам — без лимита
                msg = await acc.get_messages(int(m["hub_chat"]), ids=int(m["hub_msg"]))
                ok = bool(msg and msg.media and await acc.download_media(msg, file=str(src)))
            if not ok:
                p = pub_for(pubs, ch, code, m["via"] if "via" in m.keys() else None, from_hub=str(m["hub_chat"]) == hub)
                if not hasattr(p, "http"):              # 14.11: группа публикует аккаунтом (нет Bot API) — качаем аккаунтом,
                    try:                                # иначе ботом пульта канала (ошибка 'AccountPublisher' … 'http' — 219 неудач)
                        msg = await acc.get_messages(int(m["hub_chat"]), ids=int(m["hub_msg"]))
                        ok = bool(msg and msg.media and await acc.download_media(msg, file=str(src)))
                    except Exception:  # noqa: BLE001
                        ok = False
                    p = pubs.get(f"bot:{code}") or pubs.get("bot") or p
                if not ok and hasattr(p, "http"):
                    ok = await asyncio.to_thread(_bot_download, p, md.get("file_id", ""), src)
                if not ok and hub and hasattr(p, "http"):   # больше 20 МБ: копия на секунды в PAPA HUB → аккаунт качает
                    store.kv_set(db, "hub_staging", "1")
                    try:
                        r = await asyncio.to_thread(p.http, "copyMessage", {"chat_id": int(hub), "from_chat_id": m["hub_chat"],
                                                                             "message_id": m["hub_msg"]})
                        if r.get("ok"):
                            cid = int(r["result"]["message_id"])
                            store.kv_set(db, f"hubcopy_{cid}", "1")
                            msg = await acc.get_messages(int(hub), ids=cid)
                            ok = bool(msg and msg.media and await acc.download_media(msg, file=str(src)))
                            await asyncio.to_thread(p.http, "deleteMessage", {"chat_id": int(hub), "message_id": cid})
                    finally:
                        store.kv_set(db, "hub_staging", "")
            if not ok or not src.exists():
                raise RuntimeError("файл не скачать")
            out = await asyncio.to_thread(render, kind, src, Path(tmp) / "marked", mark_text(ch))
            if kind == "photo":
                sent = await acc.send_file(shelf, str(out), caption=f"#{m['id']}")
            else:
                th = await asyncio.to_thread(_thumb, out)
                sent = await acc.send_file(shelf, str(out), caption=f"#{m['id']}", attributes=_video_attrs(out),
                                           thumb=str(th) if th else None, supports_streaming=True, force_document=False)
        cur = store.get(db, m["id"])
        if cur["status"] not in ("queued", "draft"):        # успел выйти, пока рисовали — оставить как есть
            store.kv_set(db, f"marked_{m['id']}", "late")
            return True
        new_via = code if f"bot:{code}" in pubs else "main"
        store.update(db, m["id"], hub_chat=shelf, hub_msg=int(sent.id), hub_msgs=_json.dumps([int(sent.id)]), via=new_via)
        store.kv_set(db, f"marked_{m['id']}", "1")
        log(f"🏷 {code}: пост #{m['id']} помечен ({mark_text(ch)}) → полка")
    except Exception as e:  # noqa: BLE001 — метка не должна ломать выход поста
        store.kv_set(db, k_fail, str(int(store.kv_get(db, k_fail) or 0) + 1))
        log(f"🏷 {code}: пост #{m['id']} без метки — {type(e).__name__}: {str(e)[:200]}")
    return True


async def loop(acc, db_path: str, cfg_fn, env: dict, pubs: dict, log=print) -> None:
    from . import store
    db = store.connect(db_path)
    await asyncio.sleep(30)
    try:                                       # 02.11: посты уже на полках — права ботам до их выхода
        if not acc.is_connected():
            await acc.connect()
        for k, v in db.execute("SELECT k, v FROM kv WHERE k LIKE 'marker_shelf_%'").fetchall():
            if k[13:] in cfg_fn()["channels"] and not await grant(acc, cfg_fn(), pubs, k[13:], int(v), log):
                await rehome(acc, db, env, k[13:], int(v), log)
    except Exception as e:  # noqa: BLE001
        log(f"🏷 marker: права полок — {type(e).__name__}: {e}")
    while True:
        did = False
        try:
            if not acc.is_connected():
                await acc.connect()
            did = await step(acc, db, cfg_fn(), env, pubs, db_path, log)
        except Exception as e:  # noqa: BLE001
            log(f"🏷 marker: {type(e).__name__}: {e}")
        await asyncio.sleep(3 if did else 120)
