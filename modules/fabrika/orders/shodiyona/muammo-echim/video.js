/* Shodiyona серия «МУАММО → ЕЧИМ» (06.11.2026), 9:16, 30 к/с, ?ep=1..6.
 * Схема: МУАММО (вопрос-боль, голос) → шторка → ЕЧИМ (настоящее фото товара + название) → товар уходит вверх,
 * ниже логотип, слоган, телефон, Telegram. Товар — только настоящие фото Shodiyona (zhivoy-poster/src). */
(function () {
  const cv = document.getElementById('c'), ctx = cv.getContext('2d'), W = 1080, H = 1920, { E, prog, clamp, lerp, rr } = MK;
  MK.setFonts({ head: '"IDB"', body: '"IDX"' }); MK.setPalette({ accent: '#B8814A' }); const P = MK.P, G = P.green, OAK = P.oak, CR = P.cream;
  const N = Number(new URLSearchParams(location.search).get('ep') || 1), EP = window.EPS[N];
  window.__comp = { width: W, height: H, fps: 30, duration: EP.TOT };
  const img = {}; for (const n of ['logo', 'icon', EP.img]) { img[n] = new Image(); img[n].src = n + '.png'; }
  const ready = () => Promise.all(Object.values(img).map((i) => (i.complete && i.naturalWidth ? 1 : new Promise((r) => { i.onload = r; i.onerror = r; }))));
  const SW = EP.ANS - 0.3; // шторка «муаммо → ечим»

  function studio(c, t) { const g = c.createLinearGradient(0, 0, 0, H); g.addColorStop(0, '#FFFFFF'); g.addColorStop(1, CR); c.fillStyle = g; c.fillRect(0, 0, W, H);
    c.save(); c.globalAlpha = 0.08; c.strokeStyle = OAK; c.lineWidth = 2; for (let i = -1; i < 9; i++) { const x = i * 150 + (t * 14) % 150; c.beginPath(); c.moveTo(x, 0); c.lineTo(x + 260, H); c.stroke(); } c.restore(); }
  const txt = (c, s, x, y, fz, col, fam = 'IDB') => { c.font = `400 ${fz}px "${fam}"`; c.fillStyle = col; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText(s, x, y); };
  const fitTxt = (c, s, x, y, fz, col, maxW, fam = 'IDB') => { c.font = `400 ${fz}px "${fam}"`; txt(c, s, x, y, fz * Math.min(1, maxW / c.measureText(s).width), col, fam); };
  function pillBox(c, s, fz, bg, fg, maxW = 960) { c.font = `400 ${fz}px "IDB"`; let tw = c.measureText(s).width; const k = Math.min(1, (maxW - fz * 1.8) / tw); fz *= k; tw *= k;
    const w = tw + fz * 1.8, h = fz * 1.75; c.save(); c.shadowColor = 'rgba(0,0,0,0.22)'; c.shadowBlur = 22; c.shadowOffsetY = 8; c.fillStyle = bg; rr(c, -w / 2, -h / 2, w, h, h / 2); c.fill(); c.restore(); txt(c, s, 0, fz * 0.05, fz, fg); }
  const pop = (c, t, t0, x, y, draw, out = null) => { const k = MK.life(t, t0, out, 0.3); if (k <= 0) return; const s = E.outBack(prog(t, t0, t0 + 0.45), 1.8);
    c.save(); c.globalAlpha *= k; c.translate(x, y); c.scale(s, s); draw(c); c.restore(); };

  function problem(c, t) {
    studio(c, t);
    c.save(); c.globalAlpha = 0.07 * E.out3(prog(t, 0, 0.8)); txt(c, '?', W / 2, 980 + Math.sin(t * 1.5) * 12, 1100, OAK); c.restore();
    const iw = 120 * MK.life(t, 0, null, 0.4); if (iw > 0) c.drawImage(img.icon, W / 2 - iw / 2, 160, iw, iw * 957 / 919);
    pop(c, t, 0.1, W / 2, 470, (c) => pillBox(c, 'МУАММО', 50, OAK, '#FFFFFF'));
    EP.q.forEach((s, i) => { const t0 = EP.Q0 + 0.1 + i * 0.25, k = E.out3(prog(t, t0, t0 + 0.45)); if (k <= 0) return;
      c.save(); c.globalAlpha = k; c.translate(0, (1 - k) * 60); fitTxt(c, s, W / 2, 860 + i * 150, 132, i ? OAK : G, 980); c.restore(); });
  }

  function solution(c, t) {
    studio(c, t);
    const im = img[EP.img], ar = im.naturalWidth / im.naturalHeight;
    const up = E.inOut3(prog(t, EP.E0 - 0.1, EP.E0 + 0.6));              // на концовке товар уходит вверх
    const box = lerp(820, 600, up), cy = lerp(880, 560, up);
    const w = ar >= 1 ? box : box * ar, h = ar >= 1 ? box / ar : box;
    const s = E.outBack(prog(t, EP.ANS, EP.ANS + 0.55), 1.4), fl = Math.sin((t - EP.ANS) * 1.6) * 8 * (1 - up);
    pop(c, t, EP.ANS - 0.15, W / 2, lerp(250, 150, up), (c) => pillBox(c, 'ЕЧИМ', 50, G, CR));
    if (s > 0) { c.save(); c.globalAlpha = clamp(s); // тень на полу
      c.fillStyle = 'rgba(31,58,40,0.16)'; c.beginPath(); c.ellipse(W / 2, cy + h / 2 + 18, w * 0.42 * s, 26 * s, 0, 0, Math.PI * 2); c.fill();
      c.translate(W / 2, cy + fl); c.scale(s, s); c.drawImage(im, -w / 2, -h / 2, w, h); c.restore(); }
    pop(c, t, EP.ANS + 0.35, W / 2, lerp(1440, 980, up), (c) => pillBox(c, EP.name, 66, G, CR));
    // концовка: логотип, слоган, телефон
    const e = EP.E0 + 0.35, lk = E.outBack(prog(t, e, e + 0.5), 1.5), lw = 420 * lk, lh = lw * 1635 / 1981;
    if (lk > 0) c.drawImage(img.logo, W / 2 - lw / 2, 1240 - lh / 2, lw, lh);
    const s1 = E.out3(prog(t, EP.SL - 0.3, EP.SL + 0.1)), s2 = E.out3(prog(t, EP.SL - 0.15, EP.SL + 0.25));
    c.save(); c.globalAlpha = s1; txt(c, 'ИШЛАБ ЧИҚАРУВЧИДАН —', W / 2, 1480 + (1 - s1) * 25, 54, G); c.globalAlpha = s2; txt(c, 'ТЎҒРИДАН-ТЎҒРИ', W / 2, 1548 + (1 - s2) * 25, 54, OAK); c.restore();
    pop(c, t, EP.SL + 0.35, W / 2, 1680, (c) => pillBox(c, '+998 77 923 01 91', 62, G, CR));
    pop(c, t, EP.SL + 0.6, W / 2, 1800, (c) => pillBox(c, 'Telegram: @ShodiyonaMebelUz', 40, OAK, '#FFFFFF'));
  }

  window.__seek = async (t) => {
    await MK.warm(); await ready(); for (const f of ['IDB', 'IDX']) await document.fonts.load(`400 60px "${f}"`);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    if (t < SW + 0.3) problem(ctx, t); else solution(ctx, t);
    if (t >= SW && t < SW + 0.6) MK.wipe(ctx, { t, t0: SW, dur: 0.6, color: OAK });
    if (!/nograin/.test(location.search)) MK.grain(ctx, { t, amt: 0.02 });
  };
})();
