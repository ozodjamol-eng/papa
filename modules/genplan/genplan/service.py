"""Служба GENPLAN PAPA: раз в минуту (и сразу после 🆘) публикует посты, чьё точное время наступило.
Режим канала: live — рабочий канал; shadow — тестовые чаты (PAPA TEST GROUP / PAPA TEST).
Якоря (намоз, дуо) и реклама Хўжаобода пока остаются за GENPLAN 5."""
from __future__ import annotations

import datetime as dt
import json

from . import plan, smart, store, text
from .publish import PublishError

ERRORS: list[str] = []             # ошибки публикации — служба сообщает владельцу
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
    """Нижний хук (под юзернеймом). Решение владельца 17.10: по смыслу текста — ИИ (Anthropic).
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


async def publish_one(db, cfg, env, pubs, channel: str, m, slot: str | None, day: str, log=print,
                      now: dt.datetime | None = None) -> bool:
    ch = cfg["channels"][channel]
    own = tuple(c["username"] for c in cfg["channels"].values())
    is_ad = (m["rubric"] or "").lower().startswith("реклама")
    tag = "#РЕКЛАМА" if is_ad else tag_for(cfg, ch, m)
    from . import tails
    junk = tails.merged(db, m)                 # 18.10: + выученные хвосты источника (на момент выхода)
    sigs = tuple(ch.get("signatures") or ())
    sig = sigs[int(m["id"]) % len(sigs)] if sigs else ch.get("signature", "")
    body = text.finalize(m["text"], sig, is_ad=is_ad, own=own, hook=hook_for(cfg, ch, m, db) if not is_ad else "", tag=tag,
                         junk=junk, signatures=sigs + ((ch.get("signature"),) if ch.get("signature") else ()),
                         limit=1024 if m["has_media"] else 4096)
    media = json.loads(m["media"] or "[]") if "media" in m.keys() else []
    hub_ids = json.loads(m["hub_msgs"] or "[]") if "hub_msgs" in m.keys() else []
    via = m["via"] if "via" in m.keys() else None
    p = pub_for(pubs, ch, channel, via, from_hub=str(m["hub_chat"]) == str(env.get("HUB_CHAT_ID")))
    to = target(cfg, env, channel)
    try:
        if len(hub_ids) > 1:                               # альбом — одним постом
            if ch["publisher"] == "account":
                mid = await p.publish_album(to, m["hub_chat"], hub_ids, body)
            else:
                mid = p.publish_album(to, media, body)
        elif ch["publisher"] == "account":
            mid = await p.publish(to, body, m["hub_chat"], m["hub_msg"], bool(m["has_media"]))
        else:
            mid = p.publish(to, body, m["hub_chat"], m["hub_msg"], bool(m["has_media"]), button=share_button(ch))
        store.update(db, m["id"], status="published")
        store.record(db, channel, day, slot, m["id"], "done", mid)
        store.pulse_add(db, channel, now or dt.datetime.now(plan.TZ), "bot")
        log(f"{channel} {slot or 'срочно'}: опубликовано ({m['rubric']})")
        return True
    except PublishError as e:
        store.record(db, channel, day, slot, m["id"], "failed", error=str(e))
        ERRORS.append(f"❌ {ch['title']}: пост не вышел — {e}")
        log(f"{channel} {slot or 'срочно'}: ОШИБКА {e}")
        return False


def reconcile(db, cfg: dict, now: dt.datetime) -> int:
    """Посты из старой схемы (в очереди без точного времени) получают умное время."""
    n = 0
    for m in db.execute("SELECT * FROM materials WHERE status='queued' AND scheduled_at IS NULL").fetchall():
        if m["channel"] not in cfg["channels"]:
            continue
        st = smart.smart_time(db, cfg, m["channel"], m["rubric"], now, exclude=m["id"])
        store.update(db, m["id"], scheduled_at=(now if m["urgent"] else (st[0] if st else now)).isoformat())
        n += 1
    return n


async def tick(db, cfg: dict, env: dict, pubs: dict, now: dt.datetime | None = None, log=print) -> dict:
    now = (now or dt.datetime.now(plan.TZ)).astimezone(plan.TZ)
    day = now.date().isoformat()
    out = {"published": 0, "failed": 0, "moved": 0, "ids": [], "errors": []}
    reconcile(db, cfg, now)
    out["namaz"] = await tick_namaz(db, cfg, env, pubs, now, log)
    out["morning"] = await tick_morning(db, cfg, env, pubs, now, log)
    for channel in cfg["channels"]:
        out["ids"] += smart.fill_from_stock(db, cfg, channel, now)        # 📦 запас → в пустые слоты
        due = [m for m in store.scheduled(db, channel) if dt.datetime.fromisoformat(m["scheduled_at"]) <= now]
        urgent = [m for m in due if m["urgent"]]
        regular = [m for m in due if not m["urgent"]]
        for m in urgent:                                     # срочные — все и сразу
            ok = await publish_one(db, cfg, env, pubs, channel, m, None, day, log, now)
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
            ok = await publish_one(db, cfg, env, pubs, channel, m, t.strftime("%H:%M"), day, log, now)
            out["published" if ok else "failed"] += 1
            out["ids"].append(m["id"])
            if not ok:
                store.update(db, m["id"], status="failed")
            break                                             # обычные — по одному за проход: промежуток сохраняется
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
            try:
                if ch["publisher"] == "account":
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


def today_text(db, cfg: dict, now: dt.datetime | None = None) -> str:
    now = (now or dt.datetime.now(plan.TZ)).astimezone(plan.TZ)
    parts = [smart.day_view(db, cfg, c, now) for c in cfg["channels"]]
    modes = ", ".join(f"{ch['title']}: {'🟢 работа' if channel_mode(cfg, c) == 'live' else '🧪 тест'}"
                      for c, ch in cfg["channels"].items())
    return f"Режим — {modes}\n\n" + "\n\n".join(parts)


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
