import sys, os, json, subprocess, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
SRC="/mnt/user-data/uploads/5f7a4583-e557e7cd-1df6-4578-aab2-4265bd6c9669.mp4"
OUTRO="/home/claude/papa/docs/brand/ozod-jamol/koncovka/2s/OZOD_JAMOL_KONCOVKA_CHERNAYA.mp4"
W,H,FPS=1080,1920,30
FB="/usr/share/fonts/opentype/inter/Inter-Black.otf"
RED=(226,27,45)
INTRO_N=45; SRC_N=3188
def font_fit(txt,maxw,start=420):
    s=start
    while True:
        f=ImageFont.truetype(FB,s); b=f.getbbox(txt)
        if b[2]-b[0]<=maxw: return f,b
        s-=4
def draw_center(d,txt,cy,maxw,fill,start=420):
    f,b=font_fit(txt,maxw,start)
    d.text(((W-(b[2]-b[0]))/2-b[0], cy-(b[3]-b[1])/2-b[1]),txt,font=f,fill=fill)
    return (b[3]-b[1]), (b[2]-b[0])
def big_title(lines,cy=1180,maxw=940,bar=True):
    """RGBA layer: white Black-weight caps, red bar under, soft black shadow."""
    im=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(im)
    y=cy; hs=[]
    fs=[font_fit(t,maxw) for t in lines]
    tot=sum(b[3]-b[1] for f,b in fs)+ (len(lines)-1)*40
    y=cy-tot/2
    for (f,b),t in zip(fs,lines):
        h=b[3]-b[1]; w=b[2]-b[0]
        d.text(((W-w)/2-b[0], y-b[1]),t,font=f,fill=(255,255,255,255)); y+=h+40
    if bar:
        d.rounded_rectangle([W/2-150,y-6,W/2+150,y+14],radius=10,fill=RED+(255,))
    a=im.split()[3]
    sh=Image.new("RGBA",(W,H),(0,0,0,0))
    sh.putalpha(a.filter(ImageFilter.GaussianBlur(22)).point(lambda v:min(255,int(v*1.5))))
    out=Image.alpha_composite(sh,im)
    return np.asarray(out,dtype=np.float32)/255
def caption_layer():
    im=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(im)
    f1=ImageFont.truetype(FB,112); f2=ImageFont.truetype(FB,112)
    t1="КУТЯПСИЗМИ?"; t2="ИЗОҲДА ЁЗИНГ"
    for t,f,y,col in ((t1,f1,1210,RED+(255,)),(t2,f2,1345,(255,255,255,255))):
        b=f.getbbox(t); d.text(((W-(b[2]-b[0]))/2-b[0], y-b[1]),t,font=f,fill=col,stroke_width=0)
    a=im.split()[3]
    sh=Image.new("RGBA",(W,H),(0,0,0,0))
    sh.putalpha(a.filter(ImageFilter.GaussianBlur(16)).point(lambda v:min(255,int(v*2.2))))
    return np.asarray(Image.alpha_composite(sh,im),dtype=np.float32)/255
def window_layers():
    m=Image.new("L",(W,H),0); d=ImageDraw.Draw(m)
    f1,b1=font_fit("КАТТА",980); f2,b2=font_fit("ДАВРА",980)
    h1=b1[3]-b1[1]; h2=b2[3]-b2[1]; top=760
    d.text(((W-(b1[2]-b1[0]))/2-b1[0], top-b1[1]),"КАТТА",font=f1,fill=255)
    d.text(((W-(b2[2]-b2[0]))/2-b2[0], top+h1+50-b2[1]),"ДАВРА",font=f2,fill=255)
    sub=Image.new("RGBA",(W,H),(0,0,0,0)); ds=ImageDraw.Draw(sub)
    y=top+h1+50+h2+90
    f=ImageFont.truetype(FB,58); t="TELEGRAM"; b=f.getbbox(t)
    ds.text(((W-(b[2]-b[0]))/2-b[0], y-b[1]),t,font=f,fill=RED+(255,))
    f=ImageFont.truetype(FB,84); t="@kattadavrauz"; b=f.getbbox(t)
    ds.text(((W-(b[2]-b[0]))/2-b[0], y+80-b[1]),t,font=f,fill=(255,255,255,255))
    return np.asarray(m,dtype=np.float32)/255, np.asarray(sub,dtype=np.float32)/255
def over(fr,layer,op=1.0):
    a=layer[:,:,3:4]*op
    return fr*(1-a)+layer[:,:,:3]*a
def ease(x): x=max(0.0,min(1.0,x)); return 1-(1-x)**3
def scaled(layer,s):
    if abs(s-1)<1e-3: return layer
    im=Image.fromarray((layer*255).astype(np.uint8),"RGBA")
    nw,nh=int(W*s),int(H*s); im2=im.resize((nw,nh),Image.BICUBIC)
    l=(nw-W)//2; t=(nh-H)//2
    return np.asarray(im2.crop((l,t,l+W,t+H)),dtype=np.float32)/255
T=json.load(open("timeline.json"))
L={}
def layers():
    if L: return L
    L["mohim"]=big_title(["МОҲИМ"]); L["klip"]=big_title(["ЯНГИ","КЛИП"],maxw=760)
    L["prem"]=big_title(["ПРЕМЬЕРА"]); L["tez"]=big_title(["ТЕЗ","КУНДА"],maxw=760)
    L["cap"]=caption_layer(); L["wm"],L["wsub"]=window_layers()
    return L
def compose(fr,t):
    """fr float32 HxWx3 0..1, t = source seconds"""
    Ls=layers()
    for key in ("mohim","klip","prem","tez"):
        a,b=T[key]
        if a<=t<b:
            k=(t-a)*FPS; kout=(b-t)*FPS
            op=min(1.0,(k+1)/3.0)*min(1.0,kout/4.0)
            s=1.14-0.14*ease((k+1)/5.0)
            fl=max(0.0,0.42-0.14*k)
            fr=fr+(1-fr)*fl
            fr=over(fr,scaled(Ls[key],s),op)
    a,b=T["cap"]
    if a<=t<b:
        op=min(1.0,(t-a)*FPS/6.0)*min(1.0,(b-t)*FPS/6.0)
        fr=over(fr,Ls["cap"],op)
    a,b=T["win"]
    if a<=t<b:
        k=(t-a)*FPS; kout=(b-t)*FPS
        dark=ease(k/6.0)*min(1.0,kout/6.0)
        m=Ls["wm"][:,:,None]
        fr=fr*(1-dark*(1-m))
        sop=ease((k-10)/8.0)*min(1.0,kout/6.0)
        if sop>0: fr=over(fr,Ls["wsub"],sop)
    return fr
# ---------- intro (path A) at 1080x1920
def intro_frames():
    rng=np.random.default_rng(7)
    def tl(txt,cy):
        im=Image.new("L",(W,H),0); d=ImageDraw.Draw(im); draw_center(d,txt,cy,930,255); return im
    t1=tl("PAPARAZZI",862); t2=tl("КАТТА ДАВРА",1058)
    a1=np.asarray(t1,dtype=np.float32)/255; a2=np.asarray(t2,dtype=np.float32)/255
    b1=np.asarray(t1.filter(ImageFilter.GaussianBlur(21)),dtype=np.float32)/255
    b2=np.asarray(t2.filter(ImageFilter.GaussianBlur(21)),dtype=np.float32)/255
    yy,xx=np.mgrid[0:H,0:W].astype(np.float32)
    g=lambda cx,cy,r: np.exp(-(((xx-cx)**2+(yy-cy)**2)/(2*r*r)))
    g1=g(180,495,315); g2=g(915,1440,315); g3=g(540,960,630)
    dec=(1.0,0.75,0.4,0.18,0.06); F1,F2,F3=4,19,34
    fa=lambda i,s: dec[i-s] if 0<=i-s<len(dec) else 0.0
    for i in range(INTRO_N):
        fr=np.zeros((H,W),np.float32); f1=fa(i,F1); f2=fa(i,F2)
        if i>F1: fr+=a1*0.96
        if i>F2: fr+=a2*0.96
        fr+=b1*f1*0.9+b2*f2*0.9+g1*f1*1.15+0.12*f1+g2*f2*1.15+0.12*f2
        if i>=F3:
            k=(i-F3)/(INTRO_N-1-F3); k=k*k*(3-2*k); fr+=g3*k*2.2+k*k*1.3
        fr=np.clip(fr,0,1); fr+=rng.normal(0,0.035,(H,W)).astype(np.float32)*(1-fr*0.7)
        yield np.repeat((np.clip(fr,0,1)*255).astype(np.uint8)[:,:,None],3,2)
def src_reader(extra=[]):
    return subprocess.Popen(["ffmpeg","-v","error"]+extra+["-i",SRC,"-vf",f"scale={W}:{H}:flags=lanczos","-f","rawvideo","-pix_fmt","rgb24","-"],stdout=subprocess.PIPE)
if sys.argv[1]=="stills":
    ims=[]
    for t in [float(x) for x in sys.argv[2:]]:
        p=subprocess.run(["ffmpeg","-v","error","-ss",str(t),"-i",SRC,"-frames:v","1","-vf",f"scale={W}:{H}:flags=lanczos","-f","rawvideo","-pix_fmt","rgb24","-"],capture_output=True)
        fr=np.frombuffer(p.stdout,dtype=np.uint8).reshape(H,W,3).astype(np.float32)/255
        o=(np.clip(compose(fr,t),0,1)*255).astype(np.uint8)
        ims.append(Image.fromarray(o).resize((360,640)))
    sh=Image.new("RGB",(360*len(ims),640))
    for i,im in enumerate(ims): sh.paste(im,(360*i,0))
    sh.save("out/stills.jpg",quality=88)
else:
    out=sys.argv[2]
    enc=subprocess.Popen(["ffmpeg","-v","error","-y","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-","-c:v","libx264","-crf","23","-maxrate","3100k","-bufsize","6200k","-preset","slow","-pix_fmt","yuv420p","-movflags","+faststart",out+".tmp.mp4"],stdin=subprocess.PIPE)
    for f in intro_frames(): enc.stdin.write(f.tobytes())
    rd=src_reader(); n=0; sz=W*H*3
    lo=min(v[0] for v in T.values())-0.1; hi=max(v[1] for v in T.values())+0.1
    while True:
        buf=rd.stdout.read(sz)
        if len(buf)<sz: break
        t=n/FPS
        if lo<=t<=hi:
            fr=np.frombuffer(buf,dtype=np.uint8).reshape(H,W,3).astype(np.float32)/255
            buf=(np.clip(compose(fr,t),0,1)*255).astype(np.uint8).tobytes()
        enc.stdin.write(buf); n+=1
    rd.wait()
    o=subprocess.Popen(["ffmpeg","-v","error","-i",OUTRO,"-vf",f"scale={W}:{H},fps={FPS}","-f","rawvideo","-pix_fmt","rgb24","-"],stdout=subprocess.PIPE)
    m=0
    while True:
        buf=o.stdout.read(sz)
        if len(buf)<sz: break
        enc.stdin.write(buf); m+=1
    enc.stdin.close(); enc.wait(); assert enc.returncode==0
    os.rename(out+".tmp.mp4",out); print("src frames",n,"outro frames",m)
