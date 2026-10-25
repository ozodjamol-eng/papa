import numpy as np, glob, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
W,H=1080,1920;FPS=30;DUR=20.0;N=int(FPS*DUR)
M9='/home/claude/fonts/Montserrat-900.ttf';M8='/home/claude/fonts/Montserrat-800.ttf';M5='/home/claude/fonts/Montserrat-500.ttf'
RED=(255,16,36)
def ld(p,size=(W,H)):
    im=Image.open(p).convert('RGB');r=max(size[0]/im.width,size[1]/im.height);im=im.resize((int(im.width*r)+1,int(im.height*r)+1),Image.LANCZOS)
    return im.crop(((im.width-size[0])//2,(im.height-size[1])//2,(im.width-size[0])//2+size[0],(im.height-size[1])//2+size[1]))
BG={'diag':ld('/home/claude/bg/final/BG04_diagonal_9x16.png'),
    'portal':ld('/mnt/user-data/uploads/30_ASSETS/OZOD_JAMOL_BRAND/FONY/фоны/Неоновый портал в тёмном футуристическом зале-1.png'),
    'beton':ld('/home/claude/bg/final/BG06_beton_svet_9x16.png'),
    'graf':ld('/home/claude/bg/final/BG01_grafit_9x16.png')}
CL={k:[Image.open(f).convert('RGB') for f in sorted(glob.glob(f'clips/{k}/*.jpg'))] for k in ('gw_a','gw_b','gw_c','gw_p','fly','slogo')}
INTRO=sorted(glob.glob('/home/claude/intro/fr916/f*.png'))
def eo(x): x=np.clip(x,0,1); return 1-(1-x)**3
def eio(x): x=np.clip(x,0,1); return x*x*(3-2*x)
def bgzoom(img,p,z0=1.0,z1=1.08):
    z=z0+(z1-z0)*p;w,h=int(W/z),int(H/z);x=(W-w)//2;y=(H-h)//2
    return img.crop((x,y,x+w,y+h)).resize((W,H),Image.BILINEAR).convert('RGBA')
def text_img(lines,font,size,fill=(255,255,255),hl=None,spacing=1.12,shadow=True):
    f=ImageFont.truetype(font,size);d=ImageDraw.Draw(Image.new('L',(1,1)))
    ws=[d.textlength(l,font=f) for l in lines]
    if max(ws)>960:
        size=int(size*960/max(ws));f=ImageFont.truetype(font,size);ws=[d.textlength(l,font=f) for l in lines]
    tw=int(max(ws))+40;th=int(size*spacing*len(lines))+40
    im=Image.new('RGBA',(tw,th),(0,0,0,0));dd=ImageDraw.Draw(im)
    for i,l in enumerate(lines):
        x=(tw-ws[i])/2;y=20+i*size*spacing
        col=RED if hl and i in hl else fill
        dd.text((x,y),l,font=f,fill=col+(255,))
    if shadow:
        sh=im.getchannel('A').filter(ImageFilter.GaussianBlur(size*0.12));base=Image.new('RGBA',im.size,(0,0,0,0));base.putalpha(sh.point(lambda v:int(v*0.8)))
        base.alpha_composite(im);im=base
    return im
def put(c,im,cx,cy,a=1.0,s=1.0):
    if a<=0.01: return
    if s!=1.0: im=im.resize((max(1,int(im.width*s)),max(1,int(im.height*s))),Image.BICUBIC)
    if a<1: im=im.copy();im.putalpha(im.getchannel('A').point(lambda v:int(v*a)))
    c.alpha_composite(im,(int(cx-im.width/2),int(cy-im.height/2)))
def rounded(img,r):
    m=Image.new('L',img.size,0);ImageDraw.Draw(m).rounded_rectangle((0,0,img.width-1,img.height-1),r,fill=255)
    o=img.convert('RGBA');o.putalpha(m);return o
# phone frame
PW,PH=560,1140;SCR=(PW-36,PH-36)
def phone(screen):
    ph=Image.new('RGBA',(PW+80,PH+80),(0,0,0,0));d=ImageDraw.Draw(ph)
    glow=Image.new('L',ph.size,0);ImageDraw.Draw(glow).rounded_rectangle((40,40,40+PW,40+PH),70,fill=255);glow=glow.filter(ImageFilter.GaussianBlur(30))
    g=Image.new('RGBA',ph.size,RED+(0,));g.putalpha(glow.point(lambda v:int(v*0.55)));ph.alpha_composite(g)
    d.rounded_rectangle((40,40,40+PW,40+PH),70,fill=(18,18,20,255),outline=(90,90,95,255),width=4)
    sc=rounded(screen.resize(SCR,Image.BILINEAR),52);ph.alpha_composite(sc,(58,58))
    d.rounded_rectangle((40+PW//2-70,62,40+PW//2+70,92),15,fill=(10,10,10,255))
    return ph
def card(img,w,label):
    h=int(img.height*w/img.width);c=Image.new('RGBA',(w+60,h+150),(0,0,0,0));d=ImageDraw.Draw(c)
    d.rounded_rectangle((30,30,30+w,30+h),36,fill=(20,20,22,255),outline=(255,16,36,255),width=5)
    c.alpha_composite(rounded(img.resize((w-10,h-10),Image.BILINEAR),32),(35,35))
    f=ImageFont.truetype(M9,58);tw=d.textlength(label,font=f)
    d.rounded_rectangle(((w+60-tw)/2-30,h+58,(w+60+tw)/2+30,h+138),40,fill=RED+(255,))
    d.text(((w+60-tw)/2,h+66),label,font=f,fill=(255,255,255,255));return c
def wipe(c,t,t0):
    p=(t-t0)/0.28
    if p<0 or p>1: return
    band=Image.new('RGBA',(W*3,700),RED+(255,));dd=ImageDraw.Draw(band);dd.rectangle((0,0,W*3,40),fill=(255,255,255,255))
    band=band.rotate(45,expand=True)
    off=(-1.2+2.4*eio(p))*W*1.6
    c.alpha_composite(band,(int(W/2-band.width/2+off),int(H/2-band.height/2-off)))
HOOK=text_img(['Рекламангиз','ишламаяптими?'],M9,118,hl=[1])
S2T=text_img(['Биз бизнесингизни','экранга олиб чиқамиз'],M8,66)
SERV=[('01','МОУШН-ГРАФИК','РЕКЛАМА'),('02','ИИ ВИДЕО','ВА АВАТАР'),('03','TELEGRAM','БОТЛАР'),('04','INSTAGRAM','ВОРОНКА')]
def serv_img(n,a,b):
    f9=ImageFont.truetype(M9,76);f5=ImageFont.truetype(M5,50);fn=ImageFont.truetype(M9,60)
    im=Image.new('RGBA',(1000,210),(0,0,0,0));d=ImageDraw.Draw(im)
    d.rectangle((0,30,14,200),fill=RED+(255,));d.text((40,30),n,font=fn,fill=RED+(255,))
    d.text((150,22),a,font=f9,fill=(255,255,255,255));d.text((152,118),b,font=f5,fill=(210,210,210,255));return im
SV=[serv_img(*s) for s in SERV]
S4T=text_img(['Навбат —','сизнинг брендингизда'],M9,84,hl=[0])
USER=None
def user_img():
    f=ImageFont.truetype(M9,72);d=ImageDraw.Draw(Image.new('L',(1,1)));tw=d.textlength('@Ozodjamol',font=f)
    im=Image.new('RGBA',(int(tw)+170,130),(0,0,0,0));dd=ImageDraw.Draw(im)
    dd.rounded_rectangle((0,0,im.width-1,129),65,fill=RED+(255,))
    # telegram plane icon
    cx,cy=64,65;dd.polygon([(cx-30,cy-2),(cx+30,cy-26),(cx+18,cy+28),(cx+2,cy+12),(cx-8,cy+24),(cx-6,cy+8)],fill=(255,255,255,255))
    dd.text((115,20),'@Ozodjamol',font=f,fill=(255,255,255,255));return im
USER=user_img();ORDER=text_img(['Буюртма учун:'],M5,50,shadow=True)
os.makedirs('fr',exist_ok=True)
rng=np.random.default_rng(1)
for fi in range(N):
    t=fi/FPS
    if t<2.2:  # S1 hook
        c=bgzoom(BG['diag'],t/2.2,1.0,1.10)
        p=eo((t-0.15)/0.5);put(c,HOOK,W/2,H*0.47,a=p,s=1.25-0.25*p)
    elif t<6.2:  # S2 phone with works
        u=t-2.2;c=bgzoom(BG['portal'],u/4,1.0,1.06)
        seq=[('gw_a',0),('gw_b',1.33),('gw_c',2.66)];k=min(2,int(u/1.333));nm,st=seq[k];fr=CL[nm][min(len(CL[nm])-1,int((u-st)*FPS))]
        ph=phone(fr);pp=eo(u/0.45);put(c,ph,W/2,H*0.58+(1-pp)*H*0.5,s=0.95+0.05*eio(u/4))
        put(c,S2T,W/2,H*0.13,a=eo((u-0.2)/0.4))
    elif t<12.2:  # S3 services
        u=t-6.2;c=bgzoom(BG['beton'],u/6,1.05,1.12)
        dark=Image.new('RGBA',(W,H),(0,0,0,110));c.alpha_composite(dark)
        for i,im in enumerate(SV):
            ti=u-0.25-i*1.3;p=eo(ti/0.45)
            if p>0: put(c,im,W/2+(1-p)*W*0.8,H*0.24+i*H*0.17+(1-p)*W*0.8*0.0,a=p)
    elif t<16.2:  # S4 proof
        u=t-12.2;c=bgzoom(BG['graf'],u/4,1.0,1.06)
        if u<2.0:
            fr=CL['gw_p'][min(len(CL['gw_p'])-1,int(u*FPS))];cd=card(fr,560,'GOLD WATER');p=eo(u/0.4)
            put(c,cd,W/2,H*0.43,a=p,s=0.9+0.1*p)
        else:
            v=u-2.0;src=CL['fly'] if v<1.0 else CL['slogo'];fr=src[min(len(src)-1,int((v if v<1 else v-1.0)*FPS))]
            cd=card(fr,920,'SHODIYONA MEBEL');p=eo(v/0.4);put(c,cd,W/2,H*0.40,a=p,s=0.9+0.1*p)
        put(c,S4T,W/2,H*0.80,a=eo((u-0.3)/0.4))
    else:  # S5 logo
        u=t-16.2;n=int(u*FPS);idx=30+n if n<42 else 140+(n-42)
        c=Image.open(INTRO[min(idx,len(INTRO)-1)]).convert('RGBA')
        pu=eo((t-18.1)/0.4)
        if pu>0:
            put(c,ORDER,W/2,H*0.80,a=pu);put(c,USER,W/2,H*0.86,a=pu,s=0.9+0.1*pu)
    for t0 in (2.2,6.2,12.2,16.2): wipe(c,t,t0-0.14)
    a=np.asarray(c.convert('RGB')).astype(np.float32)
    a*=np.clip(t/0.2,0,1)*np.clip((20.0-t)/0.25,0,1)
    a+=rng.normal(0,1.3,(H,W,1))
    Image.fromarray(np.clip(a,0,255).astype(np.uint8)).save(f'fr/f{fi:04d}.png',compress_level=1)
print('ok')
