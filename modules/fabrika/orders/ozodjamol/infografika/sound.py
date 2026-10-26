"""Музыка для белой части (0–21.5 с): чистый пульс 120 bpm, щелчки на выносках, свисты на сменах, райзер в интро."""
import wave

import numpy as np

SR = 48000
DUR = 22.0
N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(7)
mix = np.zeros((N, 2))


def lp(x, fc):
    # быстрый однополюсный фильтр через свёртку с экспонентой (фиксированная частота)
    a = np.exp(-2 * np.pi * fc / SR)
    n = int(SR * 0.02)
    k = (1 - a) * a ** np.arange(n)
    return np.convolve(x, k)[:len(x)]


def hp(x, fc):
    return x - lp(x, fc)


def add(sig, g=1.0, pan=0.0, at=0.0):
    i = int(at * SR)
    sig = sig[:max(0, N - i)]
    mix[i:i + len(sig), 0] += sig * g * (1 - max(0, pan))
    mix[i:i + len(sig), 1] += sig * g * (1 + min(0, pan))


def env_exp(n, dec):
    return np.exp(-np.arange(n) / SR * dec)


def kick(at, g=0.55):
    n = int(SR * 0.45)
    tt = np.arange(n) / SR
    f = 48 + 110 * np.exp(-tt * 38)
    add(np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(n, 9), g, at=at)


def hat(at, g=0.06, dec=70):
    n = int(SR * 0.12)
    add(hp(rng.normal(0, 1, n), 6000) * env_exp(n, dec), g, at=at, pan=0.2)


def pop(at, g=0.35, f0=1400):
    n = int(SR * 0.09)
    tt = np.arange(n) / SR
    add(np.sin(2 * np.pi * (f0 * (1 + 0.6 * np.exp(-tt * 60))) * tt) * env_exp(n, 45), g, at=at)


def tick(at, g=0.12):
    n = int(SR * 0.03)
    add(hp(rng.normal(0, 1, n), 3000) * env_exp(n, 200), g, at=at)


def whoosh(at, dur=0.45, g=0.25, pan=0.0):
    n = int(SR * dur)
    x = rng.normal(0, 1, n)
    e = np.sin(np.linspace(0, np.pi, n)) ** 2
    lo = lp(x, 900)
    hi = hp(x, 2500)
    m = np.linspace(0, 1, n)
    add((lo * (1 - m) + hi * m) * e, g, pan=pan, at=at)


def hit(at, g=0.6):
    kick(at, g)
    n = int(SR * 1.2)
    add(lp(rng.normal(0, 1, n), 1800) * env_exp(n, 6), g * 0.25, at=at)


def bass(at, f, dur, g=0.16):
    n = int(SR * dur)
    tt = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 2 * f * tt)
    e = np.minimum(1, tt / 0.01) * np.exp(-tt * 3)
    add(s * e, g, at=at)


def pad(a, b, g=0.05):
    n = int(SR * (b - a))
    tt = np.arange(n) / SR
    ch = sum(np.sin(2 * np.pi * f * tt + p) for f, p in ((220, 0), (277.2, 1), (329.6, 2), (440, 3)))
    e = np.minimum(1, tt / 0.8) * np.minimum(1, (n / SR - tt) / 0.8)
    add(ch * e * (0.8 + 0.2 * np.sin(2 * np.pi * 0.5 * tt)), g, at=a)


# хук: тихо, акцент на словах
hit(0.15, 0.5)
tick(0.45); tick(0.95); tick(1.45)
whoosh(2.55, 0.5, 0.22)
pad(0.0, 21.0, 0.035)
# пульс с появлением телефона
for b in np.arange(3.0, 18.0, 0.5):
    kick(b, 0.42)
for b in np.arange(3.25, 18.0, 0.5):
    hat(b)
notes = [55.0, 55.0, 65.4, 49.0]
for k, b in enumerate(np.arange(3.0, 18.0, 1.0)):
    bass(b, notes[(k // 2) % 4], 0.9)
hit(3.0, 0.55)
for i in range(5):                                   # точки выносок
    pop(3.9 + 0.5 * i, 0.30, 1300 + 120 * i)
    tick(4.2 + 0.5 * i, 0.08)
for i in range(5):                                   # услуги крупно
    s = 8.0 + 2 * i
    whoosh(s - 0.25, 0.4, 0.22, pan=0.3 if i % 2 else -0.3)
    hit(s, 0.45)
    pop(s + 0.5, 0.25, 1700)
whoosh(17.5, 0.5, 0.25)
# доказательство: два удара карточек, мягче
hit(18.05, 0.5); pop(18.3, 0.25, 1500); pop(18.55, 0.25, 1700)
for b in np.arange(18.5, 20.5, 0.5):
    hat(b, 0.05)
# райзер в чёрное
n = int(SR * 1.6)
sw = np.linspace(0, 1, n)
x = rng.normal(0, 1, n)
add(hp(x, 500) * sw ** 2.5, 0.32, at=19.6)
whoosh(20.85, 0.6, 0.35)
# реверб
ir = rng.normal(0, 1, int(1.2 * SR)) * np.exp(-np.arange(int(1.2 * SR)) / SR * 4)
ir /= np.abs(ir).sum() * 0.06
for ch in range(2):
    mix[:, ch] += np.convolve(mix[:, ch], ir)[:N] * 0.18
fade = np.clip((21.6 - t) / 0.4, 0, 1)
mix *= fade[:, None]
mix /= np.abs(mix).max() * 1.05
w = wave.open("music.wav", "wb")
w.setnchannels(2)
w.setsampwidth(2)
w.setframerate(SR)
w.writeframes((mix * 32767).astype(np.int16).tobytes())
w.close()
print("ok")
