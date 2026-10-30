"""Служба GENPLAN PAPA: раз в минуту (и сразу после 🆘) публикует посты, чьё точное время наступило.
Режим канала: live — рабочий канал; shadow — тестовые чаты (PAPA TEST GROUP / PAPA TEST).
Якоря (намоз, дуо) и реклама Хўжаобода пока остаются за GENPLAN 5."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from . import plan, smart, store, text
from .publish import PublishError

ERRORS: list[str] = []             # ошибки публикации — служба сообщает владельцу
HELD = "held"                       # 30.10 сверка: пост не вышел, но остаётся в очереди (не failed)
LANG_HOLDS = 2                      # сколько раз откладываем пост с не узбекским текстом (+1 ч), потом — снят
LATE = dt.timedelta(hours=3)        # служба долго стояла: такие посты не публикуем пачкой, а переносим на новое время


def pub_for(pubs: dict, ch: dict, channel: str, via: str | None = None, from_hub: bool = True):
    """Кто публикует. Группа — аккаунт PAPA (берёт из хаба). Канал: материал из хаба (утро, Fabrika, старые посты) —
    главный бот (он в хабе); материал прямо из чата с ботом-пультом (решение 16.10: без хаба) — тот же бот,
    только он видит этот чат и его file_id."""
    kind = ch["publisher"]
    if kind != "bot" or from_hub or not via or via == "main":
        return pubs[kind]
    return pubs.get(f"{kind}:{via}") or pubs[kind]


def to_materials(rows) -> list[plan.Material]:
    return [plan.Material(r["id"], r["rubric"], dt.datetime.fromisoformat(r["created_at"]), r["channel"], r["text"])
            for r in rows]


def channel_mode(cfg: dict, channel: str) -> str:
    """Режим канала: свой (channels.X.mode) важнее общего — каналы переводятся в работу по одному."""
    return cfg["channels"][channel].get("mode") or cfg.get("mode", "shadow")


def target(cfg: dict, env: dict, channel: str) -> str | int:
    if channel_mode(cfg, channel) == "live":
        return "@" + cfg["channels"][channel]["username"]
    return int(env["TEST_GROUP_ID"]) if cfg["channels"][channel]["publisher"] == "account" else int(env["TEST_CHANNEL_ID"])


def hook_for(cfg: dict, ch: dict, m, db=None) -> str:
    """Нижний хук (под юзернеймом). Решение владельца 17.10: по смыслу текста — ИИ (с 27.10 — Gemini).
    Печальная тема или свой призыв в конце текста — без нашего хука (как раньше). ИИ недоступен — хук рубрики из config."""
    body, _ = text.translit.auto(text.strip_sources(m["text"] or ""))
    topics = [] if ch.get("topics") is False else cfg.get("topics", [])
    base = text.pick_hook(ch, m["rubric"], int(m["id"]), body, topics)
    if not base:                                              # печальная тема / свой призыв в тексте
        return ""
    # Схема владельца 17.10: новости — без хука; музыка — наша реклама; полезное — короткий хук ИИ; остальное — готовые
    pol = ch.get("hook_policy") or {}
    rub = m["rubric"] or ""
    t = text.topic_of(body, topics)
    tname = (t or {}).get("name", "")
    if tname in ("Дуо", "Дин"):                               # религиозное — только готовый уважительный хук
        return base
    if rub in pol.get("none", []):
        return ""
    if rub in pol.get("promo", []) or (tname == "Мусиқа" and ch.get("promo_hooks")):
        promo = ch.get("promo_hooks") or []
        return promo[int(m["id"]) % len(promo)] if promo else base
    smart_ai = rub in pol.get("ai", []) or tname in ("Соғлиқ", "Таом", "Маслаҳат")
    if not smart_ai or db is None or ch.get("ai_hooks") is False:
        return base
    keys = m.keys() if hasattr(m, "keys") else []
    if "hook_ai" in keys and m["hook_ai"] is not None:          # уже придуман для этого поста — не платим второй раз
        return m["hook_ai"]
    from . import ai
    if not ai.available():
        return base
    try:
        from . import tails
        h = ai.hook(db, text.drop_lines(body, tails.merged(db, m)), ch.get("title", ""))
    except Exception:  # noqa: BLE001 — ИИ не ответил: хук рубрики
        return base
    try:
        from . import store
        store.update(db, int(m["id"]), hook_ai=h)
    except Exception:  # noqa: BLE001
        pass
    return h


def share_button(ch: dict) -> dict | None:
    """Кнопка под постом «Дўстларга улашиш» — подписчик одним нажатием отправляет канал друзьям (рост)."""
    if not ch.get("share_button"):
        return None
    from urllib.parse import quote
    url = f"https://t.me/{ch['username']}"
    return {"text": ch["share_button"], "url": f"https://t.me/share/url?url={quote(url)}&text={quote(ch.get('share_text', ''))}"}


def tag_for(cfg: dict, ch: dict, m) -> str:
    """Хэштег по СМЫСЛУ текста (решения 17.10: «либо правильный, либо никакого»).
    1) смысл текста с тегом (пост дня, Хайрли тонг, дуо; у канала — topic_tags: юмор, спорт, полезное…) — этот тег;
    2) расплывчатая рубрика (Қизиқарли, Видео…) — без хэштега: рубрика — это место в сетке, а не смысл;
    3) рубрику выбрал сам владелец (не подтвердил подсказку бота) — тег рубрики;
    4) иначе — без хэштега."""
    if not ch.get("hashtags"):
        return ""
    if "tag" in m.keys() and m["tag"] is not None:          # 17.10: владелец выбрал подрубрику — её хэштег (один)
        return m["tag"]
    body, _ = text.translit.auto(text.strip_sources(m["text"] or ""))
    t = text.topic_of(body, cfg.get("topics", []))
    if t:
        tag = t.get("tag") or (ch.get("topic_tags") or {}).get(t["name"], "")
        if tag:
            return tag
    rubric = m["rubric"] or ""
    if rubric in (ch.get("vague_rubrics") or []):
        return ""
    guessed = bool(m["guessed"]) if "guessed" in m.keys() else False
    return "" if guessed else (ch.get("hashtags") or {}).get(rubric, "")


def cleanup_hubcopy(db, env: dict, pubs: dict, m, log=print) -> int:
    """21.10 владелец: PAPA HUB — не свалка. Служебную копию поста группы (её кладёт бот Хўжаобода, чтобы аккаунт PAPA
    мог опубликовать медиа) после выхода удаляем. Не трогаем рекламу, рекламные пакеты и Якуний пост — они выходят снова."""
    hub = str(env.get("HUB_CHAT_ID", ""))
    if not hub or str(m["hub_chat"]) != hub:
        return 0
    ids = json.loads(m["hub_msgs"] or "[]") if "hub_msgs" in m.keys() else []
    ids = [int(x) for x in (ids or [m["hub_msg"]]) if x and store.kv_get(db, f"hubcopy_{x}")]
    if not ids:
        return 0                                       # не наша копия (материал брошен прямо в PAPA HUB) — не удаляем
    from . import extras
    if extras.campaign_of(db, int(m["id"])):
        return 0
    for k in ("final_xojaobod", "final_davra", "final_paparazzi"):
        f = store.kv_get(db, k, "")
        if f and (f'"hub_msg": {ids[0]}' in f or f'"material_id": {int(m["id"])}' in f):
            return 0
    via = m["via"] if "via" in m.keys() else None
    for p in [pubs.get(f"bot:{via}"), pubs.get("bot")]:
        if not p or not hasattr(p, "http"):
            continue
        try:
            r = p.http("deleteMessages", {"chat_id": int(hub), "message_ids": ids})
        except Exception:  # noqa: BLE001
            continue
        if r.get("ok"):
            for x in ids:
                db.execute("DELETE FROM kv WHERE k=?", (f"hubcopy_{x}",))
            db.commit()
            log(f"PAPA HUB: служебная копия убрана ({len(ids)})")
            return len(ids)
    return 0


def stage(db, env: dict, pubs: dict, via: str | None, src_chat, ids: list[int], has_media: bool):
    """21.10 владелец: PAPA HUB — не свалка. Пост группы хранится там, куда его бросили (чат пульта / ХАБ группы).
    Аккаунт PAPA видит только PAPA HUB, поэтому бот кладёт туда копию ЛИШЬ на секунды публикации, потом удаляет.
    Возвращает (новые id в PAPA HUB, бот) или None — копия не нужна (текст или материал уже в PAPA HUB)."""
    hub = str(env.get("HUB_CHAT_ID", ""))
    ids = [int(x) for x in ids if x]
    if not hub or not has_media or not src_chat or str(src_chat) == hub or not ids:
        return None
    p = (pubs.get(f"bot:{via}") if via and via != "main" else None) or pubs.get("bot")
    if p is None or not hasattr(p, "http"):
        raise PublishError("нет бота, чтобы подготовить медиа для группы")
    store.kv_set(db, "hub_staging", "1")                  # главный бот не примет эту копию за новый материал
    if len(ids) > 1:
        r = p.http("copyMessages", {"chat_id": int(hub), "from_chat_id": src_chat, "message_ids": ids})
        new = [int(x["message_id"]) for x in (r.get("result") or [])] if r.get("ok") else []
    else:
        r = p.http("copyMessage", {"chat_id": int(hub), "from_chat_id": src_chat, "message_id": ids[0]})
        new = [int(r["result"]["message_id"])] if r.get("ok") else []
    if not new:
        store.kv_set(db, "hub_staging", "")
        raise PublishError("не смог подготовить медиа для группы: " + str(r.get("description", "?")))
    for x in new:
        store.kv_set(db, f"hubcopy_{x}", "1")
    return new, p


def unstage(db, env: dict, staged, log=print) -> None:
    """Секундная копия в PAPA HUB — удалить сразу после публикации (и при ошибке тоже)."""
    if not staged:
        return
    new, p = staged
    try:
        r = p.http("deleteMessages", {"chat_id": int(env["HUB_CHAT_ID"]), "message_ids": new})
        if not r.get("ok"):
            ERRORS.append(f"⚠️ PAPA HUB: не смог убрать служебную копию ({r.get('description', '?')})")
    except Exception as e:  # noqa: BLE001
        ERRORS.append(f"⚠️ PAPA HUB: не смог убрать служебную копию ({e})")
    finally:
        store.kv_set(db, "hub_staging", "")


def hub_clean_once(db, cfg: dict, env: dict, pubs: dict, log=print) -> dict:
    """21.10 владелец: «не засоряй PAPA HUB — раз и навсегда». Один раз убрать из PAPA HUB все старые служебные
    копии постов группы. Копии, которые ещё нужны (пост в плане, Якуний пост, реклама на несколько дней), сначала
    переезжают в чат пульта группы — там их источник; дальше они попадают в PAPA HUB только на секунды публикации."""
    out = {"moved": 0, "deleted": 0, "errors": 0}
    if store.kv_get(db, "hub_clean_v1") == "done":
        return out
    hub = str(env.get("HUB_CHAT_ID", ""))
    owners = [int(x) for x in str(env.get("OWNER_IDS", "")).split(",") if x.strip()]
    if not hub or not owners:
        return out
    group = next((c for c, ch in cfg["channels"].items() if ch["publisher"] == "account"), None)
    copies = {int(r[0][len("hubcopy_"):]) for r in db.execute("SELECT k FROM kv WHERE k LIKE 'hubcopy_%'").fetchall()
              if r[0][len("hubcopy_"):].isdigit()}
    if not copies:
        store.kv_set(db, "hub_clean_v1", "done")
        return out

    def bot_for(via):
        return (pubs.get(f"bot:{via}") if via and via != "main" else None) or pubs.get(f"bot:{group}") or pubs.get("bot")

    def move(ids, via):
        """Копии из PAPA HUB → тихо в чат пульта владельца; новые id или None."""
        b = bot_for(via)
        if len(ids) > 1:
            r = b.http("copyMessages", {"chat_id": owners[0], "from_chat_id": int(hub), "message_ids": ids,
                                        "disable_notification": True})
            return [int(x["message_id"]) for x in r.get("result") or []] if r.get("ok") else None
        r = b.http("copyMessage", {"chat_id": owners[0], "from_chat_id": int(hub), "message_id": ids[0],
                                   "disable_notification": True})
        return [int(r["result"]["message_id"])] if r.get("ok") else None

    keep: set[int] = set()
    for m in db.execute("SELECT * FROM materials WHERE hub_chat=? AND status IN ('queued','draft','failed')",
                        (int(hub),)).fetchall():
        ids = [int(x) for x in (json.loads(m["hub_msgs"] or "[]") or [m["hub_msg"]]) if x]
        if not ids or not all(x in copies for x in ids):
            continue                                        # брошен прямо в PAPA HUB (не служебная копия) — не трогаем
        via = (m["via"] if "via" in m.keys() else None) or group
        new = move(ids, via)
        if not new:
            out["errors"] += 1
            keep.update(ids)
            continue
        db.execute("UPDATE materials SET hub_chat=?, hub_msg=?, hub_msgs=?, via=? WHERE id=?",
                   (owners[0], new[0], json.dumps(new), via, m["id"]))
        out["moved"] += 1
    for k in ("final_xojaobod", "final_davra", "final_paparazzi"):
        f = json.loads(store.kv_get(db, k, "") or "null")
        if not f or str(f.get("hub_chat")) != hub:
            continue
        ids = [int(x) for x in (f.get("hub_msgs") or [f.get("hub_msg")]) if x]
        if not ids or not all(x in copies for x in ids):
            continue
        new = move(ids, f.get("via") or group)
        if not new:
            out["errors"] += 1
            keep.update(ids)
            continue
        f.update(hub_chat=owners[0], hub_msg=new[0], hub_msgs=new if len(new) > 1 else [], via=f.get("via") or group)
        store.kv_set(db, k, json.dumps(f, ensure_ascii=False))
        out["moved"] += 1
    db.commit()
    gone = sorted(copies - keep)
    for i in range(0, len(gone), 100):
        part = gone[i:i + 100]
        done = False
        for p in [pubs.get(f"bot:{group}"), pubs.get("bot")]:
            if not p or not hasattr(p, "http"):
                continue
            try:
                r = p.http("deleteMessages", {"chat_id": int(hub), "message_ids": part})
            except Exception:  # noqa: BLE001
                continue
            if r.get("ok"):
                done = True
                break
        if done:
            out["deleted"] += len(part)
        else:
            out["errors"] += 1
    if not out["errors"]:
        store.kv_set(db, "hub_clean_v1", "done")
    log(f"PAPA HUB очищен: перенесено {out['moved']}, удалено {out['deleted']}, ошибок {out['errors']}")
    return out


async def publish_one(db, cfg, env, pubs, channel: str, m, slot: str | None, day: str, log=print,
                      now: dt.datetime | None = None) -> bool:
    ch = cfg["channels"][channel]
    from . import translit
    if translit.language_note(m["text"] or "") and not (m["rubric"] or "").lower().startswith("реклама"):  # 20.10: предохранитель — русский текст в канал не выходит никогда
        from . import ai
        try:
            store.update(db, m["id"], text=ai.rewrite(db, m["text"], ch["title"]))
            m = store.get(db, m["id"])
        except Exception as e:  # noqa: BLE001
            store.record(db, channel, day, slot, m["id"], "failed", error=f"нет перевода: {e}")
            ERRORS.append(f"⛔ {ch['title']}: пост на русском не опубликован — нет перевода ({e}). Нажмите 🤖 в карточке.")
            log(f"{channel} {slot or 'срочно'}: ЗАДЕРЖАН — русский текст без перевода")
            return False
        if translit.language_note(m["text"] or ""):     # 30.10 сверка (№8): ИИ вернул русский/смесь — не публикуем
            k = f"langhold_{m['id']}"
            n = int(store.kv_get(db, k) or 0) + 1
            store.kv_set(db, k, str(n))
            if n > LANG_HOLDS:
                store.record(db, channel, day, slot, m["id"], "failed", error="текст не на узбекском после ИИ")
                ERRORS.append(f"⛔ {ch['title']}: пост #{m['id']} не вышел — текст так и не стал узбекским. Поправьте текст в карточке.")
                log(f"{channel} {slot or 'срочно'}: снят — текст не на узбекском")
                return False
            later = (now or dt.datetime.now(plan.TZ)) + dt.timedelta(hours=1)
            store.update(db, m["id"], status="queued", scheduled_at=later.isoformat())
            ERRORS.append(f"⏸ {ch['title']}: пост задержан: текст не на узбекском — поправьте (повтор в {later:%H:%M}, #{m['id']})")
            log(f"{channel} {slot or 'срочно'}: ЗАДЕРЖАН — после ИИ текст не узбекский, повтор в {later:%H:%M}")
            return HELD
    own = tuple(c["username"] for c in cfg["channels"].values())
    is_ad = (m["rubric"] or "").lower().startswith("реклама")
    tag = "#РЕКЛАМА" if is_ad else tag_for(cfg, ch, m)
    from . import tails
    junk = tails.merged(db, m)                 # 18.10: + выученные хвосты источника (на момент выхода)
    sigs = tuple(ch.get("signatures") or ())
    sig = sigs[int(m["id"]) % len(sigs)] if sigs else ch.get("signature", "")
    body = text.finalize(m["text"], sig, is_ad=is_ad, own=own, hook=hook_for(cfg, ch, m, db) if not is_ad else "", tag=tag,
                         junk=junk, signatures=sigs + ((ch.get("signature"),) if ch.get("signature") else ()),
                         limit=1024 if m["has_media"] else 4096, author_first=True)
    media = json.loads(m["media"] or "[]") if "media" in m.keys() else []
    hub_ids = json.loads(m["hub_msgs"] or "[]") if "hub_msgs" in m.keys() else []
    via = m["via"] if "via" in m.keys() else None
    p = pub_for(pubs, ch, channel, via, from_hub=str(m["hub_chat"]) == str(env.get("HUB_CHAT_ID")))
    to = target(cfg, env, channel)
    staged = None
    try:
        src_chat, src_ids = m["hub_chat"], (hub_ids or [m["hub_msg"]])
        if ch["publisher"] == "account":
            staged = stage(db, env, pubs, via, m["hub_chat"], src_ids, bool(m["has_media"]))
            if staged:
                src_chat, src_ids = int(env["HUB_CHAT_ID"]), staged[0]
        if len(hub_ids) > 1:                               # альбом — одним постом
            if ch["publisher"] == "account":
                mid = await p.publish_album(to, src_chat, src_ids, body)
            else:
                mid = p.publish_album(to, media, body)
        elif ch["publisher"] == "account":
            mid = await p.publish(to, body, src_chat, src_ids[0], bool(m["has_media"]))
        else:
            mid = p.publish(to, body, m["hub_chat"], m["hub_msg"], bool(m["has_media"]), button=share_button(ch))
        store.update(db, m["id"], status="published")
        store.record(db, channel, day, slot, m["id"], "done", mid)
        if ch["publisher"] == "account" and not is_ad:
            cleanup_hubcopy(db, env, pubs, m, log)
        if is_ad:                                          # 💰 31.10: реклама из заказа ассистента — клиенту «чиқди ✅»
            try:
                from . import adsin
                adsin.published(db, cfg, m["id"], mid)
            except Exception as e:  # noqa: BLE001 — отчёт клиенту не должен ломать публикацию
                log(f"adsin.published: {type(e).__name__}: {e}")
        store.pulse_add(db, channel, now or dt.datetime.now(plan.TZ), "ad" if is_ad else "bot")   # 30.10: реклама помечена — держится 10 мин
        log(f"{channel} {slot or 'срочно'}: опубликовано ({m['rubric']})")
        return True
    except PublishError as e:
        store.record(db, channel, day, slot, m["id"], "failed", error=str(e))
        ERRORS.append(f"❌ {ch['title']}: пост не вышел — {e}")
        log(f"{channel} {slot or 'срочно'}: ОШИБКА {e}")
        return False
    finally:
        unstage(db, env, staged, log)


def hourly_migrate(db, cfg: dict) -> int:
    """25.10: канал перешёл на часовую сетку — запланированные посты (не реклама, не срочные, не выбранные владельцем
    вручную 🔒) один раз заново встают в часы сетки, по прежнему порядку. Откат: убрать hourly из config.toml."""
    n = 0
    for channel, ch in cfg["channels"].items():
        k = f"hourly_v1:{channel}"
        if not smart.hourly(ch) or store.kv_get(db, k):
            continue
        for m in store.scheduled(db, channel):
            if smart.is_grid_post(m) and not m["locked"]:
                db.execute("UPDATE materials SET scheduled_at=NULL WHERE id=?", (m["id"],))
                n += 1
        db.commit()
        store.kv_set(db, k, "done")
    return n


def reconcile(db, cfg: dict, now: dt.datetime) -> int:
    """Посты из старой схемы (в очереди без точного времени) получают умное время."""
    hourly_migrate(db, cfg)
    n = 0
    for m in db.execute("SELECT * FROM materials WHERE status='queued' AND scheduled_at IS NULL ORDER BY id").fetchall():
        if m["channel"] not in cfg["channels"]:
            continue
        st = smart.smart_time(db, cfg, m["channel"], m["rubric"], now, exclude=m["id"])
        store.update(db, m["id"], scheduled_at=(now if m["urgent"] else (st[0] if st else now)).isoformat())
        n += 1
    return n


def sklad_notice(db, cfg: dict, env: dict, channel: str, ids: list[int], now: dt.datetime, log=print, bot=None) -> int:
    """26.10 владелец: «сам по сетке, с вето». Пост склада встал в час → строка в пульт канала с 🗑 (за 30+ мин)."""
    ch = cfg["channels"][channel]
    rows = [m for m in (store.get(db, i) for i in ids) if m is not None and smart.is_sklad(ch, m)]
    if not rows:
        return 0
    from . import bots
    b = bot or bots.for_channel(channel, bots.REG.get("main"))
    owners = [int(x) for x in str(env.get("OWNER_IDS", "")).split(",") if x.strip()]
    n = 0
    for m in rows:
        t = dt.datetime.fromisoformat(m["scheduled_at"]).astimezone(plan.TZ)
        kind = f"📦 Склад «{m['source']}»" if smart.sklad_rubric(ch, m["source"]) else f"📡 Источник {m['source']}"
        txt = (f"⏳ {kind} → {ch.get('title', channel)}: выйдет сам в {t:%H:%M}\n"
               f"{smart.short(m['text'], 80)}\n\nНе нужно — 🗑 Убрать.")
        kb = {"inline_keyboard": [[{"text": "🗑 Убрать", "callback_data": f"del:{m['id']}"}]]}
        for o in owners:
            try:
                b("sendMessage", chat_id=o, text=txt, reply_markup=kb, disable_web_page_preview=True)
                n += 1
            except Exception as e:  # noqa: BLE001 — уведомление не останавливает публикации
                log(f"sklad notice: {type(e).__name__}: {e}")
    return n


async def tick(db, cfg: dict, env: dict, pubs: dict, now: dt.datetime | None = None, log=print) -> dict:
    now = (now or dt.datetime.now(plan.TZ)).astimezone(plan.TZ)
    day = now.date().isoformat()
    out = {"published": 0, "failed": 0, "moved": 0, "ids": [], "errors": []}
    reconcile(db, cfg, now)
    out["namaz"] = await tick_namaz(db, cfg, env, pubs, now, log)
    out["morning"] = await tick_morning(db, cfg, env, pubs, now, log)
    out["extras"] = await tick_extras(db, cfg, env, pubs, now, log)
    for channel in cfg["channels"]:
        placed = smart.fill_from_stock(db, cfg, channel, now)            # 📦 запас → в пустые слоты
        out["ids"] += placed
        sklad_notice(db, cfg, env, channel, placed, now, log)
        try:                                                             # 📣 30.10 протокол: реклама → закрывающий пост
            closer = smart.ad_closer(db, cfg, channel, now)
            if closer:
                out["moved"] += 1
                log(f"{channel}: реклама держалась {smart.hourly(cfg['channels'][channel])['after']} мин — закрываем постом #{closer}")
        except Exception as e:  # noqa: BLE001 — закрывашка не должна ломать публикации
            log(f"ad_closer: {type(e).__name__}: {e}")
        due =[m for m in store.scheduled(db, channel) if dt.datetime.fromisoformat(m["scheduled_at"]) <= now]
        urgent = [m for m in due if m["urgent"]]
        regular = [m for m in due if not m["urgent"]]
        regular.sort(key=lambda m: (not smart.is_ad_rubric(m["rubric"]), m["scheduled_at"]))   # 25.10: реклама — раньше поста сетки
        hold = smart.ad_hold(db, cfg, channel, now)
        for m in urgent:                                     # срочные — все и сразу
            if hold:                                         # 30.10 владелец: реклама держится 10 мин — обещание клиенту
                store.update(db, m["id"], scheduled_at=hold.isoformat())
                out["moved"] += 1
                log(f"{channel}: срочный ждёт рекламу — выйдет в {hold:%H:%M}")
                continue
            ok = await publish_one(db, cfg, env, pubs, channel, m, None, day, log, now)
            if ok == HELD:
                out["moved"] += 1
                continue
            out["published" if ok else "failed"] += 1
            out["ids"].append(m["id"])
            if ok:
                out["moved"] += len(smart.shift_after_urgent(db, cfg, channel, now, now))
            else:
                store.update(db, m["id"], status="failed")
        for m in regular:
            t = dt.datetime.fromisoformat(m["scheduled_at"])
            if now - t > LATE:                                # опоздали надолго — переносим, а не вываливаем пачкой
                st = smart.smart_time(db, cfg, channel, m["rubric"], now, exclude=m["id"])
                if st:
                    store.update(db, m["id"], scheduled_at=st[0].isoformat())
                    out["moved"] += 1
                    continue
            later = smart.collision_defer(db, cfg, channel, m, now)   # ⏱ совпал с рекламой/срочным/протоколом — +10 мин
            if later:
                store.update(db, m["id"], scheduled_at=later.isoformat())
                out["moved"] += 1
                log(f"{channel} {t:%H:%M}: рядом другой пост — выйдет в {later:%H:%M}")
                continue
            ok = await publish_one(db, cfg, env, pubs, channel, m, t.strftime("%H:%M"), day, log, now)
            if ok == HELD:
                out["moved"] += 1
                continue
            out["published" if ok else "failed"] += 1
            out["ids"].append(m["id"])
            if not ok:
                store.update(db, m["id"], status="failed")
            break                                             # обычные — по одному за проход: промежуток сохраняется
    try:                                                      # 🧠 30.10: заказ штаба для куратора (пустые часы)
        from . import needs
        needs.write(db, cfg, now)
    except Exception as e:  # noqa: BLE001 — заказ не должен ломать публикации
        log(f"needs: {type(e).__name__}: {e}")
    return out


async def tick_namaz(db, cfg: dict, env: dict, pubs: dict, now: dt.datetime, log=print) -> int:
    """Намоз: посты на сегодня и завтра (идемпотентно) → публикация наступивших. Важнее любого контента."""
    from . import namaz
    n = 0
    for channel, ch in cfg["channels"].items():
        o = namaz.opts(ch)
        if not o:
            continue
        for d in (now.date(), now.date() + dt.timedelta(days=1)):
            namaz.ensure_day(db, cfg, channel, d, now)
        for r in namaz.due(db, channel, now, o["grace"]):
            p = pubs[ch["publisher"]]
            to = target(cfg, env, channel)
            photo = r["photo"] if "photo" in r.keys() else None
            if photo and not Path(photo).exists():              # баннер пропал с диска — намаз всё равно выходит, текстом
                ERRORS.append(f"⚠️ {ch['title']}: баннер намаза не найден — вышел только текст. Бросьте пост ещё раз.")
                photo = None
            try:
                if photo:                                       # 22.10: готовый пост владельца (баннер + его текст)
                    mid = p.publish_photo(to, photo, r["text"])
                    if ch["publisher"] == "account":
                        mid = await mid
                elif ch["publisher"] == "account":
                    mid = await p.publish(to, r["text"], None, None, False)
                else:
                    mid = p.publish(to, r["text"], None, None, False)
                namaz.mark(db, channel, r["day"], r["key"], "done", mid)
                store.pulse_add(db, channel, now, "namaz")
                log(f"{channel} намоз {r['key']}: опубликовано")
                n += 1
            except PublishError as e:
                namaz.mark(db, channel, r["day"], r["key"], "failed", error=str(e))
                ERRORS.append(f"❌ {ch['title']}: намоз ({r['key']}) не вышел — {e}")
    return n


async def tick_morning(db, cfg: dict, env: dict, pubs: dict, now: dt.datetime, log=print) -> int:
    """Утренний блок: «Бугун — … куни» и «Хайрли тонг» в точное время (готовит Fabrika заранее)."""
    from . import morning
    n = 0
    rem = morning.approval_reminder(db, cfg, now)
    if rem:
        ERRORS.append(rem)
    rep = curator_report(db, cfg, now)
    if rep:
        ERRORS.append(rep)
    ev = evening_report(db, cfg, now)                  # 🧠 30.10: итог дня штаба
    if ev:
        ERRORS.append(ev)
    jc = morning.juma_check(db, now)                   # 23.10: четверг вечером — есть ли видео «Жума» на завтра
    if jc:
        ERRORS.append(jc)
    for channel, ch in cfg["channels"].items():
        o = morning.opts(ch)
        if not o:
            continue
        for d in (now.date(), now.date() + dt.timedelta(days=1)):
            morning.ensure_day(db, cfg, channel, d, now)
        ready, missed = morning.due(db, channel, now, o["grace"], approval=o.get("approval"))
        for r in missed:
            if r["error"] in ("не успели подготовить", "не одобрен"):
                ERRORS.append(f"⚠️ {ch['title']}: {morning.TITLE[r['key']]} не вышел — {r['error']}")
        for r in ready:
            p = pubs[ch["publisher"]]                    # утро — из хаба; канал со своим ботом — свой бот
            to = morning.target(cfg, env, channel)
            hub_chat = int(env["HUB_CHAT_ID"]) if r["hub_msg"] else None
            own = pubs.get(f"bot:{channel}")              # 18.10: у канала свой бот-пульт — утро публикует он
            f = morning.own_file(r["id"])
            try:
                if ch["publisher"] == "bot" and own is not None:
                    if r["hub_msg"]:
                        if not f.exists():
                            raise PublishError("нет готового файла видео для бота канала (пересоберите утро: morning-refresh)")
                        from .fabrika import upload_video
                        btn = share_button(ch)
                        try:
                            from . import bots as _bots
                            res = upload_video(_bots.TOKENS[channel], to, f, r["text"] or "",
                                               {"inline_keyboard": [[btn]]} if btn else None)
                        except Exception as e:  # noqa: BLE001
                            raise PublishError(str(e)) from e
                        mid = int(res["message_id"])
                    else:
                        mid = own.publish(to, r["text"], button=share_button(ch))
                    f.unlink(missing_ok=True)
                elif ch["publisher"] == "account":
                    mid = await p.publish(to, r["text"], hub_chat, r["hub_msg"], bool(r["hub_msg"]))
                else:
                    mid = p.publish(to, r["text"], hub_chat, r["hub_msg"], bool(r["hub_msg"]), button=share_button(ch))
                morning.update(db, r["id"], status="done", message_id=mid)
                store.pulse_add(db, channel, now, "morning")
                log(f"{channel} утро {r['key']}: опубликовано")
                n += 1
            except PublishError as e:
                morning.update(db, r["id"], status="failed", error=str(e)[:300])
                ERRORS.append(f"❌ {ch['title']}: {morning.TITLE[r['key']]} не вышел — {e}")
    return n


async def tick_extras(db, cfg: dict, env: dict, pubs: dict, now: dt.datetime, log=print, fetch=None) -> int:
    """20.10 (перенос из GENPLAN 5): ☀️ погода и курс 07:00, 🌙 Якуний пост 22:00, 📣 рекламные пакеты на N дней."""
    import asyncio
    from . import extras
    extras.ensure_campaigns(db, now, cfg)
    extras.ensure_day(db, cfg, now.date(), now)
    ready, late = extras.due(db, now)
    for r in late:
        extras.mark(db, r, status="skipped", error="служба не работала в это время")
        ch = cfg["channels"].get(r["channel"])
        if ch:
            ERRORS.append(f"⚠️ {ch['title']}: {extras.TITLE[r['key']]} пропущен — служба не работала в это время")
    n = 0
    for r in ready:
        ch = cfg["channels"].get(r["channel"])
        if not ch:
            continue
        to = target(cfg, env, r["channel"])
        p = pubs[ch["publisher"]]
        video = None
        staged = None
        try:
            if r["key"] == "info":
                from . import digest
                get = fetch or digest._get
                try:
                    w = await asyncio.to_thread(digest.weather, get)
                except Exception:  # noqa: BLE001
                    w = None
                try:
                    rt = await asyncio.to_thread(digest.rates, get)
                except Exception:  # noqa: BLE001
                    rt = None
                body = extras.info_text(ch, w, rt, now.date())
                if not body:
                    raise PublishError("нет данных погоды и курса (сайты не ответили)")
                hub_chat, hub_msg, media, ids = None, None, False, []
                if (ch.get("info") or {}).get("video"):          # 🎬 20.10: ролик погоды, подпись — тот же текст
                    try:
                        video = await asyncio.to_thread(extras.weather_video, now.date())
                    except Exception as e:  # noqa: BLE001 — без ролика пост всё равно выходит текстом
                        ERRORS.append(f"⚠️ {ch['title']}: ролик погоды не готов ({e}) — вышел текст")
            else:
                f = extras.final_get(db, r["channel"])
                if not f:
                    extras.mark(db, r, status="skipped", error="Якуний пост не задан")
                    continue
                body, hub_chat, hub_msg, media, ids = f["text"], f["hub_chat"], f["hub_msg"], f["has_media"], f.get("hub_msgs") or []
                # 22.10 аудит: Якуний пост выходил как есть — без юзернейма канала, с чужим латинским хэштегом
                # (#muftiy_minbari). Теперь та же чистка, что у обычных постов: чужие подписи/хэштеги прочь,
                # латиница → кириллица, внизу наша подпись. Рубрику владельца (первая строка-хэштег) оставляем —
                # одну, кириллицей, заглавными (#МУФТИЙ_МИНБАРИ).
                from . import translit
                first = (body or "").strip().split("\n", 1)[0].strip()
                tag = ""
                if first.startswith("#") and " " not in first and len(first) > 2:
                    tag = "#" + translit.to_cyrillic(first[1:]).upper()
                own = tuple(c["username"] for c in cfg["channels"].values())
                sigs = tuple(ch.get("signatures") or ())
                sig = sigs[now.date().toordinal() % len(sigs)] if sigs else ch.get("signature", "")
                body = text.finalize(body, sig, own=own, tag=tag,
                                     signatures=sigs + ((ch.get("signature"),) if ch.get("signature") else ()),
                                     limit=1024 if media else 4096)
                if ch["publisher"] == "account":           # 21.10: в PAPA HUB — только на секунды публикации
                    staged = stage(db, env, pubs, f.get("via"), hub_chat, ids or [hub_msg], bool(media))
                    if staged:
                        hub_chat = int(env["HUB_CHAT_ID"])
                        ids = staged[0] if len(ids) > 1 else []
                        hub_msg = staged[0][0]
            mid = None
            if video:
                try:
                    res = p.publish_file(to, str(video), body, duration=25)   # 27.10: «Эрталабки дайжест» ~25 с
                    mid = await res if asyncio.iscoroutine(res) else res
                except PublishError as e:
                    ERRORS.append(f"⚠️ {ch['title']}: ролик погоды не отправился ({e}) — вышел текст")
                finally:
                    video.unlink(missing_ok=True)
            if mid is not None:
                pass
            elif len(ids) > 1 and ch["publisher"] == "account":
                mid = await p.publish_album(to, hub_chat, ids, body)
            elif ch["publisher"] == "account":
                mid = await p.publish(to, body, hub_chat, hub_msg, media)
            else:
                mid = p.publish(to, body, hub_chat, hub_msg, media, button=share_button(ch))
            extras.mark(db, r, status="done", message_id=mid)
            store.pulse_add(db, r["channel"], now, r["key"])
            log(f"{r['channel']} {r['key']}: опубликовано")
            n += 1
        except PublishError as e:
            extras.mark(db, r, status="failed", error=str(e)[:300])
            ERRORS.append(f"❌ {ch['title']}: {extras.TITLE[r['key']]} не вышел — {e}")
        finally:
            unstage(db, env, staged, log)
    return n


def today_text(db, cfg: dict, now: dt.datetime | None = None) -> str:
    now = (now or dt.datetime.now(plan.TZ)).astimezone(plan.TZ)
    parts = [smart.day_view(db, cfg, c, now) for c in cfg["channels"]]
    modes = ", ".join(f"{ch['title']}: {'🟢 работа' if channel_mode(cfg, c) == 'live' else '🧪 тест'}"
                      for c, ch in cfg["channels"].items())
    return f"Режим — {modes}\n\n" + "\n\n".join(parts)


def evening_report(db, cfg: dict, now: dt.datetime, at: str = "21:45") -> str | None:
    """🧠 30.10 Штаб: один короткий вечерний отчёт владельцу — по каждому каналу: вышло, заполнено часов, пробелы, реклама."""
    if now.time() < plan.slot_time(now.date(), at).time():
        return None
    k = f"evening_report_{now.date().isoformat()}"
    if store.kv_get(db, k):
        return None
    store.kv_set(db, k, "1")
    day = now.date().isoformat()
    lines = [f"🧠 ШТАБ · итог дня {now:%d.%m}"]
    for channel, ch in cfg["channels"].items():
        rows = db.execute("SELECT p.at, m.rubric FROM publications p LEFT JOIN materials m ON m.id=p.material_id "
                          "WHERE p.channel=? AND p.slot_date=? AND p.status='done'", (channel, day)).fetchall()
        ads = sum(1 for r in rows if smart.is_ad_rubric(r["rubric"]))
        o = smart.hourly(ch)
        hrs = ""
        if o:
            span = range(smart.hm(o["from"]).hour, smart.hm(o["to"]).hour + 1)
            got = {dt.datetime.fromisoformat(r["at"]).astimezone(plan.TZ).hour for r in rows
                   if not smart.is_ad_rubric(r["rubric"])}
            empty = [f"{h:02d}" for h in span if h not in got]
            hrs = f" · часы {len(span) - len(empty)}/{len(span)}" + (f" (пусто: {', '.join(empty)})" if empty else " ✅")
        stock = len(store.stock(db, channel))
        lines.append(f"\n{ch.get('title', channel)}: вышло {len(rows)}{hrs} · реклама {ads} · в запасе {stock}")
    return "\n".join(lines)


def curator_report(db, cfg: dict, now: dt.datetime, at: str = "21:30") -> str | None:
    """Раз в день вечером: что нашёл куратор и что из этого взял владелец — по каналам и лучшим источникам."""
    if now.time() < plan.slot_time(now.date(), at).time():
        return None
    k = f"curator_report_{now.date().isoformat()}"
    if store.kv_get(db, k):
        return None
    day = now.date().isoformat()
    rows = db.execute("SELECT channel, source, status FROM materials WHERE source IS NOT NULL AND substr(created_at,1,10)=?",
                      (day,)).fetchall()
    store.kv_set(db, k, "1")
    if not rows:
        return None
    taken = ("queued", "published")
    lines = ["📡 Куратор за сегодня"]
    for ch in sorted({r["channel"] for r in rows}):
        rs = [r for r in rows if r["channel"] == ch]
        t = sum(r["status"] in taken for r in rs)
        title = cfg["channels"].get(ch, {}).get("title", ch)
        lines.append(f"\n{title}: найдено {len(rs)}, взято {t}, ждут ✓ {sum(r['status'] == 'draft' for r in rs)}")
        by: dict[str, list[int]] = {}
        for r in rs:
            by.setdefault(r["source"], [0, 0])
            by[r["source"]][0] += 1
            by[r["source"]][1] += r["status"] in taken
        best = sorted(by.items(), key=lambda x: (-x[1][1], -x[1][0]))[:3]
        lines.append("  лучшие источники: " + ", ".join(f"{s} {v[1]}/{v[0]}" for s, v in best))
    return "\n".join(lines)
