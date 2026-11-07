"""Тизер Hasanhon Sultonov — DRUMS & SINGER. Черновой монтаж: сегменты → нормализация → склейка."""
import subprocess, os, sys
U = "/mnt/user-data/uploads"
A = "/home/claude/hs_arch"
OUT = os.path.join(A, "teaser"); os.makedirs(OUT, exist_ok=True)
F_BLK = os.path.expanduser("~/.fonts/HSMontBlack.ttf")
F_INT = os.path.expanduser("~/.fonts/HSInterB.ttf")
RED = "0xD7141F"
CAP8 = sys.argv[1] if len(sys.argv) > 1 else "MUSIQA — MENING HAYOTIM"

def src(name):
    return {"big": f"{A}/big.mp4", "a1": f"{A}/a1.mp4", "a2": f"{A}/a2.mp4", "a3": f"{A}/a3.mp4",
            "a4": f"{A}/a4.mp4", "a5": f"{A}/a5.mp4", "a7": f"{A}/a7.mp4", "b1": f"{A}/b1.mp4",
            "car": f"{A}/s1.mp4", "g2504": f"{U}/56ec1711-IMG_2504.MOV", "selfie": f"{U}/c66c4f0b-IMG_2509.MOV",
            "outro": "/home/claude/hasanhon/HASANHON_KONCOVKA_BLACK_v2.mp4"}[name]

def esc(t):
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’")

def cap(text, t0, size=78, y="h*0.80", font=F_BLK, color="white", t1=None):
    a = f"if(lt(t,{t0}),0,min(1,(t-{t0})/0.25))"
    if t1 is not None:
        a = f"if(lt(t,{t0}),0,if(gt(t,{t1}),max(0,1-(t-{t1})/0.2),min(1,(t-{t0})/0.25)))"
    return (f"drawtext=fontfile={font}:text='{esc(text)}':fontsize={size}:fontcolor={color}:"
            f"x=(w-text_w)/2:y={y}:alpha='{a}':shadowcolor=black@0.6:shadowx=0:shadowy=4")

def band(crop=None):
    """контент по ширине 1080 поверх размытого себя же (для горизонтальных/вставок)"""
    c = f"crop={crop}," if crop else ""
    return (f"[0:v]{c}split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
            f"boxblur=40:2,eq=brightness=-0.12[bg];[b]scale=1080:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2")

def full(crop=None):
    c = f"crop={crop}," if crop else ""
    return f"[0:v]{c}scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"

def seg(name, source, ss, dur, vf, caps=(), audio=None, aud_ss=None, vol=1.0, fade_in=0.0, fade_out=0.0):
    out = f"{OUT}/{name}.mp4"
    inputs = ["-ss", str(ss), "-t", str(dur), "-i", src(source)]
    if audio:
        inputs += ["-ss", str(aud_ss), "-t", str(dur), "-i", src(audio)]
    v = vf + ",fps=30,setsar=1,format=yuv420p"
    for c in caps:
        v += "," + c
    if fade_in: v += f",fade=t=in:st=0:d={fade_in}"
    if fade_out: v += f",fade=t=out:st={dur-fade_out}:d={fade_out}"
    ai = "1:a" if audio else "0:a"
    af = (f"[{ai}]aresample=48000,aformat=channel_layouts=stereo,loudnorm=I=-15:TP=-1.5:LRA=11,volume={vol},"
          f"apad,atrim=0:{dur}")
    if fade_in: af += f",afade=t=in:st=0:d={fade_in}"
    if fade_out: af += f",afade=t=out:st={dur-fade_out}:d={fade_out}"
    fc = f"{v}[v];{af}[a]"
    cmd = ["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
           "-t", str(dur), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac", "-b:a", "192k", out]
    subprocess.run(cmd, check=True)
    return out

def still(name, img, dur, caps=(), audio=None, aud_ss=0, vol=0.5):
    out = f"{OUT}/{name}.mp4"
    n = int(dur * 30)
    v = (f"[0:v]scale=2160:-2,zoompan=z='1.0+0.12*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s=1080x1350:fps=30,"
         f"pad=1080:1920:0:285:color=0x0B0B0B,setsar=1,format=yuv420p")
    for c in caps: v += "," + c
    v += f",fade=t=in:st=0:d=0.4,fade=t=out:st={dur-0.4}:d=0.4"
    af = (f"[1:a]aresample=48000,aformat=channel_layouts=stereo,loudnorm=I=-15:TP=-1.5:LRA=11,volume={vol},"
          f"apad,atrim=0:{dur},afade=t=in:st=0:d=0.4,afade=t=out:st={dur-0.5}:d=0.5")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-t", str(dur), "-i", img,
                    "-ss", str(aud_ss), "-t", str(dur), "-i", src(audio),
                    "-filter_complex", f"{v}[v];{af}[a]", "-map", "[v]", "-map", "[a]", "-t", str(dur),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac", "-b:a", "192k", out], check=True)
    return out

def black(name, dur):
    out = f"{OUT}/{name}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0x0B0B0B:s=1080x1920:r=30:d={dur}",
                    "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=stereo", "-t", str(dur),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", out], check=True)
    return out

parts = []
# 1 ГОЛОС — зал, начинает «Мажнунтол»
parts.append(seg("01_ovoz", "big", 3.0, 6.0, band("900:720:190:0"), [cap("Hasanhon Sultonov", 0.8, 84)], fade_in=0.3))
# 2 БАРАБАНЫ
parts.append(seg("02a_2008", "a1", 9.0, 1.7, band("720:396:0:442"), [cap("2008", 0.05, 120)]))
parts.append(seg("02b_2016", "a2", 5.0, 1.7, band("720:450:0:385"), [cap("2016", 0.05, 120)]))
parts.append(seg("02c_dala", "a5", 4.0, 1.9, full(), [cap("DRUMS & SINGER", 0.2, 76, color=RED)]))
# 3 УСТОЗ — фото, под ним тихо его голос из зала
parts.append(still("03_ustoz", "/mnt/user-data/uploads/5cd57978-image.jpg", 4.0,
                   [cap("Ilk ustozim — Oybek Obidov", 0.6, 62, y="h*0.86")], audio="big", aud_ss=9.0, vol=0.45))
# 4 СВАДЬБА — картинка a3, звук барабанов a4 (у a3 чужая песня)
parts.append(seg("04_toy", "a3", 40.0, 4.0, full(), [cap("20 yil sahnada", 0.3, 80)], audio="a4", aud_ss=6.0))
# 5 МАСТЕР — застолье, тамбур, голос
parts.append(seg("05_usta", "b1", 1.0, 4.0, band("720:330:0:475"), [], vol=0.9, fade_out=0.6))
parts.append(black("05b_jimlik", 1.0))
# 6 ПОЛЬША — Гданьск → поёт в машине
parts.append(seg("06a_gdansk", "g2504", 0.5, 2.0, full(), [cap("Polsha.", 0.3, 84)], vol=0.35, fade_in=0.5))
parts.append(seg("06b_car", "car", 34.0, 5.0, band(), [cap("Lekin musiqa — yuragimda.", 0.4, 62, y="h*0.84")]))
# 7 ОБРАЩЕНИЕ — селфи
parts.append(seg("07_selfie", "selfie", 9.4, 3.8, full(), []))
# 8 АВЖ — зал, пик «Мажнунтол»
w1, w2 = CAP8.split(" — ", 1) if " — " in CAP8 else (CAP8, "")
caps8 = [cap(w1 + (" —" if w2 else ""), 1.2, 92)] + ([cap(w2, 2.6, 92, y="h*0.80+110", color=RED)] if w2 else [])
parts.append(seg("08_avj", "big", 235.0, 5.5, band("900:720:190:0"), caps8, fade_out=0.4))
# 9 КОНЦОВКА — без звука (пока)
out9 = f"{OUT}/09_outro.mp4"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src("outro"), "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                "-map", "0:v", "-map", "1:a", "-shortest", "-vf", "fps=30,setsar=1,format=yuv420p",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac", out9], check=True)
parts.append(out9)

lst = f"{OUT}/list.txt"
open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
final = f"{A}/HASANHON_TIZER_v1.mp4"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart", final], check=True)
print("OK", final)
