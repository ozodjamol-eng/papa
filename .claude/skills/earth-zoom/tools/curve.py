import cv2,numpy as np,sys
v,crop,t0,t1=sys.argv[1],sys.argv[2],float(sys.argv[3]),float(sys.argv[4])
cap=cv2.VideoCapture(v);fps=cap.get(5);cap.set(cv2.CAP_PROP_POS_MSEC,t0*1000)
prev=None;t=t0;rows=[]
while t<t1:
    ok,f=cap.read()
    if not ok:break
    if crop!='none':
        x,y,w,h=map(int,crop.split(','));f=f[y:y+h,x:x+w]
    g=cv2.cvtColor(cv2.resize(f,(320,int(320*f.shape[0]/f.shape[1]))),cv2.COLOR_BGR2GRAY)
    if prev is not None:
        fl=cv2.calcOpticalFlowFarneback(prev,g,None,0.5,3,21,3,5,1.2,0)
        m=float(np.median(np.abs(fl).sum(-1)))
        if m>0.02: rows.append((t,m))
    prev=g;t+=1/fps
rows=np.array(rows); b=0.25
for s in np.arange(t0,t1,b):
    sel=rows[(rows[:,0]>=s)&(rows[:,0]<s+b),1]
    val=sel.mean() if len(sel) else 0
    print(f"{s-t0:4.2f} {'#'*int(val*2):<40} {val:5.1f}")
