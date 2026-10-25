import numpy as np, wave
SR=48000;DUR=20.0;N=int(SR*DUR);t=np.arange(N)/SR;rng=np.random.default_rng(5)
def lp(x,fc):
    fc=np.broadcast_to(fc,x.shape).astype(float);y=np.empty_like(x);a=np.exp(-2*np.pi*fc/SR);s=0.0
    for i in range(len(x)): s=(1-a[i])*x[i]+a[i]*s;y[i]=s
    return y
def bp(x,fc): h=lp(x,fc*1.6);return h-lp(h,fc/1.6)
mix=np.zeros((N,2))
def add(sig,g=1.0,pan=0.0): mix[:,0]+=sig*g*(1-max(0,pan));mix[:,1]+=sig*g*(1+min(0,pan))
def boom(t0,f0=70,f1=30,dec=2.2,g=1.0):
    ti=t-t0;m=ti>=0;fr=np.where(m,np.maximum(f1,f0*np.exp(-ti.clip(0)*4)),0)
    add(np.where(m,np.sin(2*np.pi*np.cumsum(fr)/SR)*np.exp(-ti.clip(0)*dec),0),g)
def crack(t0,g=0.4): add(lp(rng.normal(0,1,N),4500)*np.where(t>=t0,np.exp(-(t-t0).clip(0)*28),0)*(t>=t0),g)
def whoosh(t0,dur=0.5,g=0.4,pan=0):
    e=np.exp(-((t-(t0+dur*0.5))/(dur*0.3))**2);f=300+4000*np.clip((t-t0)/dur,0,1);add(bp(rng.normal(0,1,N),f)*e,g,pan)
# pad (A minor), present all along, lower in S3
pad=(np.sin(2*np.pi*55*t)+0.6*np.sin(2*np.pi*82.41*t+1)+0.35*np.sin(2*np.pi*110*t)+0.25*np.sin(2*np.pi*130.8*t))*(0.8+0.2*np.sin(2*np.pi*0.25*t))
add(pad*np.clip(t/0.8,0,1)*np.clip((20-t)/1.0,0,1),0.08)
# pulse 120bpm from 2.2 to 16.0 (kick + hat)
for b in np.arange(2.2,16.0,0.5):
    boom(b,95,45,9,0.35)
for b in np.arange(2.45,16.0,0.5):
    add(bp(rng.normal(0,1,N),7000)*np.where(t>=b,np.exp(-(t-b).clip(0)*60),0)*(t>=b),0.05)
# riser into S2 and into finale
for a,b in ((0.0,2.2),(14.6,16.2)):
    sw=np.clip((t-a)/(b-a),0,1);add(bp(rng.normal(0,1,N),200+5000*sw**2)*(sw**2)*((t>=a)&(t<b)),0.25)
# scene hits
for s in (2.2,6.2,12.2):
    boom(s,80,32,3.0,0.7);crack(s,0.3);whoosh(s-0.35,0.45,0.35)
for i in range(4):  # services
    ts=6.2+0.25+i*1.3;whoosh(ts-0.1,0.35,0.3,0.4 if i%2 else -0.4);boom(ts+0.25,110,50,8,0.35)
whoosh(14.1,0.4,0.3)
# finale: big impact at 17.2 + choir
boom(17.2,60,28,1.6,1.0);crack(17.2,0.5)
form=[(450,1.0,80),(800,0.6,90),(2830,0.12,120)]
ch=np.zeros(N)
for f0,det in ((55,0),(55,0.003),(82.41,-0.002),(110,0.002)):
    f=f0*(1+det)*(1+0.006*np.sin(2*np.pi*5*t+rng.uniform(0,6)));ph=2*np.pi*np.cumsum(f)/SR
    for h in range(1,int(4000/f0)):
        fh=h*f0;a=sum(g*np.exp(-((fh-c)/bw)**2) for c,g,bw in form)+0.15/h;ch+=a*np.sin(h*ph)
chenv=np.clip((t-15.8)/1.4,0,1)**2*np.clip((20-t)/1.2,0,1)
add(ch/np.abs(ch).max()*chenv,0.35)
sh=sum(np.sin(2*np.pi*f*t+p) for f,p in ((1760,0),(2637,1),(3520,2)))*np.where(t>=18.1,np.exp(-(t-18.1).clip(0)*1.5),0)*(t>=18.1)
add(sh,0.02,0.3);add(sh,0.02,-0.3)
ir_len=int(1.8*SR);ir=rng.normal(0,1,ir_len)*np.exp(-np.arange(ir_len)/SR*2.8);ir/=np.abs(ir).sum()*0.05
for c in range(2): mix[:,c]+=np.convolve(mix[:,c],ir)[:N]*0.22
mix/=np.abs(mix).max()*1.05
w=wave.open('music_ad.wav','wb');w.setnchannels(2);w.setsampwidth(2);w.setframerate(SR);w.writeframes((mix*32767).astype(np.int16).tobytes());w.close();print('ok')
