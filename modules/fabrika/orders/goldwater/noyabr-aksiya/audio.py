"""Звук ролика: живая речь (0373, 0376) + тихий эмбиент улицы + свой трек (music.py) с приглушением под голос.
Печатает и запускает ffmpeg → /home/claude/v/voice_mix.wav"""
import subprocess, sys
sys.path.insert(0, __file__.rsplit("/",1)[0])
from render import SEG, FPS
S = "/home/claude/v/"
# звук для каждой сцены: (файл, старт) или None; громкость
AUD = {1:("IMG_0373.wav",0.22,1.0), 2:("IMG_0373.wav",29.73,1.0), 3:("IMG_0373.wav",35.78,1.0),
       4:("IMG_0373.wav",41.56,1.0), 5:("IMG_0373.wav",77.63,1.0), 6:("IMG_0376.wav",2.95,1.0),
       0:("IMG_0377.wav",10.6,0.12), 7:("IMG_0378.wav",28.0,0.12), 8:("IMG_0379.wav",0.3,0.12),
       9:("IMG_0379.wav",6.0,0.12), 10:("IMG_0374.wav",3.0,0.12)}
off=0; parts=[]; ins=[]; speech=[]
for i,(src,st,dur,*_) in enumerate(SEG):
    d = round(dur*FPS)/FPS
    if i in AUD:
        f,s,v = AUD[i]; k=len(ins)//2; ins += ["-i", S+f]
        parts.append(f"[{k}:a]atrim={s}:{s+d},asetpts=PTS-STARTPTS,afade=t=in:d=0.04,afade=t=out:st={d-0.06}:d=0.06,"
                     f"volume={v},adelay={int(off*1000)}|{int(off*1000)}[a{k}]")
        if v==1.0: speech.append((off,off+d))
    off += d
TOTAL = off
labels="".join(f"[a{k}]" for k in range(len(parts)))
fc = ";".join(parts)+f";{labels}amix=inputs={len(parts)}:normalize=0,highpass=f=80,acompressor=threshold=-20dB:ratio=3:attack=5:release=120,apad,atrim=0:{TOTAL}[out]"
cmd = ["ffmpeg","-v","error","-y",*ins,"-filter_complex",fc,"-map","[out]","-ar","48000","-ac","1",S+"voice_mix.wav"]
subprocess.run(cmd, check=True)
open(S+"speech_ranges.txt","w").write("\n".join(f"{a:.3f} {b:.3f}" for a,b in speech)+f"\nTOTAL {TOTAL:.3f}\n")
print("TOTAL", TOTAL, "speech", speech)
