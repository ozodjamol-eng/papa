"""🗃 Хабы направлений (30.10, владелец: «такой расклад нужен каждому направлению — смех, бизнес, музыка…
собирать в один хаб с готовым текстом без юзера; оттуда берут три канала, каждый со своим юзером»).

Агенты (куратор — выбранные Telegram-источники, агент трендов Instagram) кладут ЧИСТЫЙ материал (без чужого лого и @,
наш текст на узбекской кириллице) в хаб своего направления. Каналы берут из хабов как из складов (sklad.py) в свои часы
сетки — при выходе GENPLAN сам ставит @ своего канала. Новости/местное/курс — не вечные, идут как раньше, в пульт.
Хабы — закрытые каналы профиля владельца; нет — агент создаёт сам."""
from __future__ import annotations

import os
import re

# хаб → коды рубрик источников (куратор) и направления трендов Instagram (insta.DIRECTIONS)
HUBS = {
    "РАЗВЛЕКАТЕЛЬНО": {"codes": ("humor", "fun"), "insta": ("humor", "fun_world", "fun")},
    "ФОЙДАЛИК": {"codes": ("useful",), "insta": ("useful",)},
    "ФОЙДАЛИК ОВКАТ": {"codes": ("food",), "insta": ("food",)},
    "МАЪНАВИЯТ": {"codes": ("faith",), "insta": ("faith",), "create": True},   # 30.10 владелец: «создай сам»
    "УЙДА БИЗНЕС": {"codes": ("biz",), "insta": ("biz",), "create": True},
    "МОТИВАЦИЯ": {"codes": ("motiv",), "insta": ("motiv",), "create": True},
    "Jonlik ijrolar": {"codes": ("music",), "insta": ("music",)},
    "ИБРАТ": {"codes": ("ibrat",), "insta": ("ibrat",), "create": True},   # 30.10 владелец: поучительные истории
}
PROMPT = """Сен — Telegram-каналлар учун муҳаррирсан. Пост матнини (ёки видео мавзусини) ўқиб, ўзимизнинг қисқа матнимизни ёз:
биринчи қатор — мос эмодзи билан қисқа сарлавҳа (БОШ ҲАРФЛАР), кейин 1–2 қисқа гап. Фақат ўзбек тилида, КИРИЛЛ алифбосида
(манба русча, инглизча ёки лотинча бўлса — таржима қил). Бошқа каналлар номи, @юзернейм, ҳавола, хэштег, реклама — ЙЎҚ.
Фактлар, дуо, оят, иқтибосларни ўзгартирма. Бугун/кеча/сана ёзма — матн вақтсиз бўлсин. Юзернейм ва чақириқни тизим
ўзи қўшади. Матн бўлмаса — видео мавзусига мос енгил сарлавҳа ёз. Фақат тайёр матнни қайтар."""


def hub_for_code(code: str | None) -> str | None:
    return next((h for h, v in HUBS.items() if code and code in v["codes"]), None)


def hub_for_direction(d: str) -> str | None:
    return next((h for h, v in HUBS.items() if d in v["insta"]), None)


_AT = re.compile(r"(?:https?://\S+|t\.me/\S+|@[A-Za-z0-9_]{4,}|#\S+)")


def clean(text: str) -> str:
    """Подстраховка после ИИ: никаких @, ссылок, хэштегов."""
    t = _AT.sub("", text or "")
    return re.sub(r"[ \t]+\n", "\n", re.sub(r"\n{3,}", "\n\n", t)).strip()


def write(text: str) -> str:
    """Наш текст (Gemini, бесплатно); без ключа/ошибка — исходный, очищенный."""
    import json
    import urllib.request
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        from . import budget
        try:
            budget.gate()                        # 30.10: лимит общий — без Gemini берём исходный текст
        except budget.BudgetStop:
            return clean(text)[:900]
        body = {"systemInstruction": {"parts": [{"text": PROMPT}]},
                "contents": [{"role": "user", "parts": [{"text": f"Матн:\n{(text or '(матн йўқ)')[:2500]}"}]}],
                "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.5}}
        for model in dict.fromkeys([os.environ.get("HUB_TEXT_MODEL", "gemini-flash-latest"), "gemini-flash-lite-latest"]):
            req = urllib.request.Request(f"{('http://127.0.0.1:8790' if os.path.exists('/etc/papa-gemini-proxy/on') else 'https://generativelanguage.googleapis.com')}/v1beta/models/{model}:generateContent",
                                         data=json.dumps(body).encode(),
                                         headers={"content-type": "application/json", "x-goog-api-key": key})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    data = json.loads(r.read())
                parts = ((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
                out = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
                if out:
                    return clean(out)[:900]
            except Exception:  # noqa: BLE001
                continue
    return clean(text)[:900]


async def entity(client, name: str, cache: dict):
    """Хаб по названию среди чатов профиля; нет и можно создавать — создаём закрытый канал."""
    if name in cache:
        return cache[name]
    from telethon.tl.functions.channels import CreateChannelRequest
    want = re.sub(r"[\W_]+", "", name).casefold()
    if not cache.get("_dialogs"):
        cache["_dialogs"] = {}
        async for d in client.iter_dialogs():
            if d.is_channel and not d.is_group:
                cache["_dialogs"][re.sub(r"[\W_]+", "", d.title or "").casefold()] = d.entity
    ent = cache["_dialogs"].get(want)
    if ent is None and HUBS.get(name, {}).get("create"):
        r = await client(CreateChannelRequest(title=name, about="PAPA — хаб направления (чистый материал для каналов)",
                                              megagroup=False))
        ent = r.chats[0]
        cache["_dialogs"][want] = ent
    cache[name] = ent
    return ent


async def put(client, hub_ent, msgs: list, text: str) -> bool:
    """Положить в хаб без подписи «переслано»: медиа (альбом — одним) + наш текст."""
    media = [m.media for m in msgs if getattr(m, "media", None)]
    if not media:
        return False
    try:
        await client.send_file(hub_ent, media if len(media) > 1 else media[0], caption=text or None)
    except TypeError:                     # альбом со смешанным медиа — кладём первое (30.10, 2 случая у архивариуса)
        try:
            await client.send_file(hub_ent, media[0], caption=text or None)
        except TypeError:                 # 31.10: Telegram не даёт переслать это медиа ссылкой — скачать и залить заново
            m = next(x for x in msgs if getattr(x, "media", None))
            data = await client.download_media(m, file=bytes)
            if not data:
                return False
            import io
            f = io.BytesIO(data)
            f.name = "video.mp4" if getattr(m, "video", None) else "photo.jpg"
            await client.send_file(hub_ent, f, caption=text or None, supports_streaming=bool(getattr(m, "video", None)))
    return True


BANK_FOLDER = "KATTA BANK"
BANK_EXTRA_USERS = ["shayx_nuriddinxoliqnazar"]          # 30.10 владелец: канал Муфтия — в банк
BANK_EXTRA_TITLES = ("POOL", "ПУЛ")                      # 30.10: утренний и вечерний пулы — в банк


async def make_bank(client, log=print) -> dict:
    """🏦 30.10 владелец: папка «KATTA BANK» со всеми хабами направлений (новые хабы — создать)."""
    from .sortfolders import create_folders
    cache: dict = {}
    chans, missing = [], []
    for name in HUBS:
        ent = await entity(client, name, cache)
        if ent is None:
            missing.append(name)
            continue
        chans.append({"entity": ent})
        log(f"  🏦 {name}: {'есть' if ent else 'нет'}")
    # 30.10 владелец: «всё в одном месте» — в банк ещё канал Муфтия и наши пулы (утренний, вечерний и др. POOL)
    for u in BANK_EXTRA_USERS:
        try:
            chans.append({"entity": await client.get_entity(u)})
            log(f"  🏦 @{u}: есть")
        except Exception:  # noqa: BLE001
            missing.append("@" + u)
    async for d in client.iter_dialogs():
        t = (d.title or "").upper()
        if d.is_channel and not d.is_group and any(w in t for w in BANK_EXTRA_TITLES):
            chans.append({"entity": d.entity})
            log(f"  🏦 {d.title}: есть")
    # что владелец сам добавил в папку — не теряем
    try:
        from telethon.tl.functions.messages import GetDialogFiltersRequest
        res = await client(GetDialogFiltersRequest())
        for f in getattr(res, "filters", res):
            t = getattr(f, "title", "")
            if getattr(t, "text", t) == BANK_FOLDER:
                chans += [{"entity": pe} for pe in getattr(f, "include_peers", [])]
    except Exception:  # noqa: BLE001
        pass
    seen, uniq = set(), []
    for c in chans:
        e = c["entity"]
        k = getattr(e, "id", None) or getattr(e, "channel_id", None) or getattr(e, "chat_id", None) or getattr(e, "user_id", None) or id(e)
        if k not in seen:
            seen.add(k)
            uniq.append(c)
    done = await create_folders(client, {BANK_FOLDER: uniq}, log=log)
    return {"папка": done, "нет хаба": missing}
