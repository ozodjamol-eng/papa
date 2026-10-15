"""Сортировщик каналов владельца по папкам-назначениям (решение владельца 16.10).

Профиль Разведки (= профиль владельца) читает все свои каналы, ИИ (Gemini, бесплатно) по последним постам
определяет тему каждого канала, и агент создаёт три НОВЫЕ папки Telegram — по одной на наш канал.
Один канал может попасть в несколько папок. Старые папки владельца не трогаются.
Отчёт (что куда и почему) — в pub/morning/folders.json и в «Избранное» профиля."""
from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

CATS = ("news", "sport", "humor", "music", "showbiz", "live_music", "useful", "health", "home_business", "recipes",
        "local", "religion", "interesting", "politics_official", "ads_market", "other")
CAT_RU = {"news": "новости", "sport": "спорт", "humor": "юмор", "music": "музыка", "showbiz": "шоу-бизнес",
          "live_music": "живая музыка/ретро", "useful": "полезное", "health": "здоровье", "home_business": "бизнес из дома",
          "recipes": "рецепты", "local": "Андижон/Хўжаобод", "religion": "религия", "interesting": "интересное",
          "politics_official": "официальное", "ads_market": "купля-продажа/реклама", "other": "другое"}
# папка (до 12 знаков — ограничение Telegram) → темы
FOLDERS = {
    "P→Давра": ("news", "sport", "humor", "useful", "home_business", "interesting", "recipes", "politics_official"),
    "P→Paparazzi": ("music", "showbiz", "live_music", "humor"),
    "P→Хўжаобод": ("local", "useful", "health", "humor", "religion", "recipes"),
}
MAX_IN_FOLDER = 100          # лимит Telegram на папку (без Premium)
SKIP_TITLES = ("papa ", "nexus", "papa hub", "papa склад", "papa test")

SYSTEM = """Ты сортируешь Telegram-каналы по темам для медиа-холдинга в Узбекистане.
Для каждого канала по названию и последним постам выбери 1–2 темы из списка:
news, sport, humor, music, showbiz, live_music, useful, health, home_business, recipes, local, religion, interesting,
politics_official, ads_market, other.
Пояснения: live_music — живые выступления, концерты, ретро-песни; home_business — заработок из дома, лайфхаки для хозяек,
маленький бизнес; local — Андижан, Хўжаобод, местные новости района; ads_market — барахолки, купля-продажа, сплошная реклама;
politics_official — пресс-службы, министерства.
Ответ — ТОЛЬКО JSON: {"<id>": ["тема", "тема"], ...}"""


def folders_for(cats: list[str]) -> list[str]:
    return [f for f, want in FOLDERS.items() if any(c in want for c in cats)]


def plan(channels: list[dict], cats: dict[str, list[str]]) -> dict[str, list[dict]]:
    """Каналы → папки; в папке — самые крупные (по подписчикам) до лимита."""
    out: dict[str, list[dict]] = {f: [] for f in FOLDERS}
    for ch in channels:
        cs = [c for c in cats.get(str(ch["id"]), []) if c in CATS]
        if not cs or "ads_market" in cs and len(cs) == 1:
            continue
        for f in folders_for(cs):
            out[f].append({**ch, "cats": cs})
    for f in out:
        out[f] = sorted(out[f], key=lambda c: -(c.get("subscribers") or 0))[:MAX_IN_FOLDER]
    return out


def gemini(system: str, user: str) -> str:
    body = {"systemInstruction": {"parts": [{"text": system}]}, "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"maxOutputTokens": 4096, "temperature": 0.1, "responseMimeType": "application/json"}}
    err = None
    for model in dict.fromkeys([os.environ.get("GEMINI_MODEL", "gemini-flash-latest"), "gemini-flash-latest", "gemini-2.5-flash"]):
        req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                     data=json.dumps(body).encode(),
                                     headers={"content-type": "application/json", "x-goog-api-key": os.environ["GEMINI_API_KEY"]})
        try:
            data = json.loads(urllib.request.urlopen(req, timeout=90).read())
            parts = ((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
            return "".join(p.get("text", "") for p in parts if not p.get("thought"))
        except urllib.error.HTTPError as e:
            err = f"Gemini {e.code}"
            if e.code not in (429, 500, 503, 404):
                break
        except Exception as e:  # noqa: BLE001
            err = f"Gemini {type(e).__name__}"
    raise RuntimeError(err or "Gemini: нет ответа")


def parse_json(raw: str) -> dict:
    raw = raw.strip().strip("`").removeprefix("json").strip()
    try:
        return json.loads(raw)
    except ValueError:
        a, b = raw.find("{"), raw.rfind("}")
        return json.loads(raw[a:b + 1]) if a >= 0 < b else {}


async def collect(client, log=print) -> list[dict]:
    from telethon.tl.functions.channels import GetFullChannelRequest
    out = []
    async for d in client.iter_dialogs():
        e = d.entity
        if not d.is_channel or getattr(e, "megagroup", False):
            continue
        title = d.title or ""
        if title.lower().startswith(SKIP_TITLES):
            continue
        texts = []
        try:
            async for m in client.iter_messages(e, limit=15):
                if m.message:
                    texts.append(m.message.replace("\n", " ")[:140])
        except Exception:  # noqa: BLE001
            continue
        subs = getattr(e, "participants_count", None)
        if subs is None:
            try:
                subs = (await client(GetFullChannelRequest(e))).full_chat.participants_count
            except Exception:  # noqa: BLE001
                subs = 0
        out.append({"id": e.id, "title": title, "username": getattr(e, "username", None), "subscribers": subs or 0,
                    "texts": texts[:10], "entity": e})
        await asyncio.sleep(1)
    log(f"каналов найдено: {len(out)}")
    return out


def classify(channels: list[dict], batch: int = 10, log=print) -> dict[str, list[str]]:
    cats: dict[str, list[str]] = {}
    for i in range(0, len(channels), batch):
        part = channels[i:i + batch]
        user = "\n\n".join(f"id={c['id']} · «{c['title']}»\n" + "\n".join(f"- {t}" for t in c["texts"]) for c in part)
        try:
            got = parse_json(gemini(SYSTEM, user))
            cats.update({str(k): v if isinstance(v, list) else [v] for k, v in got.items()})
        except Exception as e:  # noqa: BLE001
            log(f"  ИИ: пачка {i // batch + 1} не разобрана ({e})")
    return cats


def _title(text: str):
    """Название папки: в новых версиях Telegram — TextWithEntities, в старых — строка."""
    try:
        from telethon.tl.types import TextWithEntities
        return TextWithEntities(text=text, entities=[])
    except ImportError:
        return text


async def create_folders(client, layout: dict[str, list[dict]], log=print) -> dict[str, int]:
    from telethon.tl.functions.messages import GetDialogFiltersRequest, UpdateDialogFilterRequest
    from telethon.tl.types import DialogFilter
    res = await client(GetDialogFiltersRequest())
    existing = getattr(res, "filters", res)
    used = {getattr(f, "id", 0) for f in existing}
    by_title = {}
    for f in existing:
        t = getattr(f, "title", "")
        by_title[getattr(t, "text", t)] = getattr(f, "id", None)
    done = {}
    for name, chans in layout.items():
        if not chans:
            continue
        fid = by_title.get(name) or next(i for i in range(2, 256) if i not in used)
        used.add(fid)
        peers = [await client.get_input_entity(c["entity"]) for c in chans]
        f = DialogFilter(id=fid, title=_title(name), pinned_peers=[], include_peers=peers, exclude_peers=[])
        await client(UpdateDialogFilterRequest(id=fid, filter=f))
        done[name] = len(peers)
        log(f"папка «{name}»: {len(peers)} каналов")
        await asyncio.sleep(2)
    return done


async def run(client, out_dir: Path, log=print) -> dict:
    chans = await collect(client, log)
    cats = classify(chans, log=log)
    layout = plan(chans, cats)
    report = {f: [{"title": c["title"], "username": c["username"], "subscribers": c["subscribers"],
                   "cats": [CAT_RU.get(x, x) for x in c["cats"]]} for c in cs] for f, cs in layout.items()}
    placed = {c["id"] for cs in layout.values() for c in cs}
    unsorted = [c["title"] for c in chans if c["id"] not in placed]
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "folders.json").write_text(json.dumps({"folders": report, "skipped": unsorted,
                                                      "cats": cats}, ensure_ascii=False), encoding="utf-8")
    done = await create_folders(client, layout, log)
    lines = ["📁 PAPA: каналы разложены по папкам-назначениям (проверьте и поправьте вручную):"]
    for f, cs in report.items():
        lines.append(f"\n{f} — {len(cs)}:")
        lines += [f"• {c['title']} ({', '.join(c['cats'])})" for c in cs]
    lines.append(f"\nНе вошли (реклама/другое): {len(unsorted)}")
    text = "\n".join(lines)
    for i in range(0, len(text), 3900):
        await client.send_message("me", text[i:i + 3900], link_preview=False)
    return {"channels": len(chans), "classified": len(cats), "folders": done, "skipped": len(unsorted)}
