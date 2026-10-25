import sys, subprocess, time
from playwright.sync_api import sync_playwright
lang = sys.argv[1]
mode = sys.argv[2]  # 'stills' or 'video'
DUR, FPS = 11.0, 60
with sync_playwright() as pw:
    b = pw.chromium.launch(args=['--allow-file-access-from-files'])
    pg = b.new_page(viewport={'width': 1080, 'height': 1920}, device_scale_factor=1)
    pg.goto(f'file:///home/claude/shm/poster.html?v={lang}')
    pg.evaluate('window.ready')
    if mode == 'stills':
        ts = [float(v) for v in sys.argv[3].split(',')]
        for t in ts:
            pg.evaluate(f'render({t})')
            pg.screenshot(path=f'/home/claude/shm/st_{lang}_{t:05.2f}.png')
    else:
        out = sys.argv[3]
        ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'image2pipe', '-framerate', str(FPS), '-c:v', 'png', '-i', '-',
                               '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '16', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
        t0 = time.time()
        for i in range(int(DUR * FPS)):
            pg.evaluate(f'render({i / FPS})')
            ff.stdin.write(pg.screenshot(type='png'))
        ff.stdin.close(); ff.wait()
        print('done', time.time() - t0)
    b.close()
