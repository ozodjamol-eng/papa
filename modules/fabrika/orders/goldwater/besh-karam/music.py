"""Свой фон-трек 31 с, 100 BPM, мягкий и светлый (вода): пэд + арпеджио + лёгкий бит. Без чужой музыки."""
import numpy as np, wave
SR=44100; D=31.0; BPM=100; beat=60/BPM; N=int(SR*D); t=np.arange(N)/SR
mix=np.zeros(N)
def note(f): return 440*2**((f-69)/12)
chords=[[57,60,64],[53,57,60],[60,64,67],[55,59,62]]  # Am F C G
bar=beat*4
for i in range(int(D/bar)+1):
    c=chords[i%4]; s=int(i*bar*SR); e=min(N,int((i+1)*bar*SR)); tt=np.arange(e-s)/SR
    env=np.minimum(1,tt/0.4)*np.minimum(1,(bar-tt)/0.4)
    for m in c:
        for det in (-0.08,0.08): mix[s:e]+=0.05*env*np.sin(2*np.pi*note(m)*(1+det/100)*tt)
    for j in range(8):  # арпеджио восьмыми
        m=c[j%3]+12+(12 if j in (3,7) else 0); ss=s+int(j*beat/2*SR); L=int(0.5*SR)
        if ss>=N: break
        tl=np.arange(min(L,N-ss))/SR
        mix[ss:ss+len(tl)]+=0.07*np.exp(-tl*7)*(np.sin(2*np.pi*note(m)*tl)+0.3*np.sin(4*np.pi*note(m)*tl))
start=2*bar*0  # бит с начала, мягко
for b in range(int(D/beat)):
    s=int(b*beat*SR); L=int(0.25*SR); tl=np.arange(min(L,N-s))/SR
    f=60+60*np.exp(-tl*30); mix[s:s+len(tl)]+=0.22*np.exp(-tl*14)*np.sin(2*np.pi*np.cumsum(f)/SR)
    if b%2==1:
        n=np.random.default_rng(b).standard_normal(len(tl)); mix[s:s+len(tl)]+=0.03*np.exp(-tl*40)*n
fade=np.minimum(1,t/0.5)*np.minimum(1,(D-t)/1.5); mix*=fade
mix/=np.abs(mix).max()*1.1
st=np.stack([mix,np.roll(mix,200)],1)
with wave.open("/home/claude/gw/music.wav","wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st*32767).astype(np.int16).tobytes())
