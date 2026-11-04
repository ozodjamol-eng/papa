import cv2,numpy as np,sys,subprocess,os
src='v3_120.mp4'
cap=cv2.VideoCapture(src);frames=[];mags=[0.0];prev=None
while True:
    ok,f=cap.read()
    if not ok:break
    frames.append(f)
    g=cv2.cvtColor(cv2.resize(f[320*1280//1280:,:][0:960],(240,320)),cv2.COLOR_BGR2GRAY)
    if prev is not None:
        fl=cv2.calcOpticalFlowFarneback(prev,g,None,0.5,3,15,3,5,1.2,0)
        mags.append(float(np.median(np.abs(fl).sum(-1))))
    prev=g
mags=np.array(mags); N=len(frames)
# end of motion = last frame where motion is significant
k=np.convolve(mags,np.ones(15)/15,'same')
end=int(np.where(k>0.05*k.max())[0][-1]); print('frames',N,'motion end',end, end/120)
P=np.cumsum(mags[:end+1]); P/=P[-1]
# target: motion T sec, hold H sec; speed: smooth rise 0.5s, ease-out last 1.1s
T=float(sys.argv[1]) if len(sys.argv)>1 else 5.0; H=1.0; fps=30
t=np.linspace(0,T,int(T*fps)+1)
v=np.ones_like(t)
r=0.5; v=np.where(t<r,0.5-0.5*np.cos(np.pi*t/r),v)
e=1.1; m=t>T-e; x=(t[m]-(T-e))/e; v[m]=(1-x)**2   # quadratic ease-out to zero
Pt=np.cumsum(v); Pt-=Pt[0]; Pt/=Pt[-1]
idx=np.interp(Pt,P,np.arange(end+1)).round().astype(int)
idx=list(idx)+[end]*int(H*fps)
os.makedirs('out',exist_ok=True)
w=cv2.VideoWriter('remap_raw.mp4',cv2.VideoWriter_fourcc(*'mp4v'),fps,(frames[0].shape[1],frames[0].shape[0]))
for i in idx: w.write(frames[i])
w.release(); print('out frames',len(idx), len(idx)/fps,'s')
