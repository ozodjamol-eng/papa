"""Флагман «OZOD JAMOL Дизайн» v4 — голос владельца + субтитры по словам + лёгкая инфографика.
Без больших плашек. python3 build_vo.py UZ|RU"""
import subprocess as sp, os, sys, json, bisect
from PIL import Image, ImageDraw, ImageFont, ImageFilter

L = sys.argv[1] if len(sys.argv) > 1 else "UZ"
D = "/home/claude/fm"; S = f"{D}/src"; T = f"{D}/tmp_{L}"; os.makedirs(T, exist_ok=True)
FB = "/home/claude/fonts/Montserrat-Black.ttf"; FX = "/home/claude/fonts/Montserrat-ExtraBold.ttf"
W, H, FPS = 1080, 1920, 30
VOICE = {"UZ": "/home/claude/vo3/UZ_2_uverenno.mp3", "RU": "/home/claude/vo/dizayn_RU.mp3"}[L]
DL = "/mnt/user-data/uploads/Downloads"
WH, YL, RED, DK = (255, 255, 255, 255), (255, 200, 60, 255), (235, 60, 50, 255), (12, 12, 14, 230)
def run(c): sp.run(c, check=True)
def dur_of(p): return float(sp.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]))

LINES = {
 "UZ": ["Квартира олдингиз, лекин у ҳали коробка ҳолатида?",
        "Электрик, сантехник, сувоқчи — ҳаммасини алоҳида қидириб, овора бўласизми?",
        "Энди бунинг кераги йўқ.",
        "OZOD JAMOL Дизайн ботига ёзинг — ишингизга мос, текширилган уста топиб берамиз.",
        "Уста келиб, кўрикдан бепул ўтказади.",
        "Хоҳласангиз — таъмирдан олдин уйингизни 3D да кўрасиз.",
        "Минимализм, хай-тек, классика ёки шарқона — услубни ўзингиз танлайсиз.",
        "Битта бот — уста ҳам, дизайн ҳам. Ҳаволани изоҳда қолдирдим.",
        "OZOD JAMOL. Уйни бир марта қурасиз — бутун умр яшайсиз."],
 "RU": ["Купили квартиру, а она ещё в состоянии коробки?",
        "Электрик, сантехник, штукатур — искать каждого отдельно и мучиться?",
        "Теперь это не нужно.",
        "Напишите в бот OZOD JAMOL Дизайн — подберём проверенного мастера под вашу задачу.",
        "Мастер приедет и проведёт осмотр бесплатно.",
        "Хотите — увидите свой дом в 3D ещё до ремонта.",
        "Минимализм, хай-тек, классика или восточный стиль — стиль выбираете сами.",
        "Один бот — и мастер, и дизайн. Ссылку оставил в комментариях.",
        "OZOD JAMOL. Дом строят один раз — живут в нём всю жизнь."]}[L]
# инфографика по фразам (маленькие чипы, не плашки)
CHIPS = {
 "UZ": {0: ["КОРОБКА ҲОЛАТИ"], 1: ["ЭЛЕКТРИК", "САНТЕХНИК", "СУВОҚЧИ"], 3: ["ТЕКШИРИЛГАН УСТА"],
        4: ["КЎРИК — БЕПУЛ"], 5: ["3D ЛОЙИҲА"], 7: ["УСТА", "ДИЗАЙН"]},
 "RU": {0: ["СОСТОЯНИЕ: КОРОБКА"], 1: ["ЭЛЕКТРИК", "САНТЕХНИК", "ШТУКАТУР"], 3: ["ПРОВЕРЕННЫЙ МАСТЕР"],
        4: ["ОСМОТР — БЕСПЛАТНО"], 5: ["3D ПРОЕКТ"], 7: ["МАСТЕР", "ДИЗАЙН"]}}[L]
STYLES = {"UZ": ["МИНИМАЛИЗМ", "ХАЙ-ТЕК", "КЛАССИКА", "ШАРҚОНА"], "RU": ["МИНИМАЛИЗМ", "ХАЙ-ТЕК", "КЛАССИКА", "ВОСТОЧНЫЙ"]}[L]

# ---------- тайминг слов: мои слова ↔ таймлайн whisper по доле символов
ww = json.load(open(f"{D}/words_{L}.json"))
cum, tl = [0.0], []
for s, e, t in ww:
    n = max(1, len(t)); tl.append((cum[-1], s, e, n)); cum.append(cum[-1] + n)
TOT = cum[-1]
def t_at(frac):
    x = frac * TOT; i = max(0, bisect.bisect_right(cum, x) - 1); i = min(i, len(tl) - 1)
    c0, s, e, n = tl[i]; return s + (e - s) * min(1, max(0, (x - c0) / n))
words = []  # (phrase, text, start, end)
toks = []
BRK = set()
for l in LINES:
    t = []
    for w in l.split():
        if w in ("—", "-"):
            if t: BRK.add((len(toks), len(t) - 1))
        else: t.append(w)
    toks.append(t)
mt = sum(len(w) for p in toks for w in p); c = 0
for pi, p in enumerate(toks):
    for wi, w in enumerate(p):
        st = t_at(c / mt); c += len(w); en = t_at(c / mt); words.append([pi, w, st, en, (pi, wi) in BRK])
VD = dur_of(VOICE)
pstart = [min(w[2] for w in words if w[0] == k) for k in range(9)]
pstart[0] = 0.0
starts = [x[0] for i, x in enumerate(ww) if L == "UZ" or i == 0 or ww[i-1][2][-1:] in ".?!"]
VD0 = dur_of(VOICE)
for k in range(1, 9):
    near = min(starts, key=lambda z: abs(z - pstart[k]))
    if abs(near - pstart[k]) < 1.2: pstart[k] = near
# слова внутри фразы: от начала фразы до конца речи перед следующей фразой, по доле символов
for k in range(9):
    a0 = pstart[k]; nxt = pstart[k + 1] if k < 8 else VD0
    ends = [x[1] for x in ww if a0 < x[1] <= nxt + 0.01]; b0 = max(ends) if ends else nxt
    pw = [w for w in words if w[0] == k]; tot = sum(len(w[1]) for w in pw); c = 0
    for w in pw:
        w[2] = a0 + (b0 - a0) * c / tot; c += len(w[1]); w[3] = a0 + (b0 - a0) * c / tot
VD = dur_of(VOICE)
TAIL = 0.9; BODY = VD + TAIL
bounds = pstart[1:] + [BODY]
print("фразы:", [round(x, 2) for x in pstart], "длина", round(BODY, 2))

# ---------- вспомогательная графика
def chip_png(name, chips, y=250):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im); f = ImageFont.truetype(FB, 58)
    for k, t in enumerate(chips):
        tw = d.textlength(t, font=f); x0 = (W - tw) / 2 - 40; yy = y + k * 120
        d.rounded_rectangle([x0, yy, x0 + tw + 80, yy + 96], 48, fill=DK, outline=RED, width=5)
        d.text((x0 + 40, yy + 16), t, font=f, fill=WH, embedded_color=True)
    im.save(f"{T}/{name}.png")

def seg_clip(name, clip, dur, chips=None, offset=0.0):
    sp_ = max(1.0, min(2.2, (7.9 - offset) / dur))
    out = f"{T}/{name}.mp4"
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", str(offset), "-i", f"{S}/{clip}.mp4"]
    fc = f"[0:v]setpts=PTS/{sp_},scale={W}:{H}:flags=lanczos,fps={FPS},trim=0:{dur},setpts=PTS-STARTPTS[v]"
    if chips:
        chip_png(name, chips); cmd += ["-loop", "1", "-t", str(dur), "-i", f"{T}/{name}.png"]
        fc += f";[1:v]format=rgba,fade=in:st=0.1:d=0.3:alpha=1[t];[v][t]overlay=0:0[v]"
    fc += ";[v]format=yuv420p[o]"
    run(cmd + ["-filter_complex", fc, "-map", "[o]", "-an", "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", out])
    return out

def still_seg(name, img, dur, zoom=True):
    out = f"{T}/{name}.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", img, "-filter_complex",
         f"[0:v]scale={int(W*1.15)}:-2,zoompan=z='1+0.0012*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(dur*FPS)+2}:s={W}x{H}:fps={FPS},format=yuv420p[o]",
         "-map", "[o]", "-t", str(dur), "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", out])
    return out

def fill_jpg(src, dst):
    im = Image.open(src).convert("RGB"); r = max(W / im.width, H / im.height)
    im = im.resize((int(im.width * r) + 1, int(im.height * r) + 1), Image.LANCZOS)
    x, y = (im.width - W) // 2, (im.height - H) // 2; im.crop((x, y, x + W, y + H)).save(dst, quality=95)

# фон для «бот»-сцен: размытый вечерний кадр
run(["ffmpeg", "-v", "error", "-y", "-sseof", "-0.2", "-i", f"{S}/c7b.mp4", "-frames:v", "1", "-vf", f"scale={W}:{H}", f"{T}/last.png"])
bg = Image.open(f"{T}/last.png").convert("RGB").filter(ImageFilter.GaussianBlur(22))
bg = Image.blend(bg, Image.new("RGB", bg.size, (8, 8, 10)), 0.5)
logo = Image.open(f"{D}/tmp/logo.png").convert("RGBA").resize((520, 520), Image.LANCZOS)
mk = Image.new("L", (520, 520), 0); ImageDraw.Draw(mk).ellipse([4, 4, 516, 516], fill=255); logo.putalpha(mk)

def bot_frame(name, chips, handle=True):
    im = bg.convert("RGBA"); im.alpha_composite(logo, ((W - 520) // 2, 260)); d = ImageDraw.Draw(im)
    if handle:
        f = ImageFont.truetype(FB, 54); t = "@ozodjamoldizaynbot"; tw = d.textlength(t, font=f)
        d.rounded_rectangle([(W - tw) / 2 - 44, 830, (W + tw) / 2 + 44, 930], 50, fill=(255, 255, 255, 255))
        d.text(((W - tw) / 2, 845), t, font=f, fill=(10, 10, 12, 255))
    f = ImageFont.truetype(FB, 70)
    if len(chips) == 2:  # две карточки рядом: УСТА + ДИЗАЙН
        for k, t in enumerate(chips):
            x0 = 90 + k * 470; d.rounded_rectangle([x0, 990, x0 + 430, 1130], 40, fill=DK, outline=RED, width=6)
            tw = d.textlength(t, font=f); d.text((x0 + (430 - tw) / 2, 1022), t, font=f, fill=WH)
        d.text(((W - d.textlength("+", font=f)) / 2, 1022), "+", font=f, fill=YL)
    else:
        for k, t in enumerate(chips):
            tw = d.textlength(t, font=f); x0 = (W - tw) / 2 - 50
            d.rounded_rectangle([x0, 990, x0 + tw + 100, 1120], 40, fill=DK, outline=RED, width=6)
            d.text((x0 + 50, 1015), t, font=f, fill=WH)
    p = f"{T}/{name}.jpg"; im.convert("RGB").save(p, quality=95); return p

# ---------- сцены по фразам
parts = []
def L_(k): return bounds[k] - pstart[k]
parts.append(seg_clip("p0", "c1a", L_(0), CHIPS[0]))
h = L_(1) / 2; parts.append(seg_clip("p1a", "c2a", h, CHIPS[1][:2])); parts.append(seg_clip("p1b", "c3a", L_(1) - h, CHIPS[1][2:]))
parts.append(seg_clip("p2", "c4a", L_(2)))
# фраза 4: бот → логотип + ник, потом реальный кадр с чипом
h = min(2.2, L_(3) * 0.5)
parts.append(still_seg("p3a", bot_frame("b3", [], True), h)); parts.append(seg_clip("p3b", "c5a", L_(3) - h, CHIPS[3]))
parts.append(seg_clip("p4", "c6a", L_(4), CHIPS[4]))
parts.append(seg_clip("p5", "c7b", L_(5), CHIPS[5]))
q = L_(6) / 4
for j, f in enumerate(["st_japandi", "st_haytek", "st_klassika", "st_sharq"]):
    fill_jpg(f"/home/claude/fl/dizayn-out/{f}.png", f"{T}/{f}.jpg")
    im = Image.open(f"{T}/{f}.jpg").convert("RGBA"); chip_png(f"stc{j}", [STYLES[j]], 250)
    im.alpha_composite(Image.open(f"{T}/stc{j}.png")); im.convert("RGB").save(f"{T}/{f}_c.jpg", quality=95)
    parts.append(still_seg(f"p6{j}", f"{T}/{f}_c.jpg", q))
parts.append(still_seg("p7", bot_frame("b7", CHIPS[7], True), L_(7)))
parts.append(seg_clip("p8", "c7a", L_(8), None, 2.0))

# ---------- склейка видео
lst = f"{T}/list.txt"; open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", f"{T}/body_v.mp4"])

# ---------- субтитры по словам: группы до 3 слов внутри фразы, текущее слово — жёлтое
fS = ImageFont.truetype(FB, 84)
groups = []
for pi in range(9):
    pw = [w for w in words if w[0] == pi]; g = []
    for w in pw:
        g.append(w)
        tw = ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(" ".join(x[1] for x in g), font=fS)
        if len(g) == 3 or w[1][-1] in ",.?" or w[4] or tw > 860:
            if len(g) > 1 and len(g[-1][1]) <= 2 and not (w[1][-1] in ",.?" or w[4]):
                groups.append(g[:-1]); g = [g[-1]]
            else:
                groups.append(g); g = []
    if g: groups.append(g)
SUBY = 1400
def sub_png(path, g, hi):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    txt = [x[1].upper() for x in g]; sp_w = d.textlength(" ", font=fS)
    ws = [d.textlength(t, font=fS) for t in txt]; tot = sum(ws) + sp_w * (len(ws) - 1)
    lines = [[0, len(txt)]]
    if tot > 940:  # перенос на 2 строки
        lines = [[0, 1], [1, len(txt)]] if len(txt) == 2 else [[0, 2], [2, len(txt)]]
    for li, (a, b) in enumerate(lines):
        lw = sum(ws[a:b]) + sp_w * (b - a - 1); x = (W - lw) / 2; y = SUBY + li * 104
        for k in range(a, b):
            col = YL if k == hi else WH
            d.text((x, y), txt[k], font=fS, fill=col, stroke_width=8, stroke_fill=(0, 0, 0, 255)); x += ws[k] + sp_w
    im.save(path)
# кадры-события: каждая смена подсвеченного слова
ev = []
for gi, g in enumerate(groups):
    for k, w in enumerate(g):
        p = f"{T}/sub_{gi}_{k}.png"; sub_png(p, g, k)
        end = g[k + 1][2] if k + 1 < len(g) else (groups[gi + 1][0][2] if gi + 1 < len(groups) and groups[gi + 1][0][0] == g[0][0] else w[3] + 0.25)
        ev.append((w[2], max(w[2] + 0.12, end), p))
# собираем дорожку субтитров как concat png с длительностями (прозрачность → qtrle)
blank = f"{T}/blank.png"; Image.new("RGBA", (W, H), (0, 0, 0, 0)).save(blank)
seq, t = [], 0.0
for st, en, p in ev:
    st = max(st, t)
    if st - t > 0.01: seq.append((blank, st - t))
    if en - st > 0.01: seq.append((p, en - st)); t = en
seq.append((blank, BODY - t + 0.1))
cl = f"{T}/subs.txt"
open(cl, "w").write("".join(f"file '{p}'\nduration {d:.3f}\n" for p, d in seq) + f"file '{blank}'\n")
run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", cl, "-vf", f"fps={FPS},format=rgba", "-c:v", "qtrle", f"{T}/subs.mov"])
run(["ffmpeg", "-v", "error", "-y", "-i", f"{T}/body_v.mp4", "-i", f"{T}/subs.mov", "-filter_complex",
     f"[0:v][1:v]overlay=0:0:shortest=0,trim=0:{BODY},setpts=PTS-STARTPTS,format=yuv420p[o]", "-map", "[o]",
     "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-r", str(FPS), f"{T}/body_s.mp4"])

# ---------- звук: голос + музыка тихо с приглушением под голос + «вжух» на стилях
st6 = pstart[6]
run(["ffmpeg", "-v", "error", "-y", "-i", f"{T}/body_s.mp4", "-i", VOICE, "-i", f"{DL}/aurec-sunset-house-598438.mp3",
     "-i", f"{DL}/soundreality-whoosh-large-sub-384631.mp3", "-filter_complex",
     f"[1:a]aresample=48000,highpass=f=80,acompressor=threshold=-20dB:ratio=3:attack=5:release=120,aecho=0.8:0.7:40:0.12,volume=1.6,asplit=2[v][sc];"
     f"[2:a]aresample=48000,atrim=0:{BODY},afade=in:st=0:d=1.0,afade=out:st={BODY-1.8}:d=1.6,volume=0.30[m0];"
     f"[m0][sc]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[m];"
     f"[3:a]aresample=48000,adelay={int((st6-0.2)*1000)}|{int((st6-0.2)*1000)},volume=0.45[w];"
     f"[v][m][w]amix=inputs=3:duration=longest:normalize=0,atrim=0:{BODY},alimiter=limit=0.95[a]",
     "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", f"{T}/body_a.mp4"])

# ---------- + фирменная концовка
outs = []
for k, p in enumerate([f"{T}/body_a.mp4", f"{DL}/OZOD_JAMOL_KONCOVKA_CHERNAYA.mp4"]):
    o = f"{T}/z{k}.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-i", p, "-vf", f"scale={W}:{H},fps={FPS},format=yuv420p", "-c:v", "libx264", "-preset", "medium",
         "-crf", "16", "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", o]); outs.append(o)
open(f"{T}/fin.txt", "w").write("".join(f"file '{p}'\n" for p in outs))
OUT = f"{D}/OZOD_JAMOL_DIZAYN_{L}.mp4"
run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{T}/fin.txt", "-c", "copy", "-movflags", "+faststart", OUT])
print("OK", OUT, round(dur_of(OUT), 1), "s")
