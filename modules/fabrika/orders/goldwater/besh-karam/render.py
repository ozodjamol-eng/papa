"""GOLD WATER — «Янги манзил, Беш карам» (25.10.2026). 9:16 30fps. Кадры → stdout rawvideo для ffmpeg."""
import sys, math, cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
W, H, FPS = 1080, 1920, 30
G = "/home/claude/gw/sdr/"; U = "/mnt/user-data/uploads/"
FB = "/usr/share/fonts/truetype/inter/Inter-Black.ttf"
import glob
def font(sz, w="Black"):
    c = glob.glob(f"/usr/share/fonts/**/Inter-{w}.*", recursive=True) or glob.glob(f"/usr/share/fonts/**/Inter*{w}*", recursive=True)
    return ImageFont.truetype(c[0], sz)
NAVY=(0,26,67); ROYAL=(1,67,154); GOLD=(200,147,52); GOLDL=(250,226,137); WHITE=(255,255,255)
SEG = [  # (src, start, dur, title, sub, kind)
 ("c8",3.70,2.00,"ЯНГИ МАНЗИЛ!","GOLD WATER","hook"),
 ("c1",0.00,2.75,"ХЎЖАОБОД","БЕШ КАРАМ МФЙ · ДОСААФ ЁНИДА","lt"),
 ("c3",0.00,2.48,"ДОРИХОНА ОЛДИДА","","lt"),
 ("c4",0.00,1.77,"ЯНГИ СУВ АППАРАТИ","GOLD WATER","lt"),
 (U+"d87b7f19-image.jpg",0,2.00,"«МЕД ШОХ ШИФО»","КЛИНИКАСИ ЁНИДА","lt"),
 ("c2",0.00,3.00,"ШАШЛИК ВА СОМСА","РЎПАРАСИДА","lt",1.5),
 ("c8",0.00,3.50,"ОҒИРЛИК ЧЕК ЙЎЛИДА","ЖУДА ҚУЛАЙ ЛОКАЦИЯ","lt"),
 ("c6",0.00,2.50,"10 БОСҚИЧЛИ ТОЗАЛАШ","СИФАТИ ЯНАДА ЯХШИЛАНДИ","lt"),
 ("c5",0.00,2.10,"5 000 СЎМ","10 ЛИТР — АТИГИ","price"),
 (U+"de7e4196-image.jpg",0,2.20,"КЕЛИБ СИНАБ КЎРИНГ!","","lt"),
 (U+"47c9a889-image.jpg",0,2.10,"АТТАНГ ҚИЛМАЙСИЗ!","","lt"),
 ("card",0,4.60,"","","card"),
]
def fill(img):
    h, w = img.shape[:2]; s = max(W/w, H/h)
    img = cv2.resize(img, (round(w*s), round(h*s)), interpolation=cv2.INTER_AREA)
    h, w = img.shape[:2]; y=(h-H)//2; x=(w-W)//2
    return img[y:y+H, x:x+W]
class Clip:
    def __init__(s, src, start):
        s.photo = src.endswith(".jpg")
        if s.photo: s.img = fill(cv2.imread(src))
        else:
            s.cap = cv2.VideoCapture(G+src+".mp4"); s.cap.set(cv2.CAP_PROP_POS_FRAMES, round(start*FPS)); s.last=None
    def frame(s):
        if s.photo: return s.img
        ok, f = s.cap.read()
        if ok: s.last = f
        return s.last
def zoom(img, z, ox=0, oy=0):
    if abs(z-1)<1e-3: return img
    M = np.float32([[z,0,(1-z)*W/2+ox],[0,z,(1-z)*H/2+oy]])
    return cv2.warpAffine(img, M, (W,H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
def ease(t): t=min(max(t,0),1); return 1-(1-t)**3
def gold_text(d, xy, txt, f, anchor="mm"):
    # золотой градиент через маску
    x0,y0,x1,y1 = d.textbbox(xy, txt, font=f, anchor=anchor)
    m = Image.new("L",(W,H),0); ImageDraw.Draw(m).text(xy, txt, font=f, fill=255, anchor=anchor)
    g = Image.new("RGB",(W,H)); gd=ImageDraw.Draw(g)
    for yy in range(max(y0,0), min(y1+1,H)):
        k=(yy-y0)/max(1,y1-y0); c = GOLDL if k<0.45 else GOLD
        a = abs(k-0.45)/0.55; c = tuple(int(GOLDL[i]*(1-a)+GOLD[i]*a) for i in range(3))
        gd.line([(0,yy),(W,yy)], fill=c)
    return g, m
def overlay_lt(base, title, sub, t, dur, kind):
    im = Image.fromarray(cv2.cvtColor(base, cv2.COLOR_BGR2RGB)).convert("RGBA")
    lay = Image.new("RGBA",(W,H),(0,0,0,0)); d = ImageDraw.Draw(lay)
    # нижний градиент для читаемости
    grad = np.zeros((H,W,4),np.uint8); ys=np.arange(H)
    a = np.clip((ys-H*0.55)/(H*0.45),0,1)**1.3*170; grad[...,3]=a[:,None].astype(np.uint8)
    im = Image.alpha_composite(im, Image.fromarray(grad,"RGBA"))
    # бренд-метка сверху
    tag = font(34,"ExtraBold"); d.rounded_rectangle([60,90,60+d.textlength("GOLD WATER",font=tag)+60,150],30,fill=(0,26,67,200))
    d.text((90,120),"GOLD WATER",font=tag,fill=GOLDL+(255,),anchor="lm")
    p = ease(t/0.35); out = ease((t-(dur-0.18))/0.18) if dur>1 else 0
    alpha = int(255*p*(1-out)); dy = int((1-p)*60)
    if kind=="hook":
        s = 0.85+0.15*ease(t/0.3); f2 = font(int(175*s)); cy=1250+dy
        d.rounded_rectangle([70,cy-250,W-70,cy+250],50,fill=(0,26,67,int(alpha*0.82)))
        d.rounded_rectangle([70,cy-250,W-70,cy-238],6,fill=GOLD+(alpha,))
        fs=font(58,"ExtraBold"); d.text((W//2,cy-175),sub,font=fs,fill=GOLDL+(alpha,),anchor="mm")
        d.text((W//2,cy-40),"ЯНГИ",font=f2,fill=(255,255,255,alpha),anchor="mm")
        d.text((W//2,cy+125),"МАНЗИЛ!",font=f2,fill=(255,255,255,alpha),anchor="mm")
    elif kind=="price":
        fs=font(66,"ExtraBold"); ft=font(150)
        cy=1380+dy
        d.rounded_rectangle([90,cy-200,W-90,cy+150],50,fill=(0,26,67,int(alpha*0.88)))
        d.rounded_rectangle([90,cy-200,W-90,cy-188],6,fill=GOLD+(alpha,))
        d.text((W//2,cy-120),sub,font=fs,fill=(255,255,255,alpha),anchor="mm")
        lay.alpha_composite(Image.new("RGBA",(W,H)),(0,0))
        g,m = gold_text(d,(W//2,cy+30),title,ft)
        m = m.point(lambda v: v*alpha//255); lay.paste(g,(0,0),m)
    else:
        ft = font(84 if len(title)<=16 else 72); fs = font(44,"ExtraBold")
        tw = d.textlength(title,font=ft); sw = d.textlength(sub,font=fs) if sub else 0
        bw = max(tw,sw)+100; x0=60; y1=1700+dy; y0 = y1-(210 if sub else 150)
        d.rounded_rectangle([x0,y0,x0+bw,y1],34,fill=(0,26,67,int(alpha*0.86)))
        d.rounded_rectangle([x0,y0,x0+14,y1],7,fill=GOLD+(alpha,))
        if sub:
            d.text((x0+50,y0+52),sub,font=fs,fill=GOLDL+(alpha,),anchor="lm")
            d.text((x0+50,y0+140),title,font=ft,fill=(255,255,255,alpha),anchor="lm")
        else:
            d.text((x0+50,(y0+y1)//2),title,font=ft,fill=(255,255,255,alpha),anchor="lm")
    im = Image.alpha_composite(im, lay)
    return cv2.cvtColor(np.array(im.convert("RGB")), cv2.COLOR_RGB2BGR)
CARD_BG = None
def card(t):
    global CARD_BG
    if CARD_BG is None:
        b = fill(cv2.imread(U+"d40ca22f-image.jpg")); b = cv2.GaussianBlur(b,(0,0),28)
        b = (b*0.35 + np.array(NAVY[::-1])*0.65).astype(np.uint8); CARD_BG=b
    base = zoom(CARD_BG, 1.08-0.04*t/4.6)
    im = Image.fromarray(cv2.cvtColor(base, cv2.COLOR_BGR2RGB)).convert("RGBA")
    lay = Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(lay)
    def a(t0): return int(255*ease((t-t0)/0.4)), int((1-ease((t-t0)/0.4))*50)
    al,dy = a(0.0)
    # капля
    cx,cy = W//2, 520+dy
    d.ellipse([cx-120,cy-120,cx+120,cy+120],outline=GOLD+(al,),width=10)
    d.polygon([(cx,cy-80),(cx-55,cy+10),(cx+55,cy+10)],fill=(4,148,249,al)); d.ellipse([cx-56,cy-30,cx+56,cy+80],fill=(4,148,249,al))
    g,m = gold_text(d,(W//2,800+dy),"GOLD",font(170)); m=m.point(lambda v:v*al//255); lay.paste(g,(0,0),m)
    d.text((W//2,960+dy),"WATER",font=font(150),fill=(255,255,255,al),anchor="mm")
    al2,dy2=a(0.35)
    d.rounded_rectangle([W//2-200,1050+dy2,W//2+200,1120+dy2],35,fill=GOLD+(al2,))
    d.text((W//2,1085+dy2),"АНДИЖОН",font=font(48,"ExtraBold"),fill=NAVY+(al2,),anchor="mm")
    al3,dy3=a(0.7)
    d.text((W//2,1215+dy3),"СИЗ ҲАҚИНГИЗДА ҚАЙҒУРАДИ",font=font(54,"ExtraBold"),fill=GOLDL+(al3,),anchor="mm")
    d.text((W//2,1300+dy3),"Хўжаобод, Беш карам МФЙ, ДОСААФ ёнида",font=font(40,"SemiBold"),fill=(255,255,255,al3),anchor="mm")
    al4,dy4=a(1.05)
    d.rounded_rectangle([110,1420+dy4,W-110,1580+dy4],80,fill=(255,255,255,al4))
    d.text((W//2,1500+dy4),"+998 97 290 10 40",font=font(84),fill=NAVY+(al4,),anchor="mm")
    al5,_=a(1.4)
    d.text((W//2,1660),"10 ЛИТР — 5 000 СЎМ",font=font(50,"ExtraBold"),fill=(255,255,255,al5),anchor="mm")
    im = Image.alpha_composite(im, lay)
    return cv2.cvtColor(np.array(im.convert("RGB")), cv2.COLOR_RGB2BGR)
out = sys.stdout.buffer; prev=None
for i,seg in enumerate(SEG):
    src,st,dur,title,sub,kind = seg[:6]; hold = seg[6] if len(seg)>6 else 0
    n = round(dur*FPS)
    clip = None if src=="card" else Clip(src,st)
    for k in range(n):
        t=k/FPS
        if kind=="card": fr = card(t)
        else:
            raw = clip.frame() if (t>=hold or k==0) else raw
            f = raw
            z = 1.0 + (0.08 if clip.photo else 0.04)*t/dur
            if k<4: z += 0.06*(1-k/4)   # панч на склейке
            f = zoom(f, z)
            fr = overlay_lt(f, title, sub, t, dur, kind)
        if k<3 and prev is not None and i>0:  # короткий белый вспых-переход
            w = (3-k)/3*0.35; fr = cv2.addWeighted(fr,1-w,np.full_like(fr,255),w,0)
        out.write(fr.tobytes())
    prev=fr
