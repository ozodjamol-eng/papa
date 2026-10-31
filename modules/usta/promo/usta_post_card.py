from PIL import Image, ImageDraw, ImageFont, ImageFilter
W,H=1080,1350
FB="/home/claude/fonts/Montserrat-Black.ttf"; FX="/home/claude/fonts/Montserrat-ExtraBold.ttf"
bg=Image.open("bg.png").convert("RGB"); r=max(W/bg.width,H/bg.height)
bg=bg.resize((int(bg.width*r)+1,int(bg.height*r)+1),Image.LANCZOS); x=(bg.width-W)//2; y=(bg.height-H)//2
bg=bg.crop((x,y,x+W,y+H)).filter(ImageFilter.GaussianBlur(3))
im=Image.blend(bg,Image.new("RGB",(W,H),(8,8,10)),0.72).convert("RGBA"); d=ImageDraw.Draw(im)
WH,YL,RED,DK=(255,255,255),(255,200,60),(229,59,50),(14,14,16,235)
f=lambda p,s:ImageFont.truetype(p,s)
lg=Image.open("/home/claude/fm/tmp/logo.png").convert("RGBA").resize((130,130),Image.LANCZOS)
mk=Image.new("L",(130,130),0); ImageDraw.Draw(mk).ellipse([1,1,129,129],fill=255); lg.putalpha(mk)
d.ellipse([56,46,194,184],fill=WH); im.alpha_composite(lg,(60,50))
d.text((220,72),"OZOD JAMOL",font=f(FB,46),fill=WH); d.text((220,128),"ДИЗАЙН",font=f(FB,46),fill=RED)
y=240
for t,c in (("УСТАЛАР,",WH),("СИЗГА МИЖОЗ",YL),("ТОПИБ БЕРАМИЗ",YL)):
    d.text((60,y),t,font=f(FB,96),fill=c); y+=110
trades=["САНТЕХНИК","ЭЛЕКТРИК","ПАРДОЗЧИ","ПЛИТКАЧИ","СУВОҚЧИ","БЎЁҚЧИ","МЕБЕЛЧИ","ЭШИК-ДЕРАЗА"]
ft=f(FX,38); x,y=60,y+26
for t in trades:
    w=d.textlength(t,font=ft)+56
    if x+w>W-60: x=60; y+=84
    d.rounded_rectangle([x,y,x+w,y+70],35,fill=DK,outline=RED,width=4); d.text((x+28,y+12),t,font=ft,fill=WH); x+=w+14
y+=110
for big,small in (("15 КУН — БЕПУЛ","буюртмалар тўғридан-тўғри сизга"),("10% — СИЗНИКИ","ҳаволангиз орқали келган мижоздан")):
    d.rounded_rectangle([60,y,W-60,y+130],28,fill=(229,59,50,255))
    d.text((96,y+18),big,font=f(FB,52),fill=WH); d.text((96,y+82),small,font=f(FX,30),fill=(255,225,220)); y+=148
t="@ozodjamoldizaynbot"; ff=f(FB,46); tw=d.textlength(t,font=ff)
d.rounded_rectangle([(W-tw)/2-40,H-112,(W+tw)/2+40,H-36],38,fill=WH); d.text(((W-tw)/2,H-103),t,font=ff,fill=(10,10,12))
print("blocks end",y-18,"pill top",H-112)
im.convert("RGB").save("usta_post.jpg",quality=93)
