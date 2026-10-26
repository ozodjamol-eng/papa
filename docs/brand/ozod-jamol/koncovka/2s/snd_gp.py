# звук концовки на основе «Greanpatch» (Pixabay, SoundReality): дзынь на сборке + вжух на оборот + отзвук на исчезновении
import numpy as np, wave, subprocess
from scipy.signal import butter, sosfilt
SR=48000; D=2.3; N=int(SR*D); t=np.arange(N)/SR; rng=np.random.default_rng(5)
raw=subprocess.run(['ffmpeg','-loglevel','error','-i','/mnt/user-data/uploads/86969d46-soundreality-greanpatch-166007.mp3','-f','f32le','-ac','2','-ar',str(SR),'-'],capture_output=True).stdout
g=np.frombuffer(raw,np.float32).reshape(-1,2).astype(float)
def place(x,t0,gain,rate=1.0):
    if rate!=1.0:
        idx=np.arange(0,len(x)-1,rate);x=np.stack([np.interp(idx,np.arange(len(x)),x[:,c]) for c in (0,1)],1)
    out=np.zeros((N,2));a=int(t0*SR);n=min(len(x),N-a);out[a:a+n]=x[:n]*gain;return out
def bp(x,lo,hi): return sosfilt(butter(2,[lo,hi],'band',fs=SR,output='sos'),x)
def whoosh(t0,t1,gain,lo,hi,pan0=0.5,pan1=0.5):
    n=rng.normal(0,1,N);c=(t0+t1)/2;w=(t1-t0)/2;e=np.exp(-((t-c)/w)**2*2.5);o=np.zeros(N);k=14
    for i in range(k):
        a=t0+(t1-t0)*i/k;b=a+(t1-t0)/k;f=lo*(hi/lo)**(i/k);m=(t>=a)&(t<b+0.01);o+=bp(n,f*0.7,min(f*1.6,20000))*m
    o*=e*gain;p=np.clip((t-t0)/(t1-t0),0,1);pan=pan0+(pan1-pan0)*p
    return np.stack([o*(1-pan)*1.4,o*pan*1.4],1)
mix=np.zeros((N,2))
mix+=whoosh(0.0,0.42,0.35,600,7000)                      # сборка
mix+=place(g,0.38,1.0)                                    # главный «дзынь» — логотип собрался
mix+=whoosh(0.55,1.35,0.22,300,4000,0.2,0.8)              # оборот
mix+=place(g,1.45,0.35,rate=1.122)                    # отзвук на тон выше при исчезновении в точку
fade=np.clip((D-t)/0.3,0,1)[:,None];mix*=fade;mix/=np.abs(mix).max()/0.89
w=wave.open('logo_gp.wav','wb');w.setnchannels(2);w.setsampwidth(2);w.setframerate(SR);w.writeframes((mix*32767).astype(np.int16).tobytes());w.close()
