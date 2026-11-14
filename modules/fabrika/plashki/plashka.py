"""🎬 Плашки рубрик — короткие фирменные заставки (1,5 с) для каналов PAPA в стиле OZOD JAMOL (красный · чёрный · белый).

Владелец 14.11: «нам надо делать плашки, готовые мини-ролики для наших инструментов — КАТТА ДАВРА и Хўжаобод Сити»;
«у нас же есть фирменный стиль… определяемся по нему».

  python plashka.py one  <out.mp4> "<КАНАЛ>" "<РУБРИКА>" "<@username>" [black|red|white]
  python plashka.py sheet <out.jpg> "<КАНАЛ>" "<РУБРИКА>" "<@username>" [black|red|white]   — контрольный лист кадров

Ход (45 кадров, 30 к/с, без звука — тихая дорожка, чтобы клеилась к любому видео):
красная диагональ (как в знаке OJ) проходит по кадру и открывает за собой слово рубрики → под словом вырастает
красная черта, сверху имя канала, снизу @username → лёгкий наезд и вспышка в белое (склейка с видео)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, N = 1080, 1920, 30, 45
REPO = Path(__file__).resolve().parents[3]
# 14.11 владелец: «шрифт не очень хороший, лучше на латинице» → Montserrat Black (широкий геометрический, как надпись OZOD
# в знаке; лицензия OFL, файл лежит рядом — одинаково здесь, на сервере и в GitHub Actions). Только латиница.
FONT = str(Path(__file__).resolve().parent / "fonts/Montserrat-Black-Latin.ttf")
RED, WHITE, BLACK = (255, 16, 36), (255, 255, 255), (0, 0, 0)          # фирменные: #FF1024 · #FFFFFF · #000000
LOOKS = {"black": {"bg": "BG01_grafit_9x16.png", "word": WHITE, "accent": RED, "small": WHITE, "band": RED},
         "red": {"bg": "BG03_krasnyy_9x16.png", "word": WHITE, "accent": BLACK, "small": WHITE, "band": WHITE},
         "white": {"bg": "BG02_belaya_studiya_9x16.png", "word": BLACK, "accent": RED, "small": BLACK, "band": RED}}
SLOPE = 0.42                                                           # наклон диагонали (как у «J» в знаке)


def _fit(txt: str, maxw: int, start: int):
    s = start
    while True:
        f = ImageFont.truetype(FONT, s)
        b = f.getbbox(txt)
        if b[2] - b[0] <= maxw or s <= 40:
            return f, b
        s -= 4


def _tracked(d, txt, base_y, size, fill, gap):
    """Надпись вразрядку по центру, все буквы на одной линии (имя канала, @username)."""
    f = ImageFont.truetype(FONT, size)
    ws = [f.getlength(ch) for ch in txt]
    x = (W - (sum(ws) + gap * (len(txt) - 1))) / 2
    for ch, w in zip(txt, ws):
        d.text((x, base_y), ch, font=f, fill=fill, anchor="ls")
        x += w + gap


def layers(channel: str, rubric: str, user: str, look: dict):
    """Слой слова (RGBA), слой мелких надписей (RGBA), прямоугольник черты."""
    word = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(word)
    lines = rubric.split("|")
    fs = [_fit(t, 1000, 190) for t in lines]      # потолок 190: короткие слова не раздуваются, набор ровный
    tot = sum(b[3] - b[1] for _, b in fs) + (len(lines) - 1) * 44
    y = 940 - tot / 2
    for (f, b), t in zip(fs, lines):
        d.text(((W - (b[2] - b[0])) / 2 - b[0], y - b[1]), t, font=f, fill=look["word"] + (255,))
        y += b[3] - b[1] + 44
    bar_y = int(y + 22)
    small = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(small)
    _tracked(ds, channel, int(940 - tot / 2 - 70), 72, look["accent"] + (255,), 14)
    _tracked(ds, user, 1660, 60, look["small"] + (240,), 5)
    return (np.asarray(word, dtype=np.float32) / 255, np.asarray(small, dtype=np.float32) / 255, bar_y)


def _ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def frames(channel: str, rubric: str, user: str, look_name: str = "black"):
    look = LOOKS[look_name]
    bg = np.asarray(Image.open(REPO / "docs/brand/ozod-jamol/fony" / look["bg"]).convert("RGB").resize((W, H), Image.LANCZOS),
                    dtype=np.float32) / 255
    word, small, bar_y = layers(channel, rubric, user, look)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    u = xx + yy * SLOPE                                                 # координата поперёк диагонали
    umax = W + H * SLOPE
    band_col = np.array(look["band"], np.float32) / 255
    acc = np.array(look["accent"], np.float32) / 255
    for i in range(N):
        c = -260 + (umax + 520) * _ease((i - 1) / 15.0)                 # центр красной диагонали: проход за ~0,5 с
        fr = bg.copy()
        reveal = np.clip((c - u) / 60.0, 0, 1)[:, :, None]              # слово открыто там, где диагональ уже прошла
        wa = word[:, :, 3:4] * reveal
        fr = fr * (1 - wa) + word[:, :, :3] * wa
        k = _ease((i - 12) / 9.0)                                       # черта под словом и мелкие надписи
        if k > 0:
            half = int(170 * k)
            fr[bar_y:bar_y + 18, W // 2 - half:W // 2 + half] = acc
            sa = small[:, :, 3:4] * k
            fr = fr * (1 - sa) + small[:, :, :3] * sa
        ba = (np.clip(1 - np.abs(u - c) / 130.0, 0, 1) ** 0.6)[:, :, None] * (1 if i < 20 else 0)
        fr = fr * (1 - ba) + band_col * ba
        if i >= 36:                                                     # лёгкий наезд и вспышка в белое — склейка с видео
            f = ((i - 36) / (N - 1 - 36)) ** 2
            fr = fr + (1 - fr) * f
        yield (np.clip(fr, 0, 1) * 255).astype(np.uint8)


def one(out: str, channel: str, rubric: str, user: str, look: str = "black") -> None:
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                            "-i", "-", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-c:v", "libx264", "-crf", "16",
                            "-preset", "slow", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-shortest",
                            "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for f in frames(channel, rubric, user, look):
        enc.stdin.write(f.tobytes())
    enc.stdin.close()
    if enc.wait() != 0:
        raise SystemExit("ENCODE_FAIL")


def sheet(out: str, channel: str, rubric: str, user: str, look: str = "black") -> None:
    pick = (3, 7, 11, 16, 24, 34, 41)
    ims = [Image.fromarray(f).resize((270, 480)) for i, f in enumerate(frames(channel, rubric, user, look)) if i in pick]
    s = Image.new("RGB", (270 * len(ims), 480))
    for i, im in enumerate(ims):
        s.paste(im, (270 * i, 0))
    s.save(out, quality=90)


if __name__ == "__main__":
    if len(sys.argv) < 6 or sys.argv[1] not in ("one", "sheet"):
        raise SystemExit(__doc__)
    (one if sys.argv[1] == "one" else sheet)(*sys.argv[2:7])
