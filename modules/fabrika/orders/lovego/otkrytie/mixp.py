# протокол Sushi House: голос −15 LUFS + лёгкий отзвук; музыка ~−23, sidechain под голосом; затухание за 0,5 с до концовки
import sys,subprocess,numpy as np,json
vo=json.loads(sys.argv[1]); D=float(sys.argv[2]); ms=float(sys.argv[3]); out=sys.argv[4]
SR=48000; buf=np.zeros(int(D*SR),np.float32)
for n,t in vo:
    a=np.frombuffer(subprocess.run(['ffmpeg','-v','error','-i',f'vo/{n}.mp3','-ac','1','-ar',str(SR),'-f','f32le','-'],capture_output=True).stdout,np.float32)
    i=int(t*SR); assert i+len(a)<=len(buf),(n,'не влезает'); buf[i:i+len(a)]+=a
open('vo_tmp.f32','wb').write(buf.tobytes())
fo=D-0.5-1.2
flt=("[0:a]loudnorm=I=-15:TP=-1.5,aecho=0.8:0.5:40|75:0.12|0.07,asplit=2[vo][sc];"
     f"[1:a]aresample={SR},loudnorm=I=-23:TP=-6,afade=t=in:d=0.3,afade=t=out:st={fo}:d=1.2[mu];"
     "[mu][sc]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[duck];"
     "[vo][duck]amix=inputs=2:normalize=0:duration=first[o]")
subprocess.run(['ffmpeg','-y','-v','error','-f','f32le','-ar',str(SR),'-ac','1','-i','vo_tmp.f32','-ss',str(ms),'-t',str(D),'-i','mus/440.mp3',
  '-filter_complex',flt,'-map','[o]','-ac','2','-ar',str(SR),out],check=True)
