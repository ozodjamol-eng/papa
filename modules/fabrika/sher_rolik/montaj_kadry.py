# Ролик-стих из ГОТОВЫХ кадров (01.11, владелец: «используй сгенерированное, остальное не трогай»):
# медленное движение камеры (cv2, одна передискретизация), качание дерева, пульс луча, золотые пылинки, зерно, виньетка,
# титры строк внизу (Montserrat 800, по таймингам timings.json), кроссфейды 1 с. Новых генераций нет.
# Запуск: python3 montaj_kadry.py <папка_кадров> <timings.json> <audio.mp3> <итог.mp4>
import json, subprocess, sys, math
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
SRC, TJ, AUD, OUT = sys.argv[1:5]
W, H, FPS = 1080, 1920, 30
T = json.load(open(TJ)); starts = [a for a, _ in T]; ends = [a + b for a, b in T]
DUR = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", AUD], capture_output=True, text=True).stdout)
IMG = {k: cv2.imread(f"{SRC}/tushimda_{k}.jpg")[:, :, ::-1].astype(np.float32) / 255 for k in
       ["rassvet_1", "rassvet_2", "pirs_1", "pirs_2", "derevo_1", "derevo_2"]}
LINES = ["Тушимда Аллоҳ билан гаплашдим.", "Ундан шундай сўрадим:", "«Нега ёмон нарсалар яхши инсонларнинг бошига келади?»",
 "Аллоҳ қалбимга шундай илҳом қилди:", "«Энг кучли дарахтлар ҳам кучли шамоллар билан синалади.", "Ҳар қандай имтиҳон сени янада сабрли ва янада кучли қилади».",
 "Мен яна сўрадим:", "«Нега бунчалар ўзимни ёлғиз ҳис қиляпман?»", "Аллоҳ қалбимга дедики:", "«Мени кўрмаганлигинг ёнингда эмасман дегани эмас.",
 "Сенга сен ўйлагандан ҳам яқинроқман».", "Мен яна сўрадим:", "«Ҳаммаси бир кун келиб яхши бўладими?»", "«Мен тақдир қилган вақт сеники эмас. Сабр қил.",
 "Ҳар бир қийинчилик ортидан енгиллик келади.", "Шамоллар тугайди, қуёш янгидан чиқади».", "Мен қўрқиб сўрадим:", "«Бу юкларни кўтара олмасам-чи?»",
 "Аллоҳ қалбимга ҳузур берди:", "«Аллоҳ ҳеч кимга кучи етмайдиган юк бермайди.", "Сен заиф бўлганингда куч берадиган Менман».",
 "Кўз ёш билан пичирладим:", "«Гуноҳларим кўп бўлса ҳам, мени севасанми?»", "Аллоҳ яна қалбимга ҳузур берди:", "«Мен тавба қилган бандаларимга чексиз марҳаматлиман», — деди."]
assert len(LINES) == len(T)
s = starts
# план: (начало, конец, кадр, зум0, зум1, центр0(x,y доли), центр1, эффект)
SH = [(0, s[1], "pirs_1", 1.00, 1.10, (.5, .55), (.47, .5), ""),
      (s[1], s[3], "pirs_1", 1.22, 1.30, (.44, .45), (.44, .42), ""),
      (s[3], s[4], "derevo_2", 1.04, 1.14, (.55, .5), (.6, .45), "sway"),
      (s[4], s[6], "derevo_1", 1.16, 1.04, (.5, .45), (.5, .5), "sway"),
      (s[6], s[8], "pirs_1", 1.45, 1.52, (.30, .55), (.30, .52), ""),
      (s[8], s[11], "pirs_2", 1.02, 1.16, (.5, .55), (.6, .45), "beam"),
      (s[11], s[13], "derevo_1", 1.30, 1.22, (.5, .22), (.5, .28), "dark"),
      (s[13], s[15], "rassvet_1", 1.10, 1.02, (.5, .35), (.5, .45), "rise"),
      (s[15], s[16], "rassvet_2", 1.02, 1.10, (.5, .45), (.5, .35), ""),
      (s[16], s[18], "rassvet_2", 1.35, 1.35, (.48, .8), (.48, .55), ""),
      (s[18], s[21], "derevo_2", 1.02, 1.12, (.5, .55), (.52, .45), "sway"),
      (s[21], s[23], "pirs_2", 1.25, 1.35, (.6, .5), (.62, .55), "beam"),
      (s[23], DUR, "rassvet_1", 1.12, 1.00, (.5, .3), (.5, .5), "rise")]
XF = 1.0
def ease(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)
def frame_of(sh, t):
    a, b, k, z0, z1, c0, c1, fx = sh
    u = ease((t - a) / max(0.1, b - a + XF)); img = IMG[k]; h, w = img.shape[:2]
    z = z0 + (z1 - z0) * u; cx = (c0[0] + (c1[0] - c0[0]) * u) * w; cy = (c0[1] + (c1[1] - c0[1]) * u) * h
    sc = max(W / w, H / h) * z
    cx = min(max(cx, W / sc / 2), w - W / sc / 2); cy = min(max(cy, H / sc / 2), h - H / sc / 2)
    ang = 0.35 * math.sin(t * 1.3) + 0.15 * math.sin(t * 2.9) if fx == "sway" else 0
    M = cv2.getRotationMatrix2D((cx, cy), ang, sc); M[0, 2] += W / 2 - cx; M[1, 2] += H / 2 - cy
    f = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    if fx == "beam": f = f * (1 + 0.06 * (0.5 + 0.5 * math.sin(t * 1.6))) + 0.03 * (0.5 + 0.5 * math.sin(t * 1.6)) * np.array([1, .8, .5])
    if fx == "dark": f = f * (0.75 + 0.1 * u)
    if fx == "rise": f = f * (0.85 + 0.25 * u) + 0.04 * u * np.array([1, .85, .6])
    return f
rng = np.random.default_rng(7); NP = 140
P = np.c_[rng.uniform(0, W, NP), rng.uniform(0, H, NP), rng.uniform(1.2, 3.5, NP), rng.uniform(6, 22, NP), rng.uniform(0, 6.28, NP)]
yy, xx = np.mgrid[0:H, 0:W]; vig = 1 - 0.38 * (((xx - W / 2) / (W / 2)) ** 2 * 0.6 + ((yy - H / 2) / (H / 2)) ** 2 * 0.8)
vig = np.clip(vig, 0.55, 1)[..., None].astype(np.float32)
FONT = ImageFont.truetype("/home/claude/fonts/Montserrat800.ttf", 46)
def wrap(txt, maxw=900):
    d = ImageDraw.Draw(Image.new("L", (1, 1))); words = txt.split(); lines = [""]
    for wd in words:
        tryl = (lines[-1] + " " + wd).strip()
        if d.textlength(tryl, font=FONT) <= maxw: lines[-1] = tryl
        else: lines.append(wd)
    return lines
SUB = []
for i, txt in enumerate(LINES):
    ls = wrap(txt); lh = 62; hh = lh * len(ls) + 40
    im = Image.new("RGBA", (W, hh), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for j, l in enumerate(ls):
        tw = d.textlength(l, font=FONT); d.text(((W - tw) / 2, 20 + j * lh), l, font=FONT, fill=(255, 255, 255, 255))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); sh.putalpha(im.split()[3].filter(ImageFilter.GaussianBlur(9)).point(lambda v: int(v * 0.85)))
    comp = Image.alpha_composite(sh, im); a = np.asarray(comp).astype(np.float32) / 255
    SUB.append((starts[i], ends[i], a))
SUBY = 1530
ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", AUD,
                       "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-b:v", "2850k", "-maxrate", "4500k", "-bufsize", "9000k", "-pix_fmt", "yuv420p",
                       "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", OUT], stdin=subprocess.PIPE)
N = int(DUR * FPS)
for n in range(N):
    t = n / FPS
    cur = [sh for sh in SH if sh[0] - 1e-6 <= t < sh[1] + XF]
    if len(cur) >= 2 and t >= cur[1][0]:
        w2 = ease((t - cur[1][0]) / XF); fr = frame_of(cur[0], t) * (1 - w2) + frame_of(cur[1], t) * w2
    else: fr = frame_of(cur[0], t)
    # пылинки
    ov = np.zeros((H, W), np.float32)
    for (x0, y0, r, sp, ph) in P:
        x = (x0 + 12 * math.sin(t * 0.4 + ph)) % W; y = (y0 - sp * t) % H
        cv2.circle(ov, (int(x), int(y)), int(r), 0.35 + 0.25 * math.sin(t * 1.7 + ph), -1, cv2.LINE_AA)
    ov = cv2.GaussianBlur(ov, (0, 0), 1.6)[..., None]
    fr = fr * vig + ov * np.array([1, .82, .5], np.float32) * 0.35
    fr = fr + rng.normal(0, 0.007, (H // 2, W // 2, 1)).repeat(2, 0).repeat(2, 1).astype(np.float32)
    # титры
    for (a, b, sa) in SUB:
        if a - 0.2 <= t <= b + 0.6:
            al = min(1, (t - a + 0.2) / 0.35, (b + 0.6 - t) / 0.45)
            if al > 0:
                hh = sa.shape[0]; y0 = SUBY - hh // 2; reg = fr[y0:y0 + hh]
                aa = sa[..., 3:4] * al; fr[y0:y0 + hh] = reg * (1 - aa) + sa[..., :3] * aa
    # затемнение в начале и в конце
    fade = min(1, t / 1.2, (DUR - t) / 2.5); fr = fr * max(0, fade)
    ff.stdin.write((np.clip(fr, 0, 1) * 255).astype(np.uint8).tobytes())
ff.stdin.close(); ff.wait(); print("готово", OUT, f"{DUR:.1f} с, {N} кадров")
