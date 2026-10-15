"""Обработка медиа для Fabrika: логотип на видео и фото (ffmpeg), подготовка логотипа (Pillow).

Видео: 1) постоянная маленькая метка в углу (полупрозрачная);
       2) «плывущий» логотип: каждые CYCLE секунд появляется внизу у края, плывёт к середине и,
          не доходя до неё, плавно растворяется — так метку трудно вырезать.
Фото: только постоянная метка."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

CYCLE, MOVE = 12, 4.0          # период и длительность проплыва, сек


def prepare_logo(src: Path, dst: Path) -> Path:
    """PNG с прозрачностью — как есть; без прозрачности (фото) — вырезаем круг. Размер ≤ 512 px."""
    from PIL import Image, ImageDraw
    im = Image.open(src).convert("RGBA")
    im.thumbnail((512, 512))
    has_alpha = im.getextrema()[3][0] < 250
    if not has_alpha:
        side = min(im.size)
        left, top = (im.width - side) // 2, (im.height - side) // 2
        im = im.crop((left, top, left + side, top + side))
        mask = Image.new("L", im.size, 0)
        ImageDraw.Draw(mask).ellipse((0, 0, side - 1, side - 1), fill=255)
        im.putalpha(mask)
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst, "PNG")
    return dst


def probe(path: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height:format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True, timeout=60)
    j = json.loads(out.stdout or "{}")
    s = (j.get("streams") or [{}])[0]
    return {"w": int(s.get("width", 0)), "h": int(s.get("height", 0)), "dur": float((j.get("format") or {}).get("duration", 0) or 0)}


def video_filter(w: int) -> str:
    small = max(48, int(w * 0.13))      # постоянная метка
    big = max(80, int(w * 0.24))        # плывущий логотип
    fade = (f"clip(min(mod(T\\,{CYCLE})/0.5\\,({MOVE}-mod(T\\,{CYCLE}))/0.9)\\,0\\,1)")
    return (
        f"[1:v]format=rgba,scale={small}:-1,colorchannelmixer=aa=0.55[st];"
        f"[2:v]format=rgba,scale={big}:-1,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='alpha(X,Y)*0.85*{fade}'[mv];"
        f"[0:v][st]overlay=x=main_w-overlay_w-main_w*0.035:y=main_h*0.035[a];"
        f"[a][mv]overlay=eval=frame:shortest=0:"
        f"x='main_w*0.04+(main_w/2-overlay_w/2-main_w*0.04)*0.8*min(mod(t\\,{CYCLE})/{MOVE}\\,1)':"
        f"y='main_h-overlay_h-main_h*0.11',format=yuv420p[v]"
    )


def watermark_video(src: Path, logo: Path, dst: Path, crf: int = 23, timeout: int = 900) -> Path:
    info = probe(src)
    dur = info["dur"] or 60
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(src),
           "-loop", "1", "-framerate", "30", "-t", f"{dur:.2f}", "-i", str(logo),
           "-loop", "1", "-framerate", "30", "-t", f"{dur:.2f}", "-i", str(logo),
           "-filter_complex", video_filter(info["w"] or 720),
           "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf),
           "-threads", "2", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "-shortest", str(dst)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg: {r.stderr[-300:]}")
    return dst


def watermark_photo(src: Path, logo: Path, dst: Path) -> Path:
    from PIL import Image
    im = Image.open(src).convert("RGB")
    lg = Image.open(logo).convert("RGBA")
    w = max(48, int(im.width * 0.13))
    lg = lg.resize((w, int(lg.height * w / lg.width)))
    a = lg.getchannel("A").point(lambda v: int(v * 0.6))
    lg.putalpha(a)
    im.paste(lg, (im.width - w - int(im.width * 0.035), int(im.height * 0.035)), lg)
    im.save(dst, "JPEG", quality=92)
    return dst
