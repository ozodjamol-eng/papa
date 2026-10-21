/* scenes.js — КАТТА ДАВРА · интро 6 с (1920×1080, 24 fps, 120 BPM). Коллаж из рваной бумаги (техника San Diego Zoo), всё кодом, вырезки тоже кодом (comp/cutouts_code.html).
 * Рецепт «6 s intro» из SKILL.md:
 *   0.33–0.5 дойра падает (3 рисунка) · 0.5 тег · 0.58–0.83 всплывают микрофон / лампочка / ноты / смайл · 0.75–1.46 влёт в кожу дойры, ирис 1.0–1.42 (в центре — калейдоскоп)
 *   1.5–2.5 калейдоскоп (кольцо нот + кольцо смайлов), пролёты 2.2 / 2.3 / 2.4, шестиугольная дыра 2.33–2.5 · 2.5–2.92 полосы-ракета уносят самолётик
 *   3.0 «КАТТА / ДАВРА» (expo-out 9 рисунков, сел к 3.75) + взрыв полос · 3.3–4.4 самолётик пролетает · 4.5–4.92 разрыв страницы → лента с @kattadavrauz
 *   5.0–5.5 мерцание ТОЛЬКО внутри ленты (2-1-2-3-2-2 кадра) · 5.5 финальный удар · держим до 6.0
 * Время калейдоскопа = время фильма + 2.0 (KT), чтобы взять выверенную геометрию колец/пролётов/дыры из 10-секундного примера.
 */
(function () {
  'use strict';
  const { W, H, clamp, lerp, prog, E } = ENG;
  const K = KIT, X = CLX, U = CLX._, C = CL.C, DEG = Math.PI / 180;

  /* ---------- copy: каждое слово на экране — здесь (узбекская кириллица) ---------- */
  const COPY = {
    pageTag: 'БУТУН ЎЗБЕКИСТОН УЧУН',
    title: ['КАТТА', 'ДАВРА'], titleFont: '"Unbounded 900"',
    logo: '@kattadavrauz',
    bandTag: 'КЎНГИЛОЧАР · ФОЙДАЛИ',
    tgTag: 'ТЕЛЕГРАМ КАНАЛ',
  };
  const FLICK = ['pink', 'orange', 'lime', 'posters', 'streak', 'glitter'];
  const FLICK_FR = [0, 0, 1, 2, 2, 3, 3, 3, 4, 4, 5, 5];
  K.setup({ bars: [0.5, 1.5, 3.0, 4.5, 5.5] });

  /* ---------- helpers ---------- */
  const q = (t) => Math.floor(t * 12 + 1e-6) / 12;
  const drawingIdx = (t, t0) => Math.floor((t - t0) * 12 + 1e-6);
  const BUFS = new Map();
  function buf(name, w = W, h = H) {
    let c = BUFS.get(name); if (!c) { c = document.createElement('canvas'); c.width = w; c.height = h; BUFS.set(name, c); }
    const x = c.getContext('2d'); x.setTransform(1, 0, 0, 1, 0, 0); x.globalAlpha = 1; x.globalCompositeOperation = 'source-over'; x.filter = 'none'; x.clearRect(0, 0, c.width, c.height);
    return c;
  }
  const ONCE = new Map(); const once = (k, fn) => { if (!ONCE.has(k)) ONCE.set(k, fn()); return ONCE.get(k); };
  const mkc = (w, h) => { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; };
  const pc = (x, shape, fill, o) => CL.piece(x, shape, fill, Object.assign({ cache: false }, o));
  async function zoomAbout(ctx, z, fx, fy, fn) { ctx.save(); ctx.translate(fx, fy); ctx.scale(z, z); ctx.translate(-fx, -fy); await fn(); ctx.restore(); }

  /* ---------- warm-up ---------- */
  const TEAR = { y0: Math.round(H * 0.3), y1: Math.round(H * 0.7), seed: 5, flapW: 360 };
  const LOGO = { x: W / 2, y: Math.round((TEAR.y0 + TEAR.y1) / 2), h: 330, size: 170 };
  const TTL = { size: 0, off: 0 };
  let WARM = null;
  const warm = () => WARM || (WARM = (async () => {
    await CL.preload(['doira', 'mic', 'bulb', 'note', 'smile', 'plane', 'dome']);
    const m = mkc(8, 8).getContext('2d'); m.font = `400 100px ${COPY.titleFont}`;
    const tw = Math.max(...COPY.title.map((s) => [...s].reduce((a, c) => a + m.measureText(c).width, 0)));
    TTL.size = 100 * (W * 0.56) / Math.max(1, tw);
    await X.warm({ iris: 6, kaleido: 8, title: { lines: COPY.title, size: TTL.size, font: COPY.titleFont }, band: { h: LOGO.h, seed: 8 }, logo: { text: COPY.logo, size: LOGO.size }, tear: TEAR,
      cuts: ['doira', 'mic', 'bulb', 'note', 'smile', 'plane'] });
    const P = U.titleSprite(COPY.title, TTL.size, { font: COPY.titleFont }); TTL.off = P.bottom - P.ay;
  })());

  /* ======================================================================= 0–1.5 · СТРАНИЦА + ДОЙРА → влёт */
  const D = { x: 960, y: 548, h: 640 };
  const dS = D.h / 1110, SKIN = { x: D.x + (557 - 554) * dS, y: D.y + (558 - 555) * dS, r: 410 * dS };
  const pageLayer = () => CL.layer('kd_page', async (x) => {
    const B = 380;
    x.drawImage(CL.watercolor(33, { w: W + 2 * B, h: H + 2 * B, tone: 0.86, dots: 0.5, bloom: 0.7, clouds: 0.35, cloudY: [0.05, 0.35] }), -B, -B);
    await pc(x, { band: [-200, 120, 760, -60, 150, 110] }, { color: C.cobalt }, { seed: 501, amp: 12, halftone: { color: '#0B3A92', cell: 18, angle: 20, r: [0.06, 0.42], grad: [-200, 120, 760, -60] } });
    await pc(x, { band: [1180, -40, 2120, 210, 120, 90] }, { color: C.pink, brush: 0.4 }, { seed: 502, amp: 10, halftone: { color: 'rgba(229,35,30,0.7)', cell: 14, angle: 30, r: [0.04, 0.38], grad: [1180, 0, 2120, 0] } });
    await pc(x, { band: [1380, 210, 2120, 300, 54, 38] }, C.paper, { seed: 503, amp: 6, news: { alpha: 0.5, angle: -5 } });
    await pc(x, { circle: [D.x, D.y + 10, 520] }, { color: C.sun, brush: 0.6 }, { seed: 504, amp: 12, halftone: { color: 'rgba(240,122,46,0.9)', cell: 17, angle: 30, r: [0.42, 0.03], grad: [D.x, D.y + 520, D.x, D.y - 520] } });
    await pc(x, { circle: [D.x, D.y + 10, 420] }, C.paper, { seed: 505, amp: 10, dotgrid: { cell: 20, r: 0.09, angle: 12 } });
    await CL.sprite(x, 'dome', 250, 1110, { h: 640, ay: 1, rot: -3, shadow: { dx: 10, dy: 14, blur: 16, alpha: 0.4 } });
    await CL.sprite(x, 'dome', 1690, 1120, { h: 540, ay: 1, rot: 4, flipX: true, shadow: { dx: -10, dy: 14, blur: 16, alpha: 0.4 } });
    await pc(x, { band: [-200, 1010, 2120, 900, 210, 150] }, { color: C.red, speck: 0.3 }, { seed: 506, amp: 13, fx: [{ type: 'grunge', seed: 3 }] });
    await pc(x, { band: [-200, 940, 900, 990, 70, 50] }, { color: C.sun, brush: 0.6 }, { seed: 507, amp: 7 });
    await pc(x, { band: [1100, 1050, 2120, 980, 64, 44] }, C.paper, { seed: 508, amp: 7, news: { alpha: 0.5 } });
    await pc(x, { poly: [[150, 420], [380, 360], [300, 590]] }, C.teal, { seed: 509, amp: 6 });
    await pc(x, { star: [1770, 420, 70, 30, 5, -90] }, C.sun, { seed: 510, amp: 3 });
  }, { bleed: 380 });
  // всплывашки: [вырезка, x, y(низ), h, t0, rot]
  const POPS = [['mic', 330, 700, 430, 7 / 12, -10], ['bulb', 1610, 640, 420, 8 / 12, 8], ['note', 470, 360, 280, 9 / 12, -12], ['smile', 1470, 960, 270, 10 / 12, 9]];
  // дойра: 0.333 виден только нижний край · 0.417 в воздухе −8° · 0.5 приземлилась (1.035) · 0.583 стоит
  function doiraPose(t) {
    const i = drawingIdx(t, 1 / 3); if (i < 0) return null;
    if (i === 0) return { dy: -D.y - D.h * 0.5 + 110, rot: -3, s: 1 };
    if (i === 1) return { dy: 290 - D.y, rot: -8, s: 1 };
    return { dy: 0, rot: 0, s: i === 2 ? 1.035 : 1 };
  }
  async function pageWorld(ctx, t) {
    const tq = q(t), L = await pageLayer(); ctx.drawImage(L, -L.bleed, -L.bleed);
    for (const [n, x, y, h, t0, rot] of POPS) { const p = CL.pop(tq, t0, { h: h * 0.85, frames: 4 }); if (!p.on) continue; const b = CL.bob(t, x, 2.4);
      await CL.sprite(ctx, n, x + b.dx, y + p.dy + b.dy, { h, ay: 1, rot: rot + b.rot, sx: p.sx, sy: p.sy, shadow: { dx: 6, dy: 10, blur: 12, alpha: 0.35 } }); }
    const p = doiraPose(t); if (!p) return;
    if (tq >= 0.5 && tq < 0.5 + 2 / 12) await X.star(ctx, D.x, D.y, 420, t, { points: 16, inner: 0.66, color: X.PAL.yellow, seed: 3, pop: 1 }); // удар приземления
    await CL.sprite(ctx, 'doira', D.x, D.y + p.dy, { h: D.h * p.s, rot: p.rot, boil: 0.5, t, shadow: { dx: 14, dy: 22, blur: 22, alpha: 0.45 } });
  }
  const PUSH = [0.75, 1.46];
  async function pageScene(ctx, t) {
    const tq = q(t), pz = prog(tq, PUSH[0], PUSH[1]), e = pz * pz, z = (1 + 0.03 * Math.min(tq, 0.75)) * Math.pow(40, e), rS = SKIN.r * z;
    const covered = rS * 0.95 > Math.hypot(Math.max(SKIN.x, W - SKIN.x), Math.max(SKIN.y, H - SKIN.y)) + 40;
    if (!covered) await zoomAbout(ctx, z, SKIN.x, SKIN.y, () => pageWorld(ctx, t));
    if (tq >= 1.0) { // ирис выскакивает в коже дойры (2 рисунка), лепестки открываются 1.08–1.42; в центре уже крутится калейдоскоп
      const ki = prog(tq, 13 / 12, 1.42), pop = lerp(0.55, 1, clamp(drawingIdx(t, 1.0) / 2));
      await X.iris(ctx, SKIN.x, SKIN.y, rS * pop, ki, t, { n: 6, spin: 1.2, drawCenter: ki > 0.12 ? async (c, cx, cy, rr, tt) => {
        const kb = await kalBuf(tt), s = rr / (Math.hypot(W, H) / 2); c.drawImage(kb, cx - (KS / 2) * s, cy - (KS / 2) * s, KS * s, KS * s);
      } : null });
    }
    if (tq >= 0.5 && tq < 16 / 12) await X.tag(ctx, 92, 140, COPY.pageTag, { t: tq, t0: 0.5, color: 'white', font: 'sans', size: 44, anchor: 'left', rot: -0.03, tape: 'top' });
  }

  /* ======================================================================= 1.5–2.5 · КАЛЕЙДОСКОП (время KT = t + 2) */
  const KSRC = () => once('ksrc', async () => {
    const c = mkc(W, H), x = c.getContext('2d');
    x.drawImage(CL.watercolor(97, { w: W, h: H, tone: 0.95, bloom: 0.1, clouds: 0, base: '#2DB8EE', light: '#8ADAF5', deep: '#1186CC' }), 0, 0);
    const V = (x0, w0, w1, dx = 0) => ({ band: [x0, -40, x0 + dx, H + 40, w0, w1 ?? w0], tips: false });
    const BANDS = [['cob', 1030, 150], ['red', 1135, 64], ['yel', 1192, 56], ['tea', 1272, 110], ['pink', 1382, 124], ['cob', 1506, 128], ['red', 1600, 62], ['yel', 1658, 56], ['tea', 1742, 116], ['pink', 1866, 136]];
    let i = 0;
    for (const [k, cx, w] of BANDS) {
      const sh = { dx: 7, dy: 0, blur: 12, alpha: 0.35 }, seed = 960 + i++, dx = ((seed * 37) % 21) - 10, s = V(cx - dx / 2, w, w * (0.9 + (seed % 3) * 0.06), dx);
      const hg = (col) => ({ halftone: { color: col, cell: 12, angle: 25, r: [0.04, 0.4], grad: [cx - w / 2, 0, cx + w / 2, 0] } });
      if (k === 'cob') await CL.piece(x, s, { color: C.cobalt }, Object.assign({ seed, amp: 7, shadow: sh, cache: false }, hg('#0B3A92')));
      else if (k === 'red') await CL.piece(x, s, { color: C.red, speck: 0.3 }, Object.assign({ seed, amp: 6, shadow: sh, cache: false }, hg('#FBEFE4')));
      else if (k === 'yel') await CL.piece(x, s, { color: C.sun, brush: 0.6 }, Object.assign({ seed, amp: 6, shadow: sh, cache: false }, hg('rgba(240,122,46,0.8)')));
      else if (k === 'tea') await CL.piece(x, s, '#22A6C8', Object.assign({ seed, amp: 7, shadow: sh, cache: false }, hg('rgba(8,60,110,0.6)')));
      else await CL.piece(x, s, { color: C.pink, brush: 0.4 }, Object.assign({ seed, amp: 7, shadow: sh, cache: false, news: { alpha: 0.35 } }));
    }
    return c;
  });
  const KT = (t) => t + 2.0;
  const FLYERS = [{ name: 'mic', t0: 3.705, dur: 0.55, angle: 0.15, spin: 0.5, scale: 0.85 }, { name: 'bulb', t0: 3.805, dur: 0.55, angle: Math.PI - 0.2, spin: -0.8, scale: 0.85 },
    { name: 'plane', t0: 3.905, dur: 0.55, angle: 0.5, spin: 0.7, scale: 0.8 }];
  const HOLE = [[52 / 12, 0.34], [53 / 12, 0.85]];
  const holeAt = (kt) => { let h = 0; for (const [t0, v] of HOLE) if (kt >= t0 - 1e-6) h = v; return h; };
  const kOpts = (kt) => ({ segments: 8, rot: 0, twist: 0, zoom: 2.6, ratio: 0.5, levels: 7, srcScale: 1.2, rims: ['red', 'yellow', 'cyan', 'dots', 'red', 'yellow'], flyers: FLYERS, hole: holeAt(kt), drawNext: (c, tt) => titleBg(c, tt - 2.0), holeColor: '#F3A51C' });
  const KST = [['note', 10, 580, 0, 170, -90], ['smile', 11, 430, Math.PI / 8, 130, 90]];
  async function kalStickers(ctx, kt) {
    const c = kt * 2.6;
    for (const [n, m, d, a0, h, rot] of KST) {
      const k = 1.2 * Math.pow(0.5, m - c), R = d * k; if (R < 12 || (d - h) * k > 1160) continue;
      for (let i = 0; i < 8; i++) { ctx.save(); ctx.translate(W / 2, H / 2); ctx.rotate(i * Math.PI / 4 + a0); if (i % 2) ctx.scale(1, -1);
        await CL.sprite(ctx, n, R, 0, { h: h * k, rot, shadow: { dx: 5 * k, dy: 8 * k, blur: 9 * k, alpha: 0.4 } }); ctx.restore(); }
    }
  }
  const kalDraw = async (ctx, t) => {
    const kt = KT(q(t)), src = await KSRC(), o = kOpts(kt);
    await X.kaleido(ctx, kt, async (c) => c.drawImage(src, 0, 0), Object.assign({}, o, { hole: 0, flyers: [] }));
    await kalStickers(ctx, kt);
    if (o.hole > 0 || FLYERS.some((f) => kt > f.t0 && kt < f.t0 + f.dur)) await X.kaleido(ctx, kt, async () => {}, Object.assign({}, o, { levels: -1 }));
  };
  const KS = Math.ceil(Math.hypot(W, H)) + 8;
  async function kalBuf(t) { const cv = buf('kal', KS, KS), x = cv.getContext('2d'); x.translate((KS - W) / 2, (KS - H) / 2); await kalDraw(x, t); return cv; }

  /* ======================================================================= 2.5–4.5 · ракета из полос → КАТТА / ДАВРА */
  const TITLE_Y = 540;
  async function rider(c, x, y, tt) { // самолётик на голове шлейфа, улетает вверх 2.67–2.92
    const qq = q(tt), lk = prog(qq, 32 / 12, 35 / 12); if (lk >= 1) return;
    const s = lerp(1, 0.6, lk), rot = (Math.floor(tt * 12 + 1e-6) % 2 ? 4 : -4) - 30;
    await CL.sprite(c, 'plane', x, y - 640 * Math.pow(lk, 1.5), { h: 230 * s, rot, shadow: { dx: 8, dy: 14, blur: 12, alpha: 0.35 } });
  }
  async function titleBg(ctx, t) {
    const tq = q(t), tilt = 0.9 * E.inOut3(prog(tq, 2.5, 3.0)) + 0.1 * prog(tq, 3.0, 6.0);
    await CL.sky(ctx, t, { tilt, part: E.inOut3(prog(tq, 31 / 12, 3.0)) });
    if (tq >= 2.5) { const rby = H + 70, rhy = lerp(rby, H * 0.31, E.out3(clamp((tq - 2.5) / 0.42)));
      await X.rocket(ctx, t, 2.5, { vx: W / 2, vy: H * 0.31, by: rby, bx: W / 2, dur: 0.42, n: 64, width: clamp((rby - rhy) * 2.2, 300, 1050), narrow: 0.66, seed: 7, drawRider: rider }); }
    await X.burst(ctx, t, 3.0, { cx: W / 2, cy: TITLE_Y, n: 26, seed: 9 });
  }
  const TFR = [0, 0.256, 0.471, 0.62, 0.752, 0.835, 0.917, 0.95, 0.983, 1];
  async function titleScene(ctx, t) {
    await titleBg(ctx, t);
    const tq = q(t); if (tq < 3.0) return;
    const i = drawingIdx(t, 3.0), f = i < TFR.length ? TFR[i] : 1, dy0 = H * 0.075 - (TITLE_Y + TTL.off);
    await X.title(ctx, COPY.title, W / 2, TITLE_Y + dy0 * (1 - f), tq, 3.0, { size: TTL.size, font: COPY.titleFont, drop: false, zoom: 0.03 });
    if (tq >= 3.3 && tq <= 4.4) { const k = prog(tq, 3.3, 4.4), b = CL.bob(t, 17, 4);
      await CL.sprite(ctx, 'plane', lerp(-300, W + 300, k) + b.dx, 230 + Math.sin(k * 5) * 18 - k * 60 + b.dy, { h: 190, rot: -12 + b.rot, boil: 0.7, t, shadow: { dx: 12, dy: 34, blur: 14, alpha: 0.25 } }); }
  }

  /* ======================================================================= 4.5–6.0 · разрыв → лента → мерцание */
  function vnoise(seed) { const r = ENG.rng(seed * 7 + 3), N = 1024, v = new Float32Array(N); for (let i = 0; i < N; i++) v[i] = r() * 2 - 1; return (x) => { x = ((x % N) + N) % N; const i = Math.floor(x), f = x - i, s = f * f * (3 - 2 * f); return v[i] + (v[(i + 1) % N] - v[i]) * s; }; }
  function fbm(seed) { const a = vnoise(seed), b = vnoise(seed + 17), c = vnoise(seed + 29); return (x) => a(x) * 0.58 + b(x * 2.17 + 5.3) * 0.29 + c(x * 4.73 + 1.1) * 0.13; }
  const TEARDONE = (() => {
    const { y0, y1, seed } = TEAR, st = 6, n = Math.ceil((W + 80) / st) + 1, nA = fbm(seed), nB = fbm(seed + 9), nC = vnoise(seed + 3), nD = vnoise(seed + 5), r = ENG.rng(seed), xs = [], top = [], bot = [], wt = [], wb = [];
    for (let i = 0; i < n; i++) { const x = -40 + i * st; xs.push(x); top.push(y0 + nA(x / 60) * 13 + (r() - 0.5) * 3); bot.push(y1 + nB(x / 60) * 13 + (r() - 0.5) * 3); wt.push(3 + 12 * Math.pow(clamp(0.5 + 0.8 * nC(x / 70)), 1.5) + r() * 1.5); wb.push(2 + 10 * Math.pow(clamp(0.5 + 0.8 * nD(x / 70)), 1.5) + r() * 1.5); }
    const R = new Path2D(), Ts = new Path2D(), tp = new Path2D(), bp = new Path2D(), m = n - 1;
    R.moveTo(xs[0], top[0]); for (let i = 1; i <= m; i++) R.lineTo(xs[i], top[i]); for (let i = m; i >= 0; i--) R.lineTo(xs[i], bot[i]); R.closePath();
    Ts.moveTo(xs[0], top[0] - 200); for (let i = 0; i <= m; i++) Ts.lineTo(xs[i], top[i]); Ts.lineTo(xs[m], top[m] - 200); Ts.closePath();
    for (let i = 0; i <= m; i++) i ? tp.lineTo(xs[i], top[i] - wt[i]) : tp.moveTo(xs[i], top[i] - wt[i]); for (let i = m; i >= 0; i--) tp.lineTo(xs[i], top[i]); tp.closePath();
    for (let i = 0; i <= m; i++) i ? bp.lineTo(xs[i], bot[i]) : bp.moveTo(xs[i], bot[i]); for (let i = m; i >= 0; i--) bp.lineTo(xs[i], bot[i] + wb[i]); bp.closePath();
    return { R, Ts, tp, bp };
  })();
  function tearDone(ctx, A, B) {
    const T = TEARDONE; ctx.drawImage(A, 0, 0);
    ctx.save(); ctx.clip(T.R); ctx.drawImage(B, 0, 0); ctx.shadowColor = 'rgba(0,0,0,0.42)'; ctx.shadowBlur = 16; ctx.shadowOffsetY = 7; ctx.fillStyle = '#000'; ctx.fill(T.Ts); ctx.restore();
    ctx.save(); ctx.fillStyle = U.pat(ctx, X.PAL.paper); ctx.fill(T.tp); ctx.fill(T.bp); ctx.strokeStyle = 'rgba(80,60,40,0.18)'; ctx.lineWidth = 1; ctx.stroke(T.tp); ctx.stroke(T.bp); ctx.restore();
  }
  const logoAt = (c, t, style) => X.logoBand(c, COPY.logo, t, { style: style || 'band', x: LOGO.x, y: LOGO.y, h: LOGO.h, size: LOGO.size, seed: 8, boil: !style || style === 'band' });
  async function lookAt(c, t, st) {
    if (st !== 'posters') { await logoAt(c, t, st); return; }
    await CL.posters(c, t, {}); U.drawPiece(c, U.logoSprite(COPY.logo, LOGO.size, 'chrome', 8), LOGO.x, LOGO.y, { shadow: false });
  }
  const flashAt = (t) => { const i = Math.floor((t - 5.0) * 24 + 1e-6); return i >= 0 && i < FLICK_FR.length ? FLICK[FLICK_FR[i]] : null; };
  async function endScene(ctx, t) {
    const tq = q(t), st = flashAt(t), z = 1 + 0.03 * Math.max(0, tq - 5.5);
    await zoomAbout(ctx, z, W / 2, H / 2, async () => {
      const BG = buf('tbg'); await titleBg(BG.getContext('2d'), t);
      const under = async (c) => { c.drawImage(BG, 0, 0); await logoAt(c, t, null); };
      if (tq < 4.9) await X.tear(ctx, prog(tq, 53 / 12, 4.92), async (c) => titleScene(c, t), under, TEAR);
      else {
        const Bc = buf('tunder'); await under(Bc.getContext('2d')); tearDone(ctx, BG, Bc);
        if (st) { const F = buf('flash'); await lookAt(F.getContext('2d'), tq, st); ctx.save(); ctx.clip(TEARDONE.R); ctx.drawImage(F, 0, 0); ctx.restore(); } // только внутри ленты
      }
      if (tq >= 59 / 12) await X.tag(ctx, W / 2, 205, COPY.bandTag, { t: tq, t0: 59 / 12, color: 'cobalt', font: 'sans', size: 46, rot: -0.02, tape: 'top' });
      if (tq >= 5.5) await X.confetti(ctx, t, 5.5, { x: W / 2, y: LOGO.y, n: 30, speed: 1400, spread: Math.PI * 2, gravity: 1100, dur: 0.6, seed: 28 });
      if (tq >= 5.25) await X.tag(ctx, W / 2, 900, COPY.tgTag, { t: tq, t0: 5.25, color: 'yellow', font: 'sans', size: 42, rot: 0.015, tape: false });
    });
  }

  /* ======================================================================= timeline */
  const cuts = [];
  const Cut = (t0, t1, draw) => cuts.push({ t0, t1, draw: async (ctx, t, k, lt) => {
    await warm();
    const z = K.punch(q(t)); ctx.fillStyle = '#FBF8F1'; ctx.fillRect(0, 0, W, H);
    await zoomAbout(ctx, z, W / 2, H / 2, () => draw(ctx, t, k, lt));
  } });
  Cut(0.0, 1.5, (ctx, t) => pageScene(ctx, t));
  Cut(1.5, 2.5, (ctx, t) => kalDraw(ctx, t));
  Cut(2.5, 3.0, (ctx, t) => titleBg(ctx, t));
  Cut(3.0, 4.5, (ctx, t) => titleScene(ctx, t));
  Cut(4.5, 6.0, (ctx, t) => endScene(ctx, t));

  window.SCENES = { duration: 6.0, cuts, overlay: async (ctx, t) => { CL.printGrain(ctx, t, 0.05); } };
  window.COPY = COPY;
})();
