/* Демо 9:16 (15 с, 24 fps), стиль Shodiyona: «Номи — аслида» (MK.strike) — название вещи зачёркивается, на его месте настоящая роль в семье:
 * СТОЛ → ОИЛА ДАСТУРХОНИ · КИТОБ ЖАВОНИ → БОЛАНГИЗ КУТУБХОНАСИ · ПАРТА → БИРИНЧИ «БЕШ». Финал: «Номи — мебель. Маъносини сиз берасиз.» + лого + телефон.
 * Разведка «Мебель» 10.11.2026 (мотив: IKEA Canada «You Give It Meaning», 09–11.2026). Товар — лофт-ассортимент Shodiyona. Без цен. «НАМУНА». */
(function () {
  const cv = document.getElementById('c'), ctx = cv.getContext('2d'), W = 1080, H = 1920, { E, prog, clamp, lerp, rr } = MK;
  MK.setFonts({ head: '"IDB"', body: '"IDX"' }); MK.setPalette({ accent: '#B8814A' }); const P = MK.P, G = P.green, OAK = P.oak, CR = P.cream;
  window.__comp = { width: W, height: H, fps: 24, duration: 15 };
  const img = {}; for (const n of ['logo', 'icon']) { img[n] = new Image(); img[n].src = n + '.png'; }
  const ready = () => Promise.all(Object.values(img).map((i) => (i.complete && i.naturalWidth ? 1 : new Promise((r) => { i.onload = r; i.onerror = r; }))));
  const SC = [
    { t0: 0.9, out: 4.3, word: 'СТОЛ', real: ['ОИЛА', 'ДАСТУРХОНИ'], chips: ['тушлик', 'дарс', 'туғилган кун'], n: '01' },
    { t0: 4.5, out: 7.9, word: 'ЖАВОН', real: ['БОЛАНГИЗ', 'КУТУБХОНАСИ'], chips: ['биринчи китоб', 'эртаклар', 'медаллар'], n: '02' },
    { t0: 8.1, out: 11.5, word: 'ПАРТА', real: ['БИРИНЧИ', '«БЕШ» БАҲО'], chips: ['ҳарфлар', 'расмлар', 'орзулар'], n: '03' }];
  const CTA = 11.9;
  function studio(c, t) { const g = c.createLinearGradient(0, 0, 0, H); g.addColorStop(0, '#FFFFFF'); g.addColorStop(1, CR); c.fillStyle = g; c.fillRect(0, 0, W, H);
    c.save(); c.globalAlpha = 0.09; c.strokeStyle = OAK; c.lineWidth = 2; for (let i = -1; i < 9; i++) { const x = i * 150 + (t * 14) % 150; c.beginPath(); c.moveTo(x, 0); c.lineTo(x + 260, H); c.stroke(); } c.restore(); }
  const txt = (c, s, x, y, fz, col, fam = 'IDB') => { c.font = `400 ${fz}px "${fam}"`; c.fillStyle = col; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText(s, x, y); };
  function finale(c, t) { const a = CTA; studio(c, t);
    const s0 = E.outBack(prog(t, a, a + 0.45)); c.save(); c.globalAlpha = clamp(s0); txt(c, 'НОМИ — МЕБЕЛЬ.', W / 2, 300, 92, G); c.restore();
    const s3 = E.outBack(prog(t, a + 0.4, a + 0.85)); c.save(); c.globalAlpha = clamp(s3); txt(c, 'МАЪНОСИНИ', W / 2, 420, 92, OAK); txt(c, 'СИЗ БЕРАСИЗ.', W / 2, 525, 92, OAK); c.restore();
    const lk = E.outBack(prog(t, a + 0.9, a + 1.4), 1.5), lw = 560 * lk, lh = lw * 1635 / 1981; if (lk > 0) c.drawImage(img.logo, W / 2 - lw / 2, 900 - lh / 2, lw, lh);
    const ph = '+998 77 923 01 91', n = Math.floor(clamp((t - a - 1.5) / 0.05, 0, ph.length));
    if (n > 0) { c.save(); c.shadowColor = 'rgba(0,0,0,0.2)'; c.shadowBlur = 20; c.shadowOffsetY = 8; c.fillStyle = G; rr(c, 110, 1240, 860, 130, 65); c.fill(); c.restore();
      c.font = '400 70px "IDB"'; const full = c.measureText(ph).width; c.fillStyle = CR; c.textAlign = 'left'; c.textBaseline = 'middle'; c.fillText(ph.slice(0, n), W / 2 - full / 2, 1308);
      if (n < ph.length || Math.floor(t * 2) % 2) { const cw = c.measureText(ph.slice(0, n)).width; c.fillStyle = OAK; c.fillRect(W / 2 - full / 2 + cw + 8, 1278, 7, 60); } }
    const tk = E.out3(prog(t, a + 2.4, a + 2.8)); c.save(); c.globalAlpha = tk; txt(c, 'Ишлаб чиқарувчидан — тўғридан-тўғри', W / 2, 1450, 40, G, 'IDX'); txt(c, 'Telegram: @ShodiyonaMebelUz', W / 2, 1515, 40, OAK, 'IDX'); c.restore(); }
  window.__seek = async (t) => {
    await MK.warm(); await ready(); for (const f of ['IDB', 'IDX']) await document.fonts.load(`400 60px "${f}"`);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    if (t < CTA) { studio(ctx, t);
      const ik = MK.life(t, 0, 11.4, 0.4), iw = 120 * ik; if (iw > 0) ctx.drawImage(img.icon, W / 2 - iw / 2, 95, iw, iw * 957 / 919);
      const hk = MK.life(t, 0, 11.4, 0.4); ctx.save(); ctx.globalAlpha = hk; txt(ctx, 'БИЗДА УНИНГ НОМИ…', W / 2, 330 + (1 - hk) * 40, 64, G); ctx.restore();
      for (const s of SC) { MK.strike(ctx, { x: W / 2, y: 980, size: 200, word: s.word, real: s.real, chips: s.chips, t, t0: s.t0, out: s.out, ink: G, line: OAK, realInk: OAK, chipBg: G, chipFg: CR });
        const nk = MK.life(t, s.t0, s.out, 0.3); if (nk > 0) { ctx.save(); ctx.globalAlpha = nk; txt(ctx, s.n + ' / 03', W / 2, 1720, 44, OAK); ctx.restore(); }
        const ak = MK.life(t, s.t0 + 1.5, s.out, 0.3); if (ak > 0) { ctx.save(); ctx.globalAlpha = ak; txt(ctx, 'СИЗДА ЭСА…', W / 2, 440, 52, OAK, 'IDX'); ctx.restore(); } }
      ctx.save(); ctx.font = '400 26px "IDX"'; ctx.fillStyle = 'rgba(31,58,40,0.5)'; ctx.textAlign = 'left'; ctx.fillText('НАМУНА · демо', 60, 1890); ctx.restore(); }
    if (t >= 11.6 && t < 12.2) MK.wipe(ctx, { t, t0: 11.6, dur: 0.6, color: OAK });
    if (t >= CTA) finale(ctx, t);
    if (!/nograin/.test(location.search)) MK.grain(ctx, { t, amt: 0.025 });
  };
})();
