import sys, subprocess
from playwright.sync_api import sync_playwright
mode=sys.argv[1]; FPS=30; DUR=26.0
with sync_playwright() as pw:
    b=pw.chromium.launch(args=['--allow-file-access-from-files']); pg=b.new_page(viewport={'width':1080,'height':1920})
    pg.on('pageerror',lambda e:print('ERR',e)); pg.goto('file:///home/claude/oj/promo.html'); pg.evaluate('window.ready')
    if mode=='stills':
        for t in [float(s) for s in sys.argv[2].split(',')]:
            pg.evaluate(f'render({t})'); pg.screenshot(path=f'/tmp/oj_{t:05.2f}.png')
    else:
        a,bnd,out=float(sys.argv[2]),float(sys.argv[3]),sys.argv[4]
        ff=subprocess.Popen(['ffmpeg','-v','error','-y','-f','image2pipe','-framerate',str(FPS),'-c:v','png','-i','-','-c:v','libx264','-preset','veryfast','-crf','16','-pix_fmt','yuv420p',out],stdin=subprocess.PIPE)
        i=int(a*FPS)
        while i<int(bnd*FPS):
            pg.evaluate(f'render({i/FPS})'); ff.stdin.write(pg.screenshot(type='png')); i+=1
        ff.stdin.close(); ff.wait()
    b.close()
