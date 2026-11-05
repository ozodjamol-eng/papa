"""⚡ МУҲИМ — срочное полезное без политики (05.11 владелец: «такие срочные, актуальные, не политика — надо делать,
это помогает вовлечению»).

Каждые 20 минут (07:15–21:55 Ташкент) профиль Разведки читает каналы папки «XOJAOBOD CITY» и выбранные владельцем
источники Хўжаобода за последние часы и ищет то, что касается жизни человека СЕГОДНЯ: свет/газ/вода, дороги,
курс и цены на топливо, выходные и праздники, погодные предупреждения, мошенники, пенсии/пособия.
Политика, криминал, аварии и смерти — никогда. Только пост с фото/видео (31.10: пустых постов нет), кадр чистый (Gemini).
Не больше 3 в день на канал. Найденное ПЕРЕСЫЛАЕТСЯ в пульт канала; ключ поста пишется в muhim.json — пульт по нему
показывает карточку «⚡ МУҲИМ»: 🆘 — сразу в канал, 🗑 — не нужно. Без нажатия владельца ничего не выходит."""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import os
import re
from pathlib import Path

from . import curate as C

# Признаки — начало слова, кириллица и латиница (узбекский), плюс русский.
_M = (
    # свет, газ, вода — отключения и подача
    r"электр|elektr|свет(?:а|ни)?(?![\w])|svet(?![\w])|ток(?:ни)?(?![\w])|tok(?:ni)?(?![\w])|газ(?:ни|сиз)?(?![\w])|gaz(?:ni|siz)?(?![\w])|"
    r"ичимлик сув|ichimlik suv|сув(?:ни|сиз)?(?![\w])|suv(?:ni|siz)?(?![\w])|отключ|ўчирил|o[ʻ'’`]chiril|узилиш|uzilish|"
    r"берилмайди|berilmaydi|таъминот|ta[ʼ'ʻ’]?minot|"
    # дороги
    r"йўл ёпил|yo[ʻ'’`]l yopil|ёпилади|yopiladi|айланма йўл|aylanma yo[ʻ'’`]l|перекрыт|тирбандлик|tirbandlik|"
    # деньги на каждый день
    r"доллар курс|dollar kurs|валюта курс|valyuta kurs|курс доллара|бензин|benzin|метан(?![\w])|metan(?![\w])|пропан|propan|"
    r"пенсия|pensiya|нафақа|nafaqa|ойлик|oylik|тариф|tarif|"
    # выходные, праздники
    r"дам олиш кун|dam olish kun|ишланмайди|ishlanmaydi|байрам кун|bayram kun|выходн|"
    # погода — предупреждения
    r"огоҳлантир|ogohlantir|бўрон|bo[ʻ'’`]ron|дўл(?![\w])|do[ʻ'’`]l(?![\w])|сел(?:ь)?(?![\w])|sel(?![\w])|туманли|tumanli|"
    r"кучли шамол|kuchli shamol|кучли ёмғир|kuchli yomg|қор ёғ|qor yog|совуқ|sovuq|аёз|ayoz|"
    # мошенники
    r"фирибгар|firibgar|алдов|aldov|мошенни|смс орқали|sms orqali|карта маълумот|karta ma[ʼ'ʻ’]?lumot"
)
MUHIM = re.compile(r"(?<![\w'ʻ’])(?:" + _M + ")", re.I)
# Никогда: политика, криминал (curate.POLICY) + аварии, смерти, катастрофы — это паника, не польза.
_SAD = (r"ҳалок|halok|вафот|vafot|ўлим|o[ʻ'’`]lim|ўлди|o[ʻ'’`]ldi|жасад|jasad|ЙТҲ|YTH|авари|avariya|"
        r"фалокат|falokat|ёнғин|yong[ʻ'’`]in|портла|portla|погиб|смерт|трагед|теракт")
SAD = re.compile(r"(?<![\w'ʻ’])(?:" + _SAD + ")", re.I)

PER_DAY = int(os.environ.get("MUHIM_PER_DAY", "3"))
HOURS = 3                       # смотрим посты не старше 3 часов — срочное устаревает
MIN_AGE_MIN, MIN_VIEWS = 5, 100
FILE = Path(os.environ.get("SOURCES_MUHIM", "/var/lib/papa-sources-choice/muhim.json"))
CHANNELS = {"xojaobod": ("XOJAOBOD CITY", "XOJAOBODCITY", "PAPA·Шаҳар")}   # 05.11: начинаем с Хўжаобода


def is_muhim(text: str | None) -> bool:
    t = text or ""
    return bool(MUHIM.search(t)) and not SAD.search(t) and not C.POLICY["politics"].search(t) \
        and not C.POLICY["crime"].search(t)


def bot_key(ent_id: int, msg_id: int) -> str:
    """Ключ поста так, как его увидит бот в forward_origin: chat.id = -100<id>, message_id."""
    return f"-100{ent_id}:{msg_id}"


def load(path: Path | None = None) -> dict:
    try:
        return json.loads((path or FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save(data: dict, path: Path | None = None) -> None:
    p = path or FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    try:
        os.chmod(tmp, 0o640)                    # пульт (papa-genplan, группа papa-razvedka) читает
    except OSError:
        pass
    tmp.replace(p)


def mark(data: dict, channel: str, keys: list[str], now: dt.datetime) -> dict:
    """Запомнить пересланные посты (ключи для пульта) — храним 2 дня."""
    keep = {k: v for k, v in (data.get("keys") or {}).items() if v.get("ts", "") > (now - dt.timedelta(days=2)).isoformat()}
    for k in keys:
        keep[k] = {"channel": channel, "ts": now.isoformat()}
    data["keys"] = keep
    return data


def sent_today(data: dict, channel: str, day: str) -> int:
    return int(((data.get("sent") or {}).get(channel) or {}).get(day, 0))


async def run(client, state_dir: Path, now: dt.datetime | None = None, path: Path | None = None, log=print) -> dict:
    now = now or dt.datetime.now(dt.timezone.utc)
    day = (now + dt.timedelta(hours=5)).date().isoformat()          # день по Ташкенту
    data = load(path)
    try:
        cur = json.loads((state_dir / "curator.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cur = {}
    hist = [h for h in (data.get("history") or []) + (cur.get("history") or [])
            if h.get("ts", "") > (now - dt.timedelta(days=3)).isoformat()]
    folders = await C.folder_peers(client)
    from . import sources
    choice = sources.load_choice()
    report = {}
    gemini_ok = bool(os.environ.get("GEMINI_API_KEY"))
    if gemini_ok:
        os.environ["GEMINI_MODEL"] = os.environ.get("CURATOR_GEMINI_MODEL", "gemini-flash-lite-latest")
    for channel, names in CHANNELS.items():
        left = PER_DAY - sent_today(data, channel, day)
        if left <= 0:
            report[channel] = f"лимит дня {PER_DAY} — выполнен"
            continue
        since = dt.datetime.fromisoformat((data.get("last") or {}).get(channel, (now - dt.timedelta(hours=HOURS)).isoformat()))
        since = max(since - dt.timedelta(minutes=MIN_AGE_MIN), now - dt.timedelta(hours=HOURS))
        from telethon.tl.types import PeerChannel
        peers = peers_for(folders, names, choice, channel, PeerChannel)
        cands, seen = [], set()
        for p in peers:
            try:
                ent = await client.get_entity(p)
                if ent.id in seen:
                    continue
                seen.add(ent.id)
                got = await C.candidates(client, ent, since, now, channel, log, min_age=MIN_AGE_MIN, min_views=MIN_VIEWS)
                cands += [c for c in got if is_muhim(c["text"])]
            except Exception as e:  # noqa: BLE001
                log(f"  {type(e).__name__}: {str(e)[:80]}")
            await asyncio.sleep(1)
        sent, keys = 0, []
        for c in C.pick(cands, left * 3, hist):
            if sent >= left:
                break
            if c["kind"] not in ("photo", "video"):
                continue
            ok = None
            if gemini_ok:
                try:
                    ok = await C.clean_frame(client, c)
                except RuntimeError as e:
                    log(f"  проверка кадра: {e}")
                    gemini_ok = False
            hist.append({"key": c["key"], "sig": sorted(C.sig(c["text"])), "ts": now.isoformat()})
            if not ok:                         # чужое лого / не проверить — не берём (правило владельца)
                continue
            new = [bot_key(c["ent"].id, i) for i in c["ids"]]
            save(mark(data, channel, new, now), path)     # ключ — ДО пересылки: пульт должен узнать пост сразу
            try:
                await client.forward_messages(C.BOTS[channel], c["ids"], from_peer=c["ent"])
            except Exception as e:  # noqa: BLE001
                log(f"  переслать {c['key']}: {type(e).__name__}")
                continue
            keys += new
            sent += 1
            log(f"  ⚡ {channel}: {c['source']} · {c['views']} просм. · {c['text'][:60]!r}")
            await asyncio.sleep(4)
        data.setdefault("sent", {}).setdefault(channel, {})
        data["sent"][channel] = {day: sent_today(data, channel, day) + sent}
        if gemini_ok or not cands:
            data.setdefault("last", {})[channel] = now.isoformat()
        report[channel] = {"источников": len(peers), "срочных": len(cands), "переслано": sent,
                           "за день": data["sent"][channel][day]}
        log(f"⚡ {channel}: {report[channel]}")
    data["history"] = [h for h in hist if h.get("key")][-300:]
    save(data, path)
    return report


def peers_for(folders: dict, names, choice: dict | None, channel: str, PeerChannel) -> list:
    """Папка канала + все выбранные владельцем источники (включая новостные — для МУҲИМ они и нужны)."""
    from . import sources
    peers = C.peers_in(folders, names)
    uname = {x["id"]: x.get("username") for xs in (((choice or {}).get("channels") or {}).get(channel) or {}).values()
             for x in xs if x.get("username") and x.get("found_by")}
    peers += [uname[i] if i in uname else PeerChannel(i) for i in sources.ids_for(choice, channel)]
    return peers
