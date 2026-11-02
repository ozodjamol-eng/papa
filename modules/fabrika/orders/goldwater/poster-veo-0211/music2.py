"""Спокойный премиальный бэд (свой): 76 BPM, пэд + мягкое пиано-арпеджио + саб. Без ударных хитов."""
import numpy as np, wave, sys
out=sys.argv[1]; D=float(sys.argv[2]); SR=48000; beat=60/76; N=int(SR*D); t=np.arange(N)/SR
L=np.zeros(N); R=np.zeros(N); nf=lambda m:440*2**((m-69)/12)
def add(sig,s,pan=0,g=1):
    s=int(s*SR)
    if s>=N: return
    e=min(N,s+len(sig)); sig=sig[:e-s]*g; L[s:e]+=sig*(1-pan); R[s:e]+=sig*(1+pan)
ch=[[50,57,62,66],[47,54,59,62],[43,50,55,59],[45,52,57,61]]  # D Bm G A
bar=beat*4
for i in range(int(D/bar)+1):
    c=ch[i%4]; tt=np.arange(int(bar*1.1*SR))/SR; env=np.minimum(1,tt/1.2)*np.exp(-np.maximum(0,tt-bar)*3)
    for m in c[1:]:
        for d,p in((-.12,-.6),(.12,.6)): add(.03*env*np.sin(2*np.pi*nf(m+12)*(1+d/100)*tt),i*bar,p)
    add(.09*env*np.sin(2*np.pi*nf(c[0]-12)*tt),i*bar)
    for j in range(8):
        m=c[[1,2,3,2,1,2,3,2][j]]+24; tl=np.arange(int(1.6*SR))/SR
        s=np.exp(-tl*3.2)*(np.sin(2*np.pi*nf(m)*tl)+.25*np.sin(4*np.pi*nf(m)*tl)*np.exp(-tl*6))
        add(.05*s,i*bar+j*beat/2,.35 if j%2 else -.35)
fade=np.minimum(1,t/1.5)*np.minimum(1,(D-t)/1.2); L*=fade; R*=fade
# простая реверберация (задержки)
for dl,g in((.031,.35),(.047,.28),(.083,.2),(.121,.14)):
    k=int(dl*SR); L[k:]+=g*R[:-k]; R[k:]+=g*L[:-k]
m=max(abs(L).max(),abs(R).max())*1.1; L/=m; R/=m
st=(np.stack([L,R],1)*32767).astype(np.int16); w=wave.open(out,'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(st.tobytes()); w.close()
