"""Ролик «Об-ҳаво Хўжаобод» на сегодня: прогноз open-meteo → сцена (Canvas, Playwright) → звук → MP4.
Запуск: python3 make.py OUT_DIR   (нужны node+playwright, ffmpeg, numpy). Пишет OUT_DIR/xojaobod-weather-YYYY-MM-DD.mp4 и .json."""
import datetime as dt, json, os, subprocess, sys, urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
TZ = ZoneInfo("Asia/Tashkent")
LAT, LON = 40.6710, 72.5650          # Хўжаобод
HOUR = 7                              # пост выходит в 07:00 — «ҳозир» = прогноз на 07:00
WD = ["ДУШАНБА", "СЕШАНБА", "ЧОРШАНБА", "ПАЙШАНБА", "ЖУМА", "ШАНБА", "ЯКШАНБА"]
MON = ["ЯНВАР", "ФЕВРАЛ", "МАРТ", "АПРЕЛ", "МАЙ", "ИЮН", "ИЮЛ", "АВГУСТ", "СЕНТЯБР", "ОКТЯБР", "НОЯБР", "ДЕКАБР"]


def kind(code: int) -> str:
    c = int(code)
    if c in (0, 1): return "clear"
    if c == 2: return "partly"
    if c == 3: return "cloudy"
    if c in (45, 48): return "fog"
    if c in (71, 73, 75, 77, 85, 86): return "snow"
    if 51 <= c <= 67 or 80 <= c <= 82 or c >= 95: return "rain"
    return "partly"


def day_kind(codes) -> str:
    """Вид погоды по дневным часам 08–17 (суточный код open-meteo — самый «плохой» час, сутки выглядели бы пасмурными)."""
    ks = [kind(c) for c in codes if c is not None] or ["partly"]
    for pr in ("snow", "rain"):
        if ks.count(pr) >= 2:
            return pr
    if ks.count("fog") >= 3:
        return "fog"
    m = sum({"clear": 0, "partly": 1, "cloudy": 2}.get(k, 1) for k in ks) / len(ks)
    return "clear" if m < 0.6 else "partly" if m < 1.4 else "cloudy"


SKY = {"clear": "Очиқ ҳаво, қуёшли", "partly": "Қисман булутли", "cloudy": "Булутли ҳаво", "fog": "Туманли ҳаво",
       "rain": "Ёмғир ёғиши кутилмоқда", "snow": "Қор ёғиши кутилмоқда"}


def data(day: dt.date, get=None) -> dict:
    url = (f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}"
           "&hourly=temperature_2m,weather_code&daily=weather_code,temperature_2m_max,temperature_2m_min,"
           f"precipitation_probability_max&timezone=Asia%2FTashkent&start_date={day}&end_date={day + dt.timedelta(days=2)}")
    f = json.loads((get or (lambda u: urllib.request.urlopen(u, timeout=30).read()))(url))
    h, d = f["hourly"], f["daily"]
    i = h["time"].index(f"{day}T{HOUR:02d}:00")
    hc = lambda dd: [h["weather_code"][h["time"].index(f"{dd}T{x:02d}:00")] for x in range(8, 18)]
    k = day_kind(hc(day))
    return {"city": "ХЎЖАОБОД", "date": f"{WD[day.weekday()]} · {day.day} {MON[day.month - 1]}",
            "now": round(h["temperature_2m"][i]), "hi": round(d["temperature_2m_max"][0]), "lo": round(d["temperature_2m_min"][0]),
            "night": round(d["temperature_2m_min"][1]), "rain": int(d["precipitation_probability_max"][0] or 0),
            "kind": k, "sky": SKY[k], "tHi": round(d["temperature_2m_max"][1]), "tLo": round(d["temperature_2m_min"][2]),
            "tKind": day_kind(hc(day + dt.timedelta(days=1))), "user": "@xojaobodcity24", "day": day.isoformat()}


def build(out: Path, w: dict, fps: int = 60) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    name = f"xojaobod-weather-{w['day']}"
    js, raw, wav, mp4 = out / f"{name}.json", out / "video_raw.mp4", out / "audio.wav", out / f"{name}.mp4"
    js.write_text(json.dumps(w, ensure_ascii=False, indent=1), encoding="utf-8")
    subprocess.run([sys.executable, str(HERE / "audio.py"), str(wav)], check=True)
    subprocess.run(["node", str(HERE / "render.mjs"), str(HERE / "scene.html"), "video", str(fps), str(raw)], check=True,
                   env={**os.environ, "WEATHER_JSON": str(js)})
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-i", str(wav), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", str(mp4)], check=True)
    raw.unlink(missing_ok=True); wav.unlink(missing_ok=True)
    return mp4


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "out")
    day = dt.datetime.now(TZ).date()
    if len(sys.argv) > 2:
        w = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))     # готовые данные (тест вариантов)
    else:
        w = data(day)
    print(json.dumps(w, ensure_ascii=False))
    print(build(out, w))
