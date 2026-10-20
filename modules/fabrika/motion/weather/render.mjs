import { chromium } from 'playwright';
import { spawn } from 'child_process';
const [,, html, mode, arg, out] = process.argv; // mode: frames "0,3,6" outdir | video fps out.mp4
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args:['--allow-file-access-from-files'] });
const pg = await b.newPage({ viewport: { width: 1080, height: 1920 } });
await pg.goto('file://' + html); await pg.evaluate(() => window.ready);
if (mode === 'frames') {
  for (const t of arg.split(',').map(Number)) {
    await pg.evaluate(t => window.renderAt(t), t);
    await pg.screenshot({ path: `${out}/f_${String(t).padStart(5,'0')}.jpg`, type: 'jpeg', quality: 85 });
  }
} else {
  const fps = Number(arg), dur = 15, n = Math.round(dur * fps);
  const ff = spawn('ffmpeg', ['-y','-v','error','-f','image2pipe','-framerate',String(fps),'-i','-','-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-r',String(fps),out], { stdio: ['pipe','inherit','inherit'] });
  for (let i = 0; i < n; i++) {
    const img = await pg.evaluate(([t, dt]) => window.renderAt(t), [i / fps, 1/fps]);
    const buf = await pg.screenshot({ type: 'jpeg', quality: 92 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 120 === 0) console.log('frame', i, '/', n);
  }
  ff.stdin.end(); await new Promise(r => ff.on('close', r));
}
await b.close();
