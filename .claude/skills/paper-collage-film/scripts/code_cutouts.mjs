// Вырезки КОДОМ (без платной генерации): страница <project>/comp/cutouts_code.html задаёт window.__CUTS = { name: async () => canvas }.
// Скрипт открывает её в headless Chromium, обрезает прозрачные поля и пишет <project>/cutouts/<name>.png (+ cutouts.txt).
// usage: node tools/code_cutouts.mjs <project> [--page other.html] [--out dir] [name ...]
import { spawn } from 'node:child_process'; import { existsSync, readdirSync, writeFileSync, mkdirSync } from 'node:fs'; import { resolve, join } from 'node:path';
const lin = (() => { try { return readdirSync('/opt/pw-browsers').filter((d) => d.startsWith('chromium-')).map((d) => `/opt/pw-browsers/${d}/chrome-linux/chrome`); } catch { return []; } })();
const B = process.env.HFT_BROWSER || ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser', ...lin, '/usr/bin/chromium', '/usr/bin/google-chrome'].find(existsSync);
const argv = process.argv.slice(2), pi = argv.indexOf('--page'), PAGE = pi >= 0 ? argv.splice(pi, 2)[1] : 'cutouts_code.html', oi = argv.indexOf('--out'), OUTD = oi >= 0 ? argv.splice(oi, 2)[1] : 'cutouts';
const [proj, ...only] = argv; const P = resolve(proj); const PORT = 9700 + Math.floor(Math.random() * 200);
const proc = spawn(B, ['--headless=new', ...(process.platform === 'linux' ? ['--no-sandbox', '--disable-dev-shm-usage'] : []), '--no-first-run', '--disable-extensions', '--allow-file-access-from-files', '--force-color-profile=srgb', `--remote-debugging-port=${PORT}`, `--user-data-dir=/tmp/cc-${PORT}-${Date.now()}`, 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms)); let ws;
for (let i = 0; i < 80 && !ws; i++) { try { const l = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json(); const u = l.find((t) => t.type === 'page')?.webSocketDebuggerUrl; if (u) ws = new WebSocket(u); } catch {} if (!ws) await sleep(250); }
await new Promise((r) => ws.addEventListener('open', r, { once: true }));
let id = 0; const pend = new Map(); let pageErr = '';
ws.addEventListener('message', (e) => { const m = JSON.parse(e.data); if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); } else if (m.method === 'Runtime.exceptionThrown') pageErr = JSON.stringify(m.params.exceptionDetails).slice(0, 800); });
const send = (method, params = {}) => new Promise((res) => { const i = ++id; pend.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (x) => { const r = await send('Runtime.evaluate', { expression: x, returnByValue: true, awaitPromise: true }); if (r.result?.exceptionDetails) throw new Error(JSON.stringify(r.result.exceptionDetails).slice(0, 800)); return r.result?.result?.value; };
await send('Runtime.enable'); await send('Page.enable');
await send('Page.navigate', { url: 'file://' + join(P, 'comp', PAGE) });
for (let i = 0; i < 100; i++) { await sleep(200); if (pageErr) break; if (await ev('!!(window.__CUTS && document.readyState === "complete")')) break; }
if (pageErr) { console.error('PAGE ERROR', pageErr); proc.kill(); process.exit(1); }
await ev('document.fonts.ready.then(() => 1)');
const names = only.length ? only : await ev('Object.keys(window.__CUTS)');
mkdirSync(join(P, OUTD), { recursive: true }); const list = [];
for (const n of names) {
  const r = await ev(`(async () => { const c = await window.__CUTS[${JSON.stringify(n)}](); const x = c.getContext('2d'), d = x.getImageData(0, 0, c.width, c.height).data; let x0 = c.width, y0 = c.height, x1 = 0, y1 = 0;
    for (let y = 0; y < c.height; y++) for (let xx = 0; xx < c.width; xx++) if (d[(y * c.width + xx) * 4 + 3] > 6) { if (xx < x0) x0 = xx; if (xx > x1) x1 = xx; if (y < y0) y0 = y; if (y > y1) y1 = y; }
    const p = 6; x0 = Math.max(0, x0 - p); y0 = Math.max(0, y0 - p); x1 = Math.min(c.width - 1, x1 + p); y1 = Math.min(c.height - 1, y1 + p);
    const o = document.createElement('canvas'); o.width = x1 - x0 + 1; o.height = y1 - y0 + 1; o.getContext('2d').drawImage(c, -x0, -y0);
    return { w: o.width, h: o.height, url: o.toDataURL('image/png'), ox: x0, oy: y0 }; })()`);
  writeFileSync(join(P, OUTD, n + '.png'), Buffer.from(r.url.split(',')[1], 'base64')); list.push(`${n} ${r.w} ${r.h} (crop ${r.ox},${r.oy})`); console.log(n, r.w + '×' + r.h, 'crop', r.ox, r.oy);
}
writeFileSync(join(P, OUTD, (PAGE === 'cutouts_code.html' ? 'cutouts' : 'frames') + '.txt'), list.join('\n') + '\n'); ws.close(); proc.kill(); process.exit(0);
