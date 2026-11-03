import { createRequire } from 'module'; const require = createRequire(import.meta.url); const { chromium } = require('playwright');
import { spawn } from 'child_process';
import fs from 'fs';
const [,, html, arg, out] = process.argv;
const b = await chromium.launch({ args: ['--allow-file-access-from-files'] });
const pg = await b.newPage({ viewport: { width: 1080, height: 1920 } });
await pg.goto('file://' + html); await pg.evaluate(() => window.ready);
if (arg.includes(',')) {
  fs.mkdirSync(out, { recursive: true });
  for (const t of arg.split(',').map(Number)) { await pg.evaluate(t => window.renderAt(t), t); await pg.screenshot({ path: `${out}/s_${String(t).padStart(5,'0')}.jpg`, type: 'jpeg', quality: 80 }); }
} else {
  const fps = Number(arg), dur = await pg.evaluate(() => window.DUR), n = Math.round(dur * fps);
  const ff = spawn('ffmpeg', ['-y','-v','error','-f','image2pipe','-framerate',String(fps),'-i','-','-c:v','libx264','-preset','medium','-crf','17','-pix_fmt','yuv420p','-r',String(fps),out], { stdio: ['pipe','inherit','inherit'] });
  for (let i = 0; i < n; i++) {
    await pg.evaluate(t => window.renderAt(t), i / fps);
    const buf = await pg.screenshot({ type: 'jpeg', quality: 93 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 120 === 0) console.log('frame', i, '/', n);
  }
  ff.stdin.end(); await new Promise(r => ff.on('close', r));
}
await b.close();
