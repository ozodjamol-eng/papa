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
    "МАЪНАВИЯТ": {"codes": ("faith",), "insta": ("faith",)},
    "УЙДА БИЗНЕС": {"codes": ("biz",), "insta": ("biz",), "create": True},
    "МОТИВАЦИЯ": {"codes": ("motiv",), "insta": ("motiv",), "create": True},
    "Jonlik ijrolar": {"codes": ("music",), "insta": ("music",)},
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
        body = {"systemInstruction": {"parts": [{"text": PROMPT}]},
                "contents": [{"role": "user", "parts": [{"text": f"Матн:\n{(text or '(матн йўқ)')[:2500]}"}]}],
                "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.5}}
        for model in dict.fromkeys([os.environ.get("HUB_TEXT_MODEL", "gemini-flash-latest"), "gemini-flash-lite-latest"]):
            req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
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
    await client.send_file(hub_ent, media if len(media) > 1 else media[0], caption=text or None)
    return True
