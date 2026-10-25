import numpy as np, wave, subprocess
SR=48000; DUR=8.0; N=int(SR*DUR); t=np.arange(N)/SR
rng=np.random.default_rng(7)
def env(t0,a,d,length=None):
    e=np.zeros(N);i0=int(t0*SR);ia=int(a*SR)
    if ia>0: e[i0:i0+ia]=np.linspace(0,1,len(e[i0:i0+ia]))
    tt=np.arange(N-i0-ia)/SR;e[i0+ia:]=np.exp(-tt/d);return e
def lp(x,fc):  # one-pole lowpass, fc can be array
    fc=np.broadcast_to(fc,x.shape);y=np.zeros_like(x);a=np.exp(-2*np.pi*fc/SR);s=0.0
    for i in range(len(x)): s=(1-a[i])*x[i]+a[i]*s;y[i]=s
    return y
def bp(x,fc,q=1.0): 
    h=lp(x,fc*1.6);return h-lp(h,fc/1.6)
mix=np.zeros((N,2))
def add(sig,gain=1.0,pan=0.0):
    mix[:,0]+=sig*gain*(1-max(0,pan));mix[:,1]+=sig*gain*(1+min(0,pan))
# 1 drone pad (dark, A minor-ish): 55 + 82.4 + 110.0 with slow beating
pad=(np.sin(2*np.pi*55*t)+0.6*np.sin(2*np.pi*82.41*t+1)+0.35*np.sin(2*np.pi*110.3*t)+0.25*np.sin(2*np.pi*164.8*t))
pad*=0.8+0.2*np.sin(2*np.pi*0.25*t)
padenv=np.clip(t/1.2,0,1)*np.clip((8.0-t)/0.8,0,1)
add(pad*padenv,0.10)
# 2 riser 0.2-2.0 (filtered noise sweeping up)
n=rng.normal(0,1,N);sw=np.clip((t-0.2)/1.8,0,1)
riser=bp(n,200+5000*sw**2)*(sw**2)*(t<2.0)
add(riser,0.35)
# 3 whooshes
for t0,dur,pan in ((0.40,0.7,-0.4),(1.0,0.6,0.3),(1.15,0.6,0.5),(3.1,1.0,0.0),(4.25,0.7,0.2)):
    e=np.exp(-((t-(t0+dur*0.45))/(dur*0.3))**2)
    f=300+3500*np.clip((t-t0)/dur,0,1)
    add(bp(rng.normal(0,1,N),f)*e,0.45,pan)
# 4 impact at 2.0: sub boom + crack + reverb tail
ti=t-2.0;m=ti>=0
boom=np.where(m,np.sin(2*np.pi*(55*ti-12*ti**2).clip(0)*1.0)*np.exp(-ti.clip(0)*2.2),0)
boom=np.where(m,np.sin(2*np.pi*np.cumsum(np.where(m,np.maximum(28,70*np.exp(-ti.clip(0)*4)),0))/SR)*np.exp(-ti.clip(0)*2.0),0)
crack=lp(rng.normal(0,1,N),4000)*np.where(m,np.exp(-ti.clip(0)*25),0)
add(boom,1.0);add(crack,0.5)
# 5 second hit at 4.5 (wordmark) softer + shimmer
tj=t-4.5;m2=tj>=0
boom2=np.where(m2,np.sin(2*np.pi*np.cumsum(np.where(m2,np.maximum(35,80*np.exp(-tj.clip(0)*5)),0))/SR)*np.exp(-tj.clip(0)*2.8),0)
add(boom2,0.6)
sh=sum(np.sin(2*np.pi*f*t+p) for f,p in ((1760,0),(2637,1),(3520,2)))*np.where(m2,np.exp(-tj.clip(0)*1.6),0)*np.clip(tj*20,0,1)
add(sh,0.025,0.3);add(sh,0.025,-0.3)
# 6 glint ticks
for g in (2.15,6.6):
    e=np.where(t>=g,np.exp(-(t-g).clip(0)*9),0)*(t>=g)
    add(np.sin(2*np.pi*4200*t)*e,0.03)
# simple reverb: convolve with decaying noise
ir_len=int(1.8*SR);ir=rng.normal(0,1,ir_len)*np.exp(-np.arange(ir_len)/SR*2.6);ir/=np.abs(ir).sum()*0.05
for c in range(2):
    wet=np.convolve(mix[:,c],ir)[:N]*0.25
    mix[:,c]+=wet
mix/=np.abs(mix).max()*1.05
w=wave.open('music.wav','wb');w.setnchannels(2);w.setsampwidth(2);w.setframerate(SR)
w.writeframes((mix*32767).astype(np.int16).tobytes());w.close();print('ok')
