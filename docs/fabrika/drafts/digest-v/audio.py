"""Синтез звука для 3 вариантов «Кечки дайжест» (без чужой музыки — всё своё)."""
import sys, wave
import numpy as np

SR = 48000
DUR = 22.0
N = int(SR * DUR)
rng = np.random.default_rng(7)
tt = np.arange(N) / SR


def env(a, d, n):
    e = np.ones(n)
    a, d = int(a * SR), int(d * SR)
    if a: e[:a] = np.linspace(0, 1, a)
    if d: e[-d:] *= np.linspace(1, 0, d)
    return e


def add(buf, sig, t0, g=1.0):
    i = int(t0 * SR)
    j = min(N, i + len(sig))
    if i < N:
        buf[i:j] += sig[: j - i] * g


def lp(x, k=0.05):  # простой однополюсный ФНЧ
    y = np.empty_like(x); acc = 0.0
    for i, v in enumerate(x):
        acc += k * (v - acc); y[i] = acc
    return y


def kick(f0=130, f1=42, d=0.45):
    n = int(d * SR); t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t * 28)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7)


def noise_burst(d, decay, k):
    n = int(d * SR); t = np.arange(n) / SR
    return lp(rng.standard_normal(n), k) * np.exp(-t * decay)


def whoosh(d=0.7, up=True):
    n = int(d * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n)
    ks = np.linspace(0.02, 0.35, n) if up else np.linspace(0.35, 0.02, n)
    y = np.empty(n); acc = 0.0
    for i in range(n):
        acc += ks[i] * (x[i] - acc); y[i] = acc
    return y * np.sin(np.pi * t / d) ** 2


def tick():
    n = int(0.03 * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * 2400 * t) * np.exp(-t * 180)


def chime(f=880, d=1.8):
    n = int(d * SR); t = np.arange(n) / SR
    return sum(np.sin(2 * np.pi * f * m * t) * a for m, a in ((1, 1), (2.01, .35), (3.02, .15))) * np.exp(-t * 2.2)


def pad(freqs, g=0.06):
    s = sum(np.sin(2 * np.pi * f * tt + i) + 0.3 * np.sin(2 * np.pi * f * 2.003 * tt) for i, f in enumerate(freqs))
    lfo = 0.75 + 0.25 * np.sin(2 * np.pi * 0.15 * tt)
    return s * g * lfo * env(2.0, 1.6, N)


def build(V):
    L = np.zeros(N)
    L += pad([55, 110, 130.8, 164.8] if V != 3 else [41.2, 82.4, 123.5], 0.05 if V != 2 else 0.065)
    add(L, whoosh(2.0), 0.0, 0.25)
    letters = [2.0 + i * 0.12 for i in range(5)]
    if V in (1, 3):
        for h in np.arange(2.0, 19.2, 0.6):  # ритм
            add(L, noise_burst(0.05, 90, 0.6), h + 0.3, 0.06 if V == 1 else 0.09)
            add(L, kick(90, 40, 0.3), h, 0.18 if V == 1 else 0.22)
    if V == 1:
        for h in letters: add(L, kick(160, 50, 0.3), h, 0.35)
        add(L, kick(110, 35, 0.8), 3.0, 0.6)
        for h in (4.5, 5.6): add(L, noise_burst(0.12, 40, 0.3), h, 0.35)
    if V == 2:
        for h in (1.8, 3.0, 4.4, 6.9, 9.8, 12.8, 15.8): add(L, whoosh(1.2), h, 0.18)
        for h in (4.6, 10.4, 13.4, 16.4): add(L, chime(1318.5, 1.4), h, 0.05)
    if V == 3:
        for h in letters: add(L, noise_burst(0.15, 30, 0.5), h, 0.45); add(L, kick(200, 60, 0.2), h, 0.3)
        for h in (3.0, 4.5): add(L, kick(120, 30, 0.9), h, 0.55)
        for h in np.arange(3.0, 3.5, 0.05): add(L, tick(), h, 0.12)
    for a in (7.0, 7.4, 7.8):  # счёт курса
        for h in np.arange(a + 0.1, a + 1.3, 0.07): add(L, tick(), h, 0.07 if V != 2 else 0.035)
    for h in (10, 13, 16):
        add(L, whoosh(0.6), h - 0.3, 0.45 if V != 2 else 0.2)
        if V != 2: add(L, noise_burst(0.1, 50, 0.4), h + 0.3, 0.25)
    add(L, whoosh(1.4, up=False), 19.2, 0.3)
    add(L, kick(100, 30, 1.2), 20.0, 0.45 if V != 2 else 0.2)
    add(L, chime(880, 2.0), 20.1, 0.18)
    L *= env(0.05, 1.2, N)
    L /= max(1e-9, np.abs(L).max()) / 0.85
    st = np.stack([L, np.roll(L, 240)], 1)  # лёгкая ширина
    with wave.open(f"out/a{V}.wav", "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())


for v in map(int, sys.argv[1:] or ["1", "2", "3"]):
    build(v); print("audio", v)
