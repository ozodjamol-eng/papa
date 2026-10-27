"""GOLD WATER — «Ноябрь акцияси + ҳалол насия + янги манзиллар» (27.10.2026). 9:16 30fps.
Кадры → stdout rawvideo (bgr24) для ffmpeg. Исходники: /home/claude/v/sdr/<id>.mp4 (HLG→SDR, 30 fps).
Людей цветом не трогаем — только масштаб/кадрирование."""
import sys, glob, cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont
W, H, FPS = 1080, 1920, 30
S = "/home/claude/v/sdr/"
def font(sz, w="Black"):
    c = glob.glob(f"/usr/share/fonts/**/Inter-{w}.*", recursive=True)
    return ImageFont.truetype(c[0], sz)
NAVY=(0,26,67); GOLD=(200,147,52); GOLDL=(250,226,137); WATER=(4,148,249)

# (клип, старт, длительность, зум_от, зум_до, [оверлеи (t0, t1, вид, заголовок, подзаголовок)])
SEG = [
 ("0377", 10.6, 2.6, 1.10, 1.00, [(0, 2.6, "hook", "", "")]),
 ("0373",  0.22, 2.06, 1.00, 1.04, [(0.2, 2.06, "lt", "GOLD WATER", "ЯНГИЛИКЛАРИМИЗ")]),
 ("0373", 29.73, 5.41, 1.00, 1.04, [(0.3, 5.41, "price", "", "")]),
 ("0373", 35.78, 5.18, 1.16, 1.20, [(0.3, 5.18, "lt", "ФАҚАТ НОЯБРЬ ОЙИДА", "АКЦИЯ")]),
 ("0373", 41.56, 6.38, 1.00, 1.05, [(0.3, 6.38, "lt", "ҲАЛОЛ НАСИЯ", "«ИШОНЧ» ДЎКОНЛАРИ ОРҚАЛИ")]),
 ("0373",  7.00, 5.04, 1.02, 1.10, [(0.2, 5.04, "big2", "КРЕДИТ ЙЎҚ", "ПРОЦЕНТ ЙЎҚ")]),
 ("0376",  2.95, 9.16, 1.00, 1.05, [(0.3, 4.5, "lt", "АСАКА ТУМАНИ", "ЯНГИ МАНЗИЛ"),
                                    (4.6, 9.16, "lt", "«887 MARKET» ОЛДИДА", "ЎЗБЕКИСТОН КЎЧАСИ")]),
 ("0378", 28.0, 2.8, 1.00, 1.06, [(0.2, 2.8, "lt", "МОЛ БОЗОРИ ЙЎЛИДА", "МЎЛЖАЛ")]),
 ("0379",  0.3, 2.8, 1.00, 1.05, [(0.2, 2.8, "lt", "АНДИЖОН ШАҲРИ", "ЎЗБЕКИСТОН КЎЧАСИ")]),
 ("0379",  6.0, 3.0, 1.04, 1.00, [(0.2, 3.0, "lt", "2-АППАРАТ ЎРНАТИЛДИ!", "ДОИМИЙ МИЖОЗИМИЗДА")]),
 ("0374",  3.0, 2.6, 1.00, 1.06, [(0.2, 2.6, "lt", "ТОЗА СУВ — СОҒЛОМ ҲАЁТ!", "")]),
 ("card",  0, 4.8, 1, 1, []),
]

def fill(img):
    h, w = img.shape[:2]; s = max(W/w, H/h)
    img = cv2.resize(img, (round(w*s), round(h*s)), interpolation=cv2.INTER_AREA)
    h, w = img.shape[:2]; y=(h-H)//2; x=(w-W)//2
    return img[y:y+H, x:x+W]
def zoom(img, z):
    if abs(z-1)<1e-3: return img
    M = np.float32([[z,0,(1-z)*W/2],[0,z,(1-z)*H*0.42]])
    return cv2.warpAffine(img, M, (W,H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
def ease(t): t=min(max(t,0),1); return 1-(1-t)**3

def gold_text(lay, xy, txt, f, alpha, anchor="mm"):
    m = Image.new("L",(W,H),0); md = ImageDraw.Draw(m); md.text(xy, txt, font=f, fill=255, anchor=anchor)
    x0,y0,x1,y1 = md.textbbox(xy, txt, font=f, anchor=anchor)
    g = np.zeros((H,W,3),np.uint8); ys = np.arange(H)
    k = np.clip((ys-y0)/max(1,y1-y0),0,1); a = np.abs(k-0.4)/0.6
    for i in range(3): g[:,:,i] = (np.array(GOLDL[i])*(1-a)+np.array(GOLD[i])*a)[:,None]
    m = m.point(lambda v: v*alpha//255)
    lay.paste(Image.fromarray(g), (0,0), m)

GRAD = np.zeros((H,W,4),np.uint8)
_a = np.clip((np.arange(H)-H*0.55)/(H*0.45),0,1)**1.3*165; GRAD[...,3]=_a[:,None].astype(np.uint8)
GRAD = Image.fromarray(GRAD,"RGBA")

def overlay(base, ovs, t):
    im = Image.fromarray(cv2.cvtColor(base, cv2.COLOR_BGR2RGB)).convert("RGBA")
    im = Image.alpha_composite(im, GRAD)
    lay = Image.new("RGBA",(W,H),(0,0,0,0)); d = ImageDraw.Draw(lay)
    tag = font(34,"ExtraBold")
    d.rounded_rectangle([60,90,60+d.textlength("GOLD WATER",font=tag)+60,150],30,fill=NAVY+(200,))
    d.text((90,120),"GOLD WATER",font=tag,fill=GOLDL+(255,),anchor="lm")
    for (t0,t1,kind,title,sub) in ovs:
        if not (t0 <= t < t1): continue
        lt = t-t0; dur = t1-t0
        p = ease(lt/0.35); out = ease((lt-(dur-0.2))/0.2)
        al = int(255*p*(1-out)); dy = int((1-p)*60)
        if kind == "hook":
            cy = 1180+dy; s = 0.85+0.15*ease(lt/0.3)
            d.rounded_rectangle([70,cy-330,W-70,cy+300],50,fill=NAVY+(int(al*0.85),))
            d.rounded_rectangle([70,cy-330,W-70,cy-318],6,fill=GOLD+(al,))
            d.text((W//2,cy-250),"GOLD WATER",font=font(58,"ExtraBold"),fill=GOLDL+(al,),anchor="mm")
            d.text((W//2,cy-130),"НОЯБРЬ",font=font(int(150*s)),fill=(255,255,255,al),anchor="mm")
            d.text((W//2,cy+15),"АКЦИЯСИ",font=font(int(150*s)),fill=(255,255,255,al),anchor="mm")
            # цена: $2700 зачёркнуто → $2300
            p2 = ease((lt-0.7)/0.35); a2 = int(al*p2)
            f1 = font(78,"ExtraBold"); x1 = W//2-215; y = cy+180
            d.text((x1,y),"$2700",font=f1,fill=(255,255,255,int(a2*0.75)),anchor="mm")
            bx = d.textbbox((x1,y),"$2700",font=f1,anchor="mm")
            ln = ease((lt-1.0)/0.25)
            d.line([(bx[0]-6,y+4),(bx[0]-6+(bx[2]-bx[0]+12)*ln,y-4)],fill=(230,40,40,a2),width=9)
            d.text((W//2-45,y),"→",font=f1,fill=GOLDL+(a2,),anchor="mm")
            p3 = ease((lt-1.2)/0.3)
            if p3>0: gold_text(lay,(W//2+175,y),"$2300",font(int(100*(0.8+0.2*p3))),int(al*p3))
        elif kind == "price":
            cy = 1340+dy
            d.rounded_rectangle([90,cy-230,W-90,cy+190],50,fill=NAVY+(int(al*0.88),))
            d.rounded_rectangle([90,cy-230,W-90,cy-218],6,fill=GOLD+(al,))
            d.text((W//2,cy-150),"АППАРАТ НАРХИ",font=font(60,"ExtraBold"),fill=(255,255,255,al),anchor="mm")
            f1 = font(70,"ExtraBold"); y = cy-50
            d.text((W//2,y),"$2700",font=f1,fill=(255,255,255,int(al*0.7)),anchor="mm")
            bx = d.textbbox((W//2,y),"$2700",font=f1,anchor="mm"); ln = ease((lt-0.5)/0.3)
            d.line([(bx[0]-8,y+4),(bx[0]-8+(bx[2]-bx[0]+16)*ln,y-4)],fill=(230,40,40,al),width=9)
            p3 = ease((lt-0.8)/0.35)
            if p3>0: gold_text(lay,(W//2,cy+85),"$2300",font(int(170*(0.8+0.2*p3))),int(al*p3))
        elif kind == "big2":
            cy = 1300+dy
            d.rounded_rectangle([90,cy-200,W-90,cy+200],50,fill=NAVY+(int(al*0.86),))
            d.rounded_rectangle([90,cy-200,W-90,cy-188],6,fill=GOLD+(al,))
            for j,(txt,yy) in enumerate(((title,cy-80),(sub,cy+80))):
                pj = ease((lt-0.35*j)/0.3); aj = int(al*pj)
                d.ellipse([150,yy-38,226,yy+38],fill=(230,40,40,aj))
                d.line([(170,yy-18),(206,yy+18)],fill=(255,255,255,aj),width=9)
                d.line([(206,yy-18),(170,yy+18)],fill=(255,255,255,aj),width=9)
                d.text((255,yy),txt,font=font(88),fill=(255,255,255,aj),anchor="lm")
        else:
            ft = font(84 if len(title)<=16 else 66); fs = font(44,"ExtraBold")
            tw = d.textlength(title,font=ft); sw = d.textlength(sub,font=fs) if sub else 0
            bw = max(tw,sw)+100; x0=60; y1=1700+dy; y0 = y1-(210 if sub else 150)
            d.rounded_rectangle([x0,y0,x0+bw,y1],34,fill=NAVY+(int(al*0.86),))
            d.rounded_rectangle([x0,y0,x0+14,y1],7,fill=GOLD+(al,))
            if sub:
                d.text((x0+50,y0+52),sub,font=fs,fill=GOLDL+(al,),anchor="lm")
                d.text((x0+50,y0+140),title,font=ft,fill=(255,255,255,al),anchor="lm")
            else:
                d.text((x0+50,(y0+y1)//2),title,font=ft,fill=(255,255,255,al),anchor="lm")
    im = Image.alpha_composite(im, lay)
    return cv2.cvtColor(np.array(im.convert("RGB")), cv2.COLOR_RGB2BGR)

CARD_BG = None
def card(t):
    global CARD_BG
    if CARD_BG is None:
        cap = cv2.VideoCapture(S+"0379.mp4"); cap.set(cv2.CAP_PROP_POS_FRAMES, 60); ok, b = cap.read()
        b = cv2.GaussianBlur(fill(b),(0,0),30)
        CARD_BG = (b*0.3 + np.array(NAVY[::-1])*0.7).astype(np.uint8)
    base = zoom(CARD_BG, 1.08-0.04*t/4.8)
    im = Image.fromarray(cv2.cvtColor(base, cv2.COLOR_BGR2RGB)).convert("RGBA")
    lay = Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(lay)
    def a(t0): return int(255*ease((t-t0)/0.4)), int((1-ease((t-t0)/0.4))*50)
    al,dy = a(0.0); cx,cy = W//2, 420+dy
    d.ellipse([cx-115,cy-115,cx+115,cy+115],outline=GOLD+(al,),width=10)
    d.polygon([(cx,cy-78),(cx-54,cy+10),(cx+54,cy+10)],fill=WATER+(al,)); d.ellipse([cx-55,cy-30,cx+55,cy+78],fill=WATER+(al,))
    gold_text(lay,(W//2,690+dy),"GOLD",font(165),al)
    d.text((W//2,845+dy),"WATER",font=font(145),fill=(255,255,255,al),anchor="mm")
    al2,dy2 = a(0.3)
    d.rounded_rectangle([W//2-200,935+dy2,W//2+200,1005+dy2],35,fill=GOLD+(al2,))
    d.text((W//2,970+dy2),"АНДИЖОН",font=font(48,"ExtraBold"),fill=NAVY+(al2,),anchor="mm")
    al3,dy3 = a(0.6)
    d.text((W//2,1100+dy3),"НОЯБРЬ АКЦИЯСИ",font=font(60,"ExtraBold"),fill=(255,255,255,al3),anchor="mm")
    f1 = font(70,"ExtraBold"); y = 1200+dy3
    d.text((W//2-205,y),"$2700",font=f1,fill=(255,255,255,int(al3*0.7)),anchor="mm")
    bx = d.textbbox((W//2-205,y),"$2700",font=f1,anchor="mm")
    d.line([(bx[0]-6,y+4),(bx[2]+6,y-4)],fill=(230,40,40,al3),width=8)
    d.text((W//2-40,y),"→",font=f1,fill=GOLDL+(al3,),anchor="mm")
    gold_text(lay,(W//2+165,y),"$2300",font(92),al3)
    al4,dy4 = a(0.9)
    d.text((W//2,1305+dy4),"ҲАЛОЛ НАСИЯ · КРЕДИТСИЗ, ПРОЦЕНТСИЗ",font=font(40,"ExtraBold"),fill=GOLDL+(al4,),anchor="mm")
    al5,dy5 = a(1.2)
    d.rounded_rectangle([110,1420+dy5,W-110,1580+dy5],80,fill=(255,255,255,al5))
    d.text((W//2,1500+dy5),"+998 97 290 10 40",font=font(84),fill=NAVY+(al5,),anchor="mm")
    al6,_ = a(1.5)
    d.text((W//2,1665),"10 ЛИТР — 5 000 СЎМ",font=font(48,"ExtraBold"),fill=(255,255,255,al6),anchor="mm")
    im = Image.alpha_composite(im, lay)
    return cv2.cvtColor(np.array(im.convert("RGB")), cv2.COLOR_RGB2BGR)

if __name__ == "__main__":
    out = sys.stdout.buffer
    for i,(src,st,dur,z0,z1,ovs) in enumerate(SEG):
        n = round(dur*FPS)
        cap = None
        if src != "card":
            cap = cv2.VideoCapture(S+src+".mp4"); cap.set(cv2.CAP_PROP_POS_FRAMES, round(st*FPS)); last=None
        for k in range(n):
            t = k/FPS
            if cap is None: fr = card(t)
            else:
                ok, f = cap.read()
                if ok: last = fill(f)
                z = z0+(z1-z0)*t/dur
                if k<4 and i>0: z += 0.05*(1-k/4)
                fr = overlay(zoom(last, z), ovs, t)
            if k<3 and i>0:
                w = (3-k)/3*0.3; fr = cv2.addWeighted(fr,1-w,np.full_like(fr,255),w,0)
            out.write(fr.tobytes())
