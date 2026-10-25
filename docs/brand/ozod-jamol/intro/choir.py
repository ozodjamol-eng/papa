import numpy as np, wave
SR=48000;DUR=8.0;N=int(SR*DUR);t=np.arange(N)/SR;rng=np.random.default_rng(11)
form=[(450,1.0,80),(800,0.6,90),(2830,0.12,120)]   # vowel "o"
def voice(f0,det,vib_ph):
    f=f0*(1+det)*(1+0.006*np.sin(2*np.pi*5.2*t+vib_ph))*(1+0.002*rng.normal(0,1,N).cumsum()/np.sqrt(N))
    ph=2*np.pi*np.cumsum(f)/SR;out=np.zeros(N)
    for h in range(1,int(4000/f0)):
        fh=h*f0;a=sum(g*np.exp(-((fh-c)/bw)**2) for c,g,bw in form)+0.15/h
        out+=a*np.sin(h*ph)
    return out
ch=np.zeros((N,2))
for i,(f0,pan) in enumerate([(55,0),(55,0.3),(55,-0.3),(82.41,0.4),(82.41,-0.4),(110,0.2),(110,-0.2)]):
    v=voice(f0,rng.uniform(-0.004,0.004),rng.uniform(0,6.28))
    ch[:,0]+=v*(1-max(0,pan));ch[:,1]+=v*(1+min(0,pan))
env=np.clip((t-0.9)/1.1,0,1)**2*0.8+0.4*np.exp(-np.maximum(0,t-2.0)*1.5)*(t>=2.0)+0.35*np.exp(-np.maximum(0,t-4.5)*1.2)*(t>=4.5)
env*=np.clip((8.0-t)/1.0,0,1)
ch*=env[:,None]
ir_len=int(2.5*SR);ir=rng.normal(0,1,ir_len)*np.exp(-np.arange(ir_len)/SR*2.0);ir/=np.abs(ir).sum()*0.04
for c in range(2): ch[:,c]=ch[:,c]*0.6+np.convolve(ch[:,c],ir)[:N]*0.5
ch/=np.abs(ch).max()*1.05
w=wave.open('choir.wav','wb');w.setnchannels(2);w.setsampwidth(2);w.setframerate(SR);w.writeframes((ch*32767).astype(np.int16).tobytes());w.close();print('ok')
