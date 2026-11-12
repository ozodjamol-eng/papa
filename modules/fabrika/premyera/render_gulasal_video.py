"""Премьера по ВИДЕО артиста (12.11.2026, Гуласал Абдуллаева «Сиз мен билан»).
Урок владельца: если прислано готовое видео — оно идёт на весь ролик, наш диктор — в промежутках пения.
Видео идёт по своей линии времени (без склеек). Под диктором: вокал убран (минус), видео затемнено и размыто,
крупные тексты = речь. Во время пения — внизу матовая плашка поверх чужих латинских подписей и наши строки кириллицей.
Хелперы (text_layer, pill, over, leak, sweep, dust) — из render_gulyosar.py.
"""
import sys, subprocess, math
import cv2, numpy as np
sys.path.insert(0, "/home/claude/papa/modules/fabrika/premyera")
import render_gulyosar as R
from render_gulyosar import text_layer, pill, over, win, rise, ease, leak, sweep, dust, BLK, XB, RED, W, H, FPS

SRC = "/home/claude/in/src.mp4"
OUT = "/home/claude/vs/main_v.mp4"
DUR = 51.0
A1, A2, B, C = 12.6, 26.7, 40.15, 45.2          # старты фраз диктора на общей линии
QUIET = [(12.45, 16.45), (26.55, 32.95), (40.0, 99)]  # где вокал убран (нужно и для звука)
PINK = (255, 225, 238)

# матовая плашка поверх чужих подписей (в исходнике ~y 850–1010 из 1280 → 1275–1515)
BY0, BY1 = 1320, 1650
m = np.zeros((H, 1), np.float32)
yy = np.arange(H, dtype=np.float32)
m[:, 0] = np.clip((yy - BY0) / 45, 0, 1) * np.clip((BY1 - yy) / 45, 0, 1)
BAND = m[..., None]

def lyr(t):
    return text_layer([(t, BLK, 64, (255, 255, 255), 2, 0)])

LYR = [(2.3, 7.8, text_layer([("ЯНГИ ҚЎШИҚ", BLK, 72, (255, 255, 255), 4, 0)])),
       (8.0, 10.25, lyr("СИЗ МЕН БИЛАН")), (10.25, 12.45, lyr("МЕН СИЗ БИЛАН")),
       (16.5, 21.2, lyr("ҚУВВАТ ОЛИБ ЯШАЙМАНДА")), (21.2, 26.5, lyr("ЖОНИМ ДЕГАН СЎЗИНГИЗДАН")),
       (33.0, 37.0, lyr("ДОИМ ГУЛДЕК ЯШНАЙМАНДА")), (37.0, 40.0, lyr("СЕВАМАН ДЕГАН СЎЗИНГИЗДАН"))]
for i, (a, b, L) in enumerate(LYR):  # длинные строки ужать по ширине
    if L.shape[1] > W - 80:
        k = (W - 80) / L.shape[1]
        LYR[i] = (a, b, cv2.resize(L, (int(L.shape[1] * k), int(L.shape[0] * k)), interpolation=cv2.INTER_AREA))

L_PREM_BIG = text_layer([("ПРЕМЬЕРА", BLK, 128, (255, 255, 255), 6, 0)])
L_PREM_TOP = text_layer([("ПРЕМЬЕРА", BLK, 44, (255, 255, 255), 16, 0)])
P_SONG_TOP = pill("«СИЗ МЕН БИЛАН»", 34, fill=RED, fg=(255, 255, 255), icon=False)
C_DATE = text_layer([("15-НОЯБРЬ", BLK, 150, (255, 255, 255), 2, 0)])
C_TIME = text_layer([("СОАТ 20:00", BLK, 96, (255, 255, 255), 4, 0)])
C_N1 = text_layer([("ГУЛАСАЛ", BLK, 150, (255, 255, 255), 2, 0)])
C_N2 = text_layer([("АБДУЛЛАЕВА", BLK, 124, (255, 255, 255), 2, 0)])
C_SONG = pill("«СИЗ МЕН БИЛАН»", 72, fill=RED, fg=(255, 255, 255), icon=False)
C_EXC = text_layer([("ЭКСКЛЮЗИВ ПРЕМЬЕРА", XB, 50, PINK, 6, 0)])
D_W = [text_layer([(w, BLK, 96, (255, 255, 255), 3, 0)]) for w in ("МЕҲР", "БАХТ", "ТУЙҒУ")]
D_NEW = text_layer([("ЯНГИ ҚЎШИҚ", BLK, 100, (255, 255, 255), 4, 0)])
E_1 = text_layer([("ПРЕМЬЕРАНИ", XB, 52, PINK, 10, 0)])
E_2 = text_layer([("КАТТА ДАВРА", BLK, 116, (255, 255, 255), 2, 0)])
E_3 = text_layer([("КАНАЛИДА КУТИНГ!", BLK, 64, (255, 255, 255), 3, 0)])
E_4 = text_layer([("15-НОЯБРЬ · 20:00", XB, 50, (255, 205, 225), 4, 0)])
P_TG_BIG = pill("@kattadavrauz", 46)


def quiet_k(t, r=0.35):
    """0 — обычное видео, 1 — под диктором (затемнение/размытие)."""
    k = 0.0
    for a, b in QUIET:
        k = max(k, min(1, max(0, (t - a) / r)) * min(1, max(0, (b - t) / r)))
    return k


def prep(src):
    f = cv2.resize(src, (W, H), interpolation=cv2.INTER_LANCZOS4).astype(np.float32) / 255
    f = f[:, :, ::-1]
    bl = cv2.GaussianBlur(f, (0, 0), 1.4)
    return np.clip(f * 1.3 - bl * 0.3, 0, 1)


def frame(t, f):
    fr = f.copy()
    q = quiet_k(t)
    # плашка: размытие + затемнение (прячет латинские подписи исходника)
    band = cv2.GaussianBlur(fr[BY0 - 80:BY1 + 80], (0, 0), 30)[80:-80] * 0.36
    fr[BY0:BY1] = fr[BY0:BY1] * (1 - BAND[BY0:BY1]) + band * BAND[BY0:BY1]
    if q > 0.01:
        bq = cv2.GaussianBlur(fr, (0, 0), 3 + 9 * q)
        fr = fr * (1 - q) + bq * q
        fr *= (1 - 0.5 * q)
    # верх: тег «ПРЕМЬЕРА» + песня (в пении)
    vis_top = win(t, 2.3, DUR, 0.4, 0.3) * (1 - q)
    over(fr, L_PREM_TOP, W / 2, 150, vis_top)
    over(fr, P_SONG_TOP, W / 2, 230, vis_top)
    # интро
    if t < 2.3:
        leak(fr, 1.1 * max(0, 1 - t / 1.0), t)
        over(fr, L_PREM_BIG, W / 2, H / 2, win(t, 0.6, 2.2, 0.35, 0.3), 1.12 - 0.12 * ease((t - 0.6) / 0.6))
    # строки песни на плашке
    for a, b, L in LYR:
        over(fr, L, W / 2, (BY0 + BY1) / 2 + rise(t, a, .35, 30), win(t, a, b, .3, .25))
    # A1: дата / время
    over(fr, C_DATE, W / 2, 860 + rise(t, A1, .4, 60), win(t, A1, A1 + 3.6, .35, .3), 1.06 - 0.06 * ease((t - A1) / .5))
    over(fr, C_TIME, W / 2, 1030 + rise(t, A1 + 1.43, .4, 60), win(t, A1 + 1.43, A1 + 3.6, .35, .3))
    leak(fr, 0.6 * max(0, 1 - abs(t - A1 + 0.1) / 0.35), t)
    # A2: имя / песня / эксклюзив
    over(fr, C_N1, W / 2, 760 + rise(t, A2, .4, 60), win(t, A2, A2 + 6.1, .35, .3))
    over(fr, C_N2, W / 2, 920 + rise(t, A2 + 0.5, .4, 60), win(t, A2 + 0.5, A2 + 6.1, .35, .3))
    over(fr, C_SONG, W / 2, 1110, win(t, A2 + 1.95, A2 + 6.1, .25, .3), 1.25 - 0.25 * ease((t - A2 - 1.95) / .35))
    over(fr, C_EXC, W / 2, 1240 + rise(t, A2 + 3.9, .4, 40), win(t, A2 + 3.9, A2 + 6.1, .35, .3))
    leak(fr, 0.6 * max(0, 1 - abs(t - A2 + 0.1) / 0.35), t)
    sweep(fr, t, A2 + 2.0)
    # B: смысл
    for i, (w, ts, y) in enumerate(zip(D_W, (B + 0.05, B + 0.6, B + 1.5), (720, 860, 1000))):
        over(fr, w, W / 2, y + rise(t, ts, .4, 50), win(t, ts, B + 4.75, .35, .3))
    over(fr, D_NEW, W / 2, 1170 + rise(t, B + 3.0, .4, 50), win(t, B + 3.0, B + 4.75, .35, .3), 1.1 - 0.1 * ease((t - B - 3.0) / .4))
    # C: призыв
    if t >= C - 0.1:
        over(fr, E_1, W / 2, 700 + rise(t, C), win(t, C, 99))
        over(fr, E_2, W / 2, 830 + rise(t, C + 0.45, .45, 60), win(t, C + 0.45, 99), 1.08 - 0.08 * ease((t - C - 0.45) / .5))
        over(fr, E_3, W / 2, 960 + rise(t, C + 1.3), win(t, C + 1.3, 99))
        over(fr, P_TG_BIG, W / 2, 1130 + rise(t, C + 1.9), win(t, C + 1.9, 99))
        over(fr, E_4, W / 2, 1270 + rise(t, C + 2.4), win(t, C + 2.4, 99))
        sweep(fr, t, C + 2.8, 1.2)
    dust(fr, t)
    fr += (np.random.rand(H // 4, W // 4).astype(np.float32).repeat(4, 0).repeat(4, 1)[..., None] - .5) * 0.02
    if t > DUR - 0.4:
        fr *= max(0, (DUR - t) / 0.4)
    return np.clip(fr, 0, 1)


if __name__ == "__main__":
    cap = cv2.VideoCapture(SRC)
    if len(sys.argv) > 1 and sys.argv[1] == "stills":
        for t in [1.2, 5.0, 9.0, 14.5, 19.0, 29.5, 35.0, 42.5, 48.5]:
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000); ok, s = cap.read()
            cv2.imwrite(f"/home/claude/vs/sv_{t:05.1f}.jpg", (frame(t, prep(s))[:, :, ::-1] * 255).astype(np.uint8))
        sys.exit()
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", OUT], stdin=subprocess.PIPE)
    n = int(DUR * FPS); last = None
    for i in range(n):
        ok, s = cap.read()
        if ok: last = s
        p.stdin.write((frame(i / FPS, prep(last)) * 255).astype(np.uint8).tobytes())
        if i % 300 == 0: print(i, n, flush=True)
    p.stdin.close(); p.wait()
