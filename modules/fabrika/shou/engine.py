"""🎤 Движок «Шоу-бизнес янгилик» (шаблон Фабрики №9) — один код на все выпуски PAPARAZZI × КАТТА ДАВРА.

Эталон — ролик «Моҳим» 14.11 (`modules/fabrika/orders/kattadavra/mohim-anons/render.py`): там всё было вписано в код
руками. Здесь то же самое собирается по заданию `job.json` — без правки кода, и здесь, и на GitHub Actions.

  python engine.py analyze <видео>                  — карта исходника: склейки, громкость по полсекунды, цвет акцента
  python engine.py check   <job.json>               — сверка задания с правилами владельца (без рендера)
  python engine.py stills  <job.json> <out.jpg>     — контрольный лист кадров с титрами (быстрая проверка глазами)
  python engine.py render  <job.json> <out.mp4>     — готовый ролик: интро → материал целиком → концовка OZOD JAMOL

job.json (секунды — по ИСХОДНИКУ, интро движок прибавляет сам):
{"src": "artist.mp4",
 "quiet_until": 22.0,          # до этой секунды — вступление и слова артиста: ни голоса, ни титров (правило 3)
 "song_from": 22.0,            # с этой секунды звучит чистая песня; диктор — не раньше чем через 4 с (правило 4)
 "accent": [226, 27, 45],      # цвет акцента по кадрам артиста (analyze подсказывает)
 "titles": [{"lines": ["МОҲИМ"], "at": 27.97, "dur": 0.9}],              # титры-вспышки на склейках, не больше 5
 "caption": {"lines": ["КУТЯПСИЗМИ?", "ИЗОҲДА ЁЗИНГ"], "from": 43.0, "to": 47.2},     # вопрос-призыв (необязательно)
 "window": {"lines": ["КАТТА", "ДАВРА"], "label": "TELEGRAM", "sub": "@kattadavrauz", "from": 51.4, "to": 53.9},
 "voice": [{"file": "m01.mp3", "at": 26.6}],                             # строки диктора (готовые mp3 из «Голоса»)
 "intro": ["PAPARAZZI", "КАТТА ДАВРА"], "outro": "black"}

Правила владельца (14.11, «всегда») зашиты в check(): материал не режется, музыка артиста не отделяется (диктор поверх,
−5 дБ под голосом), вступление и слова артиста не перекрываются, в конце песня звучит одна, концовка OZOD JAMOL всегда."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

W, H, FPS = 1080, 1920, 30
INTRO_N = 45                                   # 1,5 с — интро-плашка, вариант А (утверждён 14.11)
INTRO_S = INTRO_N / FPS
MAX_TITLES = 5
VOICE_AFTER_SONG = 4.0                         # диктор — не раньше 4 с чистой песни
TAIL_ALONE = 2.0                               # в конце песня звучит одна — не меньше 2 с без диктора
DUCK_DB, DUCK_FADE = -5.0, 0.5                 # музыка под диктором −5 дБ, плавно 0,5 с
REPO = Path(__file__).resolve().parents[3]
OUTROS = {"black": "OZOD_JAMOL_KONCOVKA_CHERNAYA.mp4", "white": "OZOD_JAMOL_KONCOVKA_BELAYA.mp4",
          "red": "OZOD_JAMOL_KONCOVKA_KRASNAYA.mp4"}
RED = (226, 27, 45)


def font_path() -> str:
    """Inter Black (жирный — правило 31.10). FONT=… переопределяет; иначе ищем в системе."""
    for p in (os.environ.get("FONT"), "/usr/share/fonts/opentype/inter/Inter-Black.otf",
              "/usr/share/fonts/truetype/inter/Inter-Black.ttf"):
        if p and Path(p).exists():
            return p
    r = subprocess.run(["fc-match", "-f", "%{file}", "Inter:weight=900"], capture_output=True, text=True)
    if r.returncode == 0 and r.stdout.strip() and "Inter" in r.stdout:
        return r.stdout.strip()
    raise SystemExit("NO_FONT: нет Inter Black (apt install fonts-inter или FONT=путь)")


# ---------- исходник ----------
def probe(path: str) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height,r_frame_rate",
                        "-of", "json", path], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"NO_SRC: {path}: {r.stderr.strip()[:200]}")
    d = json.loads(r.stdout)
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), {})
    return {"duration": float(d["format"]["duration"]), "width": v.get("width"), "height": v.get("height"),
            "audio": any(s.get("codec_type") == "audio" for s in d.get("streams", []))}


def cuts(path: str, thr: float = 0.3) -> list[float]:
    """Склейки исходника (секунды) — на них ставим титры и ключевые слова диктора."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", f"select='gt(scene,{thr})',metadata=print:file=-",
                        "-an", "-f", "null", "-"], capture_output=True, text=True)
    out = []
    for line in r.stdout.splitlines():
        if "pts_time:" in line:
            out.append(round(float(line.split("pts_time:")[1].split()[0]), 3))
    return out


def loudness(path: str, step: float = 0.5) -> list[float]:
    """Громкость по полсекунды (дБ, 0 = максимум ролика) — видно, где тихое вступление/речь и где вступает песня."""
    import numpy as np
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "8000", "-f", "s16le", "-"], capture_output=True)
    a = np.frombuffer(r.stdout, dtype=np.int16).astype(np.float32) / 32768
    n = int(8000 * step)
    if len(a) < n:
        return []
    rms = np.sqrt((a[:len(a) // n * n].reshape(-1, n) ** 2).mean(axis=1) + 1e-12)
    db = 20 * np.log10(rms / max(rms.max(), 1e-6))
    return [round(float(x), 1) for x in db]


def accent(path: str, duration: float) -> list[int]:
    """Цвет акцента по кадрам артиста (правило 13.11: цвет подбираем сами по фону, не спрашиваем): самый частый
    насыщенный тон кадров, приведённый к яркому. Кадры серые/тёмные — фирменный красный."""
    import colorsys
    import numpy as np
    hist = np.zeros(36)
    for i in range(8):
        t = duration * (i + 0.5) / 8
        p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", path, "-frames:v", "1", "-vf", "scale=64:114",
                            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
        if len(p.stdout) < 64 * 114 * 3:
            continue
        px = np.frombuffer(p.stdout, dtype=np.uint8).reshape(-1, 3).astype(np.float32) / 255
        mx, mn = px.max(axis=1), px.min(axis=1)
        sat = (mx - mn) / np.maximum(mx, 1e-6)
        good = (sat > 0.45) & (mx > 0.35)
        for r_, g_, b_ in px[good]:
            hist[int(colorsys.rgb_to_hsv(r_, g_, b_)[0] * 36) % 36] += 1
    if hist.sum() < 200:
        return list(RED)
    hue = (int(hist.argmax()) + 0.5) / 36
    return [int(round(c * 255)) for c in colorsys.hsv_to_rgb(hue, 0.86, 0.92)]


def analyze(path: str) -> dict:
    p = probe(path)
    return {**p, "cuts": cuts(path), "loudness_db_per_0.5s": loudness(path) if p["audio"] else [],
            "accent": accent(path, p["duration"])}


# ---------- сверка с правилами ----------
def check(job: dict, src_dur: float, voice_len: dict[str, float]) -> list[str]:
    """Список нарушений правил владельца; пусто — можно собирать."""
    bad = []
    quiet, song = float(job.get("quiet_until", 0)), job.get("song_from")
    if song is None:
        bad.append("нет song_from: неизвестно, где начинается чистая песня — диктора ставить нельзя")
        song = quiet
    song = float(song)
    titles = job.get("titles") or []
    if len(titles) > MAX_TITLES:
        bad.append(f"титров {len(titles)} — можно не больше {MAX_TITLES}")
    for t in titles:
        if not t.get("lines"):
            bad.append("титр без текста")
        if t["at"] < quiet:
            bad.append(f"титр {t.get('lines')} на {t['at']} с — раньше конца слов артиста ({quiet} с)")
        if t["at"] + t.get("dur", 0.9) > src_dur:
            bad.append(f"титр {t.get('lines')} выходит за конец ролика")
    for name in ("caption", "window"):
        x = job.get(name)
        if x and (x["from"] < quiet or x["to"] > src_dur or x["from"] >= x["to"]):
            bad.append(f"{name}: время {x['from']}–{x['to']} вне материала или раньше конца слов артиста")
    spans = []
    for v in job.get("voice") or []:
        n = voice_len.get(v["file"])
        if n is None:
            bad.append(f"нет файла голоса {v['file']}")
            continue
        a, b = float(v["at"]), float(v["at"]) + n
        if a < song + VOICE_AFTER_SONG:
            bad.append(f"голос {v['file']} на {a} с — раньше чем через {VOICE_AFTER_SONG:g} с чистой песни (песня с {song} с)")
        if b > src_dur - TAIL_ALONE:
            bad.append(f"голос {v['file']} кончается на {b:.1f} с — в конце песня должна звучать одна ({TAIL_ALONE:g} с)")
        spans.append((a, b, v["file"]))
    spans.sort()
    for (a1, b1, f1), (a2, b2, f2) in zip(spans, spans[1:]):
        if a2 < b1:
            bad.append(f"голос {f2} начинается раньше, чем кончился {f1}")
    if job.get("outro", "black") not in OUTROS:
        bad.append(f"концовка «{job.get('outro')}» — есть только black / white / red")
    return bad


# ---------- картинка ----------
def _pil():
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    return Image, ImageDraw, ImageFilter, ImageFont


def font_fit(txt: str, maxw: int, start: int = 420):
    _, _, _, ImageFont = _pil()
    s = start
    while True:
        f = ImageFont.truetype(font_path(), s)
        b = f.getbbox(txt)
        if b[2] - b[0] <= maxw or s <= 40:
            return f, b
        s -= 4


def big_title(lines: list[str], color, cy: int = 1180, maxw: int | None = None):
    """Слой титра: белые буквы Black, черта цвета акцента, мягкая тень."""
    import numpy as np
    Image, ImageDraw, ImageFilter, _ = _pil()
    maxw = maxw or (940 if len(lines) == 1 else 760)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    fs = [font_fit(t, maxw) for t in lines]
    tot = sum(b[3] - b[1] for _, b in fs) + (len(lines) - 1) * 40
    y = cy - tot / 2
    for (f, b), t in zip(fs, lines):
        d.text(((W - (b[2] - b[0])) / 2 - b[0], y - b[1]), t, font=f, fill=(255, 255, 255, 255))
        y += b[3] - b[1] + 40
    d.rounded_rectangle([W / 2 - 150, y - 6, W / 2 + 150, y + 14], radius=10, fill=tuple(color) + (255,))
    a = im.split()[3]
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sh.putalpha(a.filter(ImageFilter.GaussianBlur(22)).point(lambda v: min(255, int(v * 1.5))))
    return np.asarray(Image.alpha_composite(sh, im), dtype=np.float32) / 255


def caption_layer(lines: list[str], color):
    """Вопрос-призыв: обычная надпись выше нижней пятой части экрана (зона кнопок Reels). Первая строка — цветом акцента."""
    import numpy as np
    Image, ImageDraw, ImageFilter, _ = _pil()
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    y = 1210
    for i, t in enumerate(lines[:2]):
        f, b = font_fit(t, 960, 112)
        d.text(((W - (b[2] - b[0])) / 2 - b[0], y - b[1]), t, font=f, fill=(tuple(color) if i == 0 else (255, 255, 255)) + (255,))
        y += 135
    a = im.split()[3]
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sh.putalpha(a.filter(ImageFilter.GaussianBlur(16)).point(lambda v: min(255, int(v * 2.2))))
    return np.asarray(Image.alpha_composite(sh, im), dtype=np.float32) / 255


def window_layers(lines: list[str], label: str, sub: str, color):
    """Финальное «окно»: кадр виден сквозь буквы на чёрном, ниже подпись (TELEGRAM / @канал)."""
    import numpy as np
    Image, ImageDraw, _, ImageFont = _pil()
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    y = 760
    for t in lines[:2]:
        f, b = font_fit(t, 980)
        d.text(((W - (b[2] - b[0])) / 2 - b[0], y - b[1]), t, font=f, fill=255)
        y += b[3] - b[1] + 50
    y += 40
    s = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(s)
    for t, size, col, dy in ((label, 58, tuple(color), 0), (sub, 84, (255, 255, 255), 80)):
        if t:
            f = ImageFont.truetype(font_path(), size)
            b = f.getbbox(t)
            ds.text(((W - (b[2] - b[0])) / 2 - b[0], y + dy - b[1]), t, font=f, fill=col + (255,))
    return np.asarray(m, dtype=np.float32) / 255, np.asarray(s, dtype=np.float32) / 255


def _over(fr, layer, op=1.0):
    a = layer[:, :, 3:4] * op
    return fr * (1 - a) + layer[:, :, :3] * a


def _ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def _scaled(layer, s):
    import numpy as np
    Image = _pil()[0]
    if abs(s - 1) < 1e-3:
        return layer
    im = Image.fromarray((layer * 255).astype(np.uint8), "RGBA")
    nw, nh = int(W * s), int(H * s)
    l, t = (nw - W) // 2, (nh - H) // 2
    return np.asarray(im.resize((nw, nh), Image.BICUBIC).crop((l, t, l + W, t + H)), dtype=np.float32) / 255


class Look:
    """Все слои одного выпуска (строятся один раз) + сборка кадра по секунде исходника."""

    def __init__(self, job: dict):
        self.color = tuple(job.get("accent") or RED)
        self.titles = [(t["at"], t["at"] + t.get("dur", 0.9), big_title(t["lines"], self.color, maxw=t.get("maxw")))
                       for t in job.get("titles") or []]
        c, w = job.get("caption"), job.get("window")
        self.cap = (c["from"], c["to"], caption_layer(c["lines"], self.color)) if c else None
        self.win = (w["from"], w["to"], *window_layers(w.get("lines") or ["КАТТА", "ДАВРА"], w.get("label", "TELEGRAM"),
                                                       w.get("sub", "@kattadavrauz"), self.color)) if w else None
        spans = [(a, b) for a, b, _ in self.titles] + ([self.cap[:2]] if self.cap else []) + ([self.win[:2]] if self.win else [])
        self.lo = min((a for a, _ in spans), default=1e9) - 0.1
        self.hi = max((b for _, b in spans), default=-1e9) + 0.1

    def compose(self, fr, t: float):
        for a, b, layer in self.titles:
            if a <= t < b:
                k, kout = (t - a) * FPS, (b - t) * FPS
                op = min(1.0, (k + 1) / 3.0) * min(1.0, kout / 4.0)
                fr = fr + (1 - fr) * max(0.0, 0.42 - 0.14 * k)                 # вспышка на склейке
                fr = _over(fr, _scaled(layer, 1.14 - 0.14 * _ease((k + 1) / 5.0)), op)
        if self.cap and self.cap[0] <= t < self.cap[1]:
            a, b, layer = self.cap
            fr = _over(fr, layer, min(1.0, (t - a) * FPS / 6.0) * min(1.0, (b - t) * FPS / 6.0))
        if self.win and self.win[0] <= t < self.win[1]:
            a, b, m, sub = self.win
            k, kout = (t - a) * FPS, (b - t) * FPS
            dark = _ease(k / 6.0) * min(1.0, kout / 6.0)
            fr = fr * (1 - dark * (1 - m[:, :, None]))
            sop = _ease((k - 10) / 8.0) * min(1.0, kout / 6.0)
            if sop > 0:
                fr = _over(fr, sub, sop)
        return fr


def intro_frames(texts: list[str]):
    """Интро 1,5 с, вариант А: чёрный фон + зерно, вспышка → первое имя, вспышка → второе под ним, третья — в белое. Без звука."""
    import numpy as np
    Image, ImageDraw, ImageFilter, _ = _pil()
    rng = np.random.default_rng(7)

    def tl(txt, cy):
        im = Image.new("L", (W, H), 0)
        f, b = font_fit(txt, 930)
        ImageDraw.Draw(im).text(((W - (b[2] - b[0])) / 2 - b[0], cy - (b[3] - b[1]) / 2 - b[1]), txt, font=f, fill=255)
        return im
    t1, t2 = tl(texts[0], 862), tl(texts[1], 1058)
    a1, a2 = (np.asarray(x, dtype=np.float32) / 255 for x in (t1, t2))
    b1, b2 = (np.asarray(x.filter(ImageFilter.GaussianBlur(21)), dtype=np.float32) / 255 for x in (t1, t2))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

    def g(cx, cy, r):
        return np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * r * r)))
    g1, g2, g3 = g(180, 495, 315), g(915, 1440, 315), g(540, 960, 630)
    dec, F1, F2, F3 = (1.0, 0.75, 0.4, 0.18, 0.06), 4, 19, 34

    def fa(i, s):
        return dec[i - s] if 0 <= i - s < len(dec) else 0.0
    for i in range(INTRO_N):
        fr = np.zeros((H, W), np.float32)
        f1, f2 = fa(i, F1), fa(i, F2)
        if i > F1:
            fr += a1 * 0.96
        if i > F2:
            fr += a2 * 0.96
        fr += b1 * f1 * 0.9 + b2 * f2 * 0.9 + g1 * f1 * 1.15 + 0.12 * f1 + g2 * f2 * 1.15 + 0.12 * f2
        if i >= F3:
            k = (i - F3) / (INTRO_N - 1 - F3)
            k = k * k * (3 - 2 * k)
            fr += g3 * k * 2.2 + k * k * 1.3
        fr = np.clip(fr, 0, 1)
        fr += rng.normal(0, 0.035, (H, W)).astype(np.float32) * (1 - fr * 0.7)
        yield np.repeat((np.clip(fr, 0, 1) * 255).astype(np.uint8)[:, :, None], 3, 2)


FIT = f"scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1"


def _reader(path: str, extra: tuple = ()):
    return subprocess.Popen(["ffmpeg", "-v", "error", *extra, "-i", path, "-vf", f"{FIT},fps={FPS}", "-f", "rawvideo",
                             "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)


def outro_path(job: dict) -> str:
    return str(REPO / "docs/brand/ozod-jamol/koncovka/2s" / OUTROS[job.get("outro", "black")])


def stills(job: dict, out: str, times: list[float] | None = None) -> None:
    """Контрольный лист: кадр на середине каждого титра, призыва и «окна»."""
    import numpy as np
    Image = _pil()[0]
    look = Look(job)
    times = times or [round((a + b) / 2, 2) for a, b, _ in look.titles] + \
        ([round((look.cap[0] + look.cap[1]) / 2, 2)] if look.cap else []) + ([round(look.win[1] - 0.4, 2)] if look.win else [])
    ims = []
    for t in times:
        p = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", job["src"], "-frames:v", "1", "-vf", FIT,
                            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
        if len(p.stdout) < W * H * 3:
            continue
        fr = np.frombuffer(p.stdout, dtype=np.uint8).reshape(H, W, 3).astype(np.float32) / 255
        ims.append(Image.fromarray((np.clip(look.compose(fr, t), 0, 1) * 255).astype(np.uint8)).resize((360, 640)))
    sheet = Image.new("RGB", (360 * max(len(ims), 1), 640))
    for i, im in enumerate(ims):
        sheet.paste(im, (360 * i, 0))
    sheet.save(out, quality=88)


# ---------- звук ----------
def duck_expr(spans: list[tuple[float, float]]) -> str:
    """Громкость музыки по времени (ffmpeg volume, eval=frame): 1 → −5 дБ под каждой строкой диктора, плавно 0,5 с."""
    g = 10 ** (DUCK_DB / 20)
    if not spans:
        return "1"
    parts = [f"clip((t-{a - DUCK_FADE:.3f})/{DUCK_FADE},0,1)*clip(({b + DUCK_FADE:.3f}-t)/{DUCK_FADE},0,1)" for a, b in spans]
    return f"1-{1 - g:.4f}*min(1,{'+'.join(parts)})"


def audio_filter(job: dict, voice_len: dict[str, float], src_dur: float, has_audio: bool) -> tuple[str, int]:
    """filter_complex звука. Входы: 0 — видеоряд, 1 — исходник, 2 — концовка, 3… — строки диктора.
    Исходник как есть (общий loudnorm по музыке не делаем), под диктором −5 дБ; голос — EQ + компрессор + loudnorm −13;
    общий лимитер; после материала — звук концовки OZOD JAMOL."""
    voices = job.get("voice") or []
    spans = [(INTRO_S + v["at"], INTRO_S + v["at"] + voice_len[v["file"]]) for v in voices]
    main = INTRO_S + src_dur
    fmt = "aformat=sample_rates=44100:channel_layouts=stereo"
    src = (f"[1:a]{fmt},adelay={int(INTRO_S * 1000)}:all=1" if has_audio
           else f"anullsrc=r=44100:cl=stereo,atrim=0:{main:.3f}")
    fc = [f"{src},volume='{duck_expr(spans)}':eval=frame[m]"]
    names = ["[m]"]
    for i, v in enumerate(voices):
        fc.append(f"[{3 + i}:a]{fmt},highpass=f=80,equalizer=f=3200:t=q:w=1.2:g=2.5,"
                  f"acompressor=threshold=-18dB:ratio=3:attack=8:release=120,loudnorm=I=-13:TP=-1.5:LRA=7,"
                  f"{fmt},adelay={int((INTRO_S + v['at']) * 1000)}:all=1[v{i}]")
        names.append(f"[v{i}]")
    fc.append(f"{''.join(names)}amix=inputs={len(names)}:normalize=0:duration=longest,alimiter=limit=0.94,"
              f"apad,atrim=0:{main:.3f},asetpts=PTS-STARTPTS[a0]")
    fc.append(f"[2:a]{fmt},asetpts=PTS-STARTPTS[o];[a0][o]concat=n=2:v=0:a=1[a]")
    return ";".join(fc), len(voices)


# ---------- сборка ----------
def voice_lengths(job: dict) -> dict[str, float]:
    out = {}
    for v in job.get("voice") or []:
        if Path(v["file"]).exists():
            out[v["file"]] = probe(v["file"])["duration"]
    return out


def load(path: str) -> dict:
    job = json.loads(Path(path).read_text(encoding="utf-8"))
    base = Path(path).resolve().parent
    job["src"] = str((base / job["src"]).resolve()) if not os.path.isabs(job["src"]) else job["src"]
    for v in job.get("voice") or []:
        if not os.path.isabs(v["file"]):
            v["file"] = str((base / v["file"]).resolve())
    return job


def render(job: dict, out: str, log=print) -> dict:
    import numpy as np
    p = probe(job["src"])
    vl = voice_lengths(job)
    bad = check(job, p["duration"], vl)
    if bad:
        raise SystemExit("RULES:\n- " + "\n- ".join(bad))
    look = Look(job)
    tmp = out + ".video.mp4"
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                            "-i", "-", "-c:v", "libx264", "-crf", "23", "-maxrate", "3100k", "-bufsize", "6200k",
                            "-preset", os.environ.get("X264_PRESET", "slow"), "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
    for f in intro_frames(job.get("intro") or ["PAPARAZZI", "КАТТА ДАВРА"]):
        enc.stdin.write(f.tobytes())
    rd, n, sz = _reader(job["src"]), 0, W * H * 3
    while True:
        buf = rd.stdout.read(sz)
        if len(buf) < sz:
            break
        t = n / FPS
        if look.lo <= t <= look.hi:
            fr = np.frombuffer(buf, dtype=np.uint8).reshape(H, W, 3).astype(np.float32) / 255
            buf = (np.clip(look.compose(fr, t), 0, 1) * 255).astype(np.uint8).tobytes()
        enc.stdin.write(buf)
        n += 1
    rd.wait()
    o, m = _reader(outro_path(job)), 0
    while True:
        buf = o.stdout.read(sz)
        if len(buf) < sz:
            break
        enc.stdin.write(buf)
        m += 1
    o.wait()
    enc.stdin.close()
    if enc.wait() != 0 or n == 0 or m == 0:
        raise SystemExit(f"VIDEO_FAIL: кадров материала {n}, концовки {m}")
    fc, nv = audio_filter(job, vl, n / FPS, p["audio"])
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", tmp, "-i", job["src"], "-i", outro_path(job)]
    for v in job.get("voice") or []:
        cmd += ["-i", v["file"]]
    cmd += ["-filter_complex", fc, "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", "-shortest", out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    os.remove(tmp)
    if r.returncode != 0:
        raise SystemExit("AUDIO_FAIL: " + r.stderr.strip()[-400:])
    res = {"материал_кадров": n, "концовка_кадров": m, "строк_диктора": nv, "секунд": round(probe(out)["duration"], 2),
           "МБ": round(os.path.getsize(out) / 1e6, 1)}
    log(f"SHOU_DONE {res}")
    return res


def main(argv: list[str]) -> None:
    if len(argv) < 3:
        raise SystemExit(__doc__)
    cmd = argv[1]
    if cmd == "analyze":
        print(json.dumps(analyze(argv[2]), ensure_ascii=False))
    elif cmd == "check":
        job = load(argv[2])
        bad = check(job, probe(job["src"])["duration"], voice_lengths(job))
        print("OK — правила соблюдены" if not bad else "RULES:\n- " + "\n- ".join(bad))
        sys.exit(1 if bad else 0)
    elif cmd == "stills":
        stills(load(argv[2]), argv[3])
    elif cmd == "render":
        render(load(argv[2]), argv[3])
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
