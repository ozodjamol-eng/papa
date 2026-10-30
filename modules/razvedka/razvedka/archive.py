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
SCAN = 400                                    # постов просмотреть за запуск
PACE = 5                                      # сек между запросами к Gemini
TAKE = 30                                     # положить в банк за запуск (на канал)
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
        done, skip, per = 0, 0, {}
        for it in picks:
            if done >= TAKE:
                st["pos"][ch] = it["id"] + 1                     # остальные сильные — в следующий запуск
                break
            jpeg = None
            try:
                jpeg = await client.download_media(it["msgs"][0], file=bytes, thumb=-1)
            except Exception:  # noqa: BLE001
                pass
            res = None
            for wait in (0, 65):                                 # 31.10: 429 — чаще всего лимит в минуту; пауза и ещё раз
                if wait:
                    await asyncio.sleep(wait)
                try:
                    res = await asyncio.to_thread(classify, it["text"], jpeg)
                    break
                except RuntimeError as e:
                    if "лимит" not in str(e) or wait:
                        log(f"  {e} — остальное в следующий раз")
                        break
            await asyncio.sleep(PACE)                            # бесплатный Gemini: не больше ~12 запросов в минуту
            if res is None:
                st["pos"][ch] = it["id"]                         # продолжим с этого места
                break
            if res["hub"] == "SKIP":
                skip += 1
                continue
            hub_ent = await hubs.entity(client, res["hub"], cache)
            try:
                if not hub_ent or not await hubs.put(client, hub_ent, sorted(it["msgs"], key=lambda x: x.id), res["text"]):
                    continue
            except Exception as e:  # noqa: BLE001
                log(f"  в хаб: {type(e).__name__}")
                continue
            done += 1
            per[res["hub"]] = per.get(res["hub"], 0) + 1
            log(f"  📚 {ch} #{it['id']} ({it['date']:%Y-%m}) → {res['hub']}")
            await asyncio.sleep(3)
        report[ch] = {"просмотрено": len(items), "сильных": len(picks), "в банк": done, "пропуск": skip, "по хабам": per}
    state_dir.mkdir(parents=True, exist_ok=True)
    sf.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
    return report
