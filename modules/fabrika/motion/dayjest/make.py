"""«Эрталабки / Кечки дайжест» Хўжаобод Сити 24 — ролик в стиле iPhone (утверждён владельцем 27.10.2026).

python3 make.py tong OUT_DIR                 → OUT_DIR/xojaobod-weather-ДАТА.mp4 (+.json)  — выходит в 07:00 вместо «Об-ҳаво»
python3 make.py kech OUT_DIR [frankfurt.json] → OUT_DIR/<канал>-digest-ДАТА.mp4 (канал из json: xojaobod | davra) — 20:30
Данные: open-meteo (погода, восход/закат, воздух), cbu.uz (курс; вечером — из данных Франкфурта), Бомдод — от Франкфурта
(время вводит владелец). Фон и музыка — assets/ (Pixabay, лицензия Pixabay), концовка OZOD JAMOL — docs/brand.
Нужны node+playwright, ffmpeg. Нет данных какого-то блока — экрана нет, ролик короче (никаких выдуманных цифр).
"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
TZ = ZoneInfo("Asia/Tashkent")
LAT, LON = 40.6710, 72.5650
# 28.10 владелец: КАТТА ДАВРА тоже на iPhone-дайджесте (без намаза и без рекламной плитки). Старый ролик с новостями убран.
CHANNELS = {
    "xojaobod": {"lat": LAT, "lon": LON, "city": "Хўжаобод", "user": "@xojaobodcity24", "title": "ХЎЖАОБОД СИТИ 24",
                 "bomdod": True, "ad": True},
    "davra": {"lat": 41.2995, "lon": 69.2401, "city": "Тошкент", "user": "@kattadavrauz", "title": "КАТТА ДАВРА",
              "bomdod": False, "ad": False},
}
WD = ["Душанба", "Сешанба", "Чоршанба", "Пайшанба", "Жума", "Шанба", "Якшанба"]
MON = ["январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь"]
DESC = {"clear": "Қуёшли", "partly": "Қисман булутли", "cloudy": "Булутли", "fog": "Туманли", "rain": "Ёмғир", "snow": "Қор"}
OUTRO = {"tong": "OZOD_JAMOL_KONCOVKA_BELAYA.mp4", "kech": "OZOD_JAMOL_KONCOVKA_CHERNAYA.mp4"}
AD = "Мурожаат: @Ozodjamol"     # реклама — только в Хўжаобод Сити 24 (решение владельца 20.10)


def get(url: str, tries: int = 3) -> bytes:
    err = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 PAPA-dayjest"})
            return urllib.request.urlopen(req, timeout=30).read()
        except Exception as e:  # noqa: BLE001
            err = e
            time.sleep(4 * (i + 1))
    raise RuntimeError(f"{url.split('/')[2]}: {err}")


def kind(code) -> str:
    c = int(code)
    if c in (0, 1): return "clear"
    if c == 2: return "partly"
    if c == 3: return "cloudy"
    if c in (45, 48): return "fog"
    if c in (71, 73, 75, 77, 85, 86): return "snow"
    if 51 <= c <= 67 or 80 <= c <= 82 or c >= 95: return "rain"
    return "partly"


def part_kind(codes) -> str:
    ks = [kind(c) for c in codes if c is not None] or ["partly"]
    for pr in ("snow", "rain"):
        if ks.count(pr) >= 2:
            return pr
    if ks.count("fog") >= 3:
        return "fog"
    m = sum({"clear": 0, "partly": 1, "cloudy": 2}.get(k, 1) for k in ks) / len(ks)
    return "clear" if m < 0.6 else "partly" if m < 1.4 else "cloudy"


def icon(k: str, night: bool) -> str:
    if k == "clear": return "moon" if night else "sun"
    if k == "partly": return "partlyn" if night else "partly"
    if k in ("rain", "snow"): return k
    return "cloud"


def hm(iso: str) -> str:
    return iso[11:16]


def daylen(sec) -> str:
    m = int(round(float(sec) / 60))
    return f"Кун узунлиги {m // 60} соат {m % 60} дақиқа"


def tip(parts: list[dict], rain: int, wind: float) -> str:
    lo, hi = min(p["t"] for p in parts), max(p["t"] for p in parts)
    ks = [p["k"] for p in parts]
    if "snow" in ks: return "❄️ Қор ёғади — йўлда эҳтиёт бўлинг"
    if rain >= 50 or "rain" in ks: return "☂️ Ёмғир кутилмоқда — соябон олинг"
    if wind >= 10: return "🌬 Шамол кучли — эҳтиёт бўлинг"
    if hi >= 33: return "💧 Иссиқ — кўпроқ сув ичинг"
    if lo <= 3: return "🧣 Совуқ — иссиқ кийининг"
    if hi - parts[0]["t"] >= 9: return "🧥 Эрталаб салқин — кун давомида илиқ"
    return "🙂 Ҳаво мўътадил — яхши кун!"


AQT = [(50, "Яхши — сайр учун ажойиб"), (100, "Ўртача — сезгир кишилар эҳтиёт бўлсин"),
       (150, "Сезгирлар учун зарарли — узоқ сайр қилманг"), (200, "Зарарли — ташқарида кам бўлинг"),
       (9999, "Жуда зарарли — уйда қолинг")]


def weather(day: dt.date, night_part: bool, lat: float = LAT, lon: float = LON) -> dict:
    """Погода дня day: тонг (08:00), кун (максимум), кеч (19:00); восход/закат; дождь, ветер (м/с)."""
    today = dt.datetime.now(TZ).date()
    f = json.loads(get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
                       "&hourly=temperature_2m,weather_code&daily=temperature_2m_max,precipitation_probability_max,"
                       "wind_speed_10m_max,sunrise,sunset,daylight_duration&timezone=Asia%2FTashkent"
                       f"&start_date={today}&end_date={max(day, today + dt.timedelta(days=1))}"))
    h, d = f["hourly"], f["daily"]
    hix = lambda x: h["time"].index(f"{day}T{x:02d}:00")
    codes = lambda a, b: [h["weather_code"][hix(x)] for x in range(a, b)]
    di = d["time"].index(day.isoformat())
    parts = [{"label": "Тонг", "t": round(h["temperature_2m"][hix(8)]), "k": part_kind(codes(6, 11)), "night": False},
             {"label": "Кун", "t": round(d["temperature_2m_max"][di]), "k": part_kind(codes(11, 17)), "night": False},
             {"label": "Кеч", "t": round(h["temperature_2m"][hix(19)]), "k": part_kind(codes(17, 22)), "night": True}]
    for p in parts:
        p.update(desc="Очиқ ҳаво" if p["night"] and p["k"] == "clear" else DESC[p["k"]], icon=icon(p["k"], p["night"]))
    rain = int(d["precipitation_probability_max"][di] or 0)
    wind = round(float(d["wind_speed_10m_max"][di] or 0) / 3.6)
    return {"parts": parts, "rain": rain, "wind": wind, "sunrise": d["sunrise"], "sunset": d["sunset"],
            "days": d["time"], "daylight": d["daylight_duration"]}


def aqi(lat: float = LAT, lon: float = LON) -> int | None:
    try:
        a = json.loads(get(f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}"
                           "&current=us_aqi&timezone=Asia%2FTashkent"))["current"].get("us_aqi")
        return None if a is None else int(round(a))
    except Exception:  # noqa: BLE001
        return None


def rates() -> list[dict]:
    sign = {"USD": "$", "EUR": "€", "RUB": "₽"}
    try:
        by = {x["Ccy"]: x for x in json.loads(get("https://cbu.uz/uz/arkhiv-kursov-valyut/json/"))}
    except Exception:  # noqa: BLE001
        return []
    return [{"c": c, "s": sign[c], "v": float(by[c]["Rate"]), "d": float(by[c].get("Diff") or 0)} for c in sign if c in by]


def data(mode: str, fk: dict | None = None, channel: str = "xojaobod") -> dict:
    ch = CHANNELS[channel]
    now = dt.datetime.now(TZ)
    today = now.date()
    day = today if mode == "tong" else today + dt.timedelta(days=1)
    w = weather(day, mode == "kech", ch["lat"], ch["lon"])
    i = lambda dd: w["days"].index(dd.isoformat())
    if mode == "tong":
        sun = [{"label": "Бугун қуёш чиқиши", "time": hm(w["sunrise"][i(today)]), "dir": "up"},
               {"label": "Бугун қуёш ботиши", "time": hm(w["sunset"][i(today)]), "dir": "down"}]
        dl, brand, wt, rt = daylen(w["daylight"][i(today)]), "ЭРТАЛАБКИ ДАЙЖЕСТ", "Бугун об-ҳаво", "Бугунги курс · сўм"
        r = (fk or {}).get("rates") or rates()
    else:
        sun = [{"label": "Бугун қуёш ботиши", "time": hm(w["sunset"][i(today)]), "dir": "down"},
               {"label": "Эртага қуёш чиқиши", "time": hm(w["sunrise"][i(day)]), "dir": "up"}]
        dl, brand, wt, rt = daylen(w["daylight"][i(day)]), "КЕЧКИ ДАЙЖЕСТ", "Эртага об-ҳаво", "Валюта курси · сўм"
        r = (fk or {}).get("rates") or rates()
    a = aqi(ch["lat"], ch["lon"])
    d = {"mode": mode, "channel": channel, "day": today.isoformat(), "brand": brand, "city": ch["city"],
         "date": f"{WD[today.weekday()]}, {today.day} {MON[today.month - 1]}",
         "sun": sun, "daylen": dl, "bomdod": ((fk or {}).get("bomdod") or "") if ch["bomdod"] else "",
         "wtitle": wt, "parts": [{k: p[k] for k in ("label", "t", "desc", "icon")} for p in w["parts"]],
         "rw": f"💧 Ёмғир {w['rain']}%   🌬 Шамол {w['wind']} м/с", "tip": tip(w["parts"], w["rain"], w["wind"]),
         "aqi": a, "aqt": next(t for lim, t in AQT if a is not None and a <= lim) if a is not None else "",
         "rtitle": rt, "rates": [{"c": x["c"], "s": x["s"], "v": x["v"], "d": x["d"]} for x in r],
         "ad": (fk or {}).get("ad", AD) if ch["ad"] else "", "adsub": "Ҳар куни минглаб ўқувчи кўради",
         "user": ch["user"], "channel_title": ch["title"]}
    return d


def season(day: dt.date) -> str:
    return "qish" if day.month in (12, 1, 2) else "kuz"     # весна/лето — добавить фоны, когда владелец утвердит


def asset(name: str) -> Path:
    p = HERE / "assets" / name
    if not p.exists() and "_qish" in name:                  # зимнего фона ещё нет — осенний (предупреждение в лог)
        print(f"⚠️ нет {name} — беру осенний фон", flush=True)
        p = HERE / "assets" / name.replace("_qish", "_kuz")
    return p


def build(mode: str, out: Path, d: dict) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    day = d["day"]
    chn = d.get("channel", "xojaobod")
    name = f"{chn}-weather-{day}" if mode == "tong" else f"{chn}-digest-{day}"
    js = out / f"{name}.json"
    js.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    frames, raw, main, mp4 = out / f"{name}-frames", out / f"{name}.raw.mp4", out / f"{name}.main.mp4", out / f"{name}.mp4"
    frames.mkdir(exist_ok=True)
    bg = asset(f"bg_{mode}_{season(dt.date.fromisoformat(day))}.mp4")
    if d.get("_bg") and Path(d["_bg"]).exists():            # 🌆 30.10: фон дня из вечернего пула (Франкфурт)
        bg = Path(d["_bg"])
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-stream_loop", "-1", "-i", str(bg), "-t", "28",
                    "-vf", "fps=30,scale=1080:1920", "-q:v", "3", str(frames / "%04d.jpg")], check=True)
    r = subprocess.run(["node", str(HERE / "render.mjs"), str(HERE / "page.html"), str(js), str(frames), "30", str(raw)],
                       check=True, capture_output=True, text=True)
    print(r.stdout[-400:], flush=True)
    dur = float([ln for ln in r.stdout.splitlines() if ln.startswith("DUR")][-1].split()[1])
    music = asset(f"music_{mode}.mp3")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-i", str(music), "-filter_complex",
                    f"[1:a]atrim=0:{dur},afade=t=in:d=0.8,afade=t=out:st={max(0, dur - 1.2):.2f}:d=1.2,"
                    "aresample=48000,aformat=channel_layouts=stereo[a]", "-map", "0:v", "-map", "[a]",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{dur}", str(main)], check=True)
    outro = REPO / "docs/brand/ozod-jamol/koncovka/2s" / OUTRO[mode]
    if outro.exists():                                        # фирменная концовка OZOD JAMOL (решение владельца 27.10)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(main), "-i", str(outro), "-filter_complex",
                        "[0:v]fps=30,format=yuv420p,setsar=1[v0];[1:v]fps=30,scale=1080:1920,format=yuv420p,setsar=1[v1];"
                        "[0:a]aresample=48000,aformat=channel_layouts=stereo[a0];[1:a]aresample=48000,aformat=channel_layouts=stereo[a1];"
                        "[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]", "-map", "[v]", "-map", "[a]",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "192k",
                        "-movflags", "+faststart", str(mp4)], check=True)
    else:
        main.replace(mp4)
    for p in (raw, main):
        p.unlink(missing_ok=True)
    subprocess.run(["rm", "-rf", str(frames)])
    if mp4.stat().st_size > 45_000_000:                      # предел публикации 49 МБ — пережать, если вдруг больше
        tmp = out / f"{name}.small.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(mp4), "-c:v", "libx264", "-crf", "24", "-c:a", "copy", str(tmp)], check=True)
        tmp.replace(mp4)
    return mp4


if __name__ == "__main__":
    mode, out = sys.argv[1], Path(sys.argv[2])
    fk = None
    if len(sys.argv) > 3 and Path(sys.argv[3]).exists():
        fk = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
    if os.environ.get("DAYJEST_JSON"):                       # готовые данные (проверка)
        d = json.loads(Path(os.environ["DAYJEST_JSON"]).read_text(encoding="utf-8"))
    else:
        d = data(mode, fk, (fk or {}).get("channel") or "xojaobod")
    if len(sys.argv) > 3:                                    # 🌆 30.10: свой фон канала из вечернего пула
        for cand in (f"bg_{mode}_{Path(sys.argv[3]).stem}.mp4", f"bg_{mode}.mp4"):
            if (Path(sys.argv[3]).parent / cand).exists():
                d["_bg"] = str(Path(sys.argv[3]).parent / cand)
                break
    print(json.dumps(d, ensure_ascii=False), flush=True)
    print(build(mode, out, d), flush=True)
