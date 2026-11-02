"""Свой трек для «Живого постера» GOLD WATER: 120 BPM, светлый, вода (пэд + плак-арпеджио + бит), удары на слэмах. Без чужой музыки."""
import numpy as np, wave, sys
out = sys.argv[1]; hits = [float(v) for v in sys.argv[2].split(',')] if len(sys.argv) > 2 else []
D = 11.0; SR = 48000; BPM = 120; beat = 60 / BPM; N = int(SR * D); t = np.arange(N) / SR
L = np.zeros(N); R = np.zeros(N)
nf = lambda m: 440 * 2 ** ((m - 69) / 12)
def add(sig, s, pan=0.0, g=1.0):
    s = int(s * SR); e = min(N, s + len(sig)); sig = sig[:e - s] * g
    L[s:e] += sig * (1 - pan) ; R[s:e] += sig * (1 + pan)
chords = [[53, 57, 60, 64], [55, 59, 62, 67], [57, 60, 64, 69], [60, 64, 67, 72]]  # Fmaj7 G Am C — подъём
bar = beat * 4
# пэд (с 0.2 с)
for i in range(int(D / bar) + 1):
    c = chords[i % 4]; s = i * bar; tt = np.arange(int(bar * SR)) / SR
    env = np.minimum(1, tt / .35) * np.minimum(1, (bar - tt) / .35)
    for m in c:
        for det, pan in ((-.1, -.5), (.1, .5)):
            add(.035 * env * (np.sin(2 * np.pi * nf(m) * (1 + det / 100) * tt) + .25 * np.sin(4 * np.pi * nf(m) * tt)), s, pan)
    # бас
    tb = np.arange(int(bar * SR)) / SR
    for j in range(4):
        tl = tb[:int(beat * SR)]
        add(.16 * np.exp(-tl * 3) * np.sin(2 * np.pi * nf(c[0] - 24) * tl), s + j * beat + beat / 2 * 0)
# плак-арпеджио «капли» шестнадцатыми с 1.5 с
for k in range(int((D - 1.5) / (beat / 2))):
    s = 1.5 + k * beat / 2; bi = int(s / bar) % 4; c = chords[bi]
    m = c[[0, 2, 1, 3, 2, 1, 3, 2][k % 8]] + 12; tl = np.arange(int(.45 * SR)) / SR
    sig = np.exp(-tl * 9) * (np.sin(2 * np.pi * nf(m) * tl) + .35 * np.sin(2 * np.pi * nf(m) * 2.01 * tl) * np.exp(-tl * 20))
    add(.07 * sig, s, pan=.4 if k % 2 else -.4)
# бит с 1.5 с: кик каждая доля, хэт на офбит, клэп на 2 и 4
rng = np.random.default_rng(7)
for b in range(int((D - 1.5) / beat)):
    s = 1.5 + b * beat; tl = np.arange(int(.3 * SR)) / SR
    f = 50 + 90 * np.exp(-tl * 35); add(.34 * np.exp(-tl * 10) * np.sin(2 * np.pi * np.cumsum(f) / SR), s)
    th = np.arange(int(.06 * SR)) / SR; n = rng.standard_normal(len(th))
    hp = np.diff(n, prepend=0); add(.035 * np.exp(-th * 60) * hp, s + beat / 2, pan=.3)
    if b % 2 == 1:
        tc = np.arange(int(.2 * SR)) / SR; n2 = rng.standard_normal(len(tc)); add(.06 * np.exp(-tc * 25) * n2, s)
# удары (низкий бум) на слэмах/приземлениях
for h in hits:
    tl = np.arange(int(.9 * SR)) / SR; f = 38 + 70 * np.exp(-tl * 18)
    add(.4 * np.exp(-tl * 4.5) * np.sin(2 * np.pi * np.cumsum(f) / SR), h)
fade = np.minimum(1, t / .3) * np.minimum(1, (D - t) / .6)
L *= fade; R *= fade; m = max(abs(L).max(), abs(R).max()) * 1.05; L /= m; R /= m
st = (np.stack([L, R], 1) * 32767).astype(np.int16)
w = wave.open(out, 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(st.tobytes()); w.close()
