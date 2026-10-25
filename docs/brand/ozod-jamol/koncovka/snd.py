import numpy as np,wave,sys
V=sys.argv[1];SR=48000;N=int(SR*3.0);t=np.arange(N)/SR;rng=np.random.default_rng(3);mix=np.zeros(N)
def lp(x,fc):
    fc=np.broadcast_to(fc,x.shape).astype(float);y=np.empty_like(x);a=np.exp(-2*np.pi*fc/SR);s=0.0
    for i in range(len(x)): s=(1-a[i])*x[i]+a[i]*s;y[i]=s
    return y
def boom(t0,f0,f1,dec,g):
    ti=t-t0;m=ti>=0;fr=np.where(m,np.maximum(f1,f0*np.exp(-ti.clip(0)*4)),0);return np.where(m,np.sin(2*np.pi*np.cumsum(fr)/SR)*np.exp(-ti.clip(0)*dec),0)*g
if V=='A':
    e=np.exp(-((t-0.25)/0.12)**2);f=400+4000*np.clip(t/0.4,0,1);n=rng.normal(0,1,N)*e;h=lp(n,f*1.6);mix+=(h-lp(h,f/1.6))*0.8
    mix+=boom(0.9,65,28,2.0,1.0);mix+=lp(rng.normal(0,1,N),4500)*np.where(t>=0.9,np.exp(-(t-0.9).clip(0)*28),0)*(t>=0.9)*0.5
    mix+=sum(np.sin(2*np.pi*f*t) for f in (1760,2637,3520))*np.where(t>=1.25,np.exp(-(t-1.25).clip(0)*2),0)*(t>=1.25)*0.03
else:
    for c0 in (0.35,0.5,0.62): mix+=lp(rng.normal(0,1,N),6000)*np.where(t>=c0,np.exp(-(t-c0).clip(0)*90),0)*(t>=c0)*0.5
    hum=(np.sin(2*np.pi*100*t)+0.5*np.sin(2*np.pi*200*t))*np.clip((t-0.62)/0.2,0,1)*0.04;mix+=hum
    mix+=boom(0.62,55,30,1.4,0.8)
    mix+=sum(np.sin(2*np.pi*f*t) for f in (1318,1976,2637))*np.where(t>=1.5,np.exp(-(t-1.5).clip(0)*2),0)*(t>=1.5)*0.025
ir_len=int(1.5*SR);ir=rng.normal(0,1,ir_len)*np.exp(-np.arange(ir_len)/SR*3);ir/=np.abs(ir).sum()*0.05
mix=mix+np.convolve(mix,ir)[:N]*0.25;mix*=np.clip((3.0-t)/0.4,0,1);mix/=np.abs(mix).max()*1.1
st=np.stack([mix,mix],1);w=wave.open(f's{V}.wav','wb');w.setnchannels(2);w.setsampwidth(2);w.setframerate(SR);w.writeframes((st*32767).astype(np.int16).tobytes());w.close()
