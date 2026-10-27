// Рендер «дайжеста» кадр за кадром: фон (кадры JPEG) + стеклянные плитки (page.html) → MP4 без звука.
// node render.mjs page.html data.json frames_dir fps out.mp4  [stills: "t1,t2" вместо fps → JPEG в out-папку]
import { chromium } from 'playwright';
import { spawn } from 'child_process';
import fs from 'fs';
const [,, html, json, frames, arg, out] = process.argv;
const b = await chromium.launch({ args: ['--allow-file-access-from-files'] });
const pg = await b.newPage({ viewport: { width: 1080, height: 1920 } });
const data = fs.readFileSync(json, 'utf8');
await pg.addInitScript(d => { window.DAYJEST = JSON.parse(d); }, data);
await pg.goto('file://' + html); await pg.evaluate(() => window.ready);
const nf = fs.readdirSync(frames).filter(f => f.endsWith('.jpg')).length;
const bg = i => `file://${frames}/${String(Math.min(nf, i + 1)).padStart(4, '0')}.jpg`;
const fr = async (t, i) => pg.evaluate(async ([t, s]) => { await window.setBg(s); window.renderAt(t); }, [t, bg(i)]);
if (arg.includes(',') || arg.includes('.')) {
  fs.mkdirSync(out, { recursive: true });
  for (const t of arg.split(',').map(Number)) { await fr(t, Math.round(t * 30)); await pg.screenshot({ path: `${out}/s_${t}.jpg`, type: 'jpeg', quality: 85 }); }
} else {
  const fps = Number(arg), dur = await pg.evaluate(() => window.DUR), n = Math.round(dur * fps);
  const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-i', '-', '-c:v', 'libx264', '-preset', 'medium',
    '-crf', '19', '-pix_fmt', 'yuv420p', '-r', String(fps), out], { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let i = 0; i < n; i++) {
    await fr(i / fps, i);
    const buf = await pg.screenshot({ type: 'jpeg', quality: 92 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 150 === 0) console.log('frame', i, '/', n);
  }
  ff.stdin.end(); await new Promise(r => ff.on('close', r));
  console.log('DUR', dur);
}
await b.close();
