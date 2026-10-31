"""Флагман «OZOD JAMOL Дизайн»: 7 клипов Flow + стили + карточка + призыв + концовка → 1080x1920."""
import subprocess as sp, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
D = "/home/claude/fm"; S = f"{D}/src"; T = f"{D}/tmp"; os.makedirs(T, exist_ok=True)
FB = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
FX = "/usr/share/fonts/opentype/inter/InterDisplay-ExtraBold.otf"
W, H, FPS = 1080, 1920, 30
def run(c): sp.run(c, check=True)

def card(name, lines, pos="top", tag=None, corner=True):
    """прозрачная PNG-плашка с жирным текстом. lines: [(текст, размер, цвет)]"""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    fonts = [ImageFont.truetype(FB, s) for _, s, _ in lines]
    hs = [f.getbbox(t)[3] - f.getbbox(t)[1] for (t, _, _), f in zip(lines, fonts)]
    total = sum(hs) + 26 * (len(lines) - 1)
    y = {"top": 230, "bottom": H - 430 - total, "mid": (H - total) // 2}[pos]
    pad = 44
    ws = [d.textlength(t, font=f) for (t, _, _), f in zip(lines, fonts)]
    bw = max(ws) + 2 * pad
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(sh)
    sd.rounded_rectangle([(W - bw) / 2, y - 34, (W + bw) / 2, y + total + 40], 34, fill=(10, 10, 12, 205))
    im = Image.alpha_composite(im, sh); d = ImageDraw.Draw(im)
    for (t, s, c), f, h, w in zip(lines, fonts, hs, ws):
        d.text(((W - w) / 2, y - f.getbbox(t)[1]), t, font=f, fill=c)
        y += h + 26
    if corner:
        f = ImageFont.truetype(FB, 40); t = "3D ВИЗУАЛИЗАЦИЯ"
        d.text((W - d.textlength(t, font=f) - 36, H - 110), t, font=f, fill=(255, 255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0, 255))
    im.save(f"{T}/{name}.png")

WH, YL, RED = (255, 255, 255, 255), (255, 200, 90, 255), (235, 60, 50, 255)
# сегменты: (клип, скорость, длина_выхода, плашка)
segs = [
    ("c1a", 1.6, 4.9, [("КВАРТИРА", 112, WH), ("ҚУТИ", 112, YL), ("ҲОЛАТИДАМИ?", 104, YL)], "top"),
    ("c2a", 2.0, 3.9, [("ЭЛЕКТР ВА", 96, WH), ("САНТЕХНИКА", 96, YL)], "top"),
    ("c3a", 2.0, 3.9, [("СУВОҚ ВА", 96, WH), ("СТЯЖКА", 96, YL)], "top"),
    ("c4a", 2.0, 3.9, [("ШИФТ ВА", 96, WH), ("ЁРИТИШ", 96, YL)], "top"),
    ("c5a", 2.0, 3.9, [("ПОЛ, БЎЁҚ,", 96, WH), ("ЭШИК", 96, YL)], "top"),
    ("c6a", 2.0, 3.9, [("МЕБЕЛ ВА", 96, WH), ("БЕЗАК", 96, YL)], "top"),
    ("c7b", 1.6, 4.9, [("МАНА —", 112, WH), ("СИЗНИНГ", 112, YL), ("УЙИНГИЗ", 112, YL)], "bottom"),
]
parts = []
for i, (c, sp_, dur, lines, pos) in enumerate(segs):
    card(f"t{i}", lines, pos)
    out = f"{T}/s{i}.mp4"
    vf = (f"[0:v]setpts=PTS/{sp_},scale={W}:{H}:flags=lanczos,fps={FPS},trim=0:{dur},setpts=PTS-STARTPTS[v];"
          f"[1:v]format=rgba,fade=in:st=0.15:d=0.35:alpha=1,fade=out:st={dur-0.45}:d=0.35:alpha=1[t];"
          f"[v][t]overlay=0:0:format=auto,format=yuv420p[o];"
          f"[0:a]atempo={min(sp_,2.0)},atrim=0:{dur},asetpts=PTS-STARTPTS,volume=0.55[a]")
    run(["ffmpeg", "-v", "error", "-y", "-i", f"{S}/{c}.mp4", "-loop", "1", "-t", str(dur), "-i", f"{T}/t{i}.png",
         "-filter_complex", vf, "-map", "[o]", "-map", "[a]", "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "17", "-c:a", "aac", "-ar", "48000", "-ac", "2", out]); parts.append(out)

# стили: 4 картинки по 1.25 с, лёгкий наезд
styles = [("st_haytek", "ХАЙ-ТЕК"), ("st_klassika", "КЛАССИКА"), ("st_japandi", "ДЖАПАНДИ"), ("st_sharq", "ШАРҚОНА")]
for j, (f, nm) in enumerate(styles):
    im = Image.open(f"/home/claude/fl/dizayn-out/{f}.png").convert("RGB")
    im = im.resize((W, int(im.height * W / im.width)), Image.LANCZOS)
    top = (im.height - H) // 2 if im.height > H else 0
    if im.height < H: im = im.resize((int(im.width * H / im.height), H), Image.LANCZOS); im = im.crop(((im.width - W)//2, 0, (im.width - W)//2 + W, H))
    else: im = im.crop((0, top, W, top + H))
    im.save(f"{T}/{f}.jpg", quality=95)
    card(f"st{j}", [("УСЛУБНИ", 92, WH), ("ТАНЛАНГ", 92, WH), (nm, 112, YL)], "top")
    out = f"{T}/st{j}.mp4"; dur = 1.25
    run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", f"{T}/{f}.jpg", "-loop", "1", "-i", f"{T}/st{j}.png",
         "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-filter_complex",
         f"[0:v]scale={int(W*1.2)}:-1,zoompan=z='1+0.0016*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(dur*FPS)}:s={W}x{H}:fps={FPS}[v];"
         f"[v][1:v]overlay=0:0,format=yuv420p[o]", "-map", "[o]", "-map", "2:a", "-t", str(dur), "-r", str(FPS),
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-c:a", "aac", "-ar", "48000", "-ac", "2", out]); parts.append(out)

# карточка «что получает клиент» + призыв — на размытом вечернем кадре
run(["ffmpeg", "-v", "error", "-y", "-sseof", "-0.2", "-i", f"{S}/c7b.mp4", "-frames:v", "1", "-vf", f"scale={W}:{H}", f"{T}/last.png"])
bg = Image.open(f"{T}/last.png").convert("RGB").filter(ImageFilter.GaussianBlur(18))
bg = Image.blend(bg, Image.new("RGB", bg.size, (8, 8, 10)), 0.45); bg.save(f"{T}/bg.jpg", quality=95)
def still(name, lines, dur, pos="mid"):
    card(name, lines, pos, corner=False)
    out = f"{T}/{name}.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", f"{T}/bg.jpg", "-loop", "1", "-i", f"{T}/{name}.png",
         "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-filter_complex",
         f"[1:v]format=rgba,fade=in:st=0:d=0.3:alpha=1[t];[0:v][t]overlay=0:0,format=yuv420p[o]",
         "-map", "[o]", "-map", "2:a", "-t", str(dur), "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "17", "-c:a", "aac", "-ar", "48000", "-ac", "2", out]); parts.append(out)
still("pak", [("СИЗ ОЛАСИЗ:", 100, YL), ("3D ВИЗУАЛ", 92, WH), ("ЧИЗМАЛАР", 92, WH), ("ЭЛЕКТР РЕЖАСИ", 92, WH), ("РАНГЛАР", 92, WH)], 3.4)
# --- сцена «роль бота»: логотип + 3 шага по очереди
def botscene(dur=6.0):
    from PIL import Image as I
    logo = I.open(f"{T}/logo.png").convert("RGBA").resize((470, 470), I.LANCZOS)
    mk = I.new("L", (470, 470), 0); ImageDraw.Draw(mk).ellipse([4, 4, 466, 466], fill=255); logo.putalpha(mk)
    steps = [("1", "УЙ ЁКИ ХОНАНИ", "ТАНЛАНГ"), ("2", "ЎЛЧАМ ВА РАСМ", "ЮБОРИНГ"), ("3", "3D ЛОЙИҲАНИ", "ОЛИНГ")]
    fT = ImageFont.truetype(FB, 78); fN = ImageFont.truetype(FB, 84); fS = ImageFont.truetype(FB, 64)
    base = I.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(base)
    base.alpha_composite(logo, ((W - 470) // 2, 150))
    t = "БОТ ОРҚАЛИ — 3 ҚАДАМ"; d.text(((W - d.textlength(t, font=fT)) / 2, 660), t, font=fT, fill=YL)
    base.save(f"{T}/b0.png")
    for k, (n, a, b) in enumerate(steps):
        im = I.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        y = 820 + k * 300
        d.rounded_rectangle([70, y, W - 70, y + 250], 36, fill=(12, 12, 14, 225), outline=(235, 60, 50, 255), width=6)
        d.ellipse([110, y + 50, 260, y + 200], fill=(235, 60, 50, 255))
        d.text((185 - d.textlength(n, font=fN) / 2, y + 70), n, font=fN, fill=WH)
        d.text((300, y + 42), a, font=fS, fill=WH); d.text((300, y + 128), b, font=fS, fill=YL)
        im.save(f"{T}/b{k+1}.png")
    out = f"{T}/bot.mp4"
    fc = "[1:v]format=rgba,fade=in:st=0:d=0.3:alpha=1[l];[0:v][l]overlay=0:0[v0];"
    for k in range(3):
        st = 0.7 + k * 1.1
        fc += f"[{k+2}:v]format=rgba,fade=in:st={st}:d=0.3:alpha=1[s{k}];[v{k}][s{k}]overlay=0:0[v{k+1}];"
    fc += "[v3]format=yuv420p[o]"
    cmd = ["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", f"{T}/bg.jpg"]
    for k in range(4): cmd += ["-loop", "1", "-i", f"{T}/b{k}.png"]
    cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-filter_complex", fc, "-map", "[o]", "-map", "5:a",
            "-t", str(dur), "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-c:a", "aac", "-ar", "48000", "-ac", "2", out]
    run(cmd); parts.append(out)
botscene()
still("cta", [("ЛОЙИҲАНГИЗНИ", 100, WH), ("БУГУН БОШЛАНГ", 96, YL), ("@OZODJAMOL", 92, WH), ("DIZAYNBOT", 92, WH)], 3.4)
parts.append("/mnt/user-data/uploads/Downloads/OZOD_JAMOL_KONCOVKA_CHERNAYA.mp4")

# склейка
lst = f"{T}/list.txt"
norm = []
for k, p in enumerate(parts):
    o = f"{T}/n{k}.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-i", p, "-vf", f"scale={W}:{H},fps={FPS},format=yuv420p", "-c:v", "libx264",
         "-preset", "veryfast", "-crf", "17", "-c:a", "aac", "-ar", "48000", "-ac", "2", o]); norm.append(o)
open(lst, "w").write("".join(f"file '{p}'\n" for p in norm))
run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", f"{T}/body.mp4"])
dur = float(sp.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f"{T}/body.mp4"]))
# музыка тихо под клипами + «вжух» на стилях
st_start = sum(s[2] for s in segs)
run(["ffmpeg", "-v", "error", "-y", "-i", f"{T}/body.mp4", "-i", "/mnt/user-data/uploads/Downloads/aurec-sunset-house-598438.mp3",
     "-i", "/mnt/user-data/uploads/Downloads/soundreality-whoosh-large-sub-384631.mp3", "-filter_complex",
     f"[1:a]atrim=0:{dur},afade=in:st=0:d=1.2,afade=out:st={dur-2.6}:d=2.2,volume=0.32[m];"
     f"[2:a]adelay={int((st_start-0.15)*1000)}|{int((st_start-0.15)*1000)},volume=0.7[w];"
     f"[0:a][m][w]amix=inputs=3:duration=first:normalize=0,alimiter=limit=0.95[a]",
     "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
     f"{D}/OZOD_JAMOL_DIZAYN_flagman.mp4"])
print("OK", round(dur, 1), "s")
