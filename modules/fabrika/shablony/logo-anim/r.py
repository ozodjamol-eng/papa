import sys, subprocess
from playwright.sync_api import sync_playwright
html,mode=sys.argv[1],sys.argv[2]; FPS=30
with sync_playwright() as pw:
    b=pw.chromium.launch(args=['--allow-file-access-from-files']); pg=b.new_page(viewport={'width':1080,'height':1920})
    pg.on('pageerror',lambda e:print('ERR',e)); pg.goto(f'file:///home/claude/la/{html}'); pg.evaluate('window.ready')
    if mode=='stills':
        for t in [float(s) for s in sys.argv[3].split(',')]:
            pg.evaluate(f'render({t})'); pg.screenshot(path=f'/tmp/la_{html[:-5]}_{t:05.2f}.png')
    else:
        dur,out=float(sys.argv[3]),sys.argv[4]
        ff=subprocess.Popen(['ffmpeg','-v','error','-y','-f','image2pipe','-framerate',str(FPS),'-c:v','png','-i','-','-c:v','libx264','-preset','veryfast','-crf','15','-pix_fmt','yuv420p',out],stdin=subprocess.PIPE)
        for i in range(int(dur*FPS)):
            pg.evaluate(f'render({i/FPS})'); ff.stdin.write(pg.screenshot(type='png'))
        ff.stdin.close(); ff.wait()
    b.close()
