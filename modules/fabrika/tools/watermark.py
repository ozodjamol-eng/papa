"""Водяной знак @Ozodjamol: полупрозрачный, у края кадра, меняет край каждые ~11 с (трудно вырезать кропом)."""
import subprocess, sys
from PIL import Image, ImageDraw, ImageFont
W, H, FPS = 1080, 1920, 24
src, dst = sys.argv[1], sys.argv[2]
f = ImageFont.truetype("/home/claude/bar/fonts/cormorant-garamond-700.ttf", 44)
def mark(rot):
    tmp = Image.new("RGBA", (420, 70), (0, 0, 0, 0)); d = ImageDraw.Draw(tmp)
    d.text((12, 6), "@Ozodjamol", font=f, fill=(0, 0, 0, 90)); d.text((10, 4), "@Ozodjamol", font=f, fill=(243, 230, 200, 120))
    return tmp.rotate(rot, expand=True) if rot else tmp
M0, M90 = mark(0), mark(90)
SPOTS = [(M0, (W - 330, 40)), (M90, (18, 620)), (M0, (40, 1500)), (M90, (W - 80, 900))]
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src], capture_output=True, text=True).stdout)
N = int(dur * FPS)
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                        "-i", src, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p",
                        "-c:a", "copy", dst], stdin=subprocess.PIPE)
for i in range(N):
    b = dec.stdout.read(W * H * 3)
    if len(b) < W * H * 3: break
    img = Image.frombytes("RGB", (W, H), b).convert("RGBA")
    t = i / FPS; k = int(t // 11) % len(SPOTS); ph = t % 11
    a = min(1, ph / 0.6, (11 - ph) / 0.6)
    m, pos = SPOTS[k]
    mm = m.copy(); mm.putalpha(m.getchannel("A").point(lambda v: int(v * a)))
    img.alpha_composite(mm, pos)
    enc.stdin.write(img.convert("RGB").tobytes())
enc.stdin.close(); enc.wait(); print("wm ok", N)
