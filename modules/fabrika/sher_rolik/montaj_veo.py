# Ролик-стих из видео Veo (метод «уровень 3», лицо владельца) — 01.11.2026.
# Шаг 1: ffmpeg склеивает дубли по плану (замедление, если план длиннее дубля; кроссфейд XF).
# Шаг 2: python кладёт титры (Montserrat 800, по timings.json), лёгкое зерно, затемнение в начале/конце; звук — утверждённый.
# Урок: два дубля одной сцены подряд через кроссфейд = «призрак» (двойной силуэт) — между ними ставить другую сцену.
# Запуск: python3 montaj_veo.py <папка_клипов> <timings.json> <audio.mp3> <итог.mp4>
import json, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
SRC, TJ, AUD, OUT = sys.argv[1:5]
W, H, FPS, XF, CLIP = 1080, 1920, 30, 0.6, 7.9
T = json.load(open(TJ)); starts = [a for a, _ in T]; ends = [a + b for a, b in T]
DUR = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", AUD],
                           capture_output=True, text=True).stdout)
# (начало, конец, клип, с какой секунды клипа, до какой секунды клипа можно)
PLAN = [(0.0, 7.5, "Man_looking_at_moon_126ba817", 0, CLIP),
        (7.5, 15.3, "Man_sleeping_in_dark_99c7be03", 0, CLIP),
        (15.3, 23.2, "Lone_tree_in_storm_wind_c1b3f556", 0, CLIP),
        (23.2, 33.3, "Man_climbing_mountain_path_641e6746", 0, CLIP),
        (33.3, 41.5, "Man_walking_on_wet_shore_89b28ad7", 0, CLIP),
        (41.5, 44.8, "Man_holding_open_palms_up_301c7ab7", 0, CLIP),
        (44.8, 54.9, "Man_sleeping_in_dark_2e958e3e", 0, CLIP),
        (54.9, 62.8, "Man_standing_on_hilltop_sunrise_47b8a1c2", 0, CLIP),
        (62.8, 70.5, "Lone_tree_in_storm_wind_9b1fd54b", 0, CLIP),
        (70.5, 78.6, "Man_standing_on_hilltop_sunrise_56621725", 0, CLIP),
        (78.6, 88.7, "Man_climbing_mountain_path_3ec81cf9", 0, CLIP),
        (88.7, 96.6, "Man_looking_upward_crying_17398c86", 0, CLIP),
        (96.6, 104.5, "Man_holding_open_palms_up_e197571d", 0, CLIP),
        (104.5, 112.4, "Man_looking_upward_crying_dabe55f3", 0, CLIP),
        (112.4, DUR, "Man_kneeling_on_hill_744ecdfa", 0, CLIP)]
BASE = OUT + ".base.mp4"
inp, fl = [], []
for i, (a, b, k, s0, s1) in enumerate(PLAN):
    need = (b - a) + (XF if i < len(PLAN) - 1 else 0)
    rate = min(1.0, (s1 - s0) / need)          # <1 — замедление
    inp += ["-i", f"{SRC}/{k}.mp4"]
    fl.append(f"[{i}:v]trim={s0}:{s1},setpts=(PTS-STARTPTS)/{rate:.4f},fps={FPS},"
              f"scale={W}:{H}:flags=lanczos,setsar=1,trim=0:{need:.3f},setpts=PTS-STARTPTS[v{i}]")
prev = "v0"
for i in range(1, len(PLAN)):
    fl.append(f"[{prev}][v{i}]xfade=transition=fade:duration={XF}:offset={PLAN[i][0]:.3f}[x{i}]"); prev = f"x{i}"
subprocess.run(["ffmpeg", "-v", "error", "-y", *inp, "-filter_complex", ";".join(fl), "-map", f"[{prev}]",
                "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", BASE], check=True)
LINES = ["Тушимда Аллоҳ билан гаплашдим.", "Ундан шундай сўрадим:", "«Нега ёмон нарсалар яхши инсонларнинг бошига келади?»",
 "Аллоҳ қалбимга шундай илҳом қилди:", "«Энг кучли дарахтлар ҳам кучли шамоллар билан синалади.", "Ҳар қандай имтиҳон сени янада сабрли ва янада кучли қилади».",
 "Мен яна сўрадим:", "«Нега бунчалар ўзимни ёлғиз ҳис қиляпман?»", "Аллоҳ қалбимга дедики:", "«Мени кўрмаганлигинг ёнингда эмасман дегани эмас.",
 "Сенга сен ўйлагандан ҳам яқинроқман».", "Мен яна сўрадим:", "«Ҳаммаси бир кун келиб яхши бўладими?»", "«Мен тақдир қилган вақт сеники эмас. Сабр қил.",
 "Ҳар бир қийинчилик ортидан енгиллик келади.", "Шамоллар тугайди, қуёш янгидан чиқади».", "Мен қўрқиб сўрадим:", "«Бу юкларни кўтара олмасам-чи?»",
 "Аллоҳ қалбимга ҳузур берди:", "«Аллоҳ ҳеч кимга кучи етмайдиган юк бермайди.", "Сен заиф бўлганингда куч берадиган Менман».",
 "Кўз ёш билан пичирладим:", "«Гуноҳларим кўп бўлса ҳам, мени севасанми?»", "Аллоҳ яна қалбимга ҳузур берди:", "«Мен тавба қилган бандаларимга чексиз марҳаматлиман», — деди."]
assert len(LINES) == len(T)
FONT = ImageFont.truetype("/home/claude/fonts/Montserrat800.ttf", 50)
def wrap(txt, maxw=920):
    d = ImageDraw.Draw(Image.new("L", (1, 1))); lines = [""]
    for wd in txt.split():
        t2 = (lines[-1] + " " + wd).strip()
        if d.textlength(t2, font=FONT) <= maxw: lines[-1] = t2
        else: lines.append(wd)
    return lines
SUB = []
for i, txt in enumerate(LINES):
    ls = wrap(txt); lh = 66; hh = lh * len(ls) + 50
    im = Image.new("RGBA", (W, hh), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for j, l in enumerate(ls):
        tw = d.textlength(l, font=FONT)
        d.text(((W - tw) / 2, 25 + j * lh), l, font=FONT, fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0, 160))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); sh.putalpha(im.split()[3].filter(ImageFilter.GaussianBlur(11)).point(lambda v: int(v * 0.9)))
    a = np.asarray(Image.alpha_composite(sh, im)).astype(np.float32) / 255
    SUB.append((starts[i], ends[i], a))
SUBY = 1500
rng = np.random.default_rng(7)
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", BASE, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", AUD,
                        "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-b:v", "2850k", "-maxrate", "4500k", "-bufsize", "9000k",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", OUT], stdin=subprocess.PIPE)
n = 0; FS = W * H * 3
while True:
    buf = dec.stdout.read(FS)
    if len(buf) < FS: break
    t = n / FPS; fr = np.frombuffer(buf, np.uint8).reshape(H, W, 3).astype(np.float32) / 255
    # мягкое затемнение низа под титры (не трогает лицо)
    fr[1300:] *= np.linspace(1, 0.72, H - 1300, dtype=np.float32)[:, None, None]
    fr += rng.normal(0, 0.006, (H // 2, W // 2, 1)).repeat(2, 0).repeat(2, 1).astype(np.float32)
    for (a, b, sa) in SUB:
        if a - 0.2 <= t <= b + 0.6:
            al = min(1, (t - a + 0.2) / 0.35, (b + 0.6 - t) / 0.45)
            if al > 0:
                hh = sa.shape[0]; y0 = SUBY - hh // 2; reg = fr[y0:y0 + hh]
                aa = sa[..., 3:4] * al; fr[y0:y0 + hh] = reg * (1 - aa) + sa[..., :3] * aa
    fr *= max(0, min(1, t / 1.0, (DUR - t) / 2.5))
    enc.stdin.write((np.clip(fr, 0, 1) * 255).astype(np.uint8).tobytes()); n += 1
enc.stdin.close(); enc.wait(); dec.wait(); print("готово", OUT, f"{n / FPS:.1f} с")
