/* Демо mebel_kit — 10 с, 1920×1080, 24 fps. Предметы (стул, стол, цех) нарисованы кодом — в настоящем ролике тут кадры владельца. */
(function () {
  const cv = document.getElementById('c'), ctx = cv.getContext('2d'), W = 1920, H = 1080, { E, prog, clamp, lerp, rr } = MK, P = MK.P;
  window.__comp = { width: W, height: H, fps: 24, duration: 10 };
  const rnd = (s) => () => ((s = (s * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff);

  // ---- фон-комната ----
  function room(c, x, y, w, h, t, tint = P.cream) {
    const g = c.createLinearGradient(x, y, x, y + h); g.addColorStop(0, tint); g.addColorStop(0.68, '#EDE3D2'); g.addColorStop(0.681, '#C9A882'); g.addColorStop(1, '#A57E57'); c.fillStyle = g; c.fillRect(x, y, w, h);
    c.save(); c.globalAlpha = 0.18; c.strokeStyle = P.walnut; c.lineWidth = 2; for (let i = 0; i < 9; i++) { c.beginPath(); c.moveTo(x + w * (i / 8), y + h * 0.681); c.lineTo(x + w * 0.5 + (i - 4) * w * 0.35, y + h); c.stroke(); } c.restore();
    const lg = c.createRadialGradient(x + w * 0.78, y + h * 0.25, 10, x + w * 0.78, y + h * 0.25, w * 0.6); lg.addColorStop(0, 'rgba(255,240,210,0.55)'); lg.addColorStop(1, 'rgba(255,240,210,0)'); c.fillStyle = lg; c.fillRect(x, y, w, h);
  }
  // ---- стул (оригинальный рисунок: металл + дуб) ----
  function chair(c, cx, by, s, t) {
    c.save(); c.translate(cx, by); c.scale(s, s);
    c.fillStyle = 'rgba(0,0,0,0.18)'; c.beginPath(); c.ellipse(0, 0, 230, 34, 0, 0, Math.PI * 2); c.fill();
    const metal = (x0, y0, x1, y1, w = 16) => { c.strokeStyle = '#2B2E33'; c.lineWidth = w; c.lineCap = 'round'; c.beginPath(); c.moveTo(x0, y0); c.lineTo(x1, y1); c.stroke(); c.strokeStyle = 'rgba(255,255,255,0.18)'; c.lineWidth = 4; c.beginPath(); c.moveTo(x0 - 3, y0); c.lineTo(x1 - 3, y1); c.stroke(); };
    metal(-150, 0, -130, -330); metal(150, 0, 130, -330); metal(-95, -20, -110, -320, 12); metal(95, -20, 110, -320, 12); metal(-130, -620, -130, -330); metal(130, -620, 130, -330);
    const wood = (pts, a, b) => { const g = c.createLinearGradient(pts[0][0], pts[0][1], pts[2][0], pts[2][1]); g.addColorStop(0, a); g.addColorStop(1, b); c.fillStyle = g; c.beginPath(); pts.forEach((p, i) => (i ? c.lineTo(p[0], p[1]) : c.moveTo(p[0], p[1]))); c.closePath(); c.fill(); };
    wood([[-175, -360], [175, -360], [190, -320], [-190, -320]], '#C8935A', '#9C6A3A'); wood([[-190, -320], [190, -320], [190, -300], [-190, -300]], '#7E512C', '#6A421F');
    wood([[-150, -640], [150, -640], [160, -470], [-160, -470]], '#C8935A', '#9C6A3A');
    c.strokeStyle = 'rgba(90,55,25,0.35)'; c.lineWidth = 2; for (let i = 0; i < 6; i++) { c.beginPath(); c.moveTo(-150, -625 + i * 27); c.bezierCurveTo(-60, -630 + i * 27 + 6, 60, -620 + i * 27 - 6, 150, -625 + i * 27); c.stroke(); }
    c.restore();
  }
  function table(c, cx, by, s) {
    c.save(); c.translate(cx, by); c.scale(s, s); c.fillStyle = 'rgba(0,0,0,0.18)'; c.beginPath(); c.ellipse(0, 0, 420, 40, 0, 0, Math.PI * 2); c.fill();
    c.strokeStyle = '#2B2E33'; c.lineWidth = 22; c.lineCap = 'round'; for (const x of [-330, 330]) { c.beginPath(); c.moveTo(x, 0); c.lineTo(x * 0.9, -380); c.stroke(); }
    c.lineWidth = 12; c.beginPath(); c.moveTo(-300, -120); c.lineTo(300, -120); c.stroke();
    const g = c.createLinearGradient(0, -420, 0, -370); g.addColorStop(0, '#C8935A'); g.addColorStop(1, '#8B5A30'); c.fillStyle = g; rr(c, -420, -420, 840, 46, 8); c.fill(); c.restore();
  }
  function workshop(c, x, y, w, h, t) {
    const g = c.createLinearGradient(x, y, x, y + h); g.addColorStop(0, '#15171B'); g.addColorStop(1, '#2A2420'); c.fillStyle = g; c.fillRect(x, y, w, h);
    const fx = x + w * 0.5, fy = y + h * 0.58, glow = c.createRadialGradient(fx, fy, 5, fx, fy, w * 0.7); glow.addColorStop(0, 'rgba(255,170,60,0.75)'); glow.addColorStop(1, 'rgba(255,120,30,0)'); c.fillStyle = glow; c.fillRect(x, y, w, h);
    const r = rnd(Math.floor(t * 12) + 3); c.lineCap = 'round';
    for (let i = 0; i < 70; i++) { const a = -Math.PI * (0.15 + 0.7 * r()), sp = 60 + r() * 260, L = 10 + r() * 30; c.strokeStyle = `rgba(255,${180 + r() * 60 | 0},80,${0.5 + r() * 0.5})`; c.lineWidth = 2 + r() * 2; c.beginPath(); c.moveTo(fx + Math.cos(a) * sp, fy + Math.sin(a) * sp); c.lineTo(fx + Math.cos(a) * (sp + L), fy + Math.sin(a) * (sp + L)); c.stroke(); }
    c.fillStyle = '#3A3F46'; c.fillRect(x, fy + 20, w, 26);
  }
  const panelDraw = (c, i, [x, y, w, h], t) => {
    if (i === 0) workshop(c, x, y, w, h, t);
    else if (i === 1) { room(c, x, y, w, h, t); chair(c, x + w / 2, y + h * 0.86, h / 1080 * 0.95, t); }
    else { room(c, x, y, w, h, t, '#F4EBDD'); table(c, x + w / 2, y + h * 0.86, h / 1080 * 0.48); }
    c.fillStyle = 'rgba(0,0,0,0.0)';
    const lab = ['ЦЕХ', 'СТУЛ', 'СТОЛ'][i]; c.save(); c.globalAlpha = clamp(1 - prog(t, 1.8, 2.2)); MK.pill(c, x + w / 2, y + h - 70, lab, { size: 30, bg: P.green, fg: P.cream }); c.restore();
  };
  // ---- сцены ----
  const CH = { x: 760, by: 900, s: 1.0 };
  function chairScene(c, t) { room(c, 0, 0, W, H, t); const z = 1 + 0.04 * prog(t, 2.4, 5.4); c.save(); c.translate(W / 2, H / 2); c.scale(z, z); c.translate(-W / 2, -H / 2); chair(c, CH.x, CH.by, CH.s, t); c.restore();
    MK.size(c, { x0: CH.x - 240, y0: CH.by + 2 - 640, x1: CH.x - 240, y1: CH.by + 2, label: '85 см', t, t0: 2.9, out: 5.2, side: 1 });
    MK.size(c, { x0: CH.x - 190, y0: CH.by + 60, x1: CH.x + 190, y1: CH.by + 60, label: '45 см', t, t0: 3.15, out: 5.2, side: 1 });
    MK.pointer(c, { x: CH.x + 130, y: CH.by - 180, tx: CH.x + 420, ty: CH.by - 380, title: 'МЕТАЛЛ КАРКАС', sub: 'порошокли бўёқ', t, t0: 3.5, out: 5.25 });
    MK.pointer(c, { x: CH.x + 60, y: CH.by - 560, tx: CH.x + 420, ty: CH.by - 700, title: 'ЁҒОЧ ЎРИНДИҚ', sub: 'эман ранги', t, t0: 3.85, out: 5.25 });
    MK.lower(c, { name: 'ШОДИЁНА МЕБЕЛЬ', role: 'ишлаб чиқарувчи · Андижон', t, t0: 2.7, out: 5.1, y: 80, x: 110 });
  }
  function tableScene(c, t) { room(c, 0, 0, W, H, t, '#F4EBDD'); table(c, 1180, 860, 0.9);
    MK.counter(c, { x: 420, y: 430, to: 5, suffix: ' ЙИЛ', label: 'ИШЛАБ ЧИҚАРИШ ТАЖРИБАСИ', t, t0: 5.45, dur: 0.9, size: 200, color: P.green, labelColor: P.walnut });
    MK.swatches(c, { x: 140, y: 560, size: 130, t, t0: 5.8, items: [{ color: MK.TEX.wood('#B8814A', '#7A4E26'), name: 'ЭМАН' }, { color: MK.TEX.wood('#74421E', '#3E220E'), name: 'ЁНҒОҚ' }, { color: MK.TEX.metal('#9AA0A8'), name: 'МЕТАЛЛ' }, { color: MK.TEX.fabric('#1F3A28'), name: 'МАТО' }] });
    MK.badge(c, { x: 1680, y: 330, r: 165, lines: ['ЎРТАКАШСИЗ', 'тўғридан-тўғри', 'заводдан'], t, t0: 6.2 });
    MK.price(c, { x: 1050, y: 300, price: 'ЗАВОД НАРХИ', cur: '', note: 'ўртакаш устамасиз', fz: 58, t, t0: 6.5 });
    MK.subs(c, { t, y: H - 90, size: 58, words: [['ЎРТАКАШЛАР', 6.0, 6.35], ['ОРҚАЛИ', 6.35, 6.7], ['НАРХ', 6.7, 6.95], ['ҚЎШИЛАДИ', 6.95, 7.4]] });
  }
  function logo(c, x, y, k) { c.save(); c.translate(x, y); c.scale(k, k); c.fillStyle = P.oak; c.beginPath(); c.arc(0, -70, 70, 0, Math.PI * 2); c.fill();
    c.fillStyle = P.green; c.font = '400 92px "Montserrat 900"'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText('S', 0, -66);
    c.fillStyle = P.cream; c.font = '400 76px "Montserrat 900"'; c.fillText('SHODIYONA', 0, 60); c.font = '700 30px "Inter Tight"'; c.fillStyle = P.oak; c.fillText('M E B E L', 0, 112); c.restore(); }

  window.__seek = async (t) => {
    await MK.warm();     await document.fonts.load('400 96px "Montserrat 900"'); await document.fonts.load('700 30px "Inter Tight"');
    ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.fillStyle = P.green; ctx.fillRect(0, 0, W, H);
    if (t < 2.4) { ctx.fillStyle = P.green; ctx.fillRect(0, 0, W, H); MK.counter; MK.panels(ctx, { n: 3, t, t0: 0.15, tf: 1.8, focus: 1, draw: panelDraw }); }
    else if (t < 5.4) chairScene(ctx, t);
    else if (t < 8.0) tableScene(ctx, t);
    if (t >= 7.4 && t < 8.0) MK.wipe(ctx, { t, t0: 7.4, dur: 0.6 });
    if (t >= 7.7) MK.cta(ctx, { t, t0: 7.7, phone: '+998 70 167 37 77', lines: ['Кўргазма зали · Андижон', 'Дизайнер хизмати — бепул'], logo });
    if (!/nograin/.test(location.search)) MK.grain(ctx, { t, amt: 0.06 });
  };
})();
