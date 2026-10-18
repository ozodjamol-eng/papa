"""Самообучение чистки «хвостов» источника (18.10, владелец: «бросил пост и забыл»).

У каждого канала-источника под постами одна и та же подпись: «MANBA — izohlarda», «Telegram|Instagram|…»,
своя строка-реклама. Бот запоминает нижние строки постов по источнику:
  • строка повторилась у одного источника 3 раза → это его хвост, дальше убирается всегда (сам, без владельца);
  • кнопка «🧹 Мусор» в карточке → владелец отмечает строку, бот запоминает её сразу.
Только нижняя часть поста и только повторяющиеся строки — текст автора сверху не трогается.
Посты без источника (не пересланы из канала) сами не учат — только кнопкой владельца.
"""
from __future__ import annotations

import datetime as dt
import re
import unicodedata

LEARN_AT = 3          # столько раз строка внизу постов одного источника → хвост
ZONE = 6              # смотрим только последние N непустых строк
MAX_LEN = 140         # длинная строка — это уже текст, не подпись
NO_SOURCE = "?"

SCHEMA = """
CREATE TABLE IF NOT EXISTS tails (
    source  TEXT NOT NULL,
    key     TEXT NOT NULL,
    line    TEXT NOT NULL,
    n       INTEGER NOT NULL DEFAULT 0,
    learned INTEGER NOT NULL DEFAULT 0,   -- 1 — убирать всегда; 2 — отмечено владельцем
    at      TEXT NOT NULL,
    PRIMARY KEY (source, key)
);
"""


def setup(db) -> None:
    db.executescript(SCHEMA)


def key(line: str) -> str | None:
    t = unicodedata.normalize("NFKC", line or "").lower()
    k = re.sub(r"[\W_]+", "", t)
    return k if len(k) >= 3 else None


def _src(source: str | None) -> str:
    return (source or NO_SOURCE).lower()


def zone(text: str) -> list[str]:
    """Нижние строки поста, которые могут быть подписью источника (первые 2 строки — всегда текст)."""
    lines = [ln for ln in (text or "").split("\n") if ln.strip()]
    if len(lines) < 3:
        return []
    return [ln for ln in lines[max(2, len(lines) - ZONE):] if len(ln.strip()) <= MAX_LEN]


def observe(db, source: str | None, text: str, own: tuple[str, ...] = ()) -> list[str]:
    """Учесть нижние строки нового поста. Возвращает строки, которые только что стали хвостом."""
    if not source:
        return []
    own_l = [o.lower().lstrip("@") for o in own if o]
    now, new, seen = dt.datetime.now(dt.timezone.utc).isoformat(), [], set()
    for ln in zone(text):
        k = key(ln)
        if not k or k in seen or any(o and o in ln.lower() for o in own_l):
            continue
        seen.add(k)
        r = db.execute("SELECT n, learned FROM tails WHERE source=? AND key=?", (_src(source), k)).fetchone()
        n = (r[0] if r else 0) + 1
        learned = (r[1] if r else 0) or int(n >= LEARN_AT)
        db.execute("INSERT INTO tails(source,key,line,n,learned,at) VALUES (?,?,?,?,?,?) "
                   "ON CONFLICT(source,key) DO UPDATE SET n=excluded.n, learned=excluded.learned, at=excluded.at",
                   (_src(source), k, ln.strip(), n, learned, now))
        if learned and not (r and r[1]):
            new.append(ln.strip())
    db.commit()
    return new


def learn(db, source: str | None, line: str) -> bool:
    """Кнопка «🧹 Мусор»: строку убирать всегда для этого источника."""
    k = key(line)
    if not k:
        return False
    db.execute("INSERT INTO tails(source,key,line,n,learned,at) VALUES (?,?,?,?,2,?) "
               "ON CONFLICT(source,key) DO UPDATE SET learned=2, at=excluded.at",
               (_src(source), k, line.strip(), LEARN_AT, dt.datetime.now(dt.timezone.utc).isoformat()))
    db.commit()
    return True


def junk_for(db, source: str | None, text: str) -> list[str]:
    """Строки этого поста, которые бот уже знает как хвост источника."""
    rows = db.execute("SELECT key, learned FROM tails WHERE source=? AND learned>0", (_src(source),)).fetchall()
    if not rows:
        return []
    auto = {r[0] for r in rows if r[1] == 1}          # выучено само — только в нижней части поста
    manual = {r[0] for r in rows if r[1] == 2}        # отмечено владельцем — где угодно, кроме заголовка
    lines = [ln for ln in (text or "").split("\n") if ln.strip()]
    if len(lines) < 2:
        return []
    low = max(1, len(lines) - ZONE - 2)
    out = []
    for i, ln in enumerate(lines):
        if i == 0:                                    # первую строку (заголовок) не трогаем никогда
            continue
        k = key(ln)
        if (k in manual or (k in auto and i >= low)) and ln not in out:
            out.append(ln)
    return out


def stats(db) -> dict:
    rows = db.execute("SELECT source, COUNT(*) FROM tails WHERE learned>0 GROUP BY source").fetchall()
    return {r[0]: r[1] for r in rows}


def merged(db, m) -> list[str]:
    """Все строки-мусор поста: чужие ссылки-слова (при приёме) + выученные хвосты источника (на сейчас)."""
    import json
    keys = m.keys() if hasattr(m, "keys") else []
    junk = json.loads(m["junk"] or "[]") if "junk" in keys and m["junk"] else []
    src = m["source"] if "source" in keys else None
    for ln in junk_for(db, src, m["text"] or ""):
        if ln not in junk:
            junk.append(ln)
    return junk
