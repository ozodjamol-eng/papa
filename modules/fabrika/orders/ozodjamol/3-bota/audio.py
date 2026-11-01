"""Звук ролика «3 бота»: своя музыка (104 BPM, ре минор), звуки в ритм действиям, голос. Без чужой музыки.
Правила владельца: музыка тише голоса; перед логотипом OZOD JAMOL никаких своих вжухов — только звук ролика."""
import numpy as np, wave, subprocess as sp, json
SR = 44100; END = 54.0; N = int(SR * END); t = np.arange(N) / SR
rng = np.random.default_rng(3)
def note(m): return 440 * 2 ** ((m - 69) / 12)
def put(buf, at, sig, g=1.0):
    s = int(at * SR); e = min(len(buf), s + len(sig))
    if s < len(buf): buf[s:e] += g * sig[:e - s]
def env(L, a=.005, r=.2):
    x = np.arange(int(L * SR)) / SR; return np.minimum(1, x / a) * np.exp(-x / r)
BPM = 104; B = 60 / BPM; BAR = 4 * B; DROP = 5.3
mus = np.zeros(N)
# аккорды Dm Bb F C
CH = [[50, 53, 57], [46, 50, 53], [41, 45, 48], [48, 52, 55]]
# пэд всю длину (ночью — тёмный, потом светлее)
for i in range(int(END / BAR) + 2):
    c = CH[i % 4]; s0 = i * BAR - .3
    L = BAR + .6; x = np.arange(int(L * SR)) / SR; e = np.minimum(1, x / .6) * np.minimum(1, (L - x) / .6)
    sig = np.zeros_like(x)
    for m in c:
        for det in (-.12, .12):
            f = note(m + 12)
            sig += np.sin(2 * np.pi * f * (1 + det / 100) * x) + .25 * np.sin(4 * np.pi * f * x)
    put(mus, max(0, s0), sig * e * .022)
# тиканье часов ночью
for k in range(10):
    at = .2 + k * .5
    if at < 5.0:
        L = .03; x = np.arange(int(L * SR)) / SR; put(mus, at, rng.standard_normal(len(x)) * np.exp(-x * 300) * (.10 if k % 2 else .06))
# суб-гул ночью
x = t[:int(5.3 * SR)]; mus[:len(x)] += .05 * np.sin(2 * np.pi * 36.7 * x) * np.minimum(1, x / 1.5)
# райзер к «Бот.»
L = 1.0; x = np.arange(int(L * SR)) / SR; n = rng.standard_normal(len(x))
from scipy.signal import butter, lfilter
def bp(sig, lo, hi):
    b, a = butter(2, [lo / (SR / 2), hi / (SR / 2)], 'band'); return lfilter(b, a, sig)
put(mus, DROP - L, bp(n, 800, 6000) * (x / L) ** 2.5 * .12)
# грув после дропа (с 47.45 — разрежаем)
def kick():
    L = .35; x = np.arange(int(L * SR)) / SR; f = 50 + 90 * np.exp(-x * 35)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 9)
def hat():
    L = .06; x = np.arange(int(L * SR)) / SR; return bp(rng.standard_normal(len(x)), 6000, 14000) * np.exp(-x * 70)
def clap():
    L = .2; x = np.arange(int(L * SR)) / SR; return bp(rng.standard_normal(len(x)), 900, 3500) * np.exp(-x * 25)
nb = int((END - DROP) / B) + 1
for k in range(nb):
    at = DROP + k * B
    if at >= 53.2: break
    cta = at >= 47.45
    put(mus, at, kick(), .30 if not cta else (.22 if k % 2 == 0 else 0))
    if not cta:
        put(mus, at + B / 2, hat(), .05)
        if k % 2 == 1: put(mus, at, clap(), .045)
    # бас — корень аккорда восьмыми
    c = CH[int((at - DROP) / BAR + 1) % 4][0] - 12
    for h in (0, B / 2):
        L = B / 2 * .95; x = np.arange(int(L * SR)) / SR
        sig = np.tanh(2.2 * np.sin(2 * np.pi * note(c) * x)) * np.minimum(1, x / .01) * np.exp(-x * 4)
        put(mus, at + h, sig, .05 if not cta else .035)
    # плак-арпеджио шестнадцатыми (кроме CTA)
    if not cta:
        cc = CH[int((at - DROP) / BAR + 1) % 4]
        for j in range(4):
            m = cc[(k * 4 + j) % 3] + 24; L = .18; x = np.arange(int(L * SR)) / SR
            put(mus, at + j * B / 4, (np.sin(2 * np.pi * note(m) * x) + .3 * np.sin(6 * np.pi * note(m) * x)) * np.exp(-x * 22), .018)
# удар на дропе
L = 1.6; x = np.arange(int(L * SR)) / SR; put(mus, DROP, np.sin(2 * np.pi * np.cumsum(40 + 70 * np.exp(-x * 12)) / SR) * np.exp(-x * 2.5), .35)
# финальный аккорд на «@Ozodjamol», затем затухание до концовки
for m in CH[0]:
    L = 3.5; x = np.arange(int(L * SR)) / SR
    put(mus, 50.2, (np.sin(2 * np.pi * note(m + 12) * x) + .4 * np.sin(2 * np.pi * note(m + 24) * x)) * np.minimum(1, x / .02) * np.exp(-x * .9), .03)
fo = np.ones(N); i0 = int(53.3 * SR); fo[i0:] = np.linspace(1, 0, N - i0) ** 1.5; mus *= fo

# ---------- звуки действий ----------
sfx = np.zeros(N)
def pop(f=900):
    L = .09; x = np.arange(int(L * SR)) / SR; fr = f * (1 + 1.2 * np.exp(-x * 60))
    return np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-x * 45)
def click():
    L = .04; x = np.arange(int(L * SR)) / SR; return (np.sin(2 * np.pi * 2400 * x) * .5 + bp(rng.standard_normal(len(x)), 2000, 8000)) * np.exp(-x * 160)
def ding(f=1320):
    L = 1.2; x = np.arange(int(L * SR)) / SR
    return (np.sin(2 * np.pi * f * x) + .5 * np.sin(2 * np.pi * f * 1.5 * x) + .2 * np.sin(2 * np.pi * f * 2.0 * x)) * np.minimum(1, x / .004) * np.exp(-x * 4)
def whoosh(L=.6):
    x = np.arange(int(L * SR)) / SR; e = np.sin(np.pi * x / L) ** 2
    return bp(rng.standard_normal(len(x)), 300, 3000) * e
def tick():
    L = .025; x = np.arange(int(L * SR)) / SR; return np.sin(2 * np.pi * 3000 * x) * np.exp(-x * 200)
M = json.load(open('/home/claude/v3b/events.json'))
for at in M['pop']: put(sfx, at, pop(), .16)
for at in M['out']: put(sfx, at, pop(1300), .14)
for at in M['tap']: put(sfx, at, click(), .22)
for at in M['ding']: put(sfx, at, ding(), .07)
for at in M['card']: put(sfx, at, pop(520), .2)
for at in M['whoosh']: put(sfx, at - .25, whoosh(), .10)
for k in range(28): put(sfx, 10.65 + k * .048, tick(), .05)
# ничего своего после 52.0 (перед логотипом)
sfx[int(52.0 * SR):] = 0

def wr(path, sig):
    s = np.clip(sig, -1, 1); w = wave.open(path, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((s * 32767).astype(np.int16).tobytes()); w.close()
wr('/home/claude/v3b/music.wav', mus); wr('/home/claude/v3b/sfx.wav', sfx)
print('ok')
