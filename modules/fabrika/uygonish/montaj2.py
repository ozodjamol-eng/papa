"""«Уйғониш» v2 — полный фильм: клипы Veo + недостающие сцены из стартовых кадров (медленный наезд/отъезд).
Голос DOST-shoir ровно по всему фильму: вопросы частей, реплики, внутренний голос. Музыка UYG_M2 (190 с).
"""
import os, subprocess, json
from PIL import Image, ImageDraw, ImageFont

C = "/home/claude/uyg/c"; I = "/home/claude/uyg/img"; A = "/home/claude/uyg/a"; W = "/home/claude/uyg/w2"
F = "/home/claude/fonts"; os.makedirs(W, exist_ok=True)
FADE = 0.45

def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]))

# (вид, источник, длительность-минимум, движение для кадра, голос, субтитр, смещение голоса)
P = [
 ("card", "УЙҒОНИШ", 3.4, None, None, None, 0),
 ("clip", "01", 4.6, None, "R0", "«Она, кечиринг…»", 1.2),
 ("clip", "02", 3.8, None, None, None, 0),
 ("clip", "03", 4.0, None, None, None, 0),
 ("clip", "04", 3.6, None, None, None, 0),
 ("card", "НЕГА ЁМОН НАРСАЛАР\nЯХШИ ИНСОНЛАРНИНГ\nБОШИГА КЕЛАДИ?", 0, None, "Q1", None, 0.7),
 ("clip", "05", 4.6, None, None, None, 0),
 ("img", "s06", 4.6, "in", None, None, 0),
 ("img", "s07", 4.2, "in", None, None, 0),
 ("img", "s08", 4.4, "out", None, None, 0),
 ("img", "s09", 5.0, "in", "R1", "— Яхшилик қилмоқчи эдим… Нега?", 0.8),
 ("clip", "06", 5.0, None, None, None, 0),
 ("clip", "07", 4.4, None, None, None, 0),
 ("clip", "08", 7.4, None, "U1", "Омон қолиш — ҳеч жойинг синмаслиги эмас экан. Баъзан оғриқ билан ҳам яшашда давом этаркансан.", 0.4),
 ("clip", "09", 4.4, None, None, None, 0),
 ("card", "НЕГА БАЪЗИЛАР ЎЗИНИ\nЁЛҒИЗ ҲИС ҚИЛАДИ?", 0, None, "Q2", None, 0.7),
 ("img", "s14", 4.6, "in", None, None, 0),
 ("clip", "10", 4.6, None, "R2", "— Ҳеч ким борми?!", 1.4),
 ("img", "s16", 4.0, "in", None, None, 0),
 ("img", "s17", 4.8, "out", None, None, 0),
 ("clip", "11", 5.6, None, "U2", "Мен ҳеч кимни кўрмадим. Шунинг учун ҳеч ким йўқ деб ўйладим.", 0.4),
 ("card", "ҲАММАСИ БИР КУН КЕЛИБ\nЯХШИ БЎЛАДИМИ?", 0, None, "Q3", None, 0.7),
 ("clip", "12", 4.2, None, None, None, 0),
 ("img", "s20", 4.2, "in", "R3", "— Қачон?!", 1.3),
 ("clip", "13", 4.0, None, None, None, 0),
 ("clip", "14", 4.8, None, None, None, 0),
 ("clip", "15", 7.4, None, "U3", "Менга кутишдан бошқа йўл йўқдек эди. Аслида, кутаётганда ҳам қадам ташлашим мумкин экан.", 0.4),
 ("card", "БУ ЮКЛАРНИ\nКЎТАРА ОЛМАСАМ-ЧИ?", 0, None, "Q4", None, 0.7),
 ("img", "s24", 4.8, "in", None, None, 0),
 ("clip", "16", 4.8, None, None, "STONES", 0),
 ("clip", "17", 4.6, None, "R4", "— Қўлингизни беринг.", 2.4),
 ("clip", "18", 7.4, None, "U4", "Бутун йўлни бир қадамда босишга уринган эканман. Бугун мендан фақат шу қадам талаб қилиняпти.", 0.4),
 ("card", "ГУНОҲЛАРИМ КЎП БЎЛСА ҲАМ…\nМЕНИ КЕЧИРИШ МУМКИНМИ?", 0, None, "Q5", None, 0.7),
 ("img", "s28", 5.0, "in", None, None, 0),
 ("clip", "19", 6.2, None, "R5", "— Мен… қайтишга уялдим. Шунинг учун яна узоқлашдим.", 0.5),
 ("img", "s30", 5.0, "in", None, None, 0),
 ("clip", "20", 6.6, None, "U5", "Кечагини ўзгартира олмайман. Лекин бугун ҳам ўша одам бўлиб қолишим шарт эмас.", 0.4),
 ("clip", "21", 4.8, None, None, None, 0),
 ("img", "s33", 6.4, "out", "U6", "— Она… менман. Эрталаб олдингизга борсам майлими?", 0.9),
 ("card", "", 3.0, None, None, None, 0),
]
STONES = ["«Кечаги хато»", "«Эртага нима бўлади?»", "«Одамлар нима дейди?»"]


def fnt(n, s):
    return ImageFont.truetype(f"{F}/{n}", s)


def text_png(path, lines, f, yc, tracking=0, shade=True):
    im = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    if shade:
        g = Image.new("L", (1, 460))
        for y in range(460):
            g.putpixel((0, y), int(160 * (y / 459) ** 1.5))
        im.paste(Image.new("RGBA", (1080, 460), (0, 0, 0, 255)), (0, 1460), g.resize((1080, 460)))
    wr = []
    for ln in lines:
        cur = ""
        for w in ln.split(" "):
            c = (cur + " " + w).strip()
            if f.getlength(c) + tracking * len(c) > 900 and cur:
                wr.append(cur); cur = w
            else:
                cur = c
        wr.append(cur)
    lh = int(f.size * 1.34); y0 = yc - lh * len(wr) // 2
    for i, ln in enumerate(wr):
        if tracking:
            ws = [f.getlength(ch) + tracking for ch in ln]; x = (1080 - (sum(ws) - tracking)) / 2
            for ch, w in zip(ln, ws):
                d.text((x, y0 + i * lh), ch, font=f, fill=(255, 255, 255, 255)); x += w
        else:
            w = f.getlength(ln)
            d.text(((1080 - w) / 2 + 2, y0 + i * lh + 3), ln, font=f, fill=(0, 0, 0, 170))
            d.text(((1080 - w) / 2, y0 + i * lh), ln, font=f, fill=(255, 255, 255, 255))
    im.save(path)


def run(c):
    subprocess.run(c, check=True)


SUBF = fnt("Montserrat800.ttf", 44)
segs, voices, t = [], [], 0.0
for i, (kind, src, mind, mv, vo, sub, voff) in enumerate(P):
    vd = dur(f"{A}/{vo}.mp3") if vo else 0
    D = max(mind, voff + vd + 1.1) if vo else mind
    if kind == "clip":
        D = min(D, 7.6)
    out = f"{W}/s{i:02d}.mp4"
    fade = f"fade=t=in:st=0:d={FADE},fade=t=out:st={D-FADE:.3f}:d={FADE}"
    ov = []
    if sub == "STONES":
        for k, s in enumerate(STONES):
            p = f"{W}/st{k}.png"; text_png(p, [s], fnt("Montserrat800.ttf", 54), 1630)
            ov.append((p, 0.5 + k * 1.4, 0.5 + k * 1.4 + 1.3))
    elif sub and kind != "card":
        p = f"{W}/sub{i:02d}.png"; text_png(p, [sub], SUBF, 1640)
        ov.append((p, max(0.3, voff - 0.1), min(D - 0.3, voff + vd + 0.6)))
    if kind in ("clip", "img"):
        if kind == "clip":
            inp = ["-ss", "0.3", "-t", f"{D:.3f}", "-i", f"{C}/{src}.mp4"]
            base = "[0:v]scale=1080:1920:flags=lanczos,setsar=1,fps=24"
            amap = ["-map", "0:a", "-af", f"afade=t=in:d={FADE},afade=t=out:st={D-FADE:.3f}:d={FADE},volume=0.30"]
        else:
            n = int(round(D * 24)); z0, z1 = (1.0, 1.10) if mv == "in" else (1.10, 1.0)
            # медленный наезд/отъезд к центру-верху (лицо обычно в верхней половине)
            inp = ["-loop", "1", "-framerate", "24", "-t", f"{D:.3f}", "-i", f"{I}/{src}.jpg",
                   "-f", "lavfi", "-t", f"{D:.3f}", "-i", "anullsrc=r=44100:cl=stereo"]
            base = (f"[0:v]scale=2160:3840:flags=lanczos,zoompan=z='{z0}+({z1}-{z0})*on/{n}':"
                    f"x='iw/2-(iw/zoom/2)':y='ih*0.45-(ih/zoom*0.45)':d=1:s=1080x1920:fps=24,setsar=1")
            amap = ["-map", "1:a"]
        chain = base + "[b]"; last = "b"
        for k, (p, a, b) in enumerate(ov):
            inp += ["-loop", "1", "-t", f"{D:.3f}", "-i", p]
            idx = (1 if kind == "clip" else 2) + k
            chain += (f";[{idx}:v]format=rgba,fade=t=in:st={a:.2f}:d=0.35:alpha=1,fade=t=out:st={b-0.35:.2f}:d=0.35:alpha=1[o{k}]"
                      f";[{last}][o{k}]overlay=0:0:shortest=1[v{k}]"); last = f"v{k}"
        chain += f";[{last}]{fade},noise=alls=5:allf=t,format=yuv420p[vo]"
        run(["ffmpeg", "-v", "error", "-y", *inp, "-filter_complex", chain, "-map", "[vo]", *amap, "-t", f"{D:.3f}",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac", "-ar", "44100", "-ac", "2", out])
    else:
        if not mind:
            D = max(3.2, voff + vd + 1.3)
        p = f"{W}/card{i:02d}.png"
        if src == "УЙҒОНИШ":
            text_png(p, [src], fnt("Raleway800.ttf", 92), 960, tracking=26, shade=False)
        elif src:
            text_png(p, src.split("\n"), fnt("Raleway800.ttf", 50), 960, tracking=6, shade=False)
        else:
            Image.new("RGBA", (1080, 1920), (0, 0, 0, 0)).save(p)
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=black:s=1080x1920:r=24:d={D}",
             "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={D}", "-loop", "1", "-t", str(D), "-i", p,
             "-filter_complex", f"[2:v]format=rgba,fade=t=in:st=0.3:d=0.6:alpha=1,fade=t=out:st={D-0.7:.2f}:d=0.6:alpha=1[o];"
             "[0:v][o]overlay=0:0,format=yuv420p[vo]", "-map", "[vo]", "-map", "1:a", "-t", str(D),
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac", "-ar", "44100", "-ac", "2", out])
    if vo:
        voices.append((vo, t + voff, vd))
    segs.append(out); t += D
    print(f"{i:02d} {kind:4} {src[:12]:12} {D:4.1f}s  t={t:6.1f}", flush=True)

open(f"{W}/list.txt", "w").write("".join(f"file '{s}'\n" for s in segs))
run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{W}/list.txt", "-c", "copy", f"{W}/video.mp4"])
total = t
json.dump({"total": total, "voices": voices}, open(f"{W}/timing.json", "w"), ensure_ascii=False)

inp = ["-i", f"{W}/video.mp4", "-i", f"{A}/UYG_M2.mp3"]
duck = "+".join(f"between(t,{s-0.3:.2f},{s+d+0.5:.2f})" for _, s, d in voices)
fc = ["[0:a]volume=1.0[amb]",
      f"[1:a]atrim=0:{total:.2f},volume='if({duck},0.15,0.32)':eval=frame,afade=t=in:d=2,afade=t=out:st={total-5:.2f}:d=5[mus]"]
mix = ["[amb]", "[mus]"]
for k, (v, s, _) in enumerate(voices):
    inp += ["-i", f"{A}/{v}.mp3"]
    fc.append(f"[{k+2}:a]aresample=44100,highpass=f=70,volume=1.25,aecho=0.8:0.55:60|120:0.18|0.10,"
              f"adelay={int(s*1000)}|{int(s*1000)}[v{k}]")
    mix.append(f"[v{k}]")
fc.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0,alimiter=limit=0.9[aout]")
out = "/home/claude/uyg/Uygonish_film_v2.mp4"
vb = int((49 * 8 * 1024 * 1024 / total - 170000) * 0.93 / 1000)  # под лимит бота 50 МБ
run(["ffmpeg", "-v", "error", "-y", *inp, "-filter_complex", ";".join(fc), "-map", "0:v", "-map", "[aout]",
     "-c:v", "libx264", "-preset", "medium", "-b:v", f"{vb}k", "-maxrate", f"{int(vb*1.25)}k", "-bufsize", f"{vb*2}k",
     "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-t", f"{total:.2f}", out])
print("OK", out, round(total, 1), "с", vb, "kbps")
