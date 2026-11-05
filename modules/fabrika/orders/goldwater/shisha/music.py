"""GOLD WATER «Шиша» — свой саундтрек (стиль Glass Product: минимальная электроника, стеклянные колокольчики, саб, щелчок).
Карта событий совпадает с main.js: склейки 4.35/10.0/13.75/17.0/20.35/24.45, ступени LIT, щелчок 13.68, тишина перед ним."""
import numpy as np, wave, sys
out = sys.argv[1]; D = 29.9; SR = 48000; N = int(SR * D); t = np.arange(N) / SR
L = np.zeros(N); Rr = np.zeros(N); nf = lambda m: 440 * 2 ** ((m - 69) / 12)
rng = np.random.default_rng(5)

def add(sig, s, pan=0., g=1.):
    s = int(s * SR)
    if s >= N or s + len(sig) <= 0: return
    a = max(0, -s); s = max(0, s); e = min(N, s + len(sig) - a); sig = sig[a:a + e - s] * g
    L[s:e] += sig * (1 - pan) * .5 * 2 ** .5; Rr[s:e] += sig * (1 + pan) * .5 * 2 ** .5

def tl(d): return np.arange(int(d * SR)) / SR

def pad(m, s, d, g):   # мягкий пэд: детюн-синусы + гармоники, медленная атака
    x = tl(d); env = np.minimum(1, x / 1.4) * np.minimum(1, (d - x) / 1.2)
    sig = sum((.6 / k) * np.sin(2 * np.pi * nf(m) * k * (1 + dt) * x + k) for k in (1, 2, 3) for dt in (-.0025, .0025))
    add(sig * env, s, 0, g)

def bell(m, s, g=.18, pan=0., dec=2.4):   # FM-колокольчик (стекло)
    x = tl(dec * 1.6); f = nf(m)
    mod = 2.2 * np.exp(-x * 5) * np.sin(2 * np.pi * f * 3.5 * x)
    sig = np.exp(-x * (3 / dec)) * np.sin(2 * np.pi * f * x + mod) + .3 * np.exp(-x * 6) * np.sin(2 * np.pi * f * 2.76 * x)
    add(sig, s, pan, g)

def kick(s, g=.5):
    x = tl(.6); f = 46 + 70 * np.exp(-x * 30)
    sig = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 7); add(np.tanh(sig * 1.4), s, 0, g)

def sub(s, d, m=26, g=.35):
    x = tl(d); add(np.sin(2 * np.pi * nf(m) * x) * np.minimum(1, x / .05) * np.exp(-x * (2.2 / d)), s, 0, g)

def tick(s, g=.05, pan=0.):
    x = tl(.03); n = rng.standard_normal(len(x)); n = np.diff(n, prepend=0); add(n * np.exp(-x * 220), s, pan, g)

def snap(s):   # «щелчок»: кластер кликов + неармонический стеклянный аккорд + саб
    for k, dt in enumerate((0, .004, .011, .019)):
        x = tl(.02); add(rng.standard_normal(len(x)) * np.exp(-x * 400), s + dt, (-1) ** k * .3, .35)
    x = tl(3.5)
    for r, a in ((1, 1), (2.76, .5), (5.4, .25)):
        add(a * np.sin(2 * np.pi * 523.25 * r * x) * np.exp(-x * (1.3 * r)), s, 0, .12)
    kick(s, .7); sub(s, 2.5, 26, .5)

# Гармония (модальный ре-минор): Dm9 – B♭maj7 – Gm9 – Asus
CH = [[38, 50, 53, 57, 64], [34, 50, 53, 57, 62], [31, 50, 53, 58, 62], [33, 52, 55, 57, 64]]
bar = 2.86
for i in range(int(D / bar) + 1):
    c = CH[i % 4]
    for m in c[1:]: pad(m, i * bar - .2, bar + 1.2, .045)
    sub(i * bar, bar + .3, c[0], .1)

# Открытие: стеклянный тон, нарастание (капля в темноте)
bell(81, .15, .16, 0, 3.5); bell(76, 1.9, .1, -.3, 3)
# Склейки — мягкий удар
for s in (4.35, 10.0, 17.0, 24.45): kick(s, .42); bell(74, s, .08, 0, 2)
# Стек: сетка тиков 8-ми + колокольчик на каждой ступени (высота растёт)
LIT = [6.3 + k * .32 for k in range(10)]
for k, s in enumerate(LIT): bell([69, 72, 74, 76, 77, 79, 81, 84, 86, 88][k], s, .13, (-1) ** k * .35, 1.6)
x = 4.35
while x < 13.25: tick(x, .035 if (round((x - 4.35) / .3575) % 2) else .055, ((x * 7) % 2) - 1); x += .3575
# Мягкие арпеджио в макро
for j, m in enumerate([74, 77, 81, 79, 77, 74, 72, 74]): bell(m, 10.2 + j * .38, .07, (-1) ** j * .4, 1.4)
# Тишина перед щелчком (весь хвост обрезаем)
s0, s1 = int(13.3 * SR), int(13.68 * SR)
L[s0:s1] *= np.linspace(1, 0, s1 - s0) ** 3; Rr[s0:s1] *= np.linspace(1, 0, s1 - s0) ** 3
snap(13.68)
# Чистая вода: светлые колокольчики
for j, m in enumerate([81, 86, 88, 86]): bell(m, 14.9 + j * .55, .07, (-1) ** j * .3, 2.2)
# Цена: колокольчик-акцент на «5 000 сўм»
bell(86, 18.95, .14, 0, 2.5); bell(81, 18.95, .08, 0, 2.5)
# Адреса: колокольчик на каждый город
for j, s in enumerate((20.46, 21.26, 21.94, 22.86)): bell([76, 79, 81, 84][j], s, .09, [-.4, .4, -.2, .2][j], 1.8)
# Финал: логотип и слоган
bell(79, 24.5, .12, 0, 3); bell(86, 25.86, .09, 0, 3)

# Реверберация (задержки), лимит, затухание в конце (без своих звуков перед концовкой OZOD JAMOL)
for dl, g in ((.029, .33), (.047, .27), (.083, .2), (.131, .14), (.197, .1)):
    k = int(dl * SR); L[k:] += g * Rr[:-k]; Rr[k:] += g * L[:-k]
fade = np.minimum(1, t / .4) * np.clip((D - .05 - t) / 1.2, 0, 1)
L *= fade; Rr *= fade
m = max(abs(L).max(), abs(Rr).max()) / .89; L = np.tanh(L / m * 1.1) / np.tanh(1.1); Rr = np.tanh(Rr / m * 1.1) / np.tanh(1.1)
st = (np.stack([L, Rr], 1) * 32767 * .95).astype(np.int16)
w = wave.open(out, 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(st.tobytes()); w.close()
print('ok', out)
