import sys, math, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
W,H=map(int,sys.argv[1].split('x')); OUT=sys.argv[2]; SRC=sys.argv[3] if len(sys.argv)>3 else 'L'
FPS=30; DUR=8.0; N=int(FPS*DUR)
PORT=H>W
F='/home/claude/b3d/'
# --- emblem layers, cropped to common bbox
lay={p:Image.open(f'{F}{SRC}_{p}.png').convert('RGBA') for p in ('O','band','J')}
allα=np.maximum.reduce([np.asarray(l)[...,3] for l in lay.values()])
ys,xs=np.nonzero(allα>8); bb=(xs.min()-6,ys.min()-6,xs.max()+6,ys.max()+6)
lay={k:v.crop(bb) for k,v in lay.items()}
ew0,eh0=lay['O'].size
# layout
if PORT: EW=W*0.70; ECX,ECY0,ECY1=W/2,H*0.44,H*0.40
else:    EW=W*0.40; ECX,ECY0,ECY1=W/2,H*0.47,H*0.40
S=EW/ew0
lay={k:v.resize((int(ew0*S),int(eh0*S)),Image.LANCZOS) for k,v in lay.items()}
ew,eh=lay['O'].size
full=Image.new('RGBA',(ew,eh));[full.alpha_composite(lay[k]) for k in ('O','band','J')]
glowsrc=Image.new('RGBA',(ew+400,eh+400),(0,0,0,0)); glowsrc.paste(full,(200,200),full)
ga=np.asarray(glowsrc)[...,3].astype(np.float32)/255
red_glow=Image.fromarray((np.clip(ga,0,1)*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(60*S*2.2))
# --- text layers
U='/home/claude/b3d/Unbounded-%d.ttf'
def textlayer(scale):
    size=int(EW*0.145*scale)
    f9=ImageFont.truetype(U%900,size);f2=ImageFont.truetype(U%200,size)
    d=ImageDraw.Draw(Image.new('L',(10,10)))
    w1=d.textlength('OZOD',font=f9);w2=d.textlength('JAMOL',font=f2);gap=size*0.32;tw=int(w1+gap+w2)+10
    im=Image.new('RGBA',(tw,int(size*1.3)),(0,0,0,0));dd=ImageDraw.Draw(im)
    dd.text((0,0),'OZOD',font=f9,fill=(255,255,255,255));dd.text((w1+gap,0),'JAMOL',font=f2,fill=(255,255,255,255))
    a=np.asarray(im).astype(np.float32);hh=a.shape[0]
    g=np.linspace(1.0,0.80,hh)[:,None];a[...,:3]*=g[...,None]
    im=Image.fromarray(a.astype(np.uint8)).crop(im.getbbox())
    # tagline
    ts=int(size*(0.21 if PORT else 0.30));ft=ImageFont.truetype(U%400,ts);sp=ts*0.55
    words=['MEDIA','BUSINESS','CREATIVE'];gapd=ts*1.8
    def wl(t): return sum(d.textlength(c,font=ft) for c in t)+sp*(len(t)-1)
    tot=sum(wl(t) for t in words)+4*gapd
    tg=Image.new('RGBA',(int(tot)+10,int(ts*1.5)),(0,0,0,0));td=ImageDraw.Draw(tg);x=0;chars=[]
    for i,t in enumerate(words):
        for c in t:
            chars.append((x,c));x+=d.textlength(c,font=ft)+sp
        x-=sp
        if i<2:
            r=ts*0.17;cx=x+gapd;chars.append((cx,'•'));x+=2*gapd
    return im,(ft,ts,chars,int(tot)+10,int(ts*1.5))
TXT,TAG=textlayer(1.0 if not PORT else 0.95)
def tagimg(prog):
    ft,ts,chars,tw,th=TAG;im=Image.new('RGBA',(tw,th),(0,0,0,0));d=ImageDraw.Draw(im);n=len(chars)
    for i,(x,c) in enumerate(chars):
        a=np.clip(prog*1.6-i/n*0.6*1.6,0,1)
        if a<=0: continue
        if c=='•':
            r=ts*0.17;d.ellipse((x-r,ts*0.62-r,x+r,ts*0.62+r),fill=(255,16,36,int(255*a)))
        else: d.text((x,(1-a)*ts*0.3),c,font=ft,fill=(205,205,205,int(255*a)))
    return im
# --- background
yy,xx=np.mgrid[0:H,0:W].astype(np.float32)
r=np.sqrt(((xx-W/2)/max(W,H))**2+((yy-H*0.42)/max(W,H))**2)
BG=np.array([0.012,0.012,0.013])+(np.array([0.10,0.035,0.04])-np.array([0.012,0.012,0.013]))*np.clip(1-r*1.8,0,1)[...,None]**1.6
BG*= (1-0.5*np.clip(r*1.5-0.25,0,1))[...,None]
dg=(xx*0.7071+yy*0.7071)/max(W,H)
floor=np.clip((yy/H-0.80)/0.2,0,1)[...,None]*np.array([0.06,0.01,0.012])
def beams(t):
    b=np.zeros((H,W,3),np.float32)
    for pos,wd,st,sp in ((0.55,0.03,0.07,0.03),(0.80,0.012,0.055,-0.02),(0.35,0.008,0.04,0.025)):
        p=pos+sp*t
        b+=np.array([1.0,0.06,0.08])*st*np.exp(-((dg-p)/wd)**2)[...,None]
    return b
def ease_out(x): x=np.clip(x,0,1); return 1-(1-x)**3
def ease_io(x): x=np.clip(x,0,1); return x*x*(3-2*x)
def back(x,s=1.4): x=np.clip(x,0,1); return 1+ (s+1)*(x-1)**3 + s*(x-1)**2
def place(canvas,img,cx,cy,scale=1.0,rot=0.0,alpha=1.0):
    if alpha<=0.003: return
    im=img
    if scale!=1.0: im=im.resize((max(1,int(im.width*scale)),max(1,int(im.height*scale))),Image.BICUBIC)
    if rot: im=im.rotate(rot,Image.BICUBIC,expand=True)
    if alpha<1: a=im.getchannel('A').point(lambda v:int(v*alpha));im=im.copy();im.putalpha(a)
    canvas.alpha_composite(im,(int(cx-im.width/2),int(cy-im.height/2)))
def glint_mask(t0,t,img):
    # diagonal bright strip passing over img alpha
    p=(t-t0)/0.7
    if p<0 or p>1: return None
    a=np.asarray(img)[...,3].astype(np.float32)/255;h,w=a.shape
    gy,gx=np.mgrid[0:h,0:w].astype(np.float32);d=(gx+gy)/(w+h)
    s=np.exp(-((d-(-0.1+1.2*p))/0.035)**2)*a*0.75
    out=np.zeros((h,w,4),np.uint8);out[...,:3]=255;out[...,3]=(s*255).astype(np.uint8)
    return Image.fromarray(out)
import os; os.makedirs(OUT,exist_ok=True)
rng=np.random.default_rng(3)
for fi in range(N):
    t=fi/FPS
    fade_in=ease_io(t/0.6); fade_out=1-ease_io((t-7.5)/0.5)
    impact=np.exp(-max(0,t-2.0)*3.5)*(t>=2.0)
    bg=BG*(0.6+0.4*fade_in)+beams(t)*fade_in+floor+np.array([0.20,0.01,0.02])*impact*0.35*np.clip(1-r*2,0,1)[...,None]
    canvas=Image.fromarray((np.clip(bg,0,1)*255).astype(np.uint8)).convert('RGBA')
    # emblem position: rises after 3.2s
    k=ease_io((t-3.1)/1.1); ecy=ECY0+(ECY1-ECY0)*k; esc=1.0-0.12*k+0.02*ease_io((t-4.5)/3.5)
    shake=(rng.normal(0,1,2)*W*0.004*impact) if t>=2.0 and t<2.25 else np.zeros(2)
    cx,cy=ECX+shake[0],ecy+shake[1]
    # glow
    gl=0.22*ease_io((t-1.6)/0.5)+0.45*impact
    if gl>0:
        gimg=Image.new('RGBA',red_glow.size,(255,16,36,0));gimg.putalpha(red_glow.point(lambda v:int(min(255,v*gl*1.1))))
        place(canvas,gimg,cx,cy,esc)
    # band: slides along diagonal from bottom-left (0.4-1.4)
    pb=ease_out((t-0.4)/1.0)
    if t>=0.4:
        off=(1-pb)*W*0.9
        for sub in range(4 if pb<0.98 else 1):
            pb2=ease_out((t-0.4-sub/FPS/4)/1.0);off2=(1-pb2)*W*0.9
            place(canvas,lay['band'],cx-off2*0.7071,cy+off2*0.7071,esc,alpha=(1 if pb>0.98 else 0.35 if sub else 0.6))
    # O: scale in + rotate (1.0-1.9)
    po=(t-1.0)/0.9
    if po>0:
        place(canvas,lay['O'],cx,cy,esc*(1.25-0.25*ease_out(po)),rot=(1-ease_out(po))*-14,alpha=ease_io(po*1.4))
    # J: drops from top (1.15-2.0) with back ease
    pj=(t-1.15)/0.85
    if pj>0:
        place(canvas,lay['J'],cx,cy-(1-back(pj))*H*0.55,esc,alpha=ease_io(pj*2))
    # glints
    for g0 in (2.15,6.6):
        gm=glint_mask(g0,t,full)
        if gm is not None: place(canvas,gm,cx,cy,esc)
    # flash at impact
    if 2.0<=t<2.35:
        k2=np.exp(-(t-2.0)*12)
        rr=np.sqrt(((xx-cx)/max(W,H))**2+((yy-cy)/max(W,H))**2)
        fa=(np.exp(-(rr/0.16)**2)*0.75*k2)
        fl=np.zeros((H,W,4),np.uint8);fl[...,0]=255;fl[...,1]=200;fl[...,2]=200;fl[...,3]=(np.clip(fa,0,1)*255).astype(np.uint8)
        canvas.alpha_composite(Image.fromarray(fl))
    # wordmark reveal (4.2-5.0): wipe left->right
    pw=ease_out((t-4.25)/0.8)
    if pw>0:
        ty=ecy+eh*esc/2+(H*0.075 if not PORT else H*0.05)
        tim=TXT.copy();m=Image.new('L',tim.size,0);ImageDraw.Draw(m).rectangle((0,0,int(tim.width*pw*1.15),tim.height),fill=255)
        m=m.filter(ImageFilter.GaussianBlur(tim.height*0.25));tim.putalpha(ImageChops.multiply(tim.getchannel('A'),m))
        place(canvas,tim,ECX,ty+tim.height/2+(1-pw)*H*0.01,1.0)
        pt=ease_io((t-5.0)/1.0)
        if pt>0:
            tg=tagimg(pt);place(canvas,tg,ECX,ty+tim.height+tg.height*1.2+H*0.012)
    a=np.asarray(canvas.convert('RGB')).astype(np.float32)/255*fade_out*np.clip(t/0.25,0,1)
    a+=rng.normal(0,1.2/255,(H,W,1))
    Image.fromarray((np.clip(a,0,1)*255).astype(np.uint8)).save(f'{OUT}/f{fi:04d}.png',compress_level=1)
print('frames',N)
