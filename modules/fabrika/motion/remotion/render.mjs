// Рендер «Кечки дайжест» через Remotion: node render.mjs data.json out.mp4
// Видео (Remotion) + звук (audio.py, по тому же таймлайну) → MP4 1080×1920, 60 fps.
import {bundle} from '@remotion/bundler';
import {renderMedia, selectComposition} from '@remotion/renderer';
import {execFileSync} from 'child_process';
import fs from 'fs';
import path from 'path';
import {fileURLToPath} from 'url';
import {timeline} from './src/scene.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const [, , dataPath, out] = process.argv;
const data = JSON.parse(fs.readFileSync(dataPath, 'utf8'));
const tl = timeline(data);
const tmp = fs.mkdtempSync(path.join(path.dirname(path.resolve(out)), '.dg-'));
const raw = path.join(tmp, 'raw.mp4'), wav = path.join(tmp, 'a.wav');

execFileSync('python3', [path.join(HERE, 'audio.py'), wav, JSON.stringify(tl)], {stdio: 'inherit'});
const serveUrl = await bundle({entryPoint: path.join(HERE, 'src/index.jsx'), publicDir: path.join(HERE, '../weather/fonts')});
const inputProps = {data};
const browserExecutable = process.env.CHROME_PATH || null;
const composition = await selectComposition({serveUrl, id: 'Digest', inputProps, browserExecutable});
let last = -1;
await renderMedia({composition, serveUrl, codec: 'h264', crf: 18, x264Preset: 'medium', pixelFormat: 'yuv420p',
  outputLocation: raw, inputProps, browserExecutable, concurrency: Number(process.env.CONCURRENCY || 2),
  chromiumOptions: process.env.GL ? {gl: process.env.GL} : {},  // swangle на CPU в 16 раз медленнее
  onProgress: ({progress}) => { const p = Math.floor(progress * 10); if (p !== last) { last = p; console.log(`рендер ${p * 10}%`); } }});
execFileSync('ffmpeg', ['-v', 'error', '-y', '-i', raw, '-i', wav, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
  '-shortest', '-movflags', '+faststart', out], {stdio: 'inherit'});
fs.rmSync(tmp, {recursive: true, force: true});
console.log('готово', out, `${tl.DUR.toFixed(1)} с`);
