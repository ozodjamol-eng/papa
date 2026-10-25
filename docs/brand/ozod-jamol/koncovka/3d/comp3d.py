import sys,os,numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter,ImageChops
V=sys.argv[1];W,H=1080,1920;FPS=30;N=102;RED=(255,16,36);IMP={'1':50,'2':52,'3':56}[V];LAST=75
U='/home/claude/b3d/Unbounded-%d.ttf'
def wordmark(size):
    f9=ImageFont.truetype(U%900,size);f2=ImageFont.truetype(U%200,size);d=ImageDraw.Draw(Image.new('L',(1,1)))
    w1=d.textlength('OZOD',font=f9);w2=d.textlength('JAMOL',font=f2);g=size*0.32
    im=Image.new('RGBA',(int(w1+g+w2)+10,int(size*1.3)),(0,0,0,0));dd=ImageDraw.Draw(im)
    dd.text((0,0),'OZOD',font=f9,fill=(255,255,255,255));dd.text((w1+g,0),'JAMOL',font=f2,fill=(255,255,255,255));return im.crop(im.getbbox())
def spaced(txt,font,size,fill,sp):
    f=ImageFont.truetype(font,size);d=ImageDraw.Draw(Image.new('L',(1,1)));tw=sum(d.textlength(ch,font=f) for ch in txt)+sp*size*(len(txt)-1)
    im=Image.new('RGBA',(int(tw)+10,int(size*1.5)),(0,0,0,0));dd=ImageDraw.Draw(im);x=0
    for ch in txt: dd.text((x,0),ch,font=f,fill=fill+(255,));x+=d.textlength(ch,font=f)+sp*size
    return im.crop(im.getbbox())
WM=wordmark(96);SUB=spaced('MOTION GRAFIKA XIZMATLARI',U%400,34,(205,205,205),0.28);PL=spaced('@Ozodjamol',U%400,46,RED,0.06)
def eo(x): x=np.clip(x,0,1); return 1-(1-x)**3
def reveal(im,p):
    m=Image.new('L',im.size,0);ImageDraw.Draw(m).rectangle((0,0,int(im.width*p*1.2),im.height),fill=255);m=m.filter(ImageFilter.GaussianBlur(im.height*0.3))
    o=im.copy();o.putalpha(ImageChops.multiply(im.getchannel('A'),m));return o
def put(c,im,cx,cy,a=1.0,dy=0):
    if a<=0.01: return
    if a<1: im=im.copy();im.putalpha(im.getchannel('A').point(lambda v:int(v*a)))
    c.alpha_composite(im,(int(cx-im.width/2),int(cy-im.height/2+dy)))
ref=Image.open(f'/home/claude/o3d/F1/f{LAST:03d}.png').getchannel('A').resize((W,H));bx=ref.getbbox();LCX=(bx[0]+bx[2])/2;LCY=(bx[1]+bx[3])/2;LB=bx[3]
yy,xx=np.mgrid[0:H,0:W].astype(np.float32);r=np.sqrt(((xx-W/2)/H)**2+((yy-LCY)/H)**2)
base=np.array([0.012,0.012,0.013]);BG=base+(np.array([0.10,0.025,0.03])-base)*np.clip(1-r*2.0,0,1)[...,None]**1.5
BGI=Image.fromarray((BG*255).astype(np.uint8)).convert('RGBA')
rng=np.random.default_rng(1)
os.makedirs(f'/home/claude/o3d/C{V}',exist_ok=True)
for f in range(N):
    src=min(f,LAST);im=Image.open(f'/home/claude/o3d/F{V}/f{src:03d}.png').convert('RGBA').resize((W,H),Image.LANCZOS)
    if f>LAST:
        s=1+0.035*(f-LAST)/(N-1-LAST);nw,nh=int(W*s),int(H*s);im=im.resize((nw,nh),Image.BICUBIC)
        ox=int(LCX*s-LCX);oy=int(LCY*s-LCY);im=im.crop((ox,oy,ox+W,oy+H))
    im=im.filter(ImageFilter.UnsharpMask(2,60,2))
    if V=='2': c=im.copy()
    else: c=BGI.copy();c.alpha_composite(im)
    # bloom
    a=np.asarray(c.convert('RGB')).astype(np.float32);br=np.clip(a.max(2)-200,0,55)/55
    bl=Image.fromarray((a*br[...,None]).astype(np.uint8)).filter(ImageFilter.GaussianBlur(28))
    a=np.clip(a+np.asarray(bl).astype(np.float32)*0.9,0,255)
    c=Image.fromarray(a.astype(np.uint8)).convert('RGBA')
    t0=IMP+5
    p=(f-t0)/12
    if p>0: put(c,reveal(WM,eo(p)),W/2,LB+150,1,dy=(1-eo(p))*20)
    p=(f-t0-7)/12
    if p>0: put(c,SUB,W/2,LB+250,eo(p),dy=(1-eo(p))*16)
    p=(f-t0-13)/12
    if p>0: put(c,PL,W/2,LB+340,eo(p),dy=(1-eo(p))*16)
    a=np.asarray(c.convert('RGB')).astype(np.float32)+rng.normal(0,3.2,(H,W,1))
    a*=np.clip(1-((xx/W-0.5)**2+(yy/H-0.5)**2)*0.9,0,1)[...,None]
    fo=min(1,(N-1-f)/6+0.0) if f>N-7 else 1
    Image.fromarray(np.clip(a*fo,0,255).astype(np.uint8)).save(f'/home/claude/o3d/C{V}/c{f:03d}.png')
print('ok',V,bx)
