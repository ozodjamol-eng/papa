"""«Уйғониш» — монтаж из оставшихся клипов Veo (02.11.2026).
Клипы: /home/claude/uyg/c/NN.mp4 (720×1280, 8 с), голос DOST-shoir U1..U6, музыка UYG_M1.
Сцены через провал в чёрное, вопросы частей — чёрные карточки (Raleway 800, разрядка),
внутренний голос — субтитры Montserrat 800 внизу. Лица без цветофильтров.
"""
import json, os, subprocess
from PIL import Image, ImageDraw, ImageFont

C = "/home/claude/uyg/c"; A = "/home/claude/uyg/a"; W = "/home/claude/uyg/w"
F = "/home/claude/fonts"
os.makedirs(W, exist_ok=True)
FPS = 24; FADE = 0.45

# (тип, клип/текст, вход, длит, субтитр, голос)
PLAN = [
    ("card", "УЙҒОНИШ", 0, 3.2, None, None),
    ("clip", "01", 0.3, 4.6, "«Она, кечиринг…»", None),
    ("clip", "02", 0.5, 3.8, None, None),
    ("clip", "03", 0.3, 4.0, None, None),
    ("clip", "04", 0.5, 3.6, None, None),
    ("card", "НЕГА ЁМОН НАРСАЛАР\nЯХШИ ИНСОНЛАРНИНГ\nБОШИГА КЕЛАДИ?", 0, 3.4, None, None),
    ("clip", "05", 0.3, 4.8, None, None),
    ("clip", "06", 0.5, 5.4, None, None),
    ("clip", "07", 0.5, 4.6, None, None),
    ("clip", "08", 0.3, 5.0, "Омон қолиш — ҳеч жойинг синмаслиги эмас экан.", "U1"),
    ("clip", "09", 0.3, 4.4, "Баъзан оғриқ билан ҳам яшашда давом этаркансан.", None),
    ("card", "НЕГА БАЪЗИЛАР ЎЗИНИ\nЁЛҒИЗ ҲИС ҚИЛАДИ?", 0, 3.2, None, None),
    ("clip", "10", 0.3, 4.6, None, None),
    ("clip", "11", 0.3, 5.6, "Мен ҳеч кимни кўрмадим.\nШунинг учун ҳеч ким йўқ деб ўйладим.", "U2"),
    ("card", "ҲАММАСИ БИР КУН КЕЛИБ\nЯХШИ БЎЛАДИМИ?", 0, 3.2, None, None),
    ("clip", "12", 0.3, 4.2, None, None),
    ("clip", "13", 0.3, 4.0, None, None),
    ("clip", "14", 0.3, 5.0, None, None),
    ("clip", "15", 0.3, 7.2, "Менга кутишдан бошқа йўл йўқдек эди.\nАслида, кутаётганда ҳам қадам ташлашим мумкин экан.", "U3"),
    ("card", "БУ ЮКЛАРНИ\nКЎТАРА ОЛМАСАМ-ЧИ?", 0, 3.2, None, None),
    ("clip", "16", 0.3, 4.8, "STONES", None),
    ("clip", "17", 0.3, 4.4, None, None),
    ("clip", "18", 0.3, 7.0, "Бутун йўлни бир қадамда босишга уринган эканман.\nБугун мендан фақат шу қадам талаб қилиняпти.", "U4"),
    ("card", "ГУНОҲЛАРИМ КЎП БЎЛСА ҲАМ…\nМЕНИ КЕЧИРИШ МУМКИНМИ?", 0, 3.6, None, None),
    ("clip", "19", 0.3, 4.6, None, None),
    ("clip", "20", 0.3, 6.2, "Кечагини ўзгартира олмайман.\nЛекин бугун ҳам ўша одам бўлиб қолишим шарт эмас.", "U5"),
    ("clip", "21", 0.3, 5.6, None, None),
    ("card", "", 0, 5.6, "Она… менман.\nЭрталаб олдингизга борсам майлими?", "U6"),
    ("card", "", 0, 2.0, None, None),
]
STONES = ["«Кечаги хато»", "«Эртага нима бўлади?»", "«Одамлар нима дейди?»"]


def font(name, size):
    return ImageFont.truetype(f"{F}/{name}", size)


def text_png(path, lines, fnt, y_center, tracking=0, shade=True, alpha=255):
    im = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if shade:  # мягкое затемнение низа под текст (лицо выше — не трогаем)
        g = Image.new("L", (1, 420))
        for y in range(420):
            g.putpixel((0, y), int(150 * (y / 419) ** 1.6))
        im.paste(Image.new("RGBA", (1080, 420), (0, 0, 0, 255)), (0, 1500), g.resize((1080, 420)))
    wrapped = []
    for ln in lines:  # перенос по словам: строка не шире 920 px
        cur = ""
        for w_ in ln.split(" "):
            cand = (cur + " " + w_).strip()
            if fnt.getlength(cand) + tracking * len(cand) > 920 and cur:
                wrapped.append(cur); cur = w_
            else:
                cur = cand
        wrapped.append(cur)
    lines = wrapped
    lh = int(fnt.size * 1.32)
    y0 = y_center - lh * len(lines) // 2
    for i, ln in enumerate(lines):
        if tracking:
            ws = [fnt.getlength(ch) + tracking for ch in ln]
            x = (1080 - (sum(ws) - tracking)) / 2
            for ch, w in zip(ln, ws):
                d.text((x, y0 + i * lh), ch, font=fnt, fill=(255, 255, 255, alpha))
                x += w
        else:
            w = fnt.getlength(ln)
            d.text(((1080 - w) / 2 + 2, y0 + i * lh + 3), ln, font=fnt, fill=(0, 0, 0, 160))
            d.text(((1080 - w) / 2, y0 + i * lh), ln, font=fnt, fill=(255, 255, 255, alpha))
    im.save(path)


def run(cmd):
    subprocess.run(cmd, check=True)


segs = []; voice_at = []; t = 0.0
for i, (kind, src, ss, dur, sub, voice) in enumerate(PLAN):
    out = f"{W}/s{i:02d}.mp4"
    fade = f"fade=t=in:st=0:d={FADE},fade=t=out:st={dur - FADE:.3f}:d={FADE}"
    if kind == "clip":
        inputs = ["-ss", str(ss), "-t", f"{dur:.3f}", "-i", f"{C}/{src}.mp4"]
        vf = "[0:v]scale=1080:1920:flags=lanczos,setsar=1,fps=24"
        ov = []
        if sub == "STONES":
            for k, s in enumerate(STONES):
                p = f"{W}/st{k}.png"; text_png(p, [s], font("Montserrat800.ttf", 52), 1640)
                ov.append((p, 0.5 + k * 1.35, 0.5 + k * 1.35 + 1.25))
        elif sub:
            p = f"{W}/sub{i:02d}.png"
            text_png(p, sub.split("\n"), font("Montserrat800.ttf", 46), 1640)
            ov.append((p, 0.35, dur - 0.3))
        chain = vf + "[b]"; last = "b"
        for k, (p, a, b) in enumerate(ov):
            inputs += ["-loop", "1", "-t", f"{dur:.3f}", "-i", p]
            chain += (f";[{k+1}:v]format=rgba,fade=t=in:st={a}:d=0.35:alpha=1,fade=t=out:st={b-0.35:.3f}:d=0.35:alpha=1[o{k}]"
                      f";[{last}][o{k}]overlay=0:0:shortest=1[v{k}]")
            last = f"v{k}"
        chain += f";[{last}]{fade},noise=alls=5:allf=t,format=yuv420p[vo]"
        run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", chain, "-map", "[vo]",
             "-map", "0:a", "-af", f"afade=t=in:d={FADE},afade=t=out:st={dur-FADE:.3f}:d={FADE},volume=0.32",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac", "-ar", "44100", "-ac", "2", out])
    else:
        p = f"{W}/card{i:02d}.png"
        if src == "УЙҒОНИШ":
            text_png(p, [src], font("Raleway800.ttf", 92), 960, tracking=26, shade=False)
        elif src:
            text_png(p, src.split("\n"), font("Raleway800.ttf", 50), 960, tracking=6, shade=False)
        elif sub:
            text_png(p, sub.split("\n"), font("Montserrat800.ttf", 48), 960, shade=False)
        else:
            Image.new("RGBA", (1080, 1920), (0, 0, 0, 0)).save(p)
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=black:s=1080x1920:r=24:d={dur}",
             "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={dur}", "-loop", "1", "-t", str(dur), "-i", p,
             "-filter_complex", f"[2:v]format=rgba,fade=t=in:st=0.3:d=0.6:alpha=1,fade=t=out:st={dur-0.7:.2f}:d=0.6:alpha=1[o];"
             f"[0:v][o]overlay=0:0,format=yuv420p[vo]", "-map", "[vo]", "-map", "1:a", "-t", str(dur),
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac", "-ar", "44100", "-ac", "2", out])
    if voice:
        voice_at.append((voice, t + 0.35))
    segs.append(out); t += dur

open(f"{W}/list.txt", "w").write("".join(f"file '{s}'\n" for s in segs))
run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{W}/list.txt", "-c", "copy", f"{W}/video.mp4"])
total = t
json.dump({"total": total, "voice": voice_at}, open(f"{W}/timing.json", "w"))

# звук: музыка тихо, приглушается под голос; голос с лёгким залом
inputs = ["-i", f"{W}/video.mp4", "-i", f"{A}/UYG_M1.mp3"]
fc = []; mix = ["[amb]", "[mus]"]
fc.append("[0:a]volume=1.0[amb]")
duck = "+".join(f"between(t,{s-0.3:.2f},{s+float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',f'{A}/{v}.mp3']))+0.4:.2f})" for v, s in voice_at)
fc.append(f"[1:a]atrim=0:{total:.2f},volume='if({duck},0.16,0.34)':eval=frame,afade=t=in:d=2,afade=t=out:st={total-4:.2f}:d=4[mus]")
for k, (v, s) in enumerate(voice_at):
    inputs += ["-i", f"{A}/{v}.mp3"]
    fc.append(f"[{k+2}:a]aresample=44100,highpass=f=70,volume=1.25,aecho=0.8:0.55:60|120:0.18|0.10,adelay={int(s*1000)}|{int(s*1000)}[v{k}]")
    mix.append(f"[v{k}]")
fc.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0,alimiter=limit=0.9[aout]")
out = "/home/claude/uyg/Uygonish_film.mp4"
run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", "0:v", "-map", "[aout]",
     "-c:v", "libx264", "-preset", "medium", "-b:v", "2600k", "-maxrate", "3200k", "-bufsize", "6000k",
     "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-t", f"{total:.2f}", out])
print("OK", out, round(total, 1), "с")
