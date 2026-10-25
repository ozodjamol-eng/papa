import numpy as np,wave
SR=48000;D=38.0;N=int(SR*D);t=np.arange(N)/SR;rng=np.random.default_rng(11);mix=np.zeros(N)
def lp(x,fc):
    from scipy.signal import lfilter
    a=np.exp(-2*np.pi*fc/SR);return lfilter([1-a],[1,-a],x)
def env(t0,dec): return np.where(t>=t0,np.exp(-(t-t0).clip(0)*dec),0)
def boom(t0,f0,f1,dec,g):
    ti=t-t0;m=ti>=0;fr=np.where(m,np.maximum(f1,f0*np.exp(-ti.clip(0)*4)),0);return np.where(m,np.sin(2*np.pi*np.cumsum(fr)/SR)*np.exp(-ti.clip(0)*dec),0)*g
def noise_burst(t0,dec,fc,g): return lp(rng.normal(0,1,N),fc)*env(t0,dec)*g
def whoosh(tc,w,g,fc=3000):
    e=np.exp(-((t-tc)/w)**2);n=rng.normal(0,1,N)*e;h=lp(n,fc)-lp(n,fc/6);return h*g
def tick(t0,g=0.25,f=3500): return np.sin(2*np.pi*f*t)*env(t0,220)*g
# 1 хук: разрез + удар
mix+=whoosh(0.08,0.07,1.3,6000)+boom(0.15,80,30,2.0,1.4)+noise_burst(0.15,30,5000,0.5)
# 2 слова-удары
for t0 in (2.1,2.6,3.05,3.53,4.15,4.5): mix+=boom(t0,120,50,9,0.55)+noise_burst(t0,60,7000,0.25)
# стоп-кадр: «плёнка останавливается» + удар
st=5.35;sw=np.clip((t-(st-0.5))/0.5,0,1)*(t<st);mix+=np.sin(2*np.pi*np.cumsum(400-350*sw)/SR)*sw*0.12
mix+=whoosh(st,0.05,1.2,7000)+boom(st+0.02,90,28,1.8,1.3)
# переходы-линии
for b in (6.0,12.0,17.0,22.0,26.0): mix+=whoosh(b-0.12,0.09,1.0,5000)+boom(b,70,30,3.0,0.7)
# 3 флакон падает
mix+=boom(6.45,140,60,7,0.5)+tick(6.45,0.15,2600)
for t0 in (7.3,7.9,8.5): mix+=tick(t0,0.2,4200)
# 4 нарезка стилей по долям
for k in range(7):
    t0=12+k*0.5;mix+=noise_burst(t0,25,9000,0.35)+boom(t0,100,45,10,0.35)
mix+=noise_burst(12.5,8,12000,0.25)*np.clip((12.9-t)/0.4,0,1)  # глитч
# 5 счётчики — тики
for k in range(40):
    t0=17.3+k*0.04*(1+k*0.03)
    if t0<19.3: mix+=tick(t0,0.08,3000+k*30)
for k in range(30):
    t0=18.2+k*0.045*(1+k*0.03)
    if t0<19.8: mix+=tick(t0,0.07,2600+k*30)
# 6 сердечки
for k in range(14): mix+=tick(22.3+k*0.25+rng.uniform(0,0.1),0.1,1800+rng.uniform(0,800))
# 7 призыв
for t0 in (26.0,26.18,26.36): mix+=boom(t0,110,45,8,0.5)
mix+=sum(np.sin(2*np.pi*f*t) for f in (1760,2637,3520))*env(27.75,2)*0.035
mix/=np.abs(mix).max()*1.05
w=wave.open('sfx.wav','wb');w.setnchannels(1);w.setsampwidth(2);w.setframerate(SR);w.writeframes((mix*32767).astype(np.int16).tobytes());w.close()
