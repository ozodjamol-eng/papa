"""Кадры анимации (Playwright) + звук (numpy) → mp4 1080x1920 30fps."""
import subprocess, sys, threading, http.server, socketserver, functools, wave, os
import numpy as np
from pathlib import Path
D = Path(__file__).parent
DUR, FPS = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0, 30
FR = D / "frames"; FR.mkdir(exist_ok=True)
for f in FR.glob("*.png"): f.unlink()

H = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(D))
srv = socketserver.TCPServer(("127.0.0.1", 0), H); port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1080, "height": 1920})
    pg.on("console", lambda m: print("JS:", m.text))
    pg.goto(f"http://127.0.0.1:{port}/anim.html"); pg.evaluate("window.ready")
    n = int(DUR * FPS)
    for i in range(n):
        pg.evaluate(f"draw({i / FPS})")
        pg.locator("#c").screenshot(path=str(FR / f"f{i:04d}.png"))
    b.close()
srv.shutdown()

# ---- звук: эмбиент-пэд + «вжух» + тики на событиях
sr = 48000; t = np.arange(int(sr * DUR)) / sr; a = np.zeros_like(t)
def env(t0, att, dec):
    e = np.clip((t - t0) / att, 0, 1) * np.exp(-np.clip(t - t0 - att, 0, None) / dec); e[t < t0] = 0; return e
pad_env = np.clip(t / 1.2, 0, 1) * np.clip((DUR - t) / 0.4, 0, 1)
for f, g in ((55, .30), (82.4, .20), (110, .16), (164.8, .08), (220, .05)):
    a += g * np.sin(2 * np.pi * f * t + 0.3 * np.sin(2 * np.pi * 0.21 * t)) * pad_env
rng = np.random.default_rng(1); nz = rng.standard_normal(len(t))
k = np.exp(-np.arange(400) / 60); wh = np.convolve(nz, k / k.sum(), "same")
a += 0.9 * wh * env(0.05, 0.45, 0.25)                      # вход
a += 0.5 * wh * env(0.95, 0.35, 0.3)                       # начало чертежа
for t0, f in ((1.0, 1500), (1.45, 1700), (2.2, 1300), (2.38, 1300), (2.56, 1300), (3.25, 2000), (3.45, 2200), (3.65, 2400)):
    a += 0.22 * np.sin(2 * np.pi * f * t) * env(t0, 0.002, 0.05)
    a += 0.12 * np.sin(2 * np.pi * f / 2 * t) * env(t0, 0.002, 0.09)
sub = 0.5 * np.sin(2 * np.pi * 45 * t) * env(2.4, 0.01, 0.6)  # удар на «АНИҚ ЧИЗМА»
a += sub
a = a / np.max(np.abs(a)) * 0.55
with wave.open(str(D / "snd.wav"), "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((a * 32767).astype(np.int16).tobytes())
out = D / "proba_5s.mp4"
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(FR / "f%04d.png"), "-i", str(D / "snd.wav"),
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                "-shortest", "-movflags", "+faststart", str(out)], check=True)
print("OK", out, os.path.getsize(out) // 1024, "KB")
