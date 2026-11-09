// Рендер болванки: node render.js <scene> <out.mp4> [w h fps] [--sheet t1,t2,...]
const http = require('http'), fs = require('fs'), path = require('path'), { spawn } = require('child_process');
const { chromium } = require('playwright');
const ROOT = __dirname, THREE_DIR = path.join(ROOT, 'node_modules', 'three');
const [scene, out, W = 720, H = 1280, FPS = 30] = process.argv.slice(2).filter((a) => !a.startsWith('--'));
const sheetArg = process.argv.find((a) => a.startsWith('--sheet='));
const mime = { '.js': 'text/javascript', '.html': 'text/html' };
const srv = http.createServer((req, res) => {
  const u = decodeURIComponent(req.url.split('?')[0]);
  const f = u.startsWith('/three/') ? path.join(THREE_DIR, u.slice(7)) : path.join(ROOT, u === '/' ? 'index.html' : u);
  fs.readFile(f, (e, d) => { if (e) { res.writeHead(404); return res.end(); } res.writeHead(200, { 'Content-Type': mime[path.extname(f)] || 'application/octet-stream' }); res.end(d); });
}).listen(0, async () => {
  const port = srv.address().port;
  const b = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const pg = await b.newPage({ viewport: { width: +W, height: +H } });
  pg.on('console', (m) => { if (m.type() === 'error') console.error('PAGE:', m.text()); });
  pg.on('pageerror', (e) => console.error('PAGEERR:', e.message));
  await pg.goto(`http://localhost:${port}/?scene=${scene}&w=${W}&h=${H}`);
  await pg.waitForFunction('window.READY === true', null, { timeout: 60000 });
  const dur = await pg.evaluate('window.DURATION');
  if (sheetArg) {
    const ts = sheetArg.split('=')[1].split(',').map(Number);
    for (const t of ts) {
      const d = await pg.evaluate((t) => window.renderFrame(t), t);
      fs.writeFileSync(`${out}_${t.toFixed(2)}.jpg`, Buffer.from(d.split(',')[1], 'base64'));
    }
  } else {
    const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p', out], { stdio: ['pipe', 'inherit', 'inherit'] });
    const n = Math.round(dur * FPS);
    for (let i = 0; i < n; i++) {
      const d = await pg.evaluate((t) => window.renderFrame(t), i / FPS);
      ff.stdin.write(Buffer.from(d.split(',')[1], 'base64'));
    }
    ff.stdin.end(); await new Promise((r) => ff.on('close', r));
  }
  await b.close(); srv.close();
  console.log('done');
});
