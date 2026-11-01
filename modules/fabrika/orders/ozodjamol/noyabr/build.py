import subprocess as sp, json
V="/mnt/user-data/uploads/237d8781-2831579476065692085.mp4"
D=0.4
B=[0,4.6,8.6,12.3,16.0,19.6,23.0,26.8,29.6,31.65]
SRC=[(0,3.60),(3.60,7.97),(7.97,11.67),(12.88,15.65),(15.65,18.92),(21.66,25.16),(27.93,30.50),(25.16,27.93),(18.92,20.97)]
n=len(SRC); fc=[]; END=B[-1]
for i,(a,b) in enumerate(SRC):
    L=(B[i+1]-B[i])+(D if i<n-1 else 0); f=L/(b-a)
    interp=",minterpolate=fps=30:mi_mode=blend" if f>1.06 else ""
    fc.append(f"[0:v]trim={a}:{b},setpts=PTS-STARTPTS,setpts={f:.4f}*PTS,fps=30{interp},scale=1080:1920:flags=lanczos,unsharp=5:5:0.4,trim=0:{L:.3f},setpts=PTS-STARTPTS,format=yuv420p[s{i}]")
prev="s0"
for k in range(1,n):
    fc.append(f"[{prev}][s{k}]xfade=transition=fade:duration={D}:offset={B[k]:.3f}[x{k}]"); prev=f"x{k}"
LINES=json.load(open("lines.json"))
for i,(t0,t1) in enumerate(LINES,1):
    fc.append(f"[{i}:v]format=rgba,fade=in:st={t0-0.15:.2f}:d=0.35:alpha=1,fade=out:st={t1+0.35:.2f}:d=0.45:alpha=1[o{i}]")
    fc.append(f"[{prev}][o{i}]overlay=0:1290:shortest=1[v{i}]"); prev=f"v{i}"
cmd=["ffmpeg","-v","error","-y","-i",V]
for i in range(1,9): cmd+=["-loop","1","-t",str(END),"-framerate","30","-i",f"sub/s{i}.png"]
cmd+=["-filter_complex",";".join(fc),"-map",f"[{prev}]","-t",str(END),"-c:v","libx264","-preset","medium","-crf","16","-pix_fmt","yuv420p","video.mp4"]
sp.run(cmd,check=True); print("video ok")
