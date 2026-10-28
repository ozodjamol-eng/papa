import numpy as np, subprocess, json
SR = 44100
tl = json.load(open("/home/claude/bar/timeline.json"))
TOTAL = tl["TOTAL"]; N = int(SR * TOTAL)
def load(p):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, dtype="<f4").reshape(-1, 2).copy()
def put(buf, a, t, g=1.0):
    s = int(t * SR); e = min(len(buf), s + len(a))
    if 0 <= s < len(buf): buf[s:e] += a[:e - s] * g
voice = np.zeros((N, 2)); sfx = np.zeros((N, 2))
for i, (z, t) in enumerate(tl["V"].items(), 1):
    put(voice, load(f"/home/claude/bar/vo/B{i:02d}b.mp3"), t)
S = "/home/claude/zanjir/src/"
wh = load(S + "soundreality-whoosh-transition-6-220294.mp3")
pop = load(S + "soundreality-ui-pop-up-clear-391155.mp3")
err = load(S + "soundreality-notification-error-427345.mp3")
ding = load(S + "soundreality-ding-sound-effect-613874.mp3")
for name, s0, s1 in tl["SC"][1:]:
    put(sfx, wh, s0 - 0.12, 0.18)
for t in tl["ROLE_T"]:
    put(sfx, pop, t, 0.16)
put(sfx, err, tl["BRK"], 0.28)
put(sfx, ding, tl["SEAL"], 0.32)
mus = load("/home/claude/bar/src/spring.wav")[int(0.05 * SR):int(0.05 * SR) + N]
mus = np.pad(mus, ((0, max(0, N - len(mus))), (0, 0)))[:N]
env = np.abs(voice).max(1)
env = np.convolve(env, np.ones(int(0.15 * SR)) / int(0.15 * SR), "same")
duck = np.where(env > 0.01, 0.16, 0.36)
b0 = int(tl["BRK"] * SR); duck[b0:b0 + int(0.9 * SR)] *= 0.25        # тишина после разрыва цепи
duck = np.convolve(duck, np.ones(int(0.25 * SR)) / int(0.25 * SR), "same")
fo = np.clip((TOTAL - np.arange(N) / SR) / 1.4, 0, 1)
mix = voice + sfx + mus * (duck * fo)[:, None] * 0.9
mix /= max(1.0, np.abs(mix).max() / 0.98)
mix.astype("<f4").tofile("/home/claude/bar/mix.f32")
print("ok")
