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
    "РАЗВЛЕКАТЕЛЬНО": {"codes": ("humor", "fun"), "insta": ("humor", "fun_world")},
    # 07.11 владелец: «всё по рубрикам, чтобы не было путаницы» — главная рубрика КАТТА ДАВРА получила свой хаб
    "ТРЕНДЛАР": {"codes": ("trend",), "insta": ("fun",)},
    "ФОЙДАЛИК": {"codes": ("useful",), "insta": ("useful",)},
    "ФОЙДАЛИК ОВКАТ": {"codes": ("food",), "insta": ("food",)},
    "МАЪНАВИЯТ": {"codes": ("faith",), "insta": ("faith",), "create": True},   # 30.10 владелец: «создай сам»
    "УЙДА БИЗНЕС": {"codes": ("biz",), "insta": ("biz",), "create": True},
    "МОТИВАЦИЯ": {"codes": ("motiv",), "insta": ("motiv",), "create": True},
    "Jonlik ijrolar": {"codes": ("music",), "insta": ("music", "live", "retro")},   # 12.11: + живые и ретро-хиты
    "ИБРАТ": {"codes": ("ibrat",), "insta": ("ibrat",), "create": True},   # 30.10 владелец: поучительные истории
    # 🕰 06.11 владелец: «если надо — сделаем ещё папки». Поздравления по времени (Хайрли тонг / Жума муборак / Хайрли тун)
    # — отдельно от вечных хабов: из МАЪНАВИЯТ «Жума муборак» ушёл в 20:00. Каналы отсюда сами не берут.
    "ТАБРИКЛАР": {"codes": (), "insta": (), "create": True},
    "РЕТРО КЛИПЛАР": {"codes": (), "insta": ()},   # 12.11: склад «БАНК · РЕТРО» (ролики «РЕТРО ДАВРА»), наполняем сами
    # 12.11 владелец: «ретро есть мировые и есть узбекские — различать». «БАНК · РЕТРО» — мировые; этот — узбекские шлягеры
    # (архивариус собирает из наших каналов, retrouz.py; + подборки YouTube).
    "ЎЗБЕК РЕТРО": {"codes": (), "insta": ()},
    # 12.11 владелец: новые направления трендов Instagram — свои склады (агент создаёт сам). В ворота тем (hubgate.TOPIC)
    # НЕ добавлены нарочно: иначе куратор начнёт уводить туда посты из хабов, которые каналы уже берут в сетку.
    "ТЎЙ": {"codes": (), "insta": ("toy",), "create": True},
    # 07.11: сомнительное (ворота не нашли рубрику) — сюда, а не в чужой хаб; каналы отсюда НЕ берут, владелец разбирает.
    "ТЕКШИРУВ": {"codes": (), "insta": ()},
}
# 07.11 владелец переименовывает хабы в единый вид «БАНК · …» (кириллица). Внутренние ключи прежние;
# по названию в Telegram узнаём и старое, и новое имя — переход без остановки.
TITLES = {"РАЗВЛЕКАТЕЛЬНО": "БАНК · КУЛГИ", "ФОЙДАЛИК": "БАНК · ФОЙДАЛИ", "ФОЙДАЛИК ОВКАТ": "БАНК · ОВҚАТ",
          "МАЪНАВИЯТ": "БАНК · МАЪНАВИЯТ", "УЙДА БИЗНЕС": "БАНК · УЙ БИЗНЕСИ", "МОТИВАЦИЯ": "БАНК · МОТИВАЦИЯ",
          "Jonlik ijrolar": "БАНК · МУСИҚА", "ИБРАТ": "БАНК · ИБРАТ", "ТАБРИКЛАР": "БАНК · ТАБРИКЛАР",
          "ТРЕНДЛАР": "БАНК · ТРЕНДЛАР", "ТЕКШИРУВ": "БАНК · ТЕКШИРУВ", "РЕТРО КЛИПЛАР": "БАНК · РЕТРО",
          "ЎЗБЕК РЕТРО": "БАНК · ЎЗБЕК РЕТРО",
          "ТЎЙ": "БАНК · ТЎЙ"}


def _nn(s) -> str:
    return re.sub(r"[\W_]+", "", str(s or "")).casefold()


def key_of_title(title) -> str | None:
    """Внутренний ключ хаба по названию чата в Telegram (старое или новое «БАНК · …» имя)."""
    t = _nn(title)
    return next((k for k in HUBS if t in (_nn(k), _nn(TITLES.get(k, k)))), None) if t else None
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


CYR = re.compile(r"[А-Яа-яЎўҚқҒғҲҳЁё]")


def is_ours(text: str) -> bool:
    """01.11: наш текст = узбекская кириллица (букв кириллицы больше половины). Иначе в банк не кладём."""
    letters = [ch for ch in (text or "") if ch.isalpha()]
    return len(letters) >= 10 and sum(1 for ch in letters if CYR.match(ch)) >= 0.5 * len(letters)


def write(text: str, prompt: str | None = None) -> str:
    """Наш текст (Gemini, бесплатно). 01.11 владелец (в МАЪНАВИЯТ ушёл сырой «Mention your harami… follow karlo plz»):
    без ключа / лимит / ошибка / ответ не кириллицей — ПУСТО, материал не кладётся. Чужой текст как есть — никогда."""
    import json
    import urllib.request
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        from . import budget
        try:
            budget.gate()                        # 30.10: лимит общий — без Gemini берём исходный текст
        except budget.BudgetStop:
            return ""
        body = {"systemInstruction": {"parts": [{"text": prompt or PROMPT}]},
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
                if out and is_ours(clean(out)):
                    return clean(out)[:900]
            except Exception:  # noqa: BLE001
                continue
    return ""


async def entity(client, name: str, cache: dict):
    """Хаб по названию среди чатов профиля; нет и можно создавать — создаём закрытый канал."""
    if name in cache:
        return cache[name]
    from telethon.tl.functions.channels import CreateChannelRequest
    want = re.sub(r"[\W_]+", "", name).casefold()
    alt = _nn(TITLES.get(name, name))
    if not cache.get("_dialogs"):
        cache["_dialogs"] = {}
        async for d in client.iter_dialogs():
            if d.is_channel and not d.is_group:
                cache["_dialogs"][re.sub(r"[\W_]+", "", d.title or "").casefold()] = d.entity
    ent = cache["_dialogs"].get(alt) or cache["_dialogs"].get(want)
    if ent is None and HUBS.get(name, {}).get("create"):
        r = await client(CreateChannelRequest(title=TITLES.get(name, name), about="PAPA — хаб направления (чистый материал для каналов)",
                                              megagroup=False))
        ent = r.chats[0]
        cache["_dialogs"][want] = ent
    cache[name] = ent
    return ent


GATE_LOG: list[str] = []


async def put(client, hub_ent, msgs: list, text: str, check: bool = True) -> bool:
    """Положить в хаб без подписи «переслано»: медиа (альбом — одним) + наш текст.
    07.11: через ворота (hubgate): копия / музыка без видео / не та тема — не кладём (или кладём в нужный хаб).
    check=False — перенос, который уже решён (чистка): проверка темы не нужна, копии — проверяются."""
    media = [m.media for m in msgs if getattr(m, "media", None)]
    if not media:
        return False
    from .curate import is_news
    if is_news(text) or any(is_news(getattr(m, "message", "") or "") for m in msgs):
        return False                      # 01.11 владелец: новости в банк не кладём («ТАДБИРКОРЛАРГА СОЛИҚДАН ИМТИЁЗ» в УЙДА БИЗНЕС)
    greet = greet_of(text, msgs)
    hub_ent = await greet_redirect(client, hub_ent, text, msgs)
    from . import hubgate as G
    keys: set[str] = set()
    if G.GATE:
        name = G.hub_name(hub_ent)
        if check and not greet and name in G.TOPIC:
            want = G.topic_of(text)
            if want is None:
                GATE_LOG.append(f"{name}: нет ответа ИИ")
                return False
            if want == "NONE":                    # 07.11: не по теме ни одного хаба — в ТЕКШИРУВ на разбор владельцу
                want = "ТЕКШИРУВ"
            if want != name:
                target = await entity(client, want, {})
                if target is None:
                    return False
                GATE_LOG.append(f"{name} → {want}")
                hub_ent, name = target, want
        if name in G.CLOSED:
            GATE_LOG.append(f"{name}: закрыт (религиозное агенты не собирают)")
            return False
        if name in G.VIDEO_ONLY and not any(getattr(m, "video", None) for m in msgs):
            GATE_LOG.append(f"{name}: только видео (фото не кладём)")
            return False
        keys = G.keys_of(msgs, text)
        if keys & await G.index(client, hub_ent):
            GATE_LOG.append(f"{name}: копия")
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
    if keys:
        from . import hubgate as G
        G.remember(hub_ent, keys)
    return True


_REDIRECT_CACHE: dict = {}


def greet_of(text: str | None, msgs: list = ()) -> str | None:
    from . import timing
    return timing.kind(text) or next((k for m in msgs if (k := timing.kind(getattr(m, "message", "") or ""))), None)


async def greet_redirect(client, hub_ent, text: str | None, msgs: list = ()):
    """🕰 06.11: любой агент (архивариус, тренды, куратор) кладёт «Хайрли тонг»/«Жума муборак»/«Хайрли тун»
    не в хаб направления, а в «ТАБРИКЛАР». Хаб «ТАБРИКЛАР» создаётся сам; не вышло — в хаб направления не кладём."""
    from . import timing
    if not greet_of(text, msgs):
        return hub_ent
    tab = await entity(client, timing.HUB, _REDIRECT_CACHE)
    if tab is None:
        raise RuntimeError("нет хаба ТАБРИКЛАР")
    return tab


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


async def purge_raw(client, hours: int = 24, log=print) -> dict:
    """🧹 01.11 владелец: «немедленно просканируй всё, выяви и устрани». Удаляет из хабов банка материал агентов
    (не пересланный, за последние часы) с НЕ нашим текстом — сырой чужой (англ./турец./латиница) или без текста."""
    import datetime as dt
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=hours)
    cache: dict = {}
    out: dict = {}
    for name in HUBS:
        ent = await entity(client, name, cache)
        if not ent:
            continue
        bad, kept = [], 0
        async for m in client.iter_messages(ent, limit=300):
            if m.date < since:
                break
            if getattr(m, "fwd_from", None) or not getattr(m, "media", None):
                kept += 1
                continue                         # пересланное владельцем / текст — не трогаем
            if is_ours(m.message or ""):
                kept += 1
                continue
            bad.append(m)
        for m in bad:
            log(f"  🗑 {name} #{m.id} {m.date:%d.%m %H:%M} · {(m.message or '(без текста)').replace(chr(10), ' ')[:70]!r}")
        if bad:
            await client.delete_messages(ent, [m.id for m in bad])
        out[name] = {"удалено": len(bad), "оставлено": kept}
    return out
