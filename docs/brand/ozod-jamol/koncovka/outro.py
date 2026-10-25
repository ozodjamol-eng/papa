import sys, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
VAR=sys.argv[1]; W,H=map(int,sys.argv[2].split('x')); OUT=sys.argv[3]
FPS=30;DUR=3.0;N=int(FPS*DUR);PORT=H>W
RED=(255,16,36)
lay={p:Image.open(f'/home/claude/b3d/L_{p}.png').convert('RGBA') for p in ('O','band','J')}
al=np.maximum.reduce([np.asarray(l)[...,3] for l in lay.values()]);ys,xs=np.nonzero(al>8)
bb=(xs.min()-6,ys.min()-6,xs.max()+6,ys.max()+6);lay={k:v.crop(bb) for k,v in lay.items()}
EW=W*(0.56 if PORT else 0.30);S=EW/lay['O'].width
lay={k:v.resize((int(v.width*S),int(v.height*S)),Image.LANCZOS) for k,v in lay.items()}
full=Image.new('RGBA',lay['O'].size);[full.alpha_composite(lay[k]) for k in ('O','band','J')]
ew,eh=full.size;ECX=W/2;ECY=H*(0.40 if PORT else 0.38)
U='/home/claude/b3d/Unbounded-%d.ttf';M5='/home/claude/fonts/Montserrat-500.ttf';M9='/home/claude/fonts/Montserrat-900.ttf'
def wordmark(size):
    f9=ImageFont.truetype(U%900,size);f2=ImageFont.truetype(U%200,size);d=ImageDraw.Draw(Image.new('L',(1,1)))
    w1=d.textlength('OZOD',font=f9);w2=d.textlength('JAMOL',font=f2);g=size*0.32
    im=Image.new('RGBA',(int(w1+g+w2)+10,int(size*1.3)),(0,0,0,0));dd=ImageDraw.Draw(im)
    dd.text((0,0),'OZOD',font=f9,fill=(255,255,255,255));dd.text((w1+g,0),'JAMOL',font=f2,fill=(255,255,255,255));return im.crop(im.getbbox())
def line(txt,font,size,fill):
    f=ImageFont.truetype(font,size);d=ImageDraw.Draw(Image.new('L',(1,1)));tw=d.textlength(txt,font=f)
    im=Image.new('RGBA',(int(tw)+10,int(size*1.4)),(0,0,0,0));ImageDraw.Draw(im).text((0,0),txt,font=f,fill=fill+(255,));return im.crop(im.getbbox())
def pill(size):
    f=ImageFont.truetype(M9,size);d=ImageDraw.Draw(Image.new('L',(1,1)));tw=d.textlength('@Ozodjamol',font=f)
    h=int(size*1.7);im=Image.new('RGBA',(int(tw)+int(size*2.2),h),(0,0,0,0));dd=ImageDraw.Draw(im)
    dd.rounded_rectangle((0,0,im.width-1,h-1),h//2,fill=RED+(255,));cx,cy=int(size*0.85),h//2;r=size*0.42
    dd.polygon([(cx-r,cy-0.03*r),(cx+r,cy-0.8*r),(cx+0.6*r,cy+0.9*r),(cx+0.05*r,cy+0.4*r),(cx-0.25*r,cy+0.8*r),(cx-0.2*r,cy+0.25*r)],fill=(255,255,255,255))
    dd.text((int(size*1.6),int(size*0.22)),'@Ozodjamol',font=f,fill=(255,255,255,255));return im
k=W/1080 if PORT else H/1080
WM=wordmark(int((96 if PORT else 80)*k));SUB=line('РЕКЛАМА ХИЗМАТЛАРИ',M5,int((40 if PORT else 34)*k),(200,200,200));PL=pill(int((44 if PORT else 36)*k))
yy,xx=np.mgrid[0:H,0:W].astype(np.float32)
def eo(x): x=np.clip(x,0,1); return 1-(1-x)**3
def eio(x): x=np.clip(x,0,1); return x*x*(3-2*x)
def put(c,im,cx,cy,a=1.0,s=1.0,rot=0):
    if a<=0.01: return
    if s!=1: im=im.resize((max(1,int(im.width*s)),max(1,int(im.height*s))),Image.BICUBIC)
    if rot: im=im.rotate(rot,Image.BICUBIC,expand=True)
    if a<1: im=im.copy();im.putalpha(im.getchannel('A').point(lambda v:int(v*a)))
    c.alpha_composite(im,(int(cx-im.width/2),int(cy-im.height/2)))
def reveal(im,p):
    m=Image.new('L',im.size,0);ImageDraw.Draw(m).rectangle((0,0,int(im.width*p*1.2),im.height),fill=255);m=m.filter(ImageFilter.GaussianBlur(im.height*0.3))
    o=im.copy();o.putalpha(ImageChops.multiply(im.getchannel('A'),m));return o
ga=np.asarray(full)[...,3].astype(np.float32)/255
glowimg=Image.new('RGBA',full.size,RED+(0,));glowimg.putalpha(Image.fromarray((ga*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(ew*0.06)))
r=np.sqrt(((xx-W/2)/max(W,H))**2+((yy-ECY)/max(W,H))**2)
if VAR=='A':
    base=np.array([0.012,0.012,0.013]);BGA=base+(np.array([0.11,0.03,0.035])-base)*np.clip(1-r*1.9,0,1)[...,None]**1.5
    dg=(xx*0.7071+yy*0.7071)/max(W,H)
else:
    nz=np.random.default_rng(4).normal(0,1,(H//4,W//4)).astype(np.float32)
    t1=np.asarray(Image.fromarray(((nz-nz.min())/(nz.max()-nz.min())*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2)).resize((W,H),Image.BICUBIC)).astype(np.float32)/255
    nz2=np.random.default_rng(5).normal(0,1,(H//40,W//40)).astype(np.float32)
    t2=np.asarray(Image.fromarray(((nz2-nz2.min())/(nz2.max()-nz2.min())*255).astype(np.uint8)).resize((W,H),Image.BICUBIC)).astype(np.float32)/255
    tex=0.55+0.35*(t1-0.5)+0.35*(t2-0.5)
    cone=np.clip(1-np.abs((xx-W/2)/(W*0.06+ (yy/H)*W*0.42)),0,1)**1.6*np.clip(1-(yy/H-0.05)/0.95,0,1)*(yy>H*0.02)
    pool=np.exp(-(((xx-W/2)/(W*0.35))**2+((yy-ECY)/(H*0.22))**2))
rng=np.random.default_rng(2);import os;os.makedirs(OUT,exist_ok=True)
for fi in range(N):
    t=fi/FPS
    if VAR=='A':
        bg=BGA*eio(t/0.3)
        for pos,wd,st in ((0.55,0.03,0.07),(0.80,0.012,0.05)):
            bg=bg+np.array([1,0.06,0.08])*st*np.exp(-((dg-pos-0.03*t)/wd)**2)[...,None]*eio(t/0.3)
        imp=np.exp(-max(0,t-0.9)*4)*(t>=0.9)
        bg=bg+np.array([0.25,0.02,0.03])*imp*0.5*np.clip(1-r*2.2,0,1)[...,None]
        c=Image.fromarray((np.clip(bg,0,1)*255).astype(np.uint8)).convert('RGBA')
        # wipe band at start
        p=t/0.35
        if 0<=p<=1:
            band=Image.new('RGBA',(int(max(W,H)*3),int(max(W,H)*0.22)),RED+(255,));ImageDraw.Draw(band).rectangle((0,0,band.width,int(band.height*0.08)),fill=(255,255,255,255));band=band.rotate(45,expand=True);off=(-0.9+1.8*eio(p))*max(W,H)
            c.alpha_composite(band,(int(W/2-band.width/2+off),int(H/2-band.height/2+off)))
        sh=(rng.normal(0,1,2)*W*0.005*imp) if 0.9<=t<1.1 else np.zeros(2)
        cx,cy=ECX+sh[0],ECY+sh[1];gl=0.2+0.5*imp
        if t>0.6: g=glowimg.copy();g.putalpha(g.getchannel('A').point(lambda v:int(v*gl)));put(c,g,cx,cy,1,1.05)
        pb=eo((t-0.3)/0.6);pj=eo((t-0.4)/0.5);po=eo((t-0.35)/0.55)
        if t>0.3: put(c,lay['band'],cx-(1-pb)*W*0.9,cy+(1-pb)*W*0.9,a=min(1,pb*2))
        if t>0.35: put(c,lay['O'],cx,cy,a=min(1,po*1.5),s=1.6-0.6*po,rot=(1-po)*-25)
        if t>0.4: put(c,lay['J'],cx+(1-pj)*W*0.6,cy-(1-pj)*H*0.4,a=min(1,pj*2))
        if 0.9<=t<1.2:
            fa=np.exp(-(r/0.15)**2)*0.7*np.exp(-(t-0.9)*12);fl=np.zeros((H,W,4),np.uint8);fl[...,:3]=(255,215,215);fl[...,3]=(np.clip(fa,0,1)*255).astype(np.uint8);c.alpha_composite(Image.fromarray(fl))
        g0=1.25
    else:
        # flicker on
        on=0.0
        for (a,b,v) in ((0.35,0.42,0.7),(0.42,0.5,0.1),(0.5,0.56,0.9),(0.56,0.62,0.3),(0.62,9,1.0)):
            if a<=t<b: on=v
        if t>=0.62: on=1.0
        lum=(0.025+tex*0.05)+tex[...,]*0.0
        light=(cone*0.85+pool*0.45)*on
        img=np.stack([lum+light*tex*0.95,lum+light*tex*0.92,lum+light*tex*0.9],-1)
        img+=np.array([0.5,0.02,0.03])[None,None,:]*np.exp(-(((xx-W/2)/(W*0.45))**2))[...,None]*np.clip((yy/H-0.92)/0.08,0,1)[...,None]*0.6*on
        c=Image.fromarray((np.clip(img,0,1)*255).astype(np.uint8)).convert('RGBA')
        la=on*eio((t-0.5)/0.6)
        if la>0:
            g=glowimg.copy();g.putalpha(g.getchannel('A').point(lambda v:int(v*0.35*la)));put(c,g,ECX,ECY,1,1.05)
            put(c,full,ECX,ECY,a=la,s=0.97+0.03*eio((t-0.5)/2.5))
        g0=1.5
    # glint
    p=(t-g0)/0.6
    if 0<p<1:
        a=np.asarray(full)[...,3].astype(np.float32)/255;h,w=a.shape;gy,gx=np.mgrid[0:h,0:w].astype(np.float32)
        s=np.exp(-((((gx+gy)/(w+h))-(-0.1+1.2*p))/0.035)**2)*a*0.7;gm=np.zeros((h,w,4),np.uint8);gm[...,:3]=255;gm[...,3]=(s*255).astype(np.uint8)
        put(c,Image.fromarray(gm),ECX,ECY)
    # texts
    ty=ECY+eh/2+H*(0.05 if PORT else 0.07)
    pw=eo((t-(1.05 if VAR=='A' else 1.0))/0.5)
    if pw>0: put(c,reveal(WM,pw),ECX,ty+WM.height/2)
    ps=eo((t-1.35)/0.4)
    if ps>0: put(c,SUB,ECX,ty+WM.height+SUB.height*1.4+(1-ps)*10,a=ps)
    pp=eo((t-1.6)/0.4)
    if pp>0: put(c,PL,ECX,ty+WM.height+SUB.height*2.6+PL.height*0.9,a=pp,s=0.9+0.1*pp)
    arr=np.asarray(c.convert('RGB')).astype(np.float32)*np.clip((DUR-t)/0.3,0,1)+rng.normal(0,1.2,(H,W,1))
    Image.fromarray(np.clip(arr,0,255).astype(np.uint8)).save(f'{OUT}/f{fi:03d}.png',compress_level=1)
print('ok',VAR)
