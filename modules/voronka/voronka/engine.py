"""Цикл Voronka: новые комментарии → личный ответ в директ со ссылкой.

Защита аккаунта:
- работает только на постах из списка (или на N последних, если включено явно);
- старые комментарии при первом включении поста не трогает (если backlog=false);
- один директ человеку на пост, свои комментарии пропускает;
- не больше max_per_hour отправок в час; при ошибке лимита Meta — пауза;
- dry_run=true: ничего не отправляет, только пишет, что отправил бы."""
from __future__ import annotations

import datetime as dt
import re

from . import store
from .api import ApiError

UTC = dt.timezone.utc


def utcnow() -> dt.datetime:
    return dt.datetime.now(UTC)


def _ts(s: str) -> dt.datetime:
    return dt.datetime.strptime(s.replace("Z", "+0000"), "%Y-%m-%dT%H:%M:%S%z")


def norm(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").casefold()).strip()


def wants_link(text: str, cfg: dict) -> bool:
    if cfg.get("mode", "all") == "all":
        return True
    t = norm(text)
    return any(norm(k) in t for k in cfg.get("keywords", []))


def target_media(ig, cfg: dict, now: dt.datetime) -> list[dict]:
    max_age = dt.timedelta(days=int(cfg.get("max_age_days", 7)))
    recent = ig.recent_media(limit=int(cfg.get("scan_recent", 10)))
    allow = set(cfg.get("posts", []))
    out = []
    for m in recent:
        if now - _ts(m["timestamp"]) > max_age:
            continue
        key_hit = m["id"] in allow or any(p and p.rstrip("/") in (m.get("permalink") or "") for p in allow)
        if key_hit or cfg.get("all_recent", False):
            out.append(m)
    return out


def run_once(ig, db, cfg: dict, now: dt.datetime | None = None, log=print) -> dict:
    s = _run_once(ig, db, cfg, now or utcnow(), log)
    store.kv_set(db, "last_run", f"{(now or utcnow()).isoformat()[:19]} {s}")
    return s


def _run_once(ig, db, cfg: dict, now: dt.datetime, log=print) -> dict:
    at = now.isoformat()
    stats = {"media": 0, "new": 0, "sent": 0, "dry": 0, "dup": 0, "own": 0, "skip": 0, "error": 0, "paused": False}
    pause_until = store.kv_get(db, "pause_until")
    if pause_until and now.isoformat() < pause_until:
        stats["paused"] = True
        log(f"пауза до {pause_until} (лимит Meta)")
        return stats
    dry = bool(cfg.get("dry_run", True))
    hour_cap = int(cfg.get("max_per_hour", 30))
    sent_hour = store.sent_since(db, (now - dt.timedelta(hours=1)).isoformat())
    text_tpl = cfg["dm_text"]
    for m in target_media(ig, cfg, now):
        stats["media"] += 1
        started_key = f"media_started:{m['id']}"
        first_time = store.kv_get(db, started_key) is None
        if first_time:
            store.kv_set(db, started_key, at)
        for c in reversed(ig.comments(m["id"], limit=int(cfg.get("comments_per_poll", 50)))):
            if store.seen(db, c["id"]):
                continue
            u = c.get("from") or {}
            only = {x.lower() for x in cfg.get("only_users", [])}
            is_tester = (u.get("username") or "").lower() in only
            if only and not is_tester:
                continue  # тестовый режим: чужие комментарии не трогаем и не помечаем
            stats["new"] += 1
            if first_time and not cfg.get("backlog", False) and not is_tester:
                store.mark(db, c, m["id"], at, "skip", "до включения")
                stats["skip"] += 1
                continue
            if u.get("id") == ig.user_id or (u.get("username") or "").lower() == cfg.get("own_username", "").lower():
                store.mark(db, c, m["id"], at, "own")
                stats["own"] += 1
                continue
            if not wants_link(c.get("text", ""), cfg):
                store.mark(db, c, m["id"], at, "skip", "нет кодового слова")
                stats["skip"] += 1
                continue
            if u.get("id") and store.already_sent(db, m["id"], u["id"]):
                store.mark(db, c, m["id"], at, "dup")
                stats["dup"] += 1
                continue
            if sent_hour >= hour_cap:
                log(f"достигнут предел {hour_cap}/час — остальные в следующий цикл")
                return stats
            text = text_tpl.replace("{source}", f"ig-{m['id']}")
            if dry:
                store.mark(db, c, m["id"], at, "dry")
                stats["dry"] += 1
                log(f"[проверка] ответил бы @{u.get('username')} на «{(c.get('text') or '')[:40]}»")
                continue
            try:
                ig.private_reply(c["id"], text)
                store.mark(db, c, m["id"], at, "sent")
                stats["sent"] += 1
                sent_hour += 1
            except ApiError as e:
                store.mark(db, c, m["id"], at, "error", str(e))
                stats["error"] += 1
                log(f"ошибка отправки: {e}")
                if str(e.code) in ("4", "17", "32", "613", "10") or "limit" in e.message.lower():
                    until = (now + dt.timedelta(minutes=int(cfg.get("pause_minutes", 60)))).isoformat()
                    store.kv_set(db, "pause_until", until)
                    stats["paused"] = True
                    log(f"Meta ограничивает частоту — пауза до {until}")
                    return stats
    return stats
