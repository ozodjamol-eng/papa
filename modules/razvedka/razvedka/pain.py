"""«Боль аудитории» (этап А, решение владельца 16.10): читаем комментарии под сильными постами каналов-источников,
раскладываем на вопросы / жалобы / просьбы / шум и считаем, сколько среди них полезного.

Только чтение. Имена и id людей НЕ храним — только текст, дата и реакции; срок хранения 30 дней.
ИИ здесь нет ($0): правила по словам-маркерам, кириллица и латиница. ИИ-выжимка — этап Б, только если этап А покажет пользу."""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import re
from pathlib import Path

from .curate import ROUTES, URL, folder_peers, peers_in

RETENTION_DAYS = 30
POSTS_PER_CHANNEL, COMMENTS_PER_POST, MIN_REPLIES, POST_AGE_DAYS = 8, 60, 3, 3
KINDS = ("request", "complaint", "question", "noise")

SCHEMA = """
CREATE TABLE IF NOT EXISTS comments (
    channel_id INTEGER NOT NULL,
    post_msg_id INTEGER NOT NULL,
    comment_id INTEGER NOT NULL,
    date_utc TEXT NOT NULL,
    text TEXT NOT NULL,
    reactions INTEGER NOT NULL DEFAULT 0,
    kind TEXT NOT NULL,
    collected_at TEXT NOT NULL,
    PRIMARY KEY (channel_id, post_msg_id, comment_id)
);
CREATE INDEX IF NOT EXISTS idx_comments_date ON comments(date_utc);
"""

# Признаки — начало слова. Узбекский (кириллица + латиница) и русский.
_REQUEST = (r"сделайте|добавьте|покажите|снимите|расскажите|хотелось бы|лучше бы|пожалуйста|илтимос|iltimos|қўшинг|qo'shing|"
            r"кўрсатинг|ko'rsating|ёзинг|yozing|олиб келинг|olib keling|керак|kerak|нархи|narxi|қаердан олса|qayerdan olsa|"
            r"бериб\s?юборинг|berib\s?yuboring")
_COMPLAINT = (r"надоел|устал|ужас|плох|обман|не работает|хватит|достал|ёмон|yomon|зерик|zerik|алдов|aldov|афсус|afsus|"
              r"бас қилинг|bas qiling|ҳафа|xafa|шарманда|sharmanda|нега шунча|nega shuncha|ёлғон|yolg'on|бемаъни|bema'ni")
_QUESTION = (r"где|как |как\?|сколько|почему|когда|зачем|кто |что за|қаерда|qayerda|қандай|qanday|қанча|qancha|нега|nega|қачон|"
             r"qachon|ким |kim |нима |nima |қайси|qaysi|қайдан|qayerdan")
REQUEST, COMPLAINT, QUESTION = (re.compile(r"(?<![\w])(?:" + p + ")", re.I) for p in (_REQUEST, _COMPLAINT, _QUESTION))
# Реклама именно в комментариях. «Нархи / narxi» сюда не входит: «Narxi qancha?» — живой интерес покупателя, а не реклама.
SPAM = re.compile(r"#?реклама|#?reklama|📞|☎️|\+998[\s\d-]{9,}|t\.me/\+|joinchat|aksiya|акция|скидк|chegirma|чегирма|"
                  r"подпис|obuna\s?bo|обуна\s?бў|заработ|zarabot|пул\s?ишла|pul\s?ishla|крипт|crypto|казино|casino", re.I)
LETTERS = re.compile(r"[A-Za-zА-Яа-яЁёЎўҚқҒғҲҳ]")


def norm(text: str) -> str:
    t = (text or "").replace("’", "'").replace("ʻ", "'").replace("`", "'").replace("ʼ", "'")
    return re.sub(r"\s+", " ", t).strip()


def classify(text: str) -> str:
    t = norm(text)
    if len(LETTERS.findall(t)) < 4 or SPAM.search(t) or URL.search(t):    # эмодзи, «+», «Супер», реклама, ссылки
        return "noise"
    if REQUEST.search(t):
        return "request"
    if COMPLAINT.search(t):
        return "complaint"
    if "?" in t or QUESTION.search(t):
        return "question"
    return "noise"


def connect(db):
    db.executescript(SCHEMA)
    return db


def purge(db, now: dt.datetime) -> int:
    cut = (now - dt.timedelta(days=RETENTION_DAYS)).isoformat()
    return db.execute("DELETE FROM comments WHERE date_utc < ?", (cut,)).rowcount


def save(db, channel_id: int, post_id: int, items: list[dict], now: dt.datetime) -> int:
    n = 0
    for it in items:
        text = norm(it["text"])[:500]
        if not text:
            continue
        n += db.execute("INSERT OR IGNORE INTO comments VALUES(?,?,?,?,?,?,?,?)",
                        (channel_id, post_id, it["id"], it["date"], text, int(it.get("reactions") or 0),
                         classify(text), now.isoformat())).rowcount
    db.commit()
    return n


def summary(db) -> dict:
    kinds = {k: 0 for k in KINDS}
    for r in db.execute("SELECT kind, COUNT(*) n FROM comments GROUP BY kind"):
        kinds[r["kind"]] = r["n"]
    total = sum(kinds.values())
    useful = total - kinds["noise"]
    return {"total": total, "kinds": kinds, "useful": useful, "useful_pct": round(100 * useful / total) if total else 0}


def samples(db, kind: str, n: int = 4) -> list[str]:
    rows = db.execute("SELECT text FROM comments WHERE kind=? ORDER BY reactions DESC, length(text) DESC LIMIT ?", (kind, n))
    return [r["text"][:140] for r in rows]


async def comments_of(client, ent, post_id: int) -> list[dict]:
    out = []
    async for m in client.iter_messages(ent, reply_to=post_id, limit=COMMENTS_PER_POST, wait_time=1):
        if m.message:
            out.append({"id": m.id, "date": m.date.astimezone(dt.timezone.utc).isoformat(), "text": m.message,
                        "reactions": sum(r.count for r in getattr(getattr(m, "reactions", None), "results", None) or [])})
    return out


async def strong_posts(client, ent, now: dt.datetime) -> list:
    """Свежие посты с живым обсуждением: больше всего ответов, потом просмотров."""
    msgs = [m async for m in client.iter_messages(ent, limit=40, wait_time=1)]
    cut = now - dt.timedelta(days=POST_AGE_DAYS)
    cand = [m for m in msgs if not m.action and m.date >= cut and getattr(m, "replies", None)
            and (m.replies.replies or 0) >= MIN_REPLIES]
    return sorted(cand, key=lambda m: (m.replies.replies, m.views or 0), reverse=True)[:POSTS_PER_CHANNEL]


async def run(client, db, now: dt.datetime | None = None, log=print) -> dict:
    now = now or dt.datetime.now(dt.timezone.utc)
    connect(db)
    purge(db, now)
    folders = await folder_peers(client)
    names = sorted({n for ns in ROUTES.values() for n in ns})
    stat = {"channels": 0, "with_comments": 0, "comments_off": 0, "posts": 0, "new": 0, "errors": 0}
    for name in names:
        for p in peers_in(folders, [name]):
            try:
                ent = await client.get_entity(p)
            except Exception as e:  # noqa: BLE001 — один канал не роняет сбор
                stat["errors"] += 1
                log(f"  {type(e).__name__}: {str(e)[:80]}")
                continue
            stat["channels"] += 1
            try:
                posts = await strong_posts(client, ent, now)
                got = 0
                for m in posts:
                    items = await comments_of(client, ent, m.id)
                    stat["posts"] += 1
                    got += len(items)
                    stat["new"] += save(db, ent.id, m.id, items, now)
                stat["with_comments" if got else "comments_off"] += 1
            except Exception as e:  # noqa: BLE001 — комментарии выключены / лимит Telegram
                stat["comments_off"] += 1
                log(f"  {getattr(ent, 'username', '') or ent.id}: {type(e).__name__}")
            await asyncio.sleep(2)
    return stat


def render(stat: dict, s: dict, db) -> str:
    lines = [f"Каналов: {stat['channels']} · с обсуждениями: {stat['with_comments']} · без комментариев: {stat['comments_off']}",
             f"Постов прочитано: {stat['posts']} · новых комментариев: {stat['new']} · ошибок: {stat['errors']}",
             f"В базе: {s['total']} · полезных (вопрос/жалоба/просьба): {s['useful']} ({s['useful_pct']}%)",
             "  " + " · ".join(f"{k}: {v}" for k, v in s["kinds"].items())]
    for k, title in (("request", "Просьбы"), ("complaint", "Жалобы"), ("question", "Вопросы")):
        ex = samples(db, k, 3)
        if ex:
            lines.append(f"{title}: " + " | ".join(ex))
    return "\n".join(lines)


def dump(db, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary(db), ensure_ascii=False), encoding="utf-8")
