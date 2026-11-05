import { chromium } from 'playwright-core';
import { spawn } from 'child_process'; import fs from 'fs'; import http from 'http'; import path from 'path';
const [,, page, arg, out] = process.argv; const ROOT = process.cwd();
const types = {'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.png':'image/png','.jpg':'image/jpeg','.ttf':'font/ttf','.json':'application/json','.woff2':'font/woff2'};
const srv = http.createServer((q, s) => { const f = path.join(ROOT, decodeURIComponent(q.url.split('?')[0])); if (!fs.existsSync(f)) { s.writeHead(404); return s.end(); } s.writeHead(200, {'content-type': types[path.extname(f)] || 'application/octet-stream'}); fs.createReadStream(f).pipe(s); }).listen(0);
await new Promise(r => srv.once('listening', r)); const port = srv.address().port;
const b = await chromium.launch({ executablePath: '/usr/bin/google-chrome', args: ['--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'] });
const pg = await b.newPage({ viewport: { width: 1080, height: 1920 } });
pg.on('console', m => console.log('PAGE', m.text())); pg.on('pageerror', e => console.log('ERR', e.message));
await pg.goto(`http://localhost:${port}/${page}`); await pg.waitForFunction(() => window.ready === true, null, {timeout: 120000});
if (arg.includes(',') || !arg.includes('fps')) {
  fs.mkdirSync(out, { recursive: true });
  for (const t of arg.split(',').map(Number)) { const t0 = Date.now(); await pg.evaluate(t => window.renderAt(t), t); await pg.screenshot({ path: `${out}/s_${t.toFixed(2).padStart(6,'0')}.jpg`, type: 'jpeg', quality: 85, timeout: 0 }); console.log('t', t, Date.now() - t0, 'ms'); }
} else {
  const fps = Number(arg.replace('fps','')); const [a, z] = (process.env.RANGE || '').split(':').map(Number);
  const dur = await pg.evaluate(() => window.DUR); const n0 = Math.round((a || 0) * fps), n1 = Math.round((z || dur) * fps);
  const ff = spawn('ffmpeg', ['-y','-v','error','-f','image2pipe','-framerate',String(fps),'-i','-','-c:v','libx264','-preset','medium','-crf','16','-pix_fmt','yuv420p',out], { stdio: ['pipe','inherit','inherit'] });
  const T0 = Date.now();
  for (let i = n0; i < n1; i++) { await pg.evaluate(t => window.renderAt(t), i / fps); const buf = await pg.screenshot({ type: 'jpeg', quality: 94, timeout: 0 }); if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r)); if (i % 30 === 0) console.log('frame', i, '/', n1, ((Date.now()-T0)/1000).toFixed(0)+'s'); }
  ff.stdin.end(); await new Promise(r => ff.on('close', r));
}
await b.close(); srv.close();
