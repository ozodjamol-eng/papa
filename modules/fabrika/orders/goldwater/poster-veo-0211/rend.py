import sys, subprocess
from playwright.sync_api import sync_playwright
v, mode, out = sys.argv[1:4]
DUR = float(sys.argv[4]) if len(sys.argv) > 4 else 11.0
FPS = 60
with sync_playwright() as pw:
    b = pw.chromium.launch(args=['--allow-file-access-from-files'])
    pg = b.new_page(viewport={'width': 1080, 'height': 1920})
    pg.goto(f'file:///home/claude/shm/gw/gw.html?v={v}')
    pg.evaluate('window.ready')
    if mode == 'stills':
        for t in [float(s) for s in out.split(',')]:
            pg.evaluate(f'render({t})'); pg.screenshot(path=f'/home/claude/shm/gw/st_{v}_{t:05.2f}.png')
    else:
        ff = subprocess.Popen(['ffmpeg','-v','error','-y','-f','image2pipe','-framerate',str(FPS),'-c:v','png','-i','-',
              '-c:v','libx264','-preset','veryfast','-crf','16','-pix_fmt','yuv420p',out], stdin=subprocess.PIPE)
        for i in range(int(DUR*FPS)):
            pg.evaluate(f'render({i/FPS})'); ff.stdin.write(pg.screenshot(type='png'))
        ff.stdin.close(); ff.wait()
    b.close()
