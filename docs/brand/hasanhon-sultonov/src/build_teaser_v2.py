"""Тизер Hasanhon Sultonov v2 «с душой»: сквозной тамбур (его игра), замедления, тишина → взрыв голоса."""
import subprocess, os, sys
U = "/mnt/user-data/uploads"; A = "/home/claude/hs_arch"
OUT = os.path.join(A, "t2"); os.makedirs(OUT, exist_ok=True)
F_BLK = os.path.expanduser("~/.fonts/HSMontBlack.ttf")
RED = "0xD7141F"
CAP8 = sys.argv[1] if len(sys.argv) > 1 else "MUSIQA — MENING HAYOTIM"
S = {"big": f"{A}/big.mp4", "a1": f"{A}/a1.mp4", "a2": f"{A}/a2.mp4", "a3": f"{A}/a3.mp4", "a5": f"{A}/a5.mp4",
     "a6": f"{A}/a6.mp4", "a7": f"{A}/a7.mp4", "b1": f"{A}/b1.mp4", "car": f"{A}/s1.mp4",
     "g2504": f"{U}/56ec1711-IMG_2504.MOV", "selfie": f"{U}/c66c4f0b-IMG_2509.MOV",
     "outro": "/home/claude/hasanhon/HASANHON_KONCOVKA_BLACK_v2.mp4", "ustoz": f"{U}/5cd57978-image.jpg"}
ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", "-an"]

def esc(t): return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’")

def cap(text, t0, size=78, y="h*0.80", color="white", t1=None, fd=0.5):
    a = f"if(lt(t,{t0}),0,min(1,(t-{t0})/{fd}))"
    if t1 is not None:
        a = f"if(lt(t,{t0}),0,if(gt(t,{t1}),max(0,1-(t-{t1})/{fd}),min(1,(t-{t0})/{fd})))"
    return (f"drawtext=fontfile={F_BLK}:text='{esc(text)}':fontsize={size}:fontcolor={color}:"
            f"x=(w-text_w)/2:y={y}:alpha='{a}':shadowcolor=black@0.6:shadowx=0:shadowy=4")

def band(crop=None):
    c = f"crop={crop}," if crop else ""
    return (f"{c}split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
            f"boxblur=40:2,eq=brightness=-0.12[bg];[b]scale=1080:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2")

def full(crop=None):
    c = f"crop={crop}," if crop else ""
    return f"{c}scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"

GRAIN = "noise=alls=14:allf=t,vignette=PI/5"

def vseg(name, src, ss, dur, layout, speed=1.0, caps=(), extra="", fin=0.0, fout=0.0):
    """видео без звука; speed<1 = замедление (источник берётся dur*speed)"""
    out = f"{OUT}/{name}.mp4"
    sdur = dur * speed
    pre = f"setpts=PTS/{speed}," if speed != 1.0 else ""
    if speed != 1.0:  # плавное замедление: дорисовка кадров
        pre += "minterpolate=fps=30:mi_mode=blend,"
    v = f"[0:v]{pre}{layout},fps=30,setsar=1"
    if extra: v += "," + extra
    for c in caps: v += "," + c
    if fin: v += f",fade=t=in:st=0:d={fin}"
    if fout: v += f",fade=t=out:st={dur-fout}:d={fout}"
    v += ",format=yuv420p,trim=duration=" + str(dur)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(ss), "-t", str(sdur + 0.2), "-i", S[src],
                    "-filter_complex", v + "[v]", "-map", "[v]", "-t", str(dur), "-r", "30", *ENC, out], check=True)
    return out, dur

def vstill(name, dur, caps=()):
    out = f"{OUT}/{name}.mp4"; n = int(dur * 30)
    v = (f"[0:v]scale=2160:-2,zoompan=z='1.0+0.10*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s=1080x1350:fps=30,"
         f"pad=1080:1920:0:285:color=0x0B0B0B,setsar=1")
    for c in caps: v += "," + c
    v += f",fade=t=in:st=0:d=0.8,fade=t=out:st={dur-0.8}:d=0.8,format=yuv420p"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-t", str(dur), "-i", S["ustoz"],
                    "-filter_complex", v + "[v]", "-map", "[v]", "-t", str(dur), "-r", "30", *ENC, out], check=True)
    return out, dur

seq = []   # (файл, длительность)
seq.append(vseg("01_dala", "a5", 3.0, 5.0, full(), 0.5, [cap("Hasanhon Sultonov", 1.4, 84)], fin=1.2))
seq.append(vseg("02a_2008", "a1", 8.5, 3.5, band("720:396:0:442"), 0.5, [cap("2008", 0.4, 120)], GRAIN))
seq.append(vseg("02b_2016", "a2", 4.5, 3.5, band("720:450:0:385"), 0.5, [cap("2016", 0.4, 120)], GRAIN, fout=0.4))
seq.append(vstill("03_ustoz", 5.0, [cap("Ilk ustozim — Oybek Obidov", 0.9, 62, y="h*0.86")]))
seq.append(vseg("04_toy", "a3", 40.5, 5.0, full(), 0.5, [cap("20 yil sahnada", 1.0, 80)], fin=0.4, fout=0.5))
seq.append(vseg("05_gdansk", "g2504", 0.5, 4.0, full(), 0.5, [cap("Polsha.", 1.2, 84)], fin=0.6))
seq.append(vseg("06_car", "car", 34.0, 6.0, band(), 1.0, [cap("Lekin musiqa — yuragimda.", 0.8, 62, y="h*0.84")]))
seq.append(vseg("07_selfie", "selfie", 9.4, 3.8, full(), 1.0))
seq.append(vseg("08a_zarb", "a7", 28.0, 2.5, full(), 1.0))
w1, w2 = CAP8.split(" — ", 1) if " — " in CAP8 else (CAP8, "")
caps8 = [cap(w1 + (" —" if w2 else ""), 1.6, 92, fd=0.3)] + ([cap(w2, 3.0, 92, y="h*0.80+110", color=RED, fd=0.3)] if w2 else [])
seq.append(vseg("08b_avj", "big", 235.0, 6.0, band("900:720:190:0"), 1.0, caps8, fout=0.5))
o9 = f"{OUT}/09_outro.mp4"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", S["outro"], "-vf", "fps=30,setsar=1,format=yuv420p", *ENC, o9], check=True)
d9 = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", o9]))
seq.append((o9, d9))

# старты сегментов
starts, t = {}, 0.0
for f, d in seq:
    starts[os.path.basename(f)[:-4]] = t; t += d
TOTAL = t
lst = f"{OUT}/list.txt"; open(lst, "w").write("".join(f"file '{f}'\n" for f, _ in seq))
vid = f"{OUT}/video.mp4"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", vid], check=True)

# ЗВУК: тамбур сквозной до машины + живые куски
T_end = starts["06_car"] + 0.3
def piece(src, ss, dur, at, vol, fin=0.05, fout=0.3):
    return (src, ss, dur, at, vol, fin, fout)
pieces = [
    piece("a6", 8.0, T_end, 0.0, 0.85, fin=2.0, fout=3.0),                       # тамбур — его игра
    piece("car", 34.0, 6.0, starts["06_car"], 1.0, fin=0.4, fout=0.3),           # поёт в машине
    piece("selfie", 9.4, 3.8, starts["07_selfie"], 1.0, fin=0.1, fout=0.2),      # «biz bilan birga bo'ling»
    piece("a7", 28.0, 2.5, starts["08a_zarb"], 0.9, fin=0.8, fout=0.05),         # нарастает дробь
    piece("big", 235.0, 6.0 + d9 * 0.6, starts["08b_avj"], 1.0, fin=0.02, fout=1.6),  # авж «Мажнунтол»
]
inp, flt, labels = [], [], []
for i, (src, ss, dur, at, vol, fin, fout) in enumerate(pieces):
    inp += ["-ss", str(ss), "-t", str(dur), "-i", S[src]]
    ms = int(at * 1000)
    flt.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,loudnorm=I=-16:TP=-1.5:LRA=11,volume={vol},"
               f"afade=t=in:st=0:d={fin},afade=t=out:st={max(0,dur-fout)}:d={fout},adelay={ms}|{ms},apad[s{i}]")
    labels.append(f"[s{i}]")
flt.append(f"{''.join(labels)}amix=inputs={len(pieces)}:normalize=0,atrim=0:{TOTAL},alimiter=limit=0.95[a]")
aud = f"{OUT}/audio.m4a"
subprocess.run(["ffmpeg", "-v", "error", "-y", *inp, "-filter_complex", ";".join(flt), "-map", "[a]",
                "-c:a", "aac", "-b:a", "192k", aud], check=True)
final = f"{A}/HASANHON_TIZER_v2.mp4"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", vid, "-i", aud, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                "-c:a", "copy", "-shortest", "-movflags", "+faststart", final], check=True)
print("OK", final, round(TOTAL, 2), {k: round(v, 1) for k, v in starts.items()})
