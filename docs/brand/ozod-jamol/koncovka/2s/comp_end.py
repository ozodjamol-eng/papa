# концовка 2 с: прозрачный 3D-логотип поверх готового фона + надпись + звук
import sys, numpy as np
from PIL import Image, ImageDraw, ImageFont
C=sys.argv[1]; W,H=1080,1920
BG={'white':'BG02_belaya_studiya','black':'BG01_grafit','red':'BG03_krasnyy'}[C]
bg=Image.open(f'/home/claude/bg/final/{BG}_9x16.png').convert('RGBA').resize((W,H))
INK=(18,18,22) if C=='white' else (255,255,255)
U9='/home/claude/b3d/Unbounded-900.ttf'; U2='/home/claude/b3d/Unbounded-200.ttf'
def wordmark(size):
    f9=ImageFont.truetype(U9,size);f2=ImageFont.truetype(U2,size);d=ImageDraw.Draw(Image.new('L',(1,1)))
    w1=d.textlength('OZOD',font=f9);w2=d.textlength('JAMOL',font=f2);g=size*0.32
    im=Image.new('RGBA',(int(w1+g+w2)+10,int(size*1.3)),(0,0,0,0));dd=ImageDraw.Draw(im)
    dd.text((0,0),'OZOD',font=f9,fill=INK+(255,));dd.text((w1+g,0),'JAMOL',font=f2,fill=INK+(255,));return im.crop(im.getbbox())
WM=wordmark(64)
def eo(x): x=min(max(x,0),1); return 1-(1-x)**3
import os; os.makedirs(f'/home/claude/end2/c_{C}',exist_ok=True)
for f in range(69):
    t=f/30; c=bg.copy()
    lg=Image.open(f'/home/claude/end2/t_{C}/f{min(f,59):03d}.png').convert('RGBA').resize((W,H),Image.LANCZOS)
    c.alpha_composite(lg,(0,-150))
    a=eo((t-0.5)/0.3)*(1-eo((t-1.2)/0.15))
    if a>0:
        im=WM.copy();im.putalpha(im.getchannel('A').point(lambda v:int(v*a)))
        c.alpha_composite(im,(int(W/2-im.width/2),int(1150+(1-eo((t-0.5)/0.3))*20-im.height/2)))
    c.convert('RGB').save(f'/home/claude/end2/c_{C}/e{f:03d}.png')
