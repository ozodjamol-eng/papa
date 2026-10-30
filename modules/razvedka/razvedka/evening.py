"""🌆 Вечерний пул (30.10, владелец: «да» — вечерний пул, как утренний).

Закрытый канал «PAPA ВЕЧЕР ПУЛ» в папке KATTA BANK: спокойные вечерние видео без людей и без логотипов
(закат, вечерний город, осенний вечер, дождь). Зачем: у «Кечки дайжест» каждый вечер новый фон, а не один и тот же.

Как работает (каждый день):
1. Пул тоньше нормы сезона — агент берёт с Pixabay (бесплатно, без логотипов) 1–3 новых видео и кладёт в канал.
2. Канал = источник правды: всё, что в нём (и свои видео владельца), агент приводит к 1080×1920, 20 с, без звука,
   и складывает в /var/lib/papa-evening (<сезон>-<id сообщения>.mp4). Удалил владелец видео в канале — уходит и с диска.
3. GENPLAN в 19:50 кладёт фон дня (по кругу) рядом с данными ролика → рендер в GitHub берёт его вместо осеннего по умолчанию.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import os
import subprocess
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

POOL_TITLE = "PAPA ВЕЧЕР ПУЛ"
OUT = Path(os.environ.get("PAPA_EVENING_DIR", "/var/lib/papa-evening"))
TARGET = 14                    # видео на сезон — две недели без повторов
ADD_PER_RUN = 3
KEEP = 40                      # сколько последних видео канала держать на диске
QUERIES = {
    "kuz": ["autumn sunset", "sunset clouds", "evening city lights", "golden hour trees", "autumn evening",
            "rain window evening", "sunset sky timelapse", "night city timelapse"],
    "qish": ["winter sunset", "snow evening", "winter night city", "snowfall night", "winter sky sunset",
             "christmas lights city"],
    "bahor": ["spring sunset", "evening clouds", "sunset field", "evening city lights"],
    "yoz": ["summer sunset", "sunset sea", "evening city lights", "sunset clouds timelapse"],
}
NO_PEOPLE = {"person", "people", "man", "woman", "girl", "boy", "couple", "child", "children", "crowd", "face",
             "model", "portrait", "selfie", "family", "lady", "men", "women", "bride", "dance", "dancing"}


def season(day: dt.date) -> str:
    m = day.month
    return "qish" if m in (12, 1, 2) else "bahor" if m in (3, 4, 5) else "yoz" if m in (6, 7, 8) else "kuz"


def ok(h: dict) -> bool:
    tags = {t.strip().lower() for t in (h.get("tags") or "").split(",")}
    return 8 <= int(h.get("duration") or 0) <= 60 and not (tags & NO_PEOPLE) and bool(best_file(h))


def best_file(h: dict) -> dict | None:
    """Вертикальное — сразу; иначе самое крупное до 1920 по ширине (кроп 9:16 из 16:9)."""
    v = h.get("videos") or {}
    files = [f for f in (v.get(k) or {} for k in ("large", "medium", "small")) if f.get("url")]
    vert = [f for f in files if int(f.get("height") or 0) > int(f.get("width") or 0) and int(f.get("height") or 0) >= 1280]
    if vert:
        return vert[0]
    hd = [f for f in files if 1280 <= int(f.get("width") or 0) <= 1920]
    return hd[0] if hd else None


def search(key: str, q: str, fetch=None) -> list[dict]:
    url = "https://pixabay.com/api/videos/?" + urllib.parse.urlencode(
        {"key": key, "q": q, "per_page": 50, "safesearch": "true", "order": "popular"})
    if fetch:
        return fetch(url).get("hits") or []
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read()).get("hits") or []


def to_vertical(src: Path, dst: Path) -> Path:
    """1080×1920, 20 с, без звука; горизонталь — кроп по центру."""
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-t", "20", "-an",
                    "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", str(dst)], check=True, timeout=600)
    return dst


def _state(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


async def pool_entity(client):
    from telethon.tl.functions.channels import CreateChannelRequest
    async for d in client.iter_dialogs():
        if d.is_channel and not d.is_group and (d.title or "").strip().upper() == POOL_TITLE:
            return d.entity
    r = await client(CreateChannelRequest(title=POOL_TITLE, megagroup=False,
                                          about="PAPA — вечерние фоны для «Кечки дайжест» (без людей и логотипов)"))
    return r.chats[0]


async def run(client, state_dir: Path, now: dt.datetime | None = None, log=print) -> dict:
    now = now or dt.datetime.now(dt.timezone(dt.timedelta(hours=5)))
    s = season(now.date())
    sf = state_dir / "evening.json"
    st = _state(sf)
    used = set(st.get("pixabay", []))
    OUT.mkdir(parents=True, exist_ok=True)
    ent = await pool_entity(client)
    msgs = [m async for m in client.iter_messages(ent, limit=200) if getattr(m, "video", None)]
    in_season = [m for m in msgs if (st.get("season_of", {}).get(str(m.id)) or s) == s]
    added = 0
    key = os.environ.get("PIXABAY_API_KEY", "").strip()
    if len(in_season) < TARGET and key:
        queries = QUERIES[s]
        start = now.toordinal() % len(queries)
        for i in range(len(queries)):
            if added >= ADD_PER_RUN:
                break
            q = queries[(start + i) % len(queries)]
            try:
                hits = [h for h in search(key, q) if ok(h) and str(h["id"]) not in used]
            except Exception as e:  # noqa: BLE001
                log(f"  Pixabay «{q}»: {type(e).__name__}")
                continue
            for h in hits[:1]:
                f = best_file(h)
                with tempfile.TemporaryDirectory() as tmp:
                    raw, ver = Path(tmp) / "raw.mp4", Path(tmp) / "v.mp4"
                    try:
                        urllib.request.urlretrieve(f["url"], raw)
                        to_vertical(raw, ver)
                        m = await client.send_file(ent, str(ver), caption=f"🌆 {q} · Pixabay #{h['id']}",
                                                   supports_streaming=True)
                    except Exception as e:  # noqa: BLE001
                        log(f"  #{h['id']}: {type(e).__name__}")
                        continue
                used.add(str(h["id"]))
                st.setdefault("season_of", {})[str(m.id)] = s
                added += 1
                log(f"  🌆 + {q} (Pixabay #{h['id']})")
                await asyncio.sleep(3)
        msgs = [m async for m in client.iter_messages(ent, limit=200) if getattr(m, "video", None)]
    # канал → диск (свои видео владельца — текущий сезон)
    keep, got = set(), 0
    for m in msgs[:KEEP]:
        sz = st.setdefault("season_of", {}).setdefault(str(m.id), s)
        name = f"{sz}-{m.id}.mp4"
        keep.add(name)
        dst = OUT / name
        if dst.exists():
            continue
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw.mp4"
            try:
                await client.download_media(m, file=str(raw))
                to_vertical(raw, dst)
                os.chmod(dst, 0o640)
                got += 1
            except Exception as e:  # noqa: BLE001
                log(f"  скачать #{m.id}: {type(e).__name__}")
                dst.unlink(missing_ok=True)
    gone = 0
    for p in OUT.glob("*.mp4"):
        if p.name not in keep:
            p.unlink()
            gone += 1
    st["pixabay"] = sorted(used)
    sf.parent.mkdir(parents=True, exist_ok=True)
    sf.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
    have = sorted(p.name for p in OUT.glob(f"{s}-*.mp4"))
    return {"сезон": s, "в канале": len(msgs), "добавлено": added, "скачано": got, "удалено": gone,
            "фонов сезона": len(have)}


def pick(day: dt.date, folder: Path = OUT) -> Path | None:
    """Фон вечера: по кругу среди фонов сезона (каждый день — следующий)."""
    files = sorted(folder.glob(f"{season(day)}-*.mp4")) if folder.exists() else []
    return files[day.toordinal() % len(files)] if files else None
