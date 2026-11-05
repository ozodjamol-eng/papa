import subprocess, json
B = [3.29,4.49,5.68,6.89,8.09,9.28,10.48,11.69,12.88,14.08,15.29,16.50,20.07,21.28,22.49]
# (src_start, src_len_available) по сценам
S = [(0.9,1.43),(15.87,1.16),(3.1,1.47),(22.75,1.7),(4.6,2.1),(12.47,1.16),(13.63,1.1),(7.6,1.43),(9.6,1.7),(18.17,1.13),(21.67,1.06),(19.3,1.13),(14.73,1.14),(20.43,1.24)]
parts=[]
for i,((s,avail),a,b) in enumerate(zip(S,B[:-1],B[1:])):
    dur=b-a; speed=min(1.0,avail/dur)
    srclen=dur*speed
    o=f'seg{i:02d}.mp4'
    vf=f"trim={s}:{s+srclen},setpts=(PTS-STARTPTS)/{speed},fps=60,scale=1080:1920,setsar=1,trim=duration={dur}"
    subprocess.run(['ffmpeg','-v','error','-y','-i','../src/raw.mov','-vf',vf,'-an','-c:v','libx264','-preset','veryfast','-crf','12','-pix_fmt','yuv420p',o],check=True)
    parts.append(o); print(i,a,b,round(speed,3))
open('list.txt','w').write(''.join(f"file '{p}'\n" for p in parts))
subprocess.run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i','list.txt','-c','copy','base.mp4'],check=True)
