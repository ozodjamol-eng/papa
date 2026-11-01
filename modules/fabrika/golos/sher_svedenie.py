# Сведение стиха: куплеты с *.align.json (tts timestamps) → паузы ровно по строкам (0,65 / 1,6 с), atempo 0,88, комната, музыка MC60.mp3 −27 LUFS.
# Запуск в папке с S1a.mp3…S4a.mp3 + .align.json + MC60.mp3:  python3 sher_svedenie.py a итог.mp3
import json, subprocess, sys
def sh(c): return subprocess.run(c,shell=True,capture_output=True,text=True)
suf,out=sys.argv[1],sys.argv[2]
sh("ffmpeg -v error -y -f lavfi -i anullsrc=r=44100:cl=stereo -t 0.65 g_line.wav; ffmpeg -v error -y -f lavfi -i anullsrc=r=44100:cl=stereo -t 1.6 g_st.wav; ffmpeg -v error -y -f lavfi -i anullsrc=r=44100:cl=stereo -t 1.8 g_lead.wav")
parts=["g_lead.wav"]
for k in range(1,5):
    f=f"S{k}{suf}"; a=json.load(open(f+".align.json"))
    ch,s,e=a["characters"],a["character_start_times_seconds"],a["character_end_times_seconds"]
    nl=[i for i,c in enumerate(ch) if c=="\n"]
    # граница строки: конец последней буквы до \n и начало первой буквы после
    cuts=[]
    for i in nl:
        j=i-1
        while j>0 and not ch[j].strip(): j-=1
        m=i+1
        while m<len(ch) and not ch[m].strip(): m+=1
        cuts.append((e[j]+s[m])/2)
    first=next(i for i,c in enumerate(ch) if c.strip() and c not in "[]" and i> (ch.index("]") if "]" in ch else -1))
    st=max(0,s[first]-0.05); en=e[len(ch)-1]+0.25
    pts=[st]+cuts+[en]; print(f,[round(x,2) for x in pts])
    sh(f"ffmpeg -v error -y -i {f}.mp3 -ar 44100 -ac 2 {f}w.wav")
    for q,(x,y) in enumerate(zip(pts,pts[1:])):
        sh(f"ffmpeg -v error -y -i {f}w.wav -ss {x} -to {y} -af 'afade=t=in:d=0.02,afade=t=out:st={max(0,y-x-0.05)}:d=0.05,atempo=0.88' {f}_{q}.wav")
        parts += [f"{f}_{q}.wav", "g_line.wav" if q<len(pts)-2 else "g_st.wav"]
open("l.txt","w").write("".join(f"file '{p}'\n" for p in parts))
sh("ffmpeg -v error -y -f concat -safe 0 -i l.txt -c:a pcm_s16le vd.wav")
sh("ffmpeg -v error -y -i vd.wav -filter_complex \"[0:a]asplit[d][w];[w]aecho=0.8:0.7:23|41|67|113|190|310:0.55|0.45|0.38|0.30|0.22|0.15,lowpass=f=5500,highpass=f=180,volume=0.11[r];[d][r]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=7\" -ar 44100 v.wav")
D=float(sh("ffprobe -v error -show_entries format=duration -of csv=p=0 v.wav").stdout); L=min(62,D+5)
sh("ffmpeg -v error -y -i MC60.mp3 -af 'loudnorm=I=-27:TP=-3:LRA=7' -ar 44100 -ac 2 m.wav")
r=sh(f"ffmpeg -v error -y -i m.wav -i v.wav -filter_complex \"[0:a]atrim=0:{L},afade=t=out:st={L-4}:d=4[m];[m][1:a]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.89[o]\" -map \"[o]\" -c:a libmp3lame -b:a 320k {out}")
print("voice",round(D,1),"total",round(L,1),r.stderr)
