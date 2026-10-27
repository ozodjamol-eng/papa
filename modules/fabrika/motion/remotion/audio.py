import numpy as np, wave
import json,sys
TL=json.loads(sys.argv[2]) if len(sys.argv)>2 else {'HAS_RATES':True,'n':3,'NEWS_T0':12.5,'FIN':21.8,'DUR':25.0}
SR=44100; DUR=float(TL['DUR']); N=int(SR*DUR); t=np.arange(N)/SR
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
BPM=84; beat=60/BPM; bar=4*beat
chords=[[45,52,57,60,64],[41,48,53,57,60],[48,55,60,64,67],[43,50,55,59,62]]  # Am F C G — вечер
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
for k in range(int((float(TL['FIN'])-0.5-4.0)/(beat/2))):
    st=4.0+k*beat/2; ch=chords[int(st/bar)%4]; m=ch[[1,2,3,4,3,2,1,2][k%8]]+12
    n=int(0.5*SR); tt=np.arange(n)/SR; f=note(m)
    s=(np.sin(2*np.pi*f*tt)+0.3*np.sin(4*np.pi*f*tt))*env(n,0.003,0.18)
    add(s,st,pan=0.35*np.sin(k),gain=0.055)
# --- бас и бочка
for k in range(int((float(TL['FIN'])-0.5-4.0)/beat)):
    st=4.0+k*beat; ch=chords[int(st/bar)%4]
    n=int(0.35*SR); tt=np.arange(n)/SR
    kick=np.sin(2*np.pi*(55+90*np.exp(-tt*30))*tt)*np.exp(-tt*9)
    add(kick,st,gain=0.17 if k%2==0 else 0.0)
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
for i in range(12): add(pop(620+i*40,0.1),0.4+(i%5)*0.06+(0.35 if i>=5 else 0),pan=-0.6+i*0.1,gain=0.08)
add(whoosh(0.5),1.45,gain=0.09); add(pop(480,0.15),1.75,gain=0.12)
add(chime(880,2.5),0.2,gain=0.04)                       # закат
add(whoosh(0.8),3.0,gain=0.14)                          # к шапке
add(whoosh(0.4),3.9,gain=0.08); add(pop(560,0.16),4.5,gain=0.2); add(chime(1319,1.2),5.3,gain=0.05)
add(whoosh(0.7,False),8.0,gain=0.13)
if TL['HAS_RATES']: add(whoosh(0.4),8.3,gain=0.08)
for i in (range(3) if TL['HAS_RATES'] else []): add(pop(640+i*110,0.13),8.95+i*0.32,pan=-0.4+0.4*i,gain=0.18)
for v in (range(8) if TL['HAS_RATES'] else []): add(tick(2200+v*120),9.0+v*0.16,gain=0.05)
add(chime(1760,1.0),7.0,gain=0.03)                      # луна
if TL['HAS_RATES']: add(whoosh(0.7,False),11.9,gain=0.13)
for i in range(TL['n']):
    t0=TL['NEWS_T0']+i*3.0
    add(whoosh(0.45),t0-0.1,pan=0.5,gain=0.10); add(pop(700,0.14),t0+0.3,gain=0.18)
    for j in range(3): add(tick(2600+j*150),t0+0.3+j*0.12,gain=0.035)
FIN=float(TL['FIN'])
add(whoosh(0.8,False),FIN-0.5,gain=0.14)
add(chime(1047,3.0),FIN,gain=0.08); add(pop(330,0.25),FIN+0.3,gain=0.26); add(pop(300,0.25),FIN+0.58,gain=0.26)
add(chime(2637,1.4),FIN+1.0,gain=0.05); add(whoosh(0.5),FIN+0.6,gain=0.05)   # падающая звезда
# финальный аккорд
n=int(3.0*SR); tt=np.arange(n)/SR; fin=sum(np.sin(2*np.pi*note(m+12)*tt) for m in [45,52,57,60,64,69])
add(lp(fin,2500)*np.minimum(1,tt/0.3)*np.exp(-tt*0.9),FIN,gain=0.05)
# мастер: fade, нормализация
fade=np.clip((DUR-t)/0.8,0,1)*np.clip(t/0.4,0,1)
st=np.stack([L,Rr],1)*fade[:,None]; st/=np.max(np.abs(st))/0.89
st=np.tanh(st*1.1)/np.tanh(1.1)*0.9
import sys
w=wave.open(sys.argv[1] if len(sys.argv)>1 else 'audio.wav','wb');w.setnchannels(2);w.setsampwidth(2);w.setframerate(SR)
w.writeframes((st*32767).astype('<i2').tobytes());w.close(); print('audio ok')
