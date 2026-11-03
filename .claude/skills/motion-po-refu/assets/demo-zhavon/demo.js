/* Shodiyona — «Ичига нима сиғади?» + «6 исбот» (v2, 04.11.2026). Фирменный стиль Shodiyona: белый→кремовый фон, зелёный #1F3A28,
 * дуб #B8814A, Inter Display Black/ExtraBold, субтитры на зелёной плашке, зелёная шторка со знаком, финал с логотипом и слоганом
 * «ИШЛАБ ЧИҚАРУВЧИДАН — ТЎҒРИДАН-ТЎҒРИ». Товар — настоящий стеллаж Shodiyona (k31.png). Голос Vika (eleven_v4, uz).
 * timeline.js (window.TL) собирает build_tl.py из озвучки. Размеры в см — НАМУНА. Шрифты: fonts/ ← /usr/share/fonts/opentype/inter. */
(function () {
  const cv = document.getElementById('c'), ctx = cv.getContext('2d'), W = 1080, H = 1920, { E, prog, clamp, lerp, rr } = MK;
  MK.setFonts({ head: '"IDB"', body: '"IDX"' }); MK.setPalette({ accent: '#B8814A' }); const P = MK.P;
  const G = '#1F3A28', OAK = '#B8814A', NUT = '#74421E', CR = '#FBF8F1';
  const TL = window.TL, LN = TL.lines; window.__comp = { width: W, height: H, fps: 30, duration: TL.dur };
  const st = (i) => LN[i].t0, en = (i) => LN[i].t1;
  const INTRO = 0.95, T_ASK = st(1) + 0.2, T_FILL = st(2) - 0.1, EVERY = (en(2) - st(2) - 0.5) / 12; // все вещи на полках к концу фразы «…ҳаммаси жойида»
  const A_END = st(3) - 0.35, B_END = st(4) - 0.3, CH0 = (c) => st(4 + c) - 0.3, CH1 = (c) => (c < 5 ? st(5 + c) - 0.3 : CTA), CTA = st(10) - 0.5;
  const img = {}; for (const n of ['k31', 'logo', 'icon', 'u07']) { img[n] = new Image(); img[n].src = n + '.png'; }
  const ready = () => Promise.all(Object.values(img).map((im) => (im.complete ? 0 : new Promise((r) => { im.onload = r; im.onerror = r; }))));
  // ---- фон бренда: белый → кремовый, мягкий пол, тонкие дубовые линии ----
  const BGC = {};
  function studio(c, t, o = {}) { // кэш: фон статичный — рисуем один раз (скорость рендера)
    const key = o.floor ?? 1345; if (!BGC[key]) { const cc = document.createElement('canvas'); cc.width = W + 400; cc.height = H + 400; const x = cc.getContext('2d'); x.translate(200, 200); studioDraw(x, o); BGC[key] = cc; }
    c.drawImage(BGC[key], -200, -200);
  }
  function studioDraw(c, o) {
    const g = c.createRadialGradient(W / 2, H * 0.4, 80, W / 2, H * 0.45, H * 0.8); g.addColorStop(0, '#FFFFFF'); g.addColorStop(1, '#F1EADF'); c.fillStyle = g; c.fillRect(-200, -200, W + 400, H + 400);
    const fy = o.floor ?? 1345, f = c.createLinearGradient(0, fy, 0, H); f.addColorStop(0, '#EFE6D8'); f.addColorStop(1, '#E3D6C3'); c.fillStyle = f; c.fillRect(-200, fy, W + 400, H - fy + 200);
    c.fillStyle = 'rgba(184,129,74,0.35)'; c.fillRect(-200, fy, W + 400, 2);
    c.save(); c.globalCompositeOperation = 'multiply'; const s = c.createLinearGradient(0, 0, W, H); s.addColorStop(0, 'rgba(255,255,255,1)'); s.addColorStop(1, 'rgba(236,226,210,1)'); c.fillStyle = s; c.fillRect(-200, -200, W + 400, H + 400); c.restore();
  }
  const oakFrame = (c, k) => { if (k <= 0) return; c.save(); c.globalAlpha = k; c.strokeStyle = OAK; c.lineWidth = 3; const m = 46, L = 120 * k; // уголки, как на бренд-доске
    for (const [x, y, sx, sy] of [[m, 250, 1, 1], [W - m, 250, -1, 1], [m, 1530, 1, -1], [W - m, 1530, -1, -1]]) { c.beginPath(); c.moveTo(x, y + sy * L); c.lineTo(x, y); c.lineTo(x + sx * L, y); c.stroke(); } c.restore(); };
  const shadowUnder = (c, cx, by, w, a = 0.35) => { const g = c.createRadialGradient(cx, by, 10, cx, by, w * 0.6); g.addColorStop(0, `rgba(60,40,20,${a})`); g.addColorStop(1, 'rgba(60,40,20,0)'); c.fillStyle = g; c.beginPath(); c.ellipse(cx, by, w * 0.62, 46, 0, 0, 7); c.fill(); };
  // ---- стеллаж (фото) ----
  const IW = 416, IH = 666, SHC = {}; // k31.png; SHC — кэш стеллажа с тенью
  function shelf(c, cx, by, s, o = {}) { const w = IW * s * (o.sx || 1), h = IH * s, x = cx - w / 2, y = by - h; shadowUnder(c, cx, by - 4, w);
    const key = s.toFixed(3); if (!SHC[key]) { const pad = 60, cc = document.createElement('canvas'); cc.width = Math.ceil(IW * s) + pad * 2; cc.height = Math.ceil(IH * s) + pad * 2; const xx = cc.getContext('2d');
      xx.imageSmoothingQuality = 'high'; xx.shadowColor = 'rgba(40,28,14,0.22)'; xx.shadowBlur = 30; xx.shadowOffsetX = 16; xx.shadowOffsetY = 6; xx.drawImage(img.k31, pad, pad, IW * s, IH * s); SHC[key] = { cc, pad }; }
    const C0 = SHC[key]; c.save(); c.imageSmoothingQuality = 'high'; c.drawImage(C0.cc, x - C0.pad * (o.sx || 1), y - C0.pad, C0.cc.width * (o.sx || 1), C0.cc.height); c.restore();
    if (o.sweep != null) { c.save(); c.globalCompositeOperation = 'screen'; const sx = lerp(x - 300, x + w + 300, o.sweep), g = c.createLinearGradient(sx - 140, y, sx + 140, y + 260); g.addColorStop(0, 'rgba(255,255,255,0)'); g.addColorStop(0.5, 'rgba(255,248,232,0.5)'); g.addColorStop(1, 'rgba(255,255,255,0)'); c.fillStyle = g; c.fillRect(x, y, w, h); c.restore(); }
    return { x, y, w, h, s }; }
  // места на полках в пикселях фото: [x центра, поверхность полки]
  const SLOT = [[190, 615, 'books'], [80, 605, 'plant'], [325, 625, 'box'], [68, 372, 'toy'], [190, 383, 'vase'], [325, 500, 'frame'], [75, 487, 'basket'], [190, 250, 'binders'], [320, 262, 'candles'], [65, 128, 'clock'], [185, 130, 'books2'], [310, 142, 'succ']];
  const NAMES = { books: 'КИТОБЛАР', plant: 'ГУЛ', box: 'ҚУТИ', toy: 'ЎЙИНЧОҚ', vase: 'ВАЗА', frame: 'РАМКА', basket: 'САВАТ', binders: 'ПАПКАЛАР', candles: 'ШАМЛАР', clock: 'СОАТ', books2: 'КИТОБЛАР', succ: 'ГУЛ' };
  const DIM = { plant: [74, 96], succ: [60, 58], vase: [44, 82], clock: [64, 64], frame: [70, 70], toy: [70, 70], candles: [70, 56], books: [86, 66], books2: [80, 66], box: [92, 62], basket: [86, 58], binders: [84, 72] };
  const ITEMS = SLOT.map(([, , type]) => ({ type, name: NAMES[type] }));
  function slots(S) { return SLOT.map(([px, py, type]) => { const [w, h] = DIM[type]; const k = 1.22; return [S.x + px * S.s, S.y + (py - h * k / 2 - 2) * S.s, w * k * S.s, h * k * S.s]; }); }
  const shade = (hex, k) => { const n = parseInt(hex.slice(1), 16), f = (v) => Math.max(0, Math.min(255, Math.round(v * k))); return `rgb(${f(n >> 16)},${f((n >> 8) & 255)},${f(n & 255)})`; };
  function drawItem(c, it, w, h) { // вещи — свой рисунок, фирменные оттенки
    c.save(); c.shadowColor = 'rgba(0,0,0,0.28)'; c.shadowBlur = 10; c.shadowOffsetY = 4; const T = it.type;
    if (T === 'books' || T === 'books2') { const cols = T === 'books' ? [G, OAK, '#E9DCC4', NUT, '#6F90B2'] : ['#3F4D60', '#E9DCC4', G, OAK]; const n = cols.length, bw = w / (n + 0.4);
      cols.forEach((cl, k) => { const bh = h * (0.78 + ((k * 37) % 19) / 100), xx = -w / 2 + k * (bw + 2); c.fillStyle = cl; rr(c, xx, h / 2 - bh, bw, bh, 3); c.fill(); c.save(); c.shadowColor = 'transparent'; c.fillStyle = 'rgba(255,255,255,0.45)'; c.fillRect(xx + 3, h / 2 - bh + 8, bw - 6, 3); c.fillRect(xx + 3, h / 2 - 14, bw - 6, 3); c.restore(); }); }
    else if (T === 'plant' || T === 'succ') { const ph = h * 0.36; c.fillStyle = '#F4F0E8'; rr(c, -w * 0.28, h / 2 - ph, w * 0.56, ph, 6); c.fill(); c.shadowColor = 'transparent'; c.fillStyle = OAK; c.fillRect(-w * 0.28, h / 2 - ph, w * 0.56, 4);
      const lv = T === 'plant' ? [[-0.7, 0.62], [-0.3, 0.72], [0.05, 0.66], [0.4, 0.7], [0.75, 0.58]] : [[-0.9, 0.36], [-0.4, 0.44], [0, 0.48], [0.4, 0.44], [0.9, 0.36]];
      lv.forEach(([a, L], k) => { c.save(); c.translate(0, h / 2 - ph); c.rotate(a); c.fillStyle = k % 2 ? '#2F5A3A' : '#467A50'; const LL = h * L; c.beginPath(); c.moveTo(0, 0); c.quadraticCurveTo(w * 0.18, -LL * 0.5, 0, -LL); c.quadraticCurveTo(-w * 0.18, -LL * 0.5, 0, 0); c.fill(); c.restore(); }); }
    else if (T === 'vase') { const g = c.createLinearGradient(-w / 2, 0, w / 2, 0); g.addColorStop(0, '#E9DCC4'); g.addColorStop(0.5, '#FFFFFF'); g.addColorStop(1, '#CDBFA6'); c.fillStyle = g; c.beginPath(); c.moveTo(-w * 0.18, -h / 2); c.lineTo(w * 0.18, -h / 2); c.quadraticCurveTo(w * 0.7, h * 0.1, w * 0.3, h / 2); c.lineTo(-w * 0.3, h / 2); c.quadraticCurveTo(-w * 0.7, h * 0.1, -w * 0.18, -h / 2); c.fill();
      c.shadowColor = 'transparent'; c.strokeStyle = OAK; c.lineWidth = 2; for (const a of [-0.5, 0, 0.5]) { c.beginPath(); c.moveTo(0, -h / 2); c.quadraticCurveTo(a * w, -h * 0.9, a * w * 1.2, -h * 1.05); c.stroke(); } }
    else if (T === 'frame') { c.fillStyle = NUT; rr(c, -w / 2, -h / 2, w, h, 4); c.fill(); c.shadowColor = 'transparent'; c.fillStyle = '#F4F0E8'; c.fillRect(-w / 2 + 7, -h / 2 + 7, w - 14, h - 14); c.fillStyle = '#9DB9A1'; c.beginPath(); c.moveTo(-w / 2 + 7, h / 2 - 7); c.lineTo(-w * 0.1, -h * 0.05); c.lineTo(w * 0.1, h * 0.15); c.lineTo(w * 0.25, 0); c.lineTo(w / 2 - 7, h / 2 - 7); c.fill(); c.fillStyle = '#E9B44C'; c.beginPath(); c.arc(w * 0.2, -h * 0.2, w * 0.08, 0, 7); c.fill(); }
    else if (T === 'toy') { c.fillStyle = '#C49A6C'; c.beginPath(); c.arc(0, h * 0.18, w * 0.32, 0, 7); c.fill(); c.beginPath(); c.arc(0, -h * 0.2, w * 0.24, 0, 7); c.fill(); for (const s of [-1, 1]) { c.beginPath(); c.arc(s * w * 0.18, -h * 0.38, w * 0.09, 0, 7); c.fill(); }
      c.shadowColor = 'transparent'; c.fillStyle = '#E9DCC4'; c.beginPath(); c.ellipse(0, -h * 0.14, w * 0.1, w * 0.07, 0, 0, 7); c.fill(); c.fillStyle = '#2B2016'; for (const s of [-1, 1]) { c.beginPath(); c.arc(s * w * 0.08, -h * 0.25, 2.5 * w / 70, 0, 7); c.fill(); } }
    else if (T === 'box' || T === 'basket') { const g = c.createLinearGradient(0, -h / 2, 0, h / 2); g.addColorStop(0, T === 'box' ? '#F4F0E8' : '#D9B98A'); g.addColorStop(1, T === 'box' ? '#D8CDBB' : '#A9814F'); c.fillStyle = g; rr(c, -w / 2, -h / 2, w, h, 6); c.fill(); c.shadowColor = 'transparent';
      if (T === 'box') { c.fillStyle = G; c.fillRect(-w / 2, -h / 2 + h * 0.2, w, 5); c.fillStyle = OAK; rr(c, -w * 0.15, -h * 0.05, w * 0.3, h * 0.16, 4); c.fill(); }
      else { c.strokeStyle = 'rgba(90,60,30,0.45)'; c.lineWidth = 2; for (let k = 1; k < 5; k++) { c.beginPath(); c.moveTo(-w / 2, -h / 2 + k * h / 5); c.lineTo(w / 2, -h / 2 + k * h / 5); c.stroke(); } for (let k = 1; k < 8; k++) { c.beginPath(); c.moveTo(-w / 2 + k * w / 8, -h / 2); c.lineTo(-w / 2 + k * w / 8, h / 2); c.stroke(); } } }
    else if (T === 'binders') { [G, OAK, '#3F4D60', '#E9DCC4'].forEach((cl, k) => { const bw = w / 4.3, xx = -w / 2 + k * (bw + 3); c.fillStyle = cl; rr(c, xx, -h / 2, bw, h, 3); c.fill(); c.save(); c.shadowColor = 'transparent'; c.fillStyle = 'rgba(255,255,255,0.85)'; c.beginPath(); c.arc(xx + bw / 2, h * 0.2, bw * 0.22, 0, 7); c.fill(); c.fillRect(xx + 4, -h / 2 + 10, bw - 8, h * 0.25); c.restore(); }); }
    else if (T === 'candles') { [[-0.3, 0.9], [0, 0.7], [0.3, 0.55]].forEach(([dx, hh]) => { const cw = w * 0.24, ch = h * hh; c.fillStyle = '#FBF8F1'; rr(c, dx * w - cw / 2, h / 2 - ch, cw, ch, 5); c.fill(); c.save(); c.shadowColor = 'rgba(255,180,60,0.9)'; c.shadowBlur = 14; c.fillStyle = '#F5B342'; c.beginPath(); c.ellipse(dx * w, h / 2 - ch - 9, 4, 8, 0, 0, 7); c.fill(); c.restore(); }); }
    else if (T === 'clock') { c.fillStyle = G; c.beginPath(); c.arc(0, 0, w / 2, 0, 7); c.fill(); c.shadowColor = 'transparent'; c.fillStyle = CR; c.beginPath(); c.arc(0, 0, w / 2 - 6, 0, 7); c.fill(); c.strokeStyle = G; c.lineWidth = 3.5; c.lineCap = 'round'; c.beginPath(); c.moveTo(0, 0); c.lineTo(0, -w * 0.3); c.moveTo(0, 0); c.lineTo(w * 0.2, w * 0.08); c.stroke(); c.fillStyle = OAK; c.beginPath(); c.arc(0, 0, 3.5, 0, 7); c.fill(); }
    c.restore(); }
  // ---- общие ----
  const subs = (c, t, i0, i1) => { const words = []; for (let i = i0; i <= i1; i++) words.push(...LN[i].words); const long = words.some((w) => w[0].length > 11); MK.subs(c, { t, words, y: 1450, size: long ? 52 : 56, maxWords: long ? 2 : 3, band: 'rgba(31,58,40,0.94)', hiBg: OAK, hiFg: CR, hold: 0.35 }); };
  const cam = (c, k, z0, z1, dx = 0, dy = 0, cy = H * 0.48) => { const kk = E.inOut3(clamp(k)), z = lerp(z0, z1, kk); c.translate(W / 2 + dx * kk, cy + dy * kk); c.scale(z, z); c.translate(-W / 2, -cy); };
  const namuna = (c) => { c.save(); c.font = '400 24px "IDX"'; c.fillStyle = 'rgba(31,58,40,0.55)'; c.textAlign = 'right'; c.fillText('НАМУНА · демо', W - 170, 1530); c.restore(); };
  const txt = (c, s, x, y, fz, col, fam = 'IDB', align = 'center') => { c.font = `400 ${fz}px "${fam}"`; c.fillStyle = col; c.textAlign = align; c.textBaseline = 'middle'; c.fillText(s, x, y); };
  function shtorka(c, t) { // зелёная шторка со знаком (фирменная заставка)
    const k = prog(t, 0, INTRO); if (k >= 1) return; const out = E.inOut3(prog(t, INTRO - 0.4, INTRO));
    c.save(); c.fillStyle = G; c.fillRect(0, -out * H, W, H); const s = Math.max(0.001, E.outBack(prog(t, 0.05, 0.5), 1.7) * (1 - out * 0.4)), a = 1 - out;
    c.globalAlpha = a; c.fillStyle = CR; c.beginPath(); c.arc(W / 2, H * 0.45 - out * H, 230 * s, 0, 7); c.fill(); c.strokeStyle = OAK; c.lineWidth = 6; c.beginPath(); c.arc(W / 2, H * 0.45 - out * H, 252 * s, 0, 7); c.stroke(); const iw = 300 * s, ih = iw * 957 / 919; c.drawImage(img.icon, W / 2 - iw / 2, H * 0.45 - ih / 2 - out * H, iw, ih); c.restore(); }
  let lastN = 0, lastT = -9;
  function badge(c, t, n) { if (n !== lastN) { lastN = n; lastT = t; } if (n <= 0) return; const k = MK.life(t, T_FILL + 0.8, A_END - 0.3, 0.4), pop = 1 + 0.2 * Math.exp(-(t - lastT) * 9);
    c.save(); c.globalAlpha *= k; c.translate(815, 330); c.scale(pop * k, pop * k); c.shadowColor = 'rgba(0,0,0,0.25)'; c.shadowBlur = 24; c.shadowOffsetY = 8; c.fillStyle = G; c.beginPath(); c.arc(0, 0, 104, 0, 7); c.fill(); c.shadowColor = 'transparent';
    c.strokeStyle = OAK; c.lineWidth = 5; c.beginPath(); c.arc(0, 0, 92, 0, 7); c.stroke(); txt(c, '+' + n, 0, -10, 84, CR); txt(c, 'ТА НАРСА', 0, 50, 22, OAK, 'IDX'); c.restore(); }
  // ---- сцена A: товар → вопрос → вещи по полкам ----
  function sceneA(c, t) { const k = prog(t, 0, A_END); c.save(); cam(c, k, 1.06, 1.0, 0, 0); studio(c, t);
    const S = shelf(c, 540, 1335, 1.55, { sweep: t < T_ASK + 1.2 ? prog(t, INTRO - 0.1, T_ASK + 1.2) : null });
    WD.landed = t >= T_FILL ? MK.fill(c, { box: { x: S.x, y: S.y, w: S.w, h: S.h }, items: ITEMS, slots: slots(S), t, t0: T_FILL, every: EVERY, fly: 0.8, arc: 360, drawItem }) : 0;
    c.restore(); oakFrame(c, E.out3(prog(t, INTRO, INTRO + 0.8)));
    if (t >= T_ASK && t < T_FILL + 0.4) { const q = MK.life(t, T_ASK + 0.3, T_FILL + 0.2, 0.4), s = E.outBack(prog(t, T_ASK + 0.3, T_ASK + 0.8)); c.save(); c.globalAlpha = q; c.translate(815, 330); c.scale(s, s); c.fillStyle = OAK; c.beginPath(); c.arc(0, 0, 90, 0, 7); c.fill(); txt(c, '?', 0, 6, 120, CR); c.restore(); }
    badge(c, t, WD.landed); subs(c, t, 0, 2); }
  const WD = { landed: 0 };
  // ---- сцена B: «6 ИСБОТ» ----
  function sceneB(c, t) { const t0 = A_END, lt = t - t0; studio(c, t); oakFrame(c, 1);
    const s = E.outBack(prog(t, t0 + 0.05, t0 + 0.6), 1.8) * (1 + lt * 0.02); c.save(); c.translate(W / 2, 820); c.scale(s, s); c.shadowColor = 'rgba(31,58,40,0.25)'; c.shadowBlur = 40; c.shadowOffsetY = 16; txt(c, '6', 0, 0, 600, G); c.restore();
    const tk = E.out3(prog(t, t0 + 0.35, t0 + 0.8)); c.save(); c.globalAlpha = tk; txt(c, 'ИСБОТ', W / 2, 1210 + (1 - tk) * 40, 128, OAK); txt(c, 'СОТИБ ОЛИШДАН ОЛДИН', W / 2, 1310 + (1 - tk) * 40, 40, G, 'IDX'); c.restore();
    for (let i = 0; i < 6; i++) { const dk = E.outBack(prog(t, t0 + 0.6 + i * 0.1, t0 + 0.95 + i * 0.1)); if (dk <= 0) continue; c.fillStyle = i % 2 ? OAK : G; c.beginPath(); c.arc(W / 2 + (i - 2.5) * 66, 1395, 13 * dk, 0, 7); c.fill(); } }
  // ---- 6 глав ----
  const CH = [['ЎЛЧАМИ', 'одам ёнида'], ['МАТЕРИАЛИ', 'металл каркас'], ['ХОНАДА', 'қандай туради'], ['ЎЛЧАМЛАРИ', 'бўйи ва эни'], ['НАРХИ', 'ўртакашсиз'], ['БУЮРТМА', 'ўлчамингиз бўйича']];
  function person(c, x, by, hh) { c.save(); c.fillStyle = G; c.shadowColor = 'rgba(0,0,0,0.2)'; c.shadowBlur = 20; c.shadowOffsetX = 10; const hr = hh * 0.068;
    c.beginPath(); c.arc(x, by - hh + hr, hr, 0, 7); c.fill(); rr(c, x - hr * 0.45, by - hh + hr * 1.8, hr * 0.9, hr * 0.8, 6); c.fill();
    c.beginPath(); c.moveTo(x - hh * 0.13, by - hh * 0.79); c.quadraticCurveTo(x, by - hh * 0.83, x + hh * 0.13, by - hh * 0.79); c.lineTo(x + hh * 0.11, by - hh * 0.45); c.lineTo(x - hh * 0.11, by - hh * 0.45); c.closePath(); c.fill();
    rr(c, x - hh * 0.17, by - hh * 0.78, hh * 0.055, hh * 0.36, 14); c.fill(); rr(c, x + hh * 0.115, by - hh * 0.78, hh * 0.055, hh * 0.36, 14); c.fill();
    rr(c, x - hh * 0.105, by - hh * 0.47, hh * 0.095, hh * 0.47, 16); c.fill(); rr(c, x + hh * 0.01, by - hh * 0.47, hh * 0.095, hh * 0.47, 16); c.fill(); c.restore(); }
  function plantBig(c, x, by, s) { c.save(); c.translate(x, by); c.scale(s, s); c.fillStyle = '#F4F0E8'; rr(c, -70, -150, 140, 150, 18); c.fill(); c.fillStyle = OAK; c.fillRect(-70, -150, 140, 8);
    [[-0.8, 330], [-0.4, 400], [0, 440], [0.35, 380], [0.75, 310]].forEach(([a, L], k) => { c.save(); c.translate(0, -150); c.rotate(a); c.fillStyle = k % 2 ? '#2F5A3A' : '#467A50'; c.beginPath(); c.moveTo(0, 0); c.quadraticCurveTo(60, -L * 0.5, 0, -L); c.quadraticCurveTo(-60, -L * 0.5, 0, 0); c.fill(); c.restore(); }); c.restore(); }
  function chain(c, t, a) { const items = [['ЗАВОД', G, CR], ['ЎРТАКАШ', '#D9D1C4', '#6B6257'], ['СИЗ', OAK, CR]], y0 = 640;
    items.forEach(([s, bg, fg], i) => { const k = E.outBack(prog(t, a + 0.25 + i * 0.3, a + 0.65 + i * 0.3)); if (k <= 0) return; let y = y0 + i * 270, al = 1;
      if (i === 1) { const cut = prog(t, a + 1.6, a + 2.1); al = 1 - 0.6 * cut; }
      c.save(); c.globalAlpha = al; c.translate(W / 2, y); c.scale(k, k); c.shadowColor = 'rgba(0,0,0,0.2)'; c.shadowBlur = 20; c.shadowOffsetY = 8; c.fillStyle = bg; rr(c, -260, -70, 520, 140, 70); c.fill(); c.shadowColor = 'transparent'; txt(c, s, 0, 4, 66, fg); c.restore();
      if (i === 1) { const cut = E.inOut3(prog(t, a + 1.6, a + 2.0)); if (cut > 0) { c.save(); c.strokeStyle = NUT; c.lineWidth = 12; c.lineCap = 'round'; c.beginPath(); c.moveTo(W / 2 - 300, y + 40); c.lineTo(W / 2 - 300 + 600 * cut, y - 40); c.stroke(); c.restore(); } }
      if (i < 2) { const ak = E.out3(prog(t, a + 0.5 + i * 0.3, a + 0.8 + i * 0.3)); c.save(); c.globalAlpha = ak; c.strokeStyle = OAK; c.lineWidth = 6; c.lineCap = 'round'; c.beginPath(); c.moveTo(W / 2, y + 85); c.lineTo(W / 2, y + 185); c.moveTo(W / 2 - 22, y + 160); c.lineTo(W / 2, y + 185); c.lineTo(W / 2 + 22, y + 160); c.stroke(); c.restore(); } }); }
  function chapter(c, t, i) { const a = CH0(i), b = CH1(i), k = prog(t, a, b); c.save();
    if (i === 0) { cam(c, k, 1.0, 1.04); studio(c, t); const S = shelf(c, 700, 1330, 1.2); person(c, 230, 1330, 760); c.restore(); c.save();
      const dk = E.inOut3(prog(t, a + 0.6, a + 1.4)); if (dk > 0) { c.setLineDash([14, 12]); c.strokeStyle = OAK; c.lineWidth = 4; c.beginPath(); c.moveTo(230, S.y); c.lineTo(230 + (S.x + S.w - 230) * dk, S.y); c.stroke(); c.beginPath(); c.moveTo(230, 1330 - 760); c.lineTo(230 + (S.x - 230) * dk, 1330 - 760); c.stroke(); c.setLineDash([]); } }
    else if (i === 1) { studio(c, t); const z = 2.5 + 0.25 * k; c.save(); c.imageSmoothingQuality = 'high'; c.drawImage(img.k31, W / 2 - 150 * z - k * 60, 980 - 520 * z * 0.92, IW * z, IH * z); c.restore();
      const sx = lerp(-300, W + 300, prog(t, a + 0.2, b)), sg = c.createLinearGradient(sx - 220, 0, sx + 220, H); sg.addColorStop(0, 'rgba(255,255,255,0)'); sg.addColorStop(0.5, 'rgba(255,250,240,0.4)'); sg.addColorStop(1, 'rgba(255,255,255,0)'); c.fillStyle = sg; c.fillRect(0, 0, W, H);
      const v = c.createRadialGradient(W / 2, H * 0.5, H * 0.3, W / 2, H * 0.5, H * 0.8); v.addColorStop(0, 'rgba(255,255,255,0)'); v.addColorStop(1, 'rgba(241,234,223,0.85)'); c.fillStyle = v; c.fillRect(0, 0, W, H);
      c.restore(); c.save(); MK.pointer(c, { x: 330, y: 760, tx: 610, ty: 1080, title: 'МЕТАЛЛ КАРКАС', sub: 'қора порошок бўёқ', t, t0: a + 0.8 }); }
    else if (i === 2) { cam(c, k, 1.0, 1.05, -30); studio(c, t, { floor: 1240 });
      c.fillStyle = '#E4EEF2'; rr(c, 110, 520, 300, 470, 8); c.fill(); c.strokeStyle = '#FFFFFF'; c.lineWidth = 14; c.strokeRect(110, 520, 300, 470); c.beginPath(); c.moveTo(260, 520); c.lineTo(260, 990); c.stroke();
      c.save(); c.globalCompositeOperation = 'multiply'; const bg = c.createLinearGradient(110, 520, 700, 1400); bg.addColorStop(0, 'rgba(255,240,215,0.0)'); bg.addColorStop(1, 'rgba(225,205,175,0.35)'); c.fillStyle = bg; c.fillRect(0, 0, W, H); c.restore();
      c.fillStyle = 'rgba(184,129,74,0.18)'; c.beginPath(); c.ellipse(430, 1420, 400, 70, 0, 0, 7); c.fill();
      shelf(c, 805, 1240, 0.95); plantBig(c, 140, 1330, 0.8);
      const tw = 600, th = tw * 342 / 661; shadowUnder(c, 420, 1455, tw * 0.9, 0.3); c.drawImage(img.u07, 420 - tw / 2, 1455 - th, tw, th);
      c.restore(); c.save(); MK.size(c, { x0: 610, y0: 1290, x1: 700, y1: 1290, label: 'ЎТИШ ЖОЙИ', fz: 30, t, t0: a + 0.8, side: -1 }); }
    else if (i === 3) { cam(c, k, 1.0, 1.03); studio(c, t); const S = shelf(c, 570, 1250, 1.12); c.restore(); c.save();
      MK.size(c, { x0: S.x - 50, y0: S.y, x1: S.x - 50, y1: S.y + S.h, label: '180 см', fz: 44, t, t0: a + 0.4, side: -1 }); MK.size(c, { x0: S.x, y0: S.y + S.h + 50, x1: S.x + S.w, y1: S.y + S.h + 50, label: '110 см', fz: 44, t, t0: a + 0.75, side: 1 }); }
    else if (i === 4) { studio(c, t); oakFrame(c, 1); chain(c, t, a); c.restore(); c.save(); if (t > a + 2.0) MK.badge(c, { x: 835, y: 905, r: 100, lines: ['ЎРТАКАШСИЗ', 'заводдан'], t, t0: a + 2.0, color: OAK, ink: CR }); }
    else { cam(c, k, 1.0, 1.03); studio(c, t); const sx = 1 + 0.22 * Math.sin(Math.PI * 2 * clamp((t - a - 0.5) / 2.6)) * E.out3(prog(t, a + 0.5, a + 1.0)); const S = shelf(c, 540, 1250, 1.1, { sx });
      c.restore(); c.save(); MK.size(c, { x0: S.x, y0: S.y + S.h + 55, x1: S.x + S.w, y1: S.y + S.h + 55, label: 'БУЮРТМА БЎЙИЧА', fz: 36, t, t0: a + 0.4, side: 1 }); }
    c.restore(); MK.proof(c, { i: i + 1, n: 6, title: CH[i][0], sub: CH[i][1], t, t0: a, y: 280, size: 88, panelColor: 'rgba(31,58,40,0.95)' });
    subs(c, t, 4 + i, 4 + i); if (i === 3) namuna(c); }
  // ---- финал бренда (белый) ----
  function finale(c, t) { const a = CTA; c.save(); cam(c, prog(t, a, TL.dur), 1.0, 1.045, 0, 0, 900); studio(c, t); oakFrame(c, E.out3(prog(t, a, a + 0.6)));
    const lk = E.outBack(prog(t, a + 0.1, a + 0.7), 1.5), lw = 760 * lk, lh = lw * 1635 / 1981; if (lk > 0) c.drawImage(img.logo, W / 2 - lw / 2, 600 - lh / 2, lw, lh);
    const s1 = E.out3(prog(t, a + 0.7, a + 1.1)), s2 = E.out3(prog(t, a + 0.85, a + 1.25)); c.save(); c.globalAlpha = s1; txt(c, 'ИШЛАБ ЧИҚАРУВЧИДАН —', W / 2, 1000 + (1 - s1) * 30, 60, G); c.globalAlpha = s2; txt(c, 'ТЎҒРИДАН-ТЎҒРИ', W / 2, 1075 + (1 - s2) * 30, 60, OAK); c.restore();
    const ph = '+998 77 923 01 91', n = Math.floor(clamp((t - a - 1.3) / 0.05, 0, ph.length)); if (n > 0) { c.save(); c.shadowColor = 'rgba(0,0,0,0.2)'; c.shadowBlur = 20; c.shadowOffsetY = 8; c.fillStyle = G; rr(c, 110, 1170, 860, 130, 65); c.fill(); c.restore();
      c.font = '400 70px "IDB"'; const full = c.measureText(ph).width; c.fillStyle = CR; c.textAlign = 'left'; c.textBaseline = 'middle'; c.fillText(ph.slice(0, n), W / 2 - full / 2, 1238); if (n < ph.length || Math.floor(t * 2) % 2) { const cw = c.measureText(ph.slice(0, n)).width; c.fillStyle = OAK; c.fillRect(W / 2 - full / 2 + cw + 8, 1208, 7, 60); } }
    const tk = E.out3(prog(t, a + 2.3, a + 2.7)); c.save(); c.globalAlpha = tk; txt(c, 'Telegram: @ShodiyonaMebelUz', W / 2, 1360, 40, G, 'IDX'); c.restore(); c.restore(); subs(c, t, 10, 10); }
  window.__seek = async (t) => {
    await MK.warm(); await ready(); for (const f of ['IDB', 'IDX', 'IB']) await document.fonts.load(`400 60px "${f}"`);
    ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.fillStyle = '#FFFFFF'; ctx.fillRect(0, 0, W, H);
    if (t < A_END) sceneA(ctx, t); else if (t < B_END) sceneB(ctx, t); else if (t < CTA) { let i = 0; while (i < 5 && t >= CH1(i)) i++; chapter(ctx, t, i); } else finale(ctx, t);
    if (t < INTRO) shtorka(ctx, t);
    for (const tw of [A_END - 0.3, B_END - 0.3, ...[0, 1, 2, 3, 4].map((c) => CH1(c) - 0.3), CTA - 0.3]) if (t >= tw && t < tw + 0.6) MK.wipe(ctx, { t, t0: tw, dur: 0.6, color: OAK });
    if (!/nograin/.test(location.search)) MK.grain(ctx, { t, amt: 0.025 });
  };
})();
