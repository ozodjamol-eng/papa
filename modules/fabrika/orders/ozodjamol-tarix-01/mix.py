"""Звук «Тарих»: голос + тихий тёмный эмбиент (синтез, свой — без прав) + сдержанные звуки."""
import json, subprocess
import numpy as np
SR = 44100
tl = json.load(open("/home/claude/tarix/timeline.json"))
TOTAL = tl["TOTAL"]; N = int(SR * TOTAL)
def load(p):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, dtype="<f4").reshape(-1, 2).copy()
def put(buf, a, t, g=1.0):
    s = int(t * SR); e = min(len(buf), s + len(a))
    if 0 <= s < len(buf): buf[s:e] += a[:e - s] * g
voice = np.zeros((N, 2)); sfx = np.zeros((N, 2)); mus = np.zeros((N, 2))
for k, t in tl["ST"].items():
    put(voice, load(f"/home/claude/tarix/vo/{k}.mp3"), t)
# --- музыка: Am – F – C – G, медленные пэды + мягкий пульс 90 BPM
def hz(m): return 440 * 2 ** ((m - 69) / 12)
tt = np.arange(N) / SR
BAR = 4 * 60 / 90
prog = [[57, 60, 64], [53, 57, 60], [48, 55, 60], [55, 59, 62]]
for b in range(int(TOTAL / BAR) + 1):
    ch = prog[b % 4]; s = int(b * BAR * SR); L = min(int(BAR * SR * 1.15), N - s)
    if L <= 0: break
    t = np.arange(L) / SR
    env = np.minimum(1, t / 0.8) * np.clip((BAR * 1.15 - t) / 0.8, 0, 1)
    sig = sum(np.sin(2 * np.pi * hz(m) * d * t) for m in ch for d in (0.997, 1.003)) / 6
    sub = np.sin(2 * np.pi * hz(ch[0] - 24) * t) * 0.6
    mus[s:s + L, 0] += (sig * 0.9 + sub) * env * 0.5
    mus[s:s + L, 1] += (sig * 1.1 + sub) * env * 0.5
    for q in range(8):  # тихий пульс восьмыми
        s2 = s + int(q * BAR / 8 * SR); L2 = min(int(0.18 * SR), N - s2)
        if L2 <= 0: continue
        t2 = np.arange(L2) / SR
        p = np.sin(2 * np.pi * hz(ch[q % 3] + 12) * t2) * np.exp(-t2 * 18) * 0.22
        mus[s2:s2 + L2, q % 2] += p
mus /= np.abs(mus).max()
# --- звуки
S = "/home/claude/zanjir/src/"
wh = load(S + "soundreality-whoosh-transition-6-220294.mp3")
pop = load(S + "soundreality-ui-pop-up-clear-391155.mp3")
ding = load(S + "soundreality-ding-sound-effect-613874.mp3")
for k, t in list(tl["ST"].items())[1:]:
    put(sfx, wh, t - 0.3, 0.12)
for t in tl["POPS"]:
    put(sfx, pop, t, 0.12)
for t0, t1 in tl["FLASH"]:  # «удар» на вспышке
    L = int(0.6 * SR); t = np.arange(L) / SR
    f = 45 + 80 * np.exp(-t * 25)
    hit = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6) * 0.5
    put(sfx, np.stack([hit, hit], 1), t0)
put(sfx, ding, tl["ST"]["T09"] + 2.2, 0.18)
put(sfx, ding, tl["ST"]["T11"] + 3.4, 0.18)
env = np.abs(voice).max(1)
env = np.convolve(env, np.ones(int(0.15 * SR)) / int(0.15 * SR), "same")
duck = np.where(env > 0.01, 0.09, 0.2)
duck = np.convolve(duck, np.ones(int(0.25 * SR)) / int(0.25 * SR), "same")
fi = np.clip(tt / 1.0, 0, 1); fo = np.clip((TOTAL - tt) / 1.5, 0, 1)
mix = voice + sfx + mus * (duck * fi * fo)[:, None]
mix /= max(1.0, np.abs(mix).max() / 0.98)
mix.astype("<f4").tofile("/home/claude/tarix/mix.f32")
print("ok")
