import numpy as np, sys, json, wave
SR=48000
def whoosh(d=.5,up=True):
    n=int(SR*d);t=np.arange(n)/SR;x=np.random.randn(n)
    # sweep band via simple one-pole lowpass with moving cutoff
    fc=np.linspace(300,6000,n) if up else np.linspace(6000,300,n)
    y=np.zeros(n);a=0
    for i in range(n):
        al=1-np.exp(-2*np.pi*fc[i]/SR);a+=al*(x[i]-a);y[i]=a
    env=np.sin(np.pi*np.clip(t/d,0,1))**1.5
    return y*env*0.6
def pop(f=880,d=.12):
    t=np.arange(int(SR*d))/SR;fr=f*(1+2*np.exp(-t*40));ph=2*np.pi*np.cumsum(fr)/SR
    return np.sin(ph)*np.exp(-t*30)*.5
def ding(f=1320,d=1.2):
    t=np.arange(int(SR*d))/SR
    return (np.sin(2*np.pi*f*t)+.5*np.sin(2*np.pi*f*2.76*t)*np.exp(-t*6)+.3*np.sin(2*np.pi*f*5.4*t)*np.exp(-t*10))*np.exp(-t*3.5)*.35
def click(d=.03):
    t=np.arange(int(SR*d))/SR;return np.random.randn(len(t))*np.exp(-t*300)*.4
def boom(d=.9):
    t=np.arange(int(SR*d))/SR;f=60*np.exp(-t*2)+40;return np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*5)*.8
def tick(d=.05):
    t=np.arange(int(SR*d))/SR;return np.sin(2*np.pi*2200*t)*np.exp(-t*120)*.3
F={'whoosh':whoosh,'whoosh_dn':lambda:whoosh(.45,False),'pop':pop,'pop_hi':lambda:pop(1320),'ding':ding,'click':click,'boom':boom,'tick':tick}
ev=json.loads(sys.argv[1]);dur=float(sys.argv[2]);out=sys.argv[3]
mix=np.zeros(int(SR*dur)+SR)
for name,t0,g in ev:
    s=F[name]()*g;i=int(t0*SR);mix[i:i+len(s)]+=s[:len(mix)-i]
mix=mix[:int(SR*dur)];mix=np.tanh(mix*1.2)*.9
w=wave.open(out,'wb');w.setnchannels(1);w.setsampwidth(2);w.setframerate(SR);w.writeframes((mix*32767).astype(np.int16).tobytes());w.close()
