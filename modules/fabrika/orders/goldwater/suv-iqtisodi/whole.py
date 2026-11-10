import cv2, numpy as np, subprocess
from PIL import Image, ImageDraw, ImageFont
W,H,FPS=1080,1920,30
BLACK="/usr/share/fonts/opentype/inter/Inter-Black.otf"; XB="/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
GOLD=(236,190,92); WHITE=(255,255,255); GREY=(176,184,200)
def ease(x): x=min(max(x,0),1); return 1-(1-x)**3
def tracked(d,y,text,font,fill,track=5):
    ws=[d.textlength(c,font=font)+track for c in text]; x=W/2-(sum(ws)-track)/2
    for c,w in zip(text,ws): d.text((x,y),c,font=font,fill=fill,anchor="lm"); x+=w
out=subprocess.Popen(["ffmpeg","-nostdin","-v","error","-y","-f","rawvideo","-pix_fmt","bgr24","-s",f"{W}x{H}","-r",str(FPS),"-i","-","-c:v","libx264","-crf","17","-preset","slow","-pix_fmt","yuv420p","whole_v.mp4"],stdin=subprocess.PIPE)
cap=cv2.VideoCapture("/home/claude/tz/seg/C.mp4"); navy=np.zeros((H,W,3),np.float32); navy[:]=(70,26,8)
for i in range(int(2.0*FPS)):
    ok,f=cap.read(); bg=cv2.GaussianBlur(f.astype(np.float32),(0,0),14)*0.32+navy*0.68
    t=i/FPS; im=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(im); a=ease(t/0.5); b=ease((t-0.4)/0.5)
    tracked(d,760,"GOLD WATER",ImageFont.truetype(XB,52),GOLD+(int(255*a),),10)
    tracked(d,900+(1-b)*30,"СУВ ИҚТИСОДИ",ImageFont.truetype(BLACK,104),WHITE+(int(255*b),),4)
    tracked(d,1030+(1-b)*30,"АППАРАТ БИЗНЕСИ — РАҚАМЛАРДА",ImageFont.truetype(XB,40),GREY+(int(255*b),),5)
    fo=1-ease((t-1.75)/0.25) if t>1.75 else 1
    r=np.asarray(im).astype(np.float32); al=r[...,3:4]/255; fr=(bg*(1-al)+r[...,:3][...,::-1]*al)*fo
    out.stdin.write(fr.astype(np.uint8).tobytes())
for k in (1,2,3):
    c=cv2.VideoCapture(f"w{k}.mp4")
    while True:
        ok,f=c.read()
        if not ok: break
        out.stdin.write(f.tobytes())
c=cv2.VideoCapture("/home/claude/tz/seg/F.mp4"); i=0
while i<int(3.5*FPS):
    ok,f=c.read()
    if not ok: break
    z=1+0.035*i/(3.5*FPS); M=cv2.getRotationMatrix2D((W/2,H*0.42),0,z)
    out.stdin.write(cv2.warpAffine(f,M,(W,H),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_REFLECT).tobytes()); i+=1
c=cv2.VideoCapture("/home/claude/papa/docs/brand/ozod-jamol/koncovka/2s/OZOD_JAMOL_KONCOVKA_CHERNAYA.mp4")
while True:
    ok,f=c.read()
    if not ok: break
    out.stdin.write(cv2.resize(f,(W,H)).tobytes())
out.stdin.close(); out.wait()
