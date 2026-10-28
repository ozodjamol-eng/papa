import numpy as np, subprocess, json
SR = 44100
tl = json.load(open("/home/claude/zanjir/timeline.json"))
TOTAL = tl["TOTAL"]
N = int(SR * TOTAL)
def load(p):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, dtype="<f4").reshape(-1, 2).copy()
def put(buf, a, t, g=1.0):
    s = int(t * SR); e = min(len(buf), s + len(a))
    if s < len(buf): buf[s:e] += a[:e - s] * g

voice = np.zeros((N, 2)); sfx = np.zeros((N, 2))
for z, t in tl["V"].items():
    put(voice, load(f"/home/claude/zanjir/voice/{z}.wav"), t, 1.0)
S = "/home/claude/zanjir/src/"
wh = load(S + "soundreality-whoosh-transition-6-220294.mp3")
pop = load(S + "soundreality-ui-pop-up-clear-391155.mp3")
err = load(S + "soundreality-notification-error-427345.mp3")
ding = load(S + "soundreality-ding-sound-effect-613874.mp3")
for name, s0, s1 in tl["SC"][1:]:
    put(sfx, wh, s0 - 0.12, 0.35)
for t in tl["role_t"]:
    put(sfx, pop, t, 0.30)
put(sfx, err, tl["brk"], 0.45)
put(sfx, pop, tl["V"]["Z05"], 0.3); put(sfx, pop, tl["V"]["Z05"] + 3.78, 0.25); put(sfx, pop, tl["V"]["Z05"] + 4.7, 0.25)
put(sfx, ding, tl["tg"], 0.4)

mus = load("/home/claude/zanjir/music.wav")[:N]
mus = np.pad(mus, ((0, N - len(mus)), (0, 0)))
# ducking by voice envelope
env = np.abs(voice).max(1)
win = int(0.15 * SR)
env = np.convolve(env, np.ones(win) / win, "same")
duck = np.where(env > 0.01, 0.28, 0.6)
duck = np.convolve(duck, np.ones(int(0.2 * SR)) / int(0.2 * SR), "same")
mix = voice * 1.0 + sfx + mus[:, :] * duck[:, None] * 0.55
mix /= max(1.0, np.abs(mix).max() / 0.98)
mix.astype("<f4").tofile("/home/claude/zanjir/mix.f32")
print("ok", np.abs(mix).max())
