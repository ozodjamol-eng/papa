"""Сортировщик каналов владельца по папкам-назначениям (решение владельца 16.10).

Профиль Разведки (= профиль владельца) читает все свои каналы, ИИ (Gemini, бесплатно) по последним постам
определяет тему каждого канала, и агент создаёт три НОВЫЕ папки Telegram — по одной на наш канал.
Один канал может попасть в несколько папок. Старые папки владельца не трогаются.
Отчёт (что куда и почему) — в pub/morning/folders.json и в «Избранное» профиля."""
from __future__ import annotations

import asyncio
import json
import os
import time
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
    "PAPA·Давра": ("news", "sport", "humor", "useful", "home_business", "interesting", "recipes", "politics_official"),
    "PAPA·Музыка": ("music", "showbiz", "live_music", "humor"),
    "PAPA·Шаҳар": ("local", "useful", "health", "humor", "religion", "recipes"),
    "PAPA·Спорт": ("sport",),                 # для рубрики «Спорт» КАТТА ДАВРА (куратор читает Давра + Спорт)
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


KEYWORDS = {
    "music": ("қўшиқ", "qo'shiq", "qoshiq", "musiqa", "мусиқа", "music", "песн", "клип", "klip", "mp3", "🎵", "🎶", "xonanda", "хонанда"),
    "showbiz": ("шоу", "show", "юлдуз", "yulduz", "звезд", "артист", "artist", "сериал", "kino", "кино"),
    "live_music": ("жонли", "jonli", "ретро", "retro", "концерт", "konsert", "ижро", "ijro"),
    "news": ("янгилик", "yangilik", "новост", "xabar", "хабар", "tezkor", "тезкор", "news", "daryo", "kun.uz", "dunyo"),
    "sport": ("футбол", "futbol", "спорт", "sport", "матч", "лига", "liga", "gol ", " гол"),
    "humor": ("кулги", "kulgi", "ҳажвия", "hajviya", "юмор", "prikol", "прикол", "😂", "🤣", "latifa", "латифа", "comedy"),
    "useful": ("фойдали", "foydali", "маслаҳат", "maslahat", "полезн", "лайфхак", "layfxak", "bilasizmi", "биласизми"),
    "health": ("соғлиқ", "sog'liq", "salomatlik", "саломатлик", "врач", "шифо", "shifo", "tibbiyot", "тиббиёт", "dori", "дори"),
    "home_business": ("бизнес", "biznes", "daromad", "даромад", "заработ", "uyda ", "уйда ", "pul ishlash", "пул ишлаш"),
    "recipes": ("таом", "taom", "рецепт", "retsept", "ошхона", "oshxona", "кулинар", "pishir", "пишир"),
    "local": ("андижон", "andijon", "хўжаобод", "xo'jaobod", "xojaobod", "хожаобод"),
    "religion": ("намоз", "ислом", "islom", "дуо", "duo", "муфтий", "шайх", "shayx", "қуръон", "qur'on", "ҳадис", "hadis"),
    "ads_market": ("бозор", "bozor", "сотилади", "sotiladi", "сотамиз", "нархи", "narxi", "купл", "продаж", "savdo", "доставка"),
    "politics_official": ("пресс", "press", "вазирлиги", "vazirligi", "агентлиги", "agentligi", "департамент", "ҳокимлиги", "hokimligi"),
}


def keyword_cats(ch: dict) -> list[str]:
    """Запасной способ без ИИ: темы по словам в названии (×3) и последних постах."""
    title = (ch.get("title") or "").lower()
    body = " ".join(ch.get("texts") or []).lower()
    score = {c: 3 * sum(w in title for w in ws) + sum(body.count(w) for w in ws) for c, ws in KEYWORDS.items()}
    top = [c for c, v in sorted(score.items(), key=lambda x: -x[1]) if v >= 2][:2]
    return top or ["other"]


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
    errs = []
    key = os.environ["GEMINI_API_KEY"].strip().strip('"').strip("'")
    first = os.environ.get("GEMINI_MODEL", "").strip().strip('"').strip("'").removeprefix("models/")
    for model in dict.fromkeys([m for m in (first, "gemini-flash-latest") if m]):
        for b in (body, {**body, "generationConfig": {k: v for k, v in body["generationConfig"].items()
                                                       if k != "responseMimeType"}}):
            req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                         data=json.dumps(b).encode(),
                                         headers={"content-type": "application/json", "x-goog-api-key": key})
            try:
                data = json.loads(urllib.request.urlopen(req, timeout=90).read())
                parts = ((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
                return "".join(p.get("text", "") for p in parts if not p.get("thought"))
            except urllib.error.HTTPError as e:
                detail = (e.read() or b"")[:160].decode(errors="replace").replace("\n", " ")
                errs.append(f"{model}: {e.code} {detail}")
                if e.code == 429:
                    raise RuntimeError(f"лимит Gemini на сегодня исчерпан ({model})") from None
            except Exception as e:  # noqa: BLE001
                errs.append(f"{model}: {type(e).__name__}")
    raise RuntimeError("; ".join(errs[-3:]) or "Gemini: нет ответа")


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
    """ИИ (Gemini) по пачкам; если ИИ недоступен или исчерпан лимит — темы по ключевым словам (без ИИ)."""
    cats: dict[str, list[str]] = {}
    ai_ok = bool(os.environ.get("GEMINI_API_KEY"))
    for i in range(0, len(channels), batch):
        part = channels[i:i + batch]
        if ai_ok:
            user = "\n\n".join(f"id={c['id']} · «{c['title']}»\n" + "\n".join(f"- {t}" for t in c["texts"]) for c in part)
            got = None
            for attempt in range(3):                 # 503 «перегружена» — пауза и повтор; лимит (429) — сразу на слова
                try:
                    got = parse_json(gemini(SYSTEM, user))
                    break
                except Exception as e:  # noqa: BLE001
                    if "лимит" in str(e) or attempt == 2:
                        log(f"  ИИ недоступен ({str(e)[:90]}) — дальше сортирую по ключевым словам")
                        ai_ok = False
                        break
                    time.sleep(30 * (attempt + 1))
            if got is not None:
                cats.update({str(k): v if isinstance(v, list) else [v] for k, v in got.items()})
                continue
        for c in part:
            cats.setdefault(str(c["id"]), keyword_cats(c))
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
        try:
            await client(UpdateDialogFilterRequest(id=fid, filter=f))
        except Exception as e:  # noqa: BLE001 — без Premium не больше 10 папок: спорт останется внутри «PAPA·Давра»
            log(f"папка «{name}» не создана: {type(e).__name__}: {str(e)[:80]}")
            continue
        done[name] = len(peers)
        log(f"папка «{name}»: {len(peers)} каналов")
        await asyncio.sleep(2)
    return done


SERVICE_TITLES = ("papa hub", "papa склад", "nexus morning pool", "papa test")
SERVICE_USERS = ("PapaGenplanBot", "PaparazziUZ_PultBot")


async def add_service_to_papa(client, log=print) -> int:
    """В папку владельца «PAPA» (⭐) добавить служебные чаты: HUB, СКЛАД, MORNING POOL, тест-группу, бота (разрешение 16.10)."""
    from telethon import utils
    from telethon.tl.functions.messages import GetDialogFiltersRequest, UpdateDialogFilterRequest
    res = await client(GetDialogFiltersRequest())
    papa = None
    for f in getattr(res, "filters", res):
        t = getattr(f, "title", "")
        if str(getattr(t, "text", t)).strip().lower() == "papa" and hasattr(f, "include_peers"):
            papa = f
    if papa is None:
        log("папка «PAPA» не найдена — пропускаю")
        return 0
    have = {utils.get_peer_id(p) for p in papa.include_peers}
    add = []
    async for d in client.iter_dialogs():
        if (d.title or "").lower().startswith(SERVICE_TITLES):
            add.append(d.entity)
    for u in SERVICE_USERS:
        try:
            add.append(await client.get_entity(u))
        except Exception:  # noqa: BLE001
            pass
    n = 0
    for e in add:
        ip = await client.get_input_entity(e)
        if utils.get_peer_id(ip) not in have:
            papa.include_peers.append(ip)
            have.add(utils.get_peer_id(ip))
            n += 1
    if n:
        await client(UpdateDialogFilterRequest(id=papa.id, filter=papa))
    log(f"папка «PAPA»: добавлено служебных чатов {n}")
    return n


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
    try:
        await add_service_to_papa(client, log)
    except Exception as e:  # noqa: BLE001
        log(f"папка «PAPA»: не получилось ({type(e).__name__}: {e})")
    lines = ["📁 PAPA: каналы разложены по папкам-назначениям (проверьте и поправьте вручную):"]
    for f, cs in report.items():
        lines.append(f"\n{f} — {len(cs)}:")
        lines += [f"• {c['title']} ({', '.join(c['cats'])})" for c in cs]
    lines.append(f"\nНе вошли (реклама/другое): {len(unsorted)}")
    text = "\n".join(lines)
    for i in range(0, len(text), 3900):
        await client.send_message("me", text[i:i + 3900], link_preview=False)
    return {"channels": len(chans), "classified": len(cats), "folders": done, "skipped": len(unsorted)}
