/* Демо 9:16 (10,5 с, 24 fps): «Литромер» (MK.meter) — живой счёт «Андижон бугун ичди: … л» барабанными цифрами + «+10 Л» на каждый налив.
 * Цифры (12 318 → 12 480 л) — НАМУНА, не данные GOLD WATER. Цена 10 л = 5 000 сўм — из заказа goldwater-2026-11-05. Разведка «Вода» 05.11.2026 (мотив: Yo-Chi «Bottle Battle», живой счёт на экранах). */
(function () {
  const cv = document.getElementById('c'), ctx = cv.getContext('2d'), W = 1080, H = 1920, { E, prog, clamp, lerp, rr } = MK;
  MK.setPalette({ green: '#0B2440', oak: '#D4A63A', accent: '#F2C14E', cream: '#FFF8E7', ink: '#10151F' }); const P = MK.P;
  window.__comp = { width: W, height: H, fps: 24, duration: 10.5 };
  const L0 = 12318, L1 = 12480, TL = 6.6; // литры: старт, финиш, время докрутки
  const litres = (t) => lerp(L0, L1, E.inOut3(prog(t, 0.3, TL)) * 0.25 + prog(t, 0.3, TL) * 0.75);
  function water(c, t) { // глубокая вода: градиент + бегущие блики (каустика) + пузырьки
    const g = c.createLinearGradient(0, 0, 0, H); g.addColorStop(0, '#06162A'); g.addColorStop(0.55, '#0C3358'); g.addColorStop(1, '#125A86'); c.fillStyle = g; c.fillRect(0, 0, W, H);
    c.save(); c.globalCompositeOperation = 'lighter';
    for (let i = 0; i < 7; i++) { const y = 200 + i * 260, a = 0.05 + 0.03 * Math.sin(t * 1.3 + i); c.strokeStyle = `rgba(140,210,255,${a})`; c.lineWidth = 26; c.beginPath();
      for (let x = -40; x <= W + 40; x += 30) c.lineTo(x, y + 34 * Math.sin(x / 140 + t * 1.6 + i * 1.7) + 18 * Math.sin(x / 61 - t * 2.1)); c.stroke(); }
    for (let i = 0; i < 26; i++) { const sx = (i * 397) % W, sp = 90 + (i * 53) % 120, r = 4 + (i * 7) % 12, y = H + 40 - ((t * sp + i * 211) % (H + 120));
      c.fillStyle = 'rgba(200,235,255,0.16)'; c.beginPath(); c.arc(sx + 14 * Math.sin(t * 2 + i), y, r, 0, Math.PI * 2); c.fill(); }
    c.restore(); }
  const title = (c, s, t, t0, out, y, fz, col) => { const k = MK.life(t, t0, out, 0.4); if (k <= 0) return; c.save(); c.globalAlpha *= k; c.font = `400 ${fz}px "Montserrat 900"`; c.textAlign = 'center'; c.textBaseline = 'middle';
    const yy = y + (1 - E.outBack(prog(t, t0, t0 + 0.45))) * 50; c.lineJoin = 'round'; c.lineWidth = fz * 0.16; c.strokeStyle = 'rgba(4,12,24,0.7)'; c.strokeText(s, W / 2, yy); c.fillStyle = col || P.cream; c.fillText(s, W / 2, yy); c.restore(); };
  function pour(c, t, t0) { // «+10 Л» всплывает над литромером
    const k = prog(t, t0, t0 + 1.1); if (k <= 0 || k >= 1) return; c.save(); c.globalAlpha = 1 - E.inOut3(prog(t, t0 + 0.6, t0 + 1.1));
    const y = 640 - E.out3(k) * 110, s = E.outBack(prog(t, t0, t0 + 0.3)); c.translate(W / 2 + 380, y); c.scale(s, s); c.fillStyle = P.accent; rr(c, -120, -48, 240, 96, 48); c.fill();
    c.font = '400 58px "Montserrat 900"'; c.fillStyle = P.ink; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText('+10 Л', 0, 4); c.restore(); }
  function priceCard(c, t, t0, out) { const k = MK.life(t, t0, out, 0.45); if (k <= 0) return; c.save(); c.globalAlpha *= k;
    const s = E.outBack(prog(t, t0, t0 + 0.5)); c.translate(W / 2, 1380); c.scale(s, s); c.fillStyle = P.accent; rr(c, -420, -130, 840, 260, 40); c.fill();
    c.fillStyle = P.ink; c.textAlign = 'center'; c.textBaseline = 'middle'; c.font = '400 108px "Montserrat 900"'; c.fillText('10 Л = 5 000', 0, -22); c.font = '400 52px "Montserrat 900"'; c.fillText('СЎМ · 24/7', 0, 74); c.restore(); }
  function logo(c, x, y, k) { c.save(); c.translate(x, y); c.scale(k, k); c.fillStyle = P.oak; c.beginPath(); c.moveTo(0, -170); c.bezierCurveTo(70, -80, 90, -30, 90, 10); c.arc(0, 10, 90, 0, Math.PI); c.bezierCurveTo(-90, -30, -70, -80, 0, -170); c.fill();
    c.fillStyle = '#FFF3C8'; c.beginPath(); c.ellipse(-30, 0, 16, 34, -0.4, 0, Math.PI * 2); c.fill();
    c.fillStyle = P.cream; c.font = '400 96px "Montserrat 900"'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText('GOLD WATER', 0, 190); c.font = '400 38px "Inter Tight"'; c.fillStyle = P.accent; c.fillText('A N D I J O N', 0, 262); c.restore(); }
  window.__seek = async (t) => {
    await MK.warm(); await document.fonts.load('400 96px "Montserrat 900"'); await document.fonts.load('800 30px "Inter Tight"');
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    if (t < 7.3) { ctx.save(); const z = lerp(1, 1.05, E.inOut3(prog(t, 0, 7.3))); ctx.translate(W / 2, H / 2); ctx.scale(z, z); ctx.translate(-W / 2, -H / 2); water(ctx, t); ctx.restore();
      title(ctx, 'АНДИЖОН БУГУН', t, 0.0, 6.9, 430, 104); title(ctx, 'ИЧДИ:', t, 0.15, 6.9, 560, 104, P.accent);
      MK.meter(ctx, { x: W / 2 - 40, y: 860, value: litres, digits: 5, size: 168, unit: 'Л', label: 'GOLD WATER аппаратларидан', t, t0: 0.1, out: 6.9 });
      for (const p0 of [1.6, 2.9, 4.1, 5.3]) pour(ctx, t, p0);
      title(ctx, 'ТОЗА СУВ — ҲАР КУНИ', t, 3.6, 6.9, 1160, 74);
      priceCard(ctx, t, 4.4, 6.9);
      ctx.save(); ctx.font = '800 28px "Inter Tight"'; ctx.fillStyle = 'rgba(255,248,231,0.5)'; ctx.textAlign = 'left'; ctx.fillText('НАМУНА · демо рақамлар', 60, 1840); ctx.restore(); }
    if (t >= 6.9 && t < 7.5) MK.wipe(ctx, { t, t0: 6.9, dur: 0.6 });
    if (t >= 7.2) MK.cta(ctx, { t, t0: 7.2, phone: '+998 97 290 10 40', size: 94, lines: ['Сиз ҳам қўшилинг — 24/7', 'Ҳисобга ҳар бир литр киради'], logo });
    if (!/nograin/.test(location.search)) MK.grain(ctx, { t, amt: 0.04 });
  };
})();
