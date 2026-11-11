// Рендер «Домино»: node render.js <out.mp4|out_prefix> [w h fps] [--sheet=t1,t2]
import http from 'http'; import fs from 'fs'; import path from 'path'; import { spawn } from 'child_process';
import { chromium } from '/opt/npm-tools/node_modules/playwright/index.mjs';
const ROOT = path.dirname(new URL(import.meta.url).pathname), AUD = process.env.AUD || '/home/claude/dom/a';
const [out, W = 1080, H = 1920, FPS = 30] = process.argv.slice(2).filter((a) => !a.startsWith('--'));
const sheetArg = process.argv.find((a) => a.startsWith('--sheet='));
const mime = { '.js': 'text/javascript', '.mjs': 'text/javascript', '.html': 'text/html', '.json': 'application/json', '.wasm': 'application/wasm', '.ttf': 'font/ttf' };
const srv = http.createServer((req, res) => {
  const u = decodeURIComponent(req.url.split('?')[0]);
  const f = u.startsWith('/a/') ? path.join(AUD, u.slice(3)) : path.join(ROOT, u === '/' ? 'index.html' : u);
  fs.readFile(f, (e, d) => { if (e) { res.writeHead(404); return res.end(); } res.writeHead(200, { 'Content-Type': mime[path.extname(f)] || 'application/octet-stream' }); res.end(d); });
}).listen(0, async () => {
  const b = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const pg = await b.newPage({ viewport: { width: +W, height: +H } });
  pg.on('console', (m) => console.log('PAGE:', m.text()));
  pg.on('pageerror', (e) => console.error('PAGEERR:', e.message));
  await pg.goto(`http://localhost:${srv.address().port}/?w=${W}&h=${H}`);
  await pg.waitForFunction('window.READY === true', null, { timeout: 300000 });
  if (process.env.DBG) console.log(await pg.evaluate('window.BITMAP'), '\n', await pg.evaluate('window.VO'));
  const dur = await pg.evaluate('window.DURATION');
  const t0 = Date.now();
  if (sheetArg) {
    for (const t of sheetArg.split('=')[1].split(',').map(Number)) {
      const d = await pg.evaluate((t) => window.renderFrame(t), t);
      fs.writeFileSync(`${out}_${t.toFixed(2)}.jpg`, Buffer.from(d.split(',')[1], 'base64'));
    }
  } else {
    const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-pix_fmt', 'yuv420p', out], { stdio: ['pipe', 'inherit', 'inherit'] });
    const n = Math.round(dur * FPS);
    for (let i = 0; i < n; i++) {
      const d = await pg.evaluate((t) => window.renderFrame(t), i / FPS);
      ff.stdin.write(Buffer.from(d.split(',')[1], 'base64'));
      if (i % 60 === 0) console.log('frame', i, '/', n, ((Date.now() - t0) / 1000).toFixed(0) + 's');
    }
    ff.stdin.end(); await new Promise((r) => ff.on('close', r));
  }
  console.log('done', ((Date.now() - t0) / 1000).toFixed(0) + 's');
  await b.close(); srv.close();
});
