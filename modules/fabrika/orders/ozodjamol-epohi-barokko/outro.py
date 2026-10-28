"""Барокко-концовка OZOD JAMOL: живая золотая рама (Flow) + настоящий логотип поверх (код), блик, свечение."""
import numpy as np, subprocess
from PIL import Image, ImageFilter, ImageDraw
from scipy import ndimage

W, H, FPS = 1080, 1920, 24
SS, DUR = 0.5, 4.0
N = int(DUR * FPS)
p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", str(SS), "-i", "/home/claude/bar/src/v_frame.mp4",
                      "-vf", f"scale={W}:{H},fps={FPS}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
frames = []
for i in range(N):
    b = p.stdout.read(W * H * 3)
    if len(b) < W * H * 3: frames.append(frames[-1]); continue
    frames.append(np.frombuffer(b, np.uint8).reshape(H, W, 3))
# найти тёмный овал в каждом кадре
cents = []
for f in frames:
    lum = f.mean(2)
    reg = np.zeros_like(lum, bool); reg[150:1350, 220:860] = True
    m = (lum < 22) & reg
    m = ndimage.binary_opening(m, iterations=3)
    lab, n = ndimage.label(m)
    if n == 0: cents.append(cents[-1] if cents else (540, 600, 300, 400)); continue
    sizes = ndimage.sum(m, lab, range(1, n + 1)); k = int(np.argmax(sizes)) + 1
    ys, xs = np.where(lab == k)
    cents.append(((xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2, xs.max() - xs.min(), ys.max() - ys.min()))
c = np.array(cents, float)
c = ndimage.uniform_filter1d(c, 9, axis=0)
logo = Image.open("/home/claude/bar/src/logo_rgba.png")
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                        "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p",
                        "/home/claude/bar/outro_v.mp4"], stdin=subprocess.PIPE)
def eo(x): x = min(max(x, 0), 1); return 1 - (1 - x) ** 3
for i, f in enumerate(frames):
    t = i / FPS
    img = Image.fromarray(f).convert("RGBA")
    cx, cy, ow, oh = c[i]
    a = eo((t - 0.7) / 0.6)
    if a > 0:
        w = int(ow * 0.86 * (0.9 + 0.1 * a)); h = int(w * logo.height / logo.width)
        L = logo.resize((w, h), Image.LANCZOS)
        al = L.getchannel("A").point(lambda v: int(v * a)); L.putalpha(al)
        glow = Image.new("RGBA", (w + 160, h + 160), (0, 0, 0, 0))
        g = Image.new("RGBA", L.size, (255, 190, 90, 0)); g.putalpha(al.point(lambda v: int(v * 0.8)))
        glow.paste(g, (80, 80), g); glow = glow.filter(ImageFilter.GaussianBlur(28))
        x, y = int(cx - w / 2), int(cy - h / 2)
        img.alpha_composite(glow, (x - 80, y - 80))
        img.alpha_composite(L, (x, y))
        # блик по логотипу
        s = (t - 1.9) / 0.8
        if 0 < s < 1:
            band = Image.new("L", (w, h), 0); bd = ImageDraw.Draw(band)
            bx = -w * 0.4 + s * w * 1.8
            bd.polygon([(bx, 0), (bx + w * 0.18, 0), (bx - w * 0.12, h), (bx - w * 0.30, h)], fill=200)
            band = band.filter(ImageFilter.GaussianBlur(10))
            m2 = Image.fromarray((np.array(band, float) * np.array(al, float) / 255).astype("uint8"))
            wh = Image.new("RGBA", (w, h), (255, 245, 220, 0)); wh.putalpha(m2)
            img.alpha_composite(wh, (x, y))
    if t > DUR - 0.5:
        k = (t - (DUR - 0.5)) / 0.5
        img = Image.blend(img.convert("RGB"), Image.new("RGB", (W, H)), k).convert("RGBA")
    enc.stdin.write(img.convert("RGB").tobytes())
enc.stdin.close(); enc.wait()
# звук: фирменный Greanpatch на появлении логотипа + свечное «тишина»
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", "/home/claude/bar/outro_v.mp4", "-i",
                "/home/claude/bar/src/greanpatch.mp3", "-filter_complex",
                "[1:a]adelay=700|700,apad,atrim=0:4,loudnorm=I=-16[a]", "-map", "0:v", "-map", "[a]", "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "/home/claude/bar/outro.mp4"], check=True)
print("outro ok", c[0], c[-1])
