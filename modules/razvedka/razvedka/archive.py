"""📚 Агент-архивариус (30.10, владелец: «в самих наших каналах — дофига готового материала, особенно в PaparazziUZ;
агент ищет в самом канале и сортирует по всей тематике»).

Идёт по истории наших каналов от новых к старым (только посты старше 6 месяцев — значит, повтор уже не надоест),
берёт посты с видео/фото, без рекламы и без привязки к дате, которые набрали больше обычного для своего времени.
Gemini за один вызов: по тексту и кадру решает хаб KATTA BANK (или «пропуск») и пишет свежий текст кириллицей.
Пост кладётся в хаб (без «переслано», без @) — дальше каналы берут из банка, каждый со своим @.
Порция за запуск ограничена (бесплатный лимит Gemini). Прогресс — archive.json (до какого поста дошли)."""
from __future__ import annotations

import asyncio
import base64
import datetime as dt
import json
import os
import statistics
import urllib.request
from pathlib import Path

from . import curate, hubs, sklad

CHANNELS = ["ozodjamoll", "kattadavrauz"]     # 30.10: PaparazziUZ + КАТТА ДАВРА. xojaobodcity24 — группа, просмотров нет → не годится
MIN_AGE = dt.timedelta(days=180)
SCAN = 1500                                   # постов просмотреть за запуск (31.10: отдел Архив — было 400)
PACE = 5                                      # сек между запросами к Gemini
TAKE = 120                                    # положить в банк за запуск (на канал; 31.10 — было 30)
BATCH = 6                                     # 31.10: постов за ОДИН запрос Gemini (было по одному) — в 6 раз дешевле по лимиту
CLASSIFY = """Сен — медиа-архив муҳаррирсан. Telegram-каналимизнинг эски постини (матн ва кадр) кўриб чиқ.
Вазифа: 1) пост қайси бўлимга тегишли — фақат шулардан бири:
"РАЗВЛЕКАТЕЛЬНО" (кулги, ҳажвия, прикол), "Jonlik ijrolar" (қўшиқ, клип, жонли ижро, концерт, мусиқа),
"ФОЙДАЛИК" (фойдали маслаҳат, лайфхак, қизиқарли билим), "ФОЙДАЛИК ОВКАТ" (таом, рецепт, соғлиқ),
"МАЪНАВИЯТ" (дин, дуо, панд-насиҳат), "УЙДА БИЗНЕС" (бизнес, даромад, касб), "МОТИВАЦИЯ" (мотивация, ўз устида ишлаш),
"ИБРАТ" (ибратли ҳикоя ва видео: ҳаётий сабоқ, қилмиш ва оқибат, панд берадиган воқеа),
ёки "SKIP" — эскирган янгилик, реклама, санага боғлиқ табрик, сиёсат, жиноят, қайғули хабар, тушунарсиз.
Иккиланасанми — SKIP.
2) Бўлим SKIP бўлмаса — шу пост учун янги қисқа матн: эмодзили сарлавҳа (БОШ ҲАРФЛАР) ва 1–2 гап, ўзбек тилида КИРИЛЛ
алифбосида, @юзернейм/ҳавола/хэштег/сана йўқ, фактларни ўзгартирма.
Жавоб — ФАҚАТ JSON: {"hub": "...", "text": "..."}"""


def is_candidate(it: dict, now: dt.datetime) -> bool:
    if it["kind"] not in ("video", "photo") or it["ad"]:
        return False
    if now - it["date"] < MIN_AGE:
        return False
    t = it["text"] or ""
    return not sklad.STALE.search(t) and not curate.off_policy(t, "paparazzi")


def strong(items: list[dict]) -> list[dict]:
    """Сильнее обычного своего времени: просмотры против медианы порции."""
    vs = [it["views"] for it in items if it.get("views")]
    med = statistics.median(vs) if vs else 0
    return [it for it in items if it.get("views") and it["views"] >= med * 1.1]


def classify(text: str, jpeg: bytes | None) -> dict:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("нет ключа Gemini")
    from . import budget
    budget.gate()                                  # 30.10: лимит общий — фоновая Разведка уступает ассистенту и постам
    parts = [{"text": CLASSIFY + f"\n\nПост матни:\n{(text or '(матн йўқ)')[:2000]}"}]
    if jpeg:
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(jpeg).decode()}})
    body = {"contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1024, "responseMimeType": "application/json"}}
    last = None
    for model in dict.fromkeys([os.environ.get("ARCHIVE_MODEL", "gemini-flash-lite-latest"), "gemini-flash-latest"]):
        req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                     data=json.dumps(body).encode(), headers={"content-type": "application/json", "x-goog-api-key": key})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
            out = "".join(p.get("text", "") for p in ((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
                          if not p.get("thought"))
            res = json.loads(out[out.find("{"): out.rfind("}") + 1])
            hub = res.get("hub") if res.get("hub") in hubs.HUBS else "SKIP"
            return {"hub": hub, "text": hubs.clean(res.get("text") or "")}
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code == 429:
                raise RuntimeError("лимит Gemini") from None
        except Exception as e:  # noqa: BLE001
            last = type(e).__name__
    raise RuntimeError(f"Gemini: {last}")


CLASSIFY_BATCH = CLASSIFY.split("Жавоб —")[0] + """3) Кадрда бошқа каналнинг логотипи, сув белгиси, @юзернейм ёки TikTok/Instagram/Telegram белгиси борми — "logo": true/false.
Сенга бир нечта пост берилади (№1, №2 …), ҳар бирининг матни ва кадри.
Жавоб — ФАҚАТ JSON рўйхат, ҳар пост учун биттадан, тартиб билан: [{"n": 1, "hub": "...", "text": "...", "logo": false}, …]"""


def classify_batch(posts: list[tuple[str, bytes | None]]) -> list[dict]:
    """31.10 отдел Архив: несколько постов за один запрос. Возвращает [{hub, text, logo}] по порядку; чужое лого → SKIP."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("нет ключа Gemini")
    from . import budget
    budget.gate()
    parts = [{"text": CLASSIFY_BATCH}]
    for i, (text, jpeg) in enumerate(posts, 1):
        parts.append({"text": f"\n№{i}. Пост матни:\n{(text or '(матн йўқ)')[:1200]}"})
        if jpeg:
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(jpeg).decode()}})
    body = {"contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 600 * len(posts) + 400,
                                 "responseMimeType": "application/json"}}
    last = None
    for model in dict.fromkeys([os.environ.get("ARCHIVE_MODEL", "gemini-flash-lite-latest"), "gemini-flash-latest"]):
        req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                     data=json.dumps(body).encode(), headers={"content-type": "application/json", "x-goog-api-key": key})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.loads(r.read())
            out = "".join(p.get("text", "") for p in ((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
                          if not p.get("thought"))
            return parse_batch(out, len(posts))
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code == 429:
                raise RuntimeError("лимит Gemini") from None
        except Exception as e:  # noqa: BLE001
            last = type(e).__name__
    raise RuntimeError(f"Gemini: {last}")


def parse_batch(out: str, n: int) -> list[dict]:
    """Ответ Gemini → ровно n решений по порядку. Чего нет / непонятно / с чужим лого — SKIP (лучше пропустить)."""
    arr = json.loads(out[out.find("["): out.rfind("]") + 1])
    by = {}
    for k, r in enumerate(arr if isinstance(arr, list) else [], 1):
        if isinstance(r, dict):
            by[int(r.get("n") or k)] = r
    res = []
    for i in range(1, n + 1):
        r = by.get(i) or {}
        hub = r.get("hub") if r.get("hub") in hubs.HUBS else "SKIP"
        if r.get("logo") is True or str(r.get("logo")).lower() == "true":
            hub = "SKIP"
        res.append({"hub": hub, "text": hubs.clean(r.get("text") or ""), "logo": bool(r.get("logo") is True)})
    return res


async def run(client, state_dir: Path, now: dt.datetime | None = None, log=print) -> dict:
    now = now or dt.datetime.now(dt.timezone.utc)
    sf = state_dir / "archive.json"
    try:
        st = json.loads(sf.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        st = {}
    cache: dict = {}
    report: dict[str, dict] = {}
    for ch in CHANNELS:
        ent = await client.get_entity(ch)
        pos = int((st.get("pos") or {}).get(ch) or 0)          # до какого id дошли (идём к старым)
        if pos == -1:
            report[ch] = {"готово": "весь архив пройден"}
            continue
        items, groups = [], {}
        kw = {"offset_id": pos} if pos else {"offset_date": now - MIN_AGE}
        last_id = None
        async for m in client.iter_messages(ent, limit=SCAN, wait_time=1, **kw):
            last_id = m.id
            if m.action:
                continue
            if m.grouped_id:
                g = groups.get(m.grouped_id)
                if g:
                    g["msgs"].append(m)
                    g["text"] = g["text"] or (m.message or "")
                    continue
            it = {"id": m.id, "msgs": [m], "kind": curate.kind(m), "text": m.message or "", "date": m.date,
                  "views": m.views or 0, "ad": curate.is_ad(m.message or "", bool(getattr(m, "reply_markup", None)))}
            if m.grouped_id:
                groups[m.grouped_id] = it
            items.append(it)
        # 31.10: молодой канал (старше 6 мес. ещё ничего нет) — не «пройден навсегда», проверим завтра снова
        st.setdefault("pos", {})[ch] = last_id if last_id and len(items) else (-1 if pos else 0)
        picks = strong([it for it in items if is_candidate(it, now)])
        done, skip, logo, per = 0, 0, 0, {}
        queue = picks[:TAKE]
        if len(picks) > TAKE:
            st["pos"][ch] = picks[TAKE]["id"] + 1                # остальные сильные — в следующий запуск
        for b in range(0, len(queue), BATCH):
            chunk = queue[b:b + BATCH]
            thumbs = []
            for it in chunk:
                jpeg = None
                try:
                    jpeg = await client.download_media(it["msgs"][0], file=bytes, thumb=-1)
                except Exception:  # noqa: BLE001
                    pass
                thumbs.append((it["text"], jpeg))
            res = None
            for wait in (0, 65):                                 # 429 — чаще всего лимит в минуту; пауза и ещё раз
                if wait:
                    await asyncio.sleep(wait)
                try:
                    res = await asyncio.to_thread(classify_batch, thumbs)
                    break
                except RuntimeError as e:
                    if "лимит" not in str(e) or wait:
                        log(f"  {e} — остальное в следующий раз")
                        break
            await asyncio.sleep(PACE)
            if res is None:
                st["pos"][ch] = chunk[0]["id"] + 1               # продолжим с этой пачки
                break
            for it, r in zip(chunk, res):
                if r["hub"] == "SKIP":
                    skip += 1
                    logo += r["logo"]
                    continue
                hub_ent = await hubs.entity(client, r["hub"], cache)
                try:
                    if not hub_ent or not await hubs.put(client, hub_ent, sorted(it["msgs"], key=lambda x: x.id), r["text"]):
                        continue
                except Exception as e:  # noqa: BLE001
                    log(f"  в хаб: {type(e).__name__}")
                    continue
                done += 1
                per[r["hub"]] = per.get(r["hub"], 0) + 1
                log(f"  📚 {ch} #{it['id']} ({it['date']:%Y-%m}) → {r['hub']}")
                await asyncio.sleep(3)
        report[ch] = {"просмотрено": len(items), "сильных": len(picks), "в банк": done, "пропуск": skip, "чужое лого": logo, "по хабам": per}
    state_dir.mkdir(parents=True, exist_ok=True)
    sf.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
    return report
