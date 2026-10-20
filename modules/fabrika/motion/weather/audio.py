import numpy as np, wave
SR=44100; DUR=15.0; N=int(SR*DUR); t=np.arange(N)/SR
L=np.zeros(N); Rr=np.zeros(N)
rng=np.random.default_rng(1)
def add(sig,start,pan=0.0,gain=1.0):
    i=int(start*SR); j=min(N,i+len(sig)); s=sig[:j-i]*gain
    L[i:j]+=s*np.sqrt((1-pan)/2); Rr[i:j]+=s*np.sqrt((1+pan)/2)
def env(n,a,d):  # attack/decay seconds
    e=np.ones(n); na=max(1,int(a*SR)); e[:na]=np.linspace(0,1,na)
    e*=np.exp(-np.arange(n)/SR/d); return e
def lp(x,fc):  # one-pole lowpass
    a=np.exp(-2*np.pi*fc/SR); y=np.zeros_like(x); acc=0.0
    for k in range(len(x)): acc=(1-a)*x[k]+a*acc; y[k]=acc
    return y
def note(f): return 440*2**((f-69)/12)
BPM=100; beat=60/BPM; bar=4*beat
chords=[[48,55,60,64,67],[45,52,57,60,64],[41,48,53,57,60],[43,50,55,59,62]]  # C Am F G
# --- пэд (весь ролик), мягко нарастает на рассвете
pad=np.zeros(N)
for bi in range(int(DUR/bar)+1):
    ch=chords[bi%4]; s0=bi*bar; n=int(bar*SR*1.35); tt=np.arange(n)/SR
    seg=np.zeros(n)
    for m in ch[1:]:
        f=note(m+12)
        for det in (-0.12,0.12): seg+=np.sin(2*np.pi*f*(1+det/100)*tt+rng.random()*6)
    e=np.minimum(1,tt/0.35)*np.minimum(1,(n/SR-tt)/0.8)
    i=int(s0*SR); j=min(N,i+n); pad[i:j]+=(seg*e)[:j-i]
pad=lp(pad,1800)*0.035*np.clip(0.35+t/3.0,0,1)
L+=pad; Rr+=pad
# --- арпеджио (с 3.0 до 11.5 и финальный аккорд)
for k in range(int((11.5-3.0)/(beat/2))):
    st=3.0+k*beat/2; ch=chords[int(st/bar)%4]; m=ch[[1,2,3,4,3,2,1,2][k%8]]+12
    n=int(0.5*SR); tt=np.arange(n)/SR; f=note(m)
    s=(np.sin(2*np.pi*f*tt)+0.3*np.sin(4*np.pi*f*tt))*env(n,0.003,0.18)
    add(s,st,pan=0.35*np.sin(k),gain=0.07)
# --- бас и бочка
for k in range(int((11.5-3.0)/beat)):
    st=3.0+k*beat; ch=chords[int(st/bar)%4]
    n=int(0.35*SR); tt=np.arange(n)/SR
    kick=np.sin(2*np.pi*(55+90*np.exp(-tt*30))*tt)*np.exp(-tt*9)
    add(kick,st,gain=0.28 if k%2==0 else 0.18)
    if k%2==0:
        n2=int(beat*2*SR); t2=np.arange(n2)/SR; f=note(ch[0]-12)
        add(np.sin(2*np.pi*f*t2)*env(n2,0.01,0.6),st,gain=0.13)
# --- SFX
def whoosh(d=0.6,up=True):
    n=int(d*SR); nz=rng.standard_normal(n); tt=np.arange(n)/SR
    e=np.sin(np.pi*tt/d)**2; out=np.zeros(n); fc0,fc1=(400,4000) if up else (4000,400)
    for c in range(8):
        a,b=c*n//8,(c+1)*n//8; out[a:b]=lp(nz[a:b],fc0+(fc1-fc0)*c/7)
    return out*e
def pop(f=900,d=0.12):
    n=int(d*SR); tt=np.arange(n)/SR
    return np.sin(2*np.pi*f*(1+0.6*np.exp(-tt*40))*tt)*np.exp(-tt*35)
def chime(f=1568,d=1.6):
    n=int(d*SR); tt=np.arange(n)/SR
    return sum(np.sin(2*np.pi*f*h*tt)*np.exp(-tt*(2.5+h))/h for h in (1,2.01,3.02,4.2))
def tick(f=2400): 
    n=int(0.04*SR); tt=np.arange(n)/SR; return np.sin(2*np.pi*f*tt)*np.exp(-tt*120)
# буквы заголовка
for i in range(8): add(pop(700+i*60,0.1),0.62+i*0.07,pan=-0.6+i*0.17,gain=0.10)
add(whoosh(0.5),1.15,gain=0.10); add(pop(520,0.15),1.45,gain=0.14)
add(chime(1047,2.5),2.6,gain=0.05)            # восход
add(whoosh(0.9),2.55,gain=0.16); add(chime(2093,1.4),3.05,gain=0.05)
add(pop(380,0.2),4.05,gain=0.25)              # «+» число
for v in range(6): add(tick(2000+v*180),4.2+(v+0.5)*1.4/6,gain=0.10)
add(chime(1568,1.6),5.62,gain=0.09)
for i,c in enumerate([6.55,7.05,7.55]):
    add(whoosh(0.35),c-0.05,pan=-0.5+0.5*i,gain=0.10); add(pop(620+i*120,0.14),c+0.28,pan=-0.5+0.5*i,gain=0.22)
add(whoosh(0.4),8.25,gain=0.07); add(pop(900,0.1),8.6,gain=0.10)
for i in range(4): add(tick(3200+i*200),7.2+i*0.9,pan=-0.8+i*0.5,gain=0.04)   # птицы
add(whoosh(0.6),9.5,pan=0.6,gain=0.14); add(pop(700,0.14),10.05,gain=0.18)
add(whoosh(0.8,False),11.45,gain=0.16)
add(chime(1047,3.0),12.2,gain=0.08); add(whoosh(0.7),12.0,gain=0.12)
add(pop(330,0.25),12.55,gain=0.3); add(pop(300,0.25),12.85,gain=0.3)
add(chime(2093,2.0),13.25,gain=0.06)
# финальный аккорд
n=int(3.0*SR); tt=np.arange(n)/SR; fin=sum(np.sin(2*np.pi*note(m+12)*tt) for m in [48,55,60,64,67,72])
add(lp(fin,2500)*np.minimum(1,tt/0.3)*np.exp(-tt*0.9),12.2,gain=0.05)
# мастер: fade, нормализация
fade=np.clip((DUR-t)/0.8,0,1)*np.clip(t/0.4,0,1)
st=np.stack([L,Rr],1)*fade[:,None]; st/=np.max(np.abs(st))/0.89
st=np.tanh(st*1.1)/np.tanh(1.1)*0.9
import sys
w=wave.open(sys.argv[1] if len(sys.argv)>1 else 'audio.wav','wb');w.setnchannels(2);w.setsampwidth(2);w.setframerate(SR)
w.writeframes((st*32767).astype('<i2').tobytes());w.close(); print('audio ok')
