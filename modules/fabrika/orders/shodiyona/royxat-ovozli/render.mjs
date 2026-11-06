// node render.mjs <index.html> <fps|t1,t2,...> <out.mp4|dir>
import { createRequire } from 'module'; const require = createRequire(import.meta.url); const { chromium } = require('playwright');
import { spawn } from 'child_process'; import fs from 'fs';
const [,, html, arg, out] = process.argv;
const b = await chromium.launch({ args: ['--allow-file-access-from-files'] });
const pg = await b.newPage({ viewport: { width: 1080, height: 1920 } });
pg.on('pageerror', e => console.log('ERR', e.message));
await pg.goto('file://' + html); await pg.waitForFunction(() => window.__seek && window.__comp);
const shot = async () => Buffer.from((await pg.evaluate(() => document.getElementById('c').toDataURL('image/jpeg', 0.95))).split(',')[1], 'base64');
if (arg.includes(',')) { fs.mkdirSync(out, { recursive: true });
  for (const t of arg.split(',').map(Number)) { await pg.evaluate(t => window.__seek(t), t); fs.writeFileSync(`${out}/s_${t.toFixed(2).padStart(6, '0')}.jpg`, await shot()); }
} else { const fps = Number(arg), dur = await pg.evaluate(() => window.__comp.duration), n = Math.round(dur * fps);
  const ff = spawn('ffmpeg', ['-y','-v','error','-f','image2pipe','-framerate',String(fps),'-i','-','-c:v','libx264','-preset','medium','-crf','16','-pix_fmt','yuv420p','-r',String(fps),out], { stdio: ['pipe','inherit','inherit'] });
  for (let i = 0; i < n; i++) { await pg.evaluate(t => window.__seek(t), i / fps); const buf = await shot(); if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r)); if (i % 300 === 0) console.log('frame', i, '/', n); }
  ff.stdin.end(); await new Promise(r => ff.on('close', r)); }
await b.close();
