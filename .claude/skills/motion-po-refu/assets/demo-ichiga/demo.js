/* Демо 9:16 (13 с, 24 fps): «Ичига қаранг» (MK.fill) + «6 исбот» (MK.proof). Шкаф нарисован кодом — в настоящем ролике тут видео из магазина Shodiyona.
 * Цифры (12 вещей, 200×160 см) — НАМУНА, не данные клиента. Разведка «Мебель» 03.11.2026. */
(function () {
  const cv = document.getElementById('c'), ctx = cv.getContext('2d'), W = 1080, H = 1920, { E, prog, clamp, lerp, rr } = MK, P = MK.P;
  window.__comp = { width: W, height: H, fps: 24, duration: 14.5 };
  const room = (c, tint = '#F4EBDD') => { const g = c.createLinearGradient(0, 0, 0, H); g.addColorStop(0, tint); g.addColorStop(0.7, '#E6D9C4'); g.addColorStop(0.701, '#C9A882'); g.addColorStop(1, '#9C764F'); c.fillStyle = g; c.fillRect(0, 0, W, H);
    const lg = c.createRadialGradient(W * 0.8, H * 0.18, 10, W * 0.8, H * 0.18, W * 0.9); lg.addColorStop(0, 'rgba(255,240,210,0.6)'); lg.addColorStop(1, 'rgba(255,240,210,0)'); c.fillStyle = lg; c.fillRect(0, 0, W, H); };
  // шкаф: центр cx, низ by, ширина w, высота h, open 0..1, цвет корпуса body
  const WR = { cx: 540, by: 1260, w: 700, h: 860 };
  function wardrobe(c, o = {}) {
    const { cx, by, w, h } = Object.assign({}, WR, o), x = cx - w / 2, y = by - h, op = o.open || 0, body = o.body || ['#C8935A', '#8E5D31'];
    c.save(); c.fillStyle = 'rgba(0,0,0,0.2)'; c.beginPath(); c.ellipse(cx, by + 8, w * 0.62, 26, 0, 0, Math.PI * 2); c.fill();
    let g = c.createLinearGradient(x, 0, x + w, 0); g.addColorStop(0, body[0]); g.addColorStop(1, body[1]); c.fillStyle = g; rr(c, x - 18, y - 18, w + 36, h + 36, 10); c.fill();
    c.fillStyle = '#3A2614'; c.fillRect(x, y, w, h); // ниша
    const ig = c.createLinearGradient(0, y, 0, by); ig.addColorStop(0, 'rgba(255,220,170,0.18)'); ig.addColorStop(1, 'rgba(0,0,0,0.25)'); c.fillStyle = ig; c.fillRect(x, y, w, h);
    c.fillStyle = body[1]; for (let i = 1; i < 4; i++) c.fillRect(x, y + h * i / 4 - 6, w, 12); // полки
    c.restore();
    WR.box = { x, y, w, h };
    if (o.inside) o.inside(c);
    // двери: от петель к краям, «поворот» = сжатие по ширине + тень
    const dw = w / 2, vis = 1 - 0.88 * E.inOut3(op);
    for (const s of [-1, 1]) { const hx = s < 0 ? x : x + w, ww = dw * vis, dx = s < 0 ? hx : hx - ww;
      c.save(); const dg = c.createLinearGradient(dx, 0, dx + ww, 0); dg.addColorStop(0, body[0]); dg.addColorStop(1, body[1]); c.fillStyle = dg; c.fillRect(dx, y, ww, h);
      c.fillStyle = `rgba(0,0,0,${0.35 * op})`; c.fillRect(dx, y, ww, h);
      c.strokeStyle = 'rgba(70,40,15,0.35)'; c.lineWidth = 2; for (let i = 0; i < 9; i++) { c.beginPath(); c.moveTo(dx, y + 40 + i * h / 9); c.bezierCurveTo(dx + ww * 0.3, y + 46 + i * h / 9, dx + ww * 0.7, y + 34 + i * h / 9, dx + ww, y + 40 + i * h / 9); c.stroke(); }
      c.fillStyle = '#D9D4CB'; const kx = s < 0 ? dx + ww - 26 : dx + 16; if (ww > 40) rr(c, kx, y + h * 0.42, 10, 120, 5), c.fill();
      c.restore(); }
  }
  const person = (c, x, by, hh) => { c.save(); c.fillStyle = P.green; const hr = hh * 0.075; c.beginPath(); c.arc(x, by - hh + hr, hr, 0, Math.PI * 2); c.fill(); rr(c, x - hh * 0.13, by - hh + hr * 2.3, hh * 0.26, hh * 0.47, 30); c.fill(); rr(c, x - hh * 0.11, by - hh * 0.5, hh * 0.09, hh * 0.5, 18); c.fill(); rr(c, x + hh * 0.02, by - hh * 0.5, hh * 0.09, hh * 0.5, 18); c.fill(); c.restore(); };
  const cam = (c, t, a, b, z0 = 1, z1 = 1.06, dx = 0) => { const k = E.inOut3(prog(t, a, b)), z = lerp(z0, z1, k); c.translate(W / 2 + dx * k, H * 0.45); c.scale(z, z); c.translate(-W / 2, -H * 0.45); };
  const title = (c, s, t, t0, out, y = 330, fz = 92) => { const k = MK.life(t, t0, out, 0.4); if (k <= 0) return; c.save(); c.globalAlpha *= k; c.font = `400 ${fz}px "Montserrat 900"`; c.textAlign = 'center'; c.textBaseline = 'middle';
    c.lineWidth = fz * 0.16; c.strokeStyle = 'rgba(22,19,15,0.55)'; c.lineJoin = 'round'; const yy = y + (1 - E.outBack(prog(t, t0, t0 + 0.45))) * 50; c.strokeText(s, W / 2, yy); c.fillStyle = P.cream; c.fillText(s, W / 2, yy); c.restore(); };
  const ITEMS = ['КЎРПА', 'ЁСТИҚ', 'КЎЙЛАК', 'ЖЕМПЕР', 'СОЧИҚ', 'ЧОЙШАБ', 'ШИМ', 'КУРТКА', 'ҚУТИ', 'ЎЙИНЧОҚ', 'КИТОБ', 'СУМКА'];
  const COL = ['#1F3A28', '#B8814A', '#6B8F71', '#C9573E', '#E9B44C', '#3E5C76', '#74421E', '#8E6C8A', '#4F7A5A', '#D08C4A', '#5B6E80', '#A0522D'];
  const items = ITEMS.map((n, i) => ({ name: n, color: COL[i] }));
  function sceneFill(c, t) { // 0–5.8
    c.save(); cam(c, t, 0, 5.8, 1.0, 1.07, 0); room(c);
    wardrobe(c, { open: prog(t, 1.15, 1.85), inside: (cc) => { if (t >= 1.7) MK.fill(cc, { box: WR.box, items, t, t0: 1.75, every: 0.22, cols: 3, fly: 0.5 }); } });
    c.restore();
    // счётчик — вне камеры (стоит на месте, читается)
    if (t >= 1.75 && t < 5.1) MK.fill(c, { box: { x: -9999, y: 0, w: 1, h: 1 }, items: items.map(() => ({ color: 'transparent' })), t, t0: 1.75, every: 0.22, fly: 0.5, from: [-9999, 0], out: 4.85, counter: { x: W / 2, y: 1440, size: 150, label: 'ТА НАРСА СИҒДИ' } });
    title(c, 'ТАШҚАРИДАН —', t, 0.15, 1.1, 300, 80); title(c, 'ТАРТИБ', t, 0.25, 1.1, 400, 80);
    title(c, 'ИЧИГА ҚАРАНГ', t, 1.15, 4.9);
    if (t >= 4.9) { MK.size(c, { x0: WR.cx - WR.w / 2 - 70, y0: WR.by - WR.h - 18, x1: WR.cx - WR.w / 2 - 70, y1: WR.by + 18, label: '200 см', fz: 46, t, t0: 4.95, out: 5.65, side: -1 });
      MK.size(c, { x0: WR.cx - WR.w / 2 - 18, y0: WR.by + 90, x1: WR.cx + WR.w / 2 + 18, y1: WR.by + 90, label: '160 см', fz: 46, t, t0: 5.1, out: 5.65, side: 1 }); }
  }
  const CH = [['ОДАМ ЁНИДА', 'бўйингизга нисбатан'], ['МАТЕРИАЛИ', 'эман ранги, ЛДСП 18 мм'], ['ХОНАДА', 'ўтиш жойи қолади'], ['ЎЛЧАМЛАРИ', '200 × 160 × 60 см'], ['РАНГЛАРИ', '3 хил'], ['ОЧИЛАДИ', 'енгил, овозсиз']];
  const C0 = 5.8, CD = 0.9;
  function sceneProof(c, t) {
    const i = Math.min(5, Math.floor((t - C0) / CD)), lt = t - C0 - i * CD;
    c.save(); cam(c, lt, 0, CD, 1.0, 1.05, (i % 2 ? -1 : 1) * 30);
    if (i === 0) { room(c); wardrobe(c, { cx: 600 }); person(c, 175, WR.by, 600); }
    else if (i === 1) { MK.TEX.wood('#C8935A', '#7A4E26')(c, -100, -100, W + 200, H + 200); const sx = lerp(-400, W + 400, lt / CD), sg = c.createLinearGradient(sx - 220, 0, sx + 220, 0); sg.addColorStop(0, 'rgba(255,255,255,0)'); sg.addColorStop(0.5, 'rgba(255,245,225,0.35)'); sg.addColorStop(1, 'rgba(255,255,255,0)'); c.fillStyle = sg; c.fillRect(0, 0, W, H); }
    else if (i === 2) { room(c, '#EFE6D6'); c.fillStyle = '#BFD3E0'; rr(c, 90, 560, 300, 420, 8); c.fill(); c.strokeStyle = '#fff'; c.lineWidth = 14; c.strokeRect(90, 560, 300, 420); wardrobe(c, { cx: 760, w: 440, h: 620 }); c.fillStyle = '#6B8F71'; rr(c, 60, 1180, 520, 120, 26); c.fill(); }
    else if (i === 3) { room(c); wardrobe(c, {}); MK.size(c, { x0: WR.cx - WR.w / 2 - 70, y0: WR.by - WR.h - 18, x1: WR.cx - WR.w / 2 - 70, y1: WR.by + 18, label: '200 см', fz: 46, t: lt, t0: 0.05, side: -1 }); MK.size(c, { x0: WR.cx - WR.w / 2 - 18, y0: WR.by + 90, x1: WR.cx + WR.w / 2 + 18, y1: WR.by + 90, label: '160 см', fz: 46, t: lt, t0: 0.15, side: 1 }); }
    else if (i === 4) { room(c); const B = [['#C8935A', '#8E5D31'], ['#F1ECE4', '#CFC6B8'], ['#4A3424', '#2A1C12']][Math.min(2, Math.floor(lt / 0.3))]; wardrobe(c, { body: B }); }
    else { room(c); wardrobe(c, { open: 0.5 - 0.5 * Math.cos(Math.PI * 2 * clamp(lt / CD) ) }); }
    c.restore();
    if (i === 4) { c.save(); MK.swatches(c, { x: 289, y: 1300, size: 150, t: lt, t0: 0.02, items: [{ color: MK.TEX.wood('#C8935A', '#7A4E26'), name: 'ЭМАН' }, { color: '#F1ECE4', name: 'ОҚ' }, { color: MK.TEX.wood('#4A3424', '#2A1C12'), name: 'ВЕНГЕ' }] }); c.restore(); }
    MK.proof(c, { i: i + 1, n: 6, title: CH[i][0], sub: CH[i][1], t, t0: C0 + i * CD, y: 280, size: 92 });
  }
  function logo(c, x, y, k) { c.save(); c.translate(x, y); c.scale(k, k); c.fillStyle = P.oak; c.beginPath(); c.arc(0, -70, 70, 0, Math.PI * 2); c.fill();
    c.fillStyle = P.green; c.font = '400 92px "Montserrat 900"'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText('S', 0, -66);
    c.fillStyle = P.cream; c.font = '400 76px "Montserrat 900"'; c.fillText('SHODIYONA', 0, 60); c.font = '700 30px "Inter Tight"'; c.fillStyle = P.oak; c.fillText('M E B E L', 0, 112); c.restore(); }
  window.__seek = async (t) => {
    await MK.warm(); await document.fonts.load('400 96px "Montserrat 900"'); await document.fonts.load('800 30px "Inter Tight"');
    ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.fillStyle = P.green; ctx.fillRect(0, 0, W, H);
    if (t < C0) sceneFill(ctx, t); else if (t < 11.2) sceneProof(ctx, t);
    if (t >= 5.55 && t < 6.15) MK.wipe(ctx, { t, t0: 5.55, dur: 0.6 });
    if (t >= 10.9 && t < 11.5) MK.wipe(ctx, { t, t0: 10.9, dur: 0.6 });
    if (t >= 11.2) MK.cta(ctx, { t, t0: 11.2, phone: '+998 77 923 01 91', size: 84, lines: ['Ичига қаранг — кейин танланг', 'Telegram: @ShodiyonaMebelUz'], logo });
    if (t < 11.2) { ctx.save(); ctx.font = '800 26px "Inter Tight"'; ctx.fillStyle = 'rgba(22,19,15,0.55)'; ctx.textAlign = 'left'; ctx.fillText('НАМУНА · демо', 60, 1880 - 400 + 70); ctx.restore(); }
    if (!/nograin/.test(location.search)) MK.grain(ctx, { t, amt: 0.05 });
  };
})();
