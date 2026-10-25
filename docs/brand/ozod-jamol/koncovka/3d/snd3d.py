import numpy as np,wave,sys
V=sys.argv[1];SR=48000;D=3.4;N=int(SR*D);t=np.arange(N)/SR;rng=np.random.default_rng(int(V)+7);mix=np.zeros(N)
def lp(x,fc):
    fc=np.broadcast_to(fc,x.shape).astype(float);y=np.empty_like(x);a=np.exp(-2*np.pi*fc/SR);s=0.0
    for i in range(len(x)): s=(1-a[i])*x[i]+a[i]*s;y[i]=s
    return y
def env(t0,dec): return np.where(t>=t0,np.exp(-(t-t0).clip(0)*dec),0)
def boom(t0,f0,f1,dec,g):
    ti=t-t0;m=ti>=0;fr=np.where(m,np.maximum(f1,f0*np.exp(-ti.clip(0)*4)),0);return np.where(m,np.sin(2*np.pi*np.cumsum(fr)/SR)*np.exp(-ti.clip(0)*dec),0)*g
def whoosh(tc,w,f0,f1,g):
    e=np.exp(-((t-tc)/w)**2);p=np.clip((t-tc+2*w)/(4*w),0,1);f=f0+(f1-f0)*p;h=lp(rng.normal(0,1,N)*e,f*1.6);return (h-lp(h,f/1.6))*g
IMP={'1':50,'2':52,'3':56}[V]/30
if V=='1':
    mix+=whoosh(0.9,0.35,200,2500,0.9);mix+=whoosh(1.2,0.25,300,3500,0.8);mix+=whoosh(IMP-0.08,0.07,1500,8000,1.1)
elif V=='2':
    buzz=np.sign(np.sin(2*np.pi*110*t))*0.3+lp(rng.normal(0,1,N),7000)*0.6;mix+=buzz*np.clip(t/0.1,0,1)*np.clip((1.1-t)/0.2,0,1)*0.35
    rum=lp(rng.normal(0,1,N),180)*np.clip((t-0.7)/0.9,0,1)*(t<IMP)*4;mix+=rum
    mix+=whoosh(IMP-0.25,0.2,150,1800,0.6)
else:
    for i in range(160):
        t0=rng.uniform(0.3,IMP-0.02);mix+=lp(rng.normal(0,1,N),rng.uniform(3000,9000))*env(t0,160)*(t>=t0)*rng.uniform(0.15,0.45)
    sw=np.clip((t-0.2)/(IMP-0.2),0,1);h=lp(rng.normal(0,1,N),300+5000*sw**2);mix+=(h-lp(h,(300+5000*sw**2)/1.6))*sw**2*(t<IMP)*0.9
mix+=boom(IMP,70,26,1.5,1.3);mix+=lp(rng.normal(0,1,N),5000)*env(IMP,24)*0.6
mix+=sum(np.sin(2*np.pi*f*t) for f in (1760,2637,3520))*env(IMP+0.3,2)*0.03
ir_len=int(1.5*SR);ir=rng.normal(0,1,ir_len)*np.exp(-np.arange(ir_len)/SR*3);ir/=np.abs(ir).sum()*0.05
mix=mix+np.convolve(mix,ir)[:N]*0.25;mix*=np.clip((D-t)/0.35,0,1);mix/=np.abs(mix).max()*1.1
st=np.stack([mix,mix],1);w=wave.open(f's{V}.wav','wb');w.setnchannels(2);w.setsampwidth(2);w.setframerate(SR);w.writeframes((st*32767).astype(np.int16).tobytes());w.close()
