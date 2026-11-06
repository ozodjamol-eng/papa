/* Shodiyona «Янги уйга кўчяпсизми?» — познавательный ролик с озвучкой (06.11.2026), 9:16, 30 к/с.
 * Сценарий утверждён владельцем: хук → боль «дўконма-дўкон» → совет «хона-хона рўйхат» (чек-лист в такт голосу)
 * → «ҲАММА БИР ЖОЙДА» + 3 довода → финал (логотип, слоган, телефон, Telegram). Тайминг — timing2.json (по словам диктора). */
(function () {
  const cv = document.getElementById('c'), ctx = cv.getContext('2d'), W = 1080, H = 1920, { E, prog, clamp, lerp, rr } = MK;
  MK.setFonts({ head: '"IDB"', body: '"IDX"' }); MK.setPalette({ accent: '#B8814A' }); const P = MK.P, G = P.green, OAK = P.oak, WAL = P.walnut, CR = P.cream;
  const K = window.TIMING.keys, TOTAL = window.TIMING.total;
  window.__comp = { width: W, height: H, fps: 30, duration: TOTAL };
  const img = {}; for (const n of ['logo', 'icon']) { img[n] = new Image(); img[n].src = n + '.png'; }
  const ready = () => Promise.all(Object.values(img).map((i) => (i.complete && i.naturalWidth ? 1 : new Promise((r) => { i.onload = r; i.onerror = r; }))));

  // границы сцен
  const S2 = K.dokon - 0.35, S3 = 12.75, S4 = 28.35, S5 = 41.15;
  const ITEMS = [
    { name: 'Ошхона столи', note: 'ОШХОНА', t: K.stol }, { name: '4 та стул', note: 'ОШХОНА', t: K.stul },
    { name: 'Китоб жавони', note: 'МЕҲМОНХОНА', t: K.javon }, { name: 'Кресло', note: 'МЕҲМОНХОНА', t: K.kreslo },
    { name: 'Иш столи', note: 'ИШ ХОНАСИ', t: K.ish }, { name: 'Болалар партаси', note: 'БОЛАЛАР ХОНАСИ', t: K.parta }];
  // разные магазины — разные цвета (хаос)
  const SHOPS = [
    { w: 'СТОЛ', c: '#C9A27A', x: 270, y: 760, r: -0.16, t: K.dokon },
    { w: 'СТУЛ', c: '#3B3B3B', x: 790, y: 700, r: 0.13, t: K.stol2 - 0.2 },
    { w: 'ЖАВОН', c: '#E7E2D8', x: 560, y: 1010, r: -0.05, t: K.stul2 - 0.2 },
    { w: 'КРЕСЛО', c: '#8E3B2E', x: 250, y: 1250, r: 0.1, t: K.stul2 + 0.15 },
    { w: 'ПАРТА', c: '#6E8B9C', x: 820, y: 1220, r: -0.12, t: K.stul2 + 0.45 }];

  function studio(c, t) { const g = c.createLinearGradient(0, 0, 0, H); g.addColorStop(0, '#FFFFFF'); g.addColorStop(1, CR); c.fillStyle = g; c.fillRect(0, 0, W, H);
    c.save(); c.globalAlpha = 0.08; c.strokeStyle = OAK; c.lineWidth = 2; for (let i = -1; i < 9; i++) { const x = i * 150 + (t * 14) % 150; c.beginPath(); c.moveTo(x, 0); c.lineTo(x + 260, H); c.stroke(); } c.restore(); }
  const txt = (c, s, x, y, fz, col, fam = 'IDB', al = 'center') => { c.font = `400 ${fz}px "${fam}"`; c.fillStyle = col; c.textAlign = al; c.textBaseline = 'middle'; c.fillText(s, x, y); };
  const fitTxt = (c, s, x, y, fz, col, maxW, fam = 'IDB') => { c.font = `400 ${fz}px "${fam}"`; const k = Math.min(1, maxW / c.measureText(s).width); txt(c, s, x, y, fz * k, col, fam); };
  const pop = (c, t, t0, out, x, y, draw, dur = 0.45) => { const k = MK.life(t, t0, out, 0.35); if (k <= 0) return; const s = E.outBack(prog(t, t0, t0 + dur), 1.8);
    c.save(); c.globalAlpha *= k; c.translate(x, y); c.scale(s, s); draw(c); c.restore(); };
  const rise = (c, t, t0, out, draw) => { const k = MK.life(t, t0, out, 0.4); if (k <= 0) return; c.save(); c.globalAlpha *= k; c.translate(0, (1 - E.out3(prog(t, t0, t0 + 0.45))) * 50); draw(c); c.restore(); };
  function pillBox(c, s, fz, bg, fg, padX = 0.9) { c.font = `400 ${fz}px "IDB"`; const w = c.measureText(s).width + fz * padX * 2, h = fz * 1.75;
    c.save(); c.shadowColor = 'rgba(0,0,0,0.22)'; c.shadowBlur = 22; c.shadowOffsetY = 8; c.fillStyle = bg; rr(c, -w / 2, -h / 2, w, h, h / 2); c.fill(); c.restore();
    txt(c, s, 0, fz * 0.05, fz, fg); }

  // 1+2: хук и «дўконма-дўкон»
  function scene12(c, t) {
    studio(c, t);
    const up = E.inOut3(prog(t, S2, S2 + 0.6)); // заголовок уходит вверх и уменьшается
    const ik = MK.life(t, 0, S3 - 0.3, 0.4), iw = 130 * ik * lerp(1, 0.7, up); if (iw > 0) c.drawImage(img.icon, W / 2 - iw / 2, lerp(330, 90, up), iw, iw * 957 / 919);
    const ty = lerp(820, 300, up), fz = lerp(122, 96, up);
    rise(c, t, 0.15, S3 - 0.3, (c) => txt(c, 'ЯНГИ УЙГА', W / 2, ty, fz, G));
    rise(c, t, 0.3, S3 - 0.3, (c) => txt(c, 'КЎЧЯПСИЗМИ?', W / 2, ty + fz * 1.02, fz, OAK));
    // карточки магазинов: каждая своего цвета
    SHOPS.forEach((s, i) => {
      const k = MK.life(t, s.t, S3 - 0.35, 0.3); if (k <= 0) return;
      const drop = E.outBack(prog(t, s.t, s.t + 0.5), 1.4), shake = t > K.vaqt ? Math.sin((t - K.vaqt) * 20 + i) * 4 * Math.exp(-(t - K.vaqt) * 3) : 0;
      // хаос → порядок: в конце карточки слетаются в центр и исчезают
      const gather = E.inOut3(prog(t, S3 - 0.75, S3 - 0.3)), gx = lerp(s.x, W / 2, gather), gy = lerp(s.y, 1100, gather);
      c.save(); c.globalAlpha *= k; c.translate(gx + shake, gy - (1 - drop) * 260); c.rotate(s.r * (1 - gather)); c.scale(lerp(1, 0.5, gather), lerp(1, 0.5, gather));
      const w = 360, h = 230; c.shadowColor = 'rgba(0,0,0,0.25)'; c.shadowBlur = 26; c.shadowOffsetY = 10; c.fillStyle = '#FFFFFF'; rr(c, -w / 2, -h / 2, w, h, 26); c.fill();
      c.shadowColor = 'transparent'; c.fillStyle = s.c; rr(c, -w / 2 + 18, -h / 2 + 18, w - 36, 110, 16); c.fill();
      c.strokeStyle = 'rgba(0,0,0,0.12)'; c.lineWidth = 3; rr(c, -w / 2 + 18, -h / 2 + 18, w - 36, 110, 16); c.stroke();
      txt(c, s.w, 0, 62, 54, G); txt(c, `${i + 1}-ДЎКОН`, 0, -h / 2 + 73, 34, s.c === '#E7E2D8' ? G : '#FFFFFF', 'IDX');
      c.restore();
    });
    // «5 та дўкон — 5 хил ранг» + «вақт ҳам, пул ҳам»
    const hk = MK.life(t, K.vaqt - 0.9, S3 - 0.35, 0.35);
    if (hk > 0) { c.save(); c.globalAlpha *= hk; const s = E.outBack(prog(t, K.vaqt - 0.9, K.vaqt - 0.45), 1.6);
      c.translate(W / 2, 1530); c.scale(s, s); c.fillStyle = WAL; rr(c, -470, -85, 940, 170, 34); c.fill(); fitTxt(c, '5 ТА ДЎКОН — 5 ХИЛ РАНГ', 0, 4, 66, CR, 860); c.restore(); }
    pop(c, t, K.vaqt + 0.15, S3 - 0.35, W / 2 - 220, 1720, (c) => pillBox(c, 'ВАҚТ КЕТАДИ', 46, G, CR));
    pop(c, t, K.vaqt + 0.9, S3 - 0.35, W / 2 + 230, 1720, (c) => pillBox(c, 'ПУЛ КЕТАДИ', 46, OAK, '#FFFFFF'));
  }

  // 3: совет и чек-лист в такт голосу
  function scene3(c, t) {
    studio(c, t);
    const out = S4 - 0.4;
    const iw = 110 * MK.life(t, S3, out, 0.4); if (iw > 0) c.drawImage(img.icon, W / 2 - iw / 2, 80, iw, iw * 957 / 919);
    pop(c, t, K.maslahat - 0.05, out, W / 2, 260, (c) => pillBox(c, 'МАСЛАҲАТ', 44, OAK, '#FFFFFF'));
    rise(c, t, K.maslahat + 0.5, out, (c) => txt(c, 'ХОНА-ХОНА', W / 2, 395, 104, G));
    rise(c, t, K.maslahat + 0.7, out, (c) => txt(c, 'РЎЙХАТ ТУЗИНГ', W / 2, 500, 104, OAK));
    MK.checklist(c, { x: 70, w: W - 140, y: 610, rowH: 162, size: 60, items: ITEMS, times: ITEMS.map((it) => it.t), lag: 0.5, t, t0: 0, out,
      rowBg: '#FFFFFF', done: G, ink: G, inkDone: CR, box: OAK, boxLine: OAK, tally: { x: W / 2, y: 1745, size: 140, label: 'ТАЙЁР', color: G, full: OAK, bg: G, fg: CR } });
  }

  // 4: «ҳамма бир жойда» + доводы
  function scene4(c, t) {
    studio(c, t);
    const out = S5 - 0.4;
    const lk = E.outBack(prog(t, S4 + 0.2, S4 + 0.8), 1.5), lw = 560 * lk, lh = lw * 1635 / 1981; if (lk > 0) { c.save(); c.globalAlpha *= MK.life(t, S4, out, 0.3); c.drawImage(img.logo, W / 2 - lw / 2, 330 - lh / 2, lw, lh); c.restore(); }
    MK.badge(c, { x: W / 2, y: 900, r: 250, lines: ['ҲАММА', 'БИР ЖОЙДА'], t, t0: K.hamma - 0.25, out, color: OAK, ink: CR });
    rise(c, t, K.hamma + 1.3, out, (c) => { txt(c, 'ИШЛАБ ЧИҚАРУВЧИДАН —', W / 2, 1245, 58, G); txt(c, 'ТЎҒРИДАН-ТЎҒРИ', W / 2, 1320, 58, OAK); });
    pop(c, t, K.vositachisiz - 0.1, out, W / 2, 1480, (c) => pillBox(c, '✓  ВОСИТАЧИСИЗ', 52, G, CR));
    pop(c, t, K.arzon - 0.1, out, W / 2, 1610, (c) => pillBox(c, '✓  АРЗОНРОҚ', 52, G, CR));
    pop(c, t, K.uslub - 0.1, out, W / 2, 1740, (c) => pillBox(c, '✓  БИР УСЛУБ', 52, G, CR));
  }

  // 5: финал
  function finale(c, t) { const a = S5; studio(c, t);
    const lk = E.outBack(prog(t, a + 0.1, a + 0.7), 1.5), lw = 680 * lk, lh = lw * 1635 / 1981; if (lk > 0) c.drawImage(img.logo, W / 2 - lw / 2, 520 - lh / 2, lw, lh);
    const s1 = E.out3(prog(t, a + 0.5, a + 0.9)), s2 = E.out3(prog(t, a + 0.65, a + 1.05)); c.save(); c.globalAlpha = s1; txt(c, 'ИШЛАБ ЧИҚАРУВЧИДАН —', W / 2, 900 + (1 - s1) * 30, 60, G); c.globalAlpha = s2; txt(c, 'ТЎҒРИДАН-ТЎҒРИ', W / 2, 975 + (1 - s2) * 30, 60, OAK); c.restore();
    const tg = K.telegram - 0.2, tk = E.out3(prog(t, tg, tg + 0.4));
    c.save(); c.globalAlpha = tk; txt(c, 'Рўйхатингизни Telegram’га юборинг —', W / 2, 1090 + (1 - tk) * 20, 46, G, 'IDX'); txt(c, 'ҳаммасини йиғиб берамиз', W / 2, 1150 + (1 - tk) * 20, 46, G, 'IDX'); c.restore();
    const ph = '+998 77 923 01 91', n = Math.floor(clamp((t - (K.yigib - 0.6)) / 0.05, 0, ph.length));
    if (n > 0) { c.save(); c.shadowColor = 'rgba(0,0,0,0.2)'; c.shadowBlur = 20; c.shadowOffsetY = 8; c.fillStyle = G; rr(c, 110, 1250, 860, 135, 67); c.fill(); c.restore();
      c.font = '400 74px "IDB"'; const full = c.measureText(ph).width; c.fillStyle = CR; c.textAlign = 'left'; c.textBaseline = 'middle'; c.fillText(ph.slice(0, n), W / 2 - full / 2, 1320);
      if (n < ph.length || Math.floor(t * 2) % 2) { const cw = c.measureText(ph.slice(0, n)).width; c.fillStyle = OAK; c.fillRect(W / 2 - full / 2 + cw + 8, 1290, 7, 60); } }
    pop(c, t, K.telegram + 0.3, null, W / 2, 1480, (c) => pillBox(c, 'Telegram: @ShodiyonaMebelUz', 46, OAK, '#FFFFFF'));
  }

  window.__seek = async (t) => {
    await MK.warm(); await ready(); for (const f of ['IDB', 'IDX']) await document.fonts.load(`400 60px "${f}"`);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    if (t < S3) scene12(ctx, t); else if (t < S4) scene3(ctx, t); else if (t < S5) scene4(ctx, t); else finale(ctx, t);
    for (const s of [S3, S4, S5]) if (t >= s - 0.3 && t < s + 0.3) MK.wipe(ctx, { t, t0: s - 0.3, dur: 0.6, color: OAK });
    if (!/nograin/.test(location.search)) MK.grain(ctx, { t, amt: 0.02 });
  };
})();
