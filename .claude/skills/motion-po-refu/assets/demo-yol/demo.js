/* Демо 9:16 (13 с, 24 fps), стиль VOLIDAM × Safo Marva (бордо + золото): «Гуруҳ кундалиги» — дневник группы паломников для семей дома.
 * MK.day (штамп «3-КУН · МАДИНА») + MK.route (маршрут Хўжаобод → Мадина → Миқот → Макка → Уйга, маркер едет по дням).
 * В центре — окно «здесь живой кадр группы» (в боевом ролике: 15–20 с телефонной съёмки команды, с согласия людей в кадре).
 * Каабу/Харам НЕ рисуем (правило README «Умра»). Цен нет. Маршрут — по реальному плану группы. Разведка «Умра» 07.11.2026. «НАМУНА». */
(function () {
  const cv = document.getElementById('c'), ctx = cv.getContext('2d'), W = 1080, H = 1920, { E, prog, clamp, lerp, rr } = MK;
  MK.setFonts({ head: '"IDB"', body: '"IDX"' }); MK.setPalette({ accent: '#E0A92A', cream: '#F6F0DE' });
  const GOLD = '#E0A92A', GL = '#F6DC86', BOR = '#5A0606', BOR2 = '#6E1E2B', CR = '#F6F0DE';
  window.__comp = { width: W, height: H, fps: 24, duration: 13 };
  const img = { emblem: new Image() }; img.emblem.src = 'emblem.png';
  const ready = () => Promise.all(Object.values(img).map((i) => (i.complete && i.naturalWidth ? 1 : new Promise((r) => { i.onload = r; i.onerror = r; }))));
  const STOPS = [{ name: 'ХЎЖАОБОД', sub: 'учиш' }, { name: 'МАДИНА', sub: '' }, { name: 'МИҚОТ', sub: 'эҳром' }, { name: 'МАККА', sub: '' }, { name: 'УЙГА', sub: 'қайтиш' }];
  const DAYS = [[1.9, 0, 1, 'ХЎЖАОБОД', 'Аэропорт · дуо билан'], [3.5, 1, 3, 'МАДИНА', 'Гуруҳ соғ-омон'], [5.1, 2, 5, 'МИҚОТ', 'Эҳромга кирдик'], [6.7, 3, 6, 'МАККА', 'Онахонлар билан бирга'], [8.3, 4, 12, 'УЙГА', 'Кутиб олинг']];
  const AT = DAYS.map((d) => [d[0], d[1]]), OUT = 9.6, CTA = 10.0;
  function bg(c, t) { const g = c.createLinearGradient(0, 0, 0, H); g.addColorStop(0, BOR2); g.addColorStop(1, '#2A0508'); c.fillStyle = g; c.fillRect(0, 0, W, H);
    c.save(); c.globalAlpha = 0.07; c.strokeStyle = GL; c.lineWidth = 2; // мягкий геометрический орнамент (8-конечные звёзды), медленный дрейф
    for (let j = 0; j < 9; j++) for (let i = 0; i < 6; i++) { const x = i * 200 + (j % 2) * 100, y = j * 230 - 100 + (t * 10) % 230, r = 50; c.beginPath();
      for (let q = 0; q < 16; q++) { const a = q * Math.PI / 8, rr2 = q % 2 ? r * 0.62 : r; c.lineTo(x + Math.cos(a) * rr2, y + Math.sin(a) * rr2); } c.closePath(); c.stroke(); } c.restore(); }
  const txt = (c, s, x, y, fz, col, fam = 'IDB') => { c.font = `400 ${fz}px "${fam}"`; c.fillStyle = col; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText(s, x, y); };
  const title = (c, s, t, t0, out, y, fz, col) => { const k = MK.life(t, t0, out, 0.4); if (k <= 0) return; c.save(); c.globalAlpha *= k; txt(c, s, W / 2, y + (1 - E.outBack(prog(t, t0, t0 + 0.45))) * 50, fz, col); c.restore(); };
  function frame(c, t) { // окно под живой кадр группы
    const k = MK.life(t, 1.5, OUT, 0.5); if (k <= 0) return; const x = 110, y = 600, w = W - 220, h = 640;
    c.save(); c.globalAlpha *= k; c.shadowColor = 'rgba(0,0,0,0.45)'; c.shadowBlur = 30; c.shadowOffsetY = 12; c.fillStyle = 'rgba(20,3,5,0.55)'; rr(c, x, y, w, h, 34); c.fill(); c.shadowColor = 'transparent';
    c.lineWidth = 6; c.strokeStyle = GOLD; c.setLineDash([26, 18]); c.lineDashOffset = -t * 40; rr(c, x, y, w, h, 34); c.stroke(); c.setLineDash([]);
    const rec = Math.floor(t * 2) % 2; c.fillStyle = rec ? '#E5484D' : 'rgba(229,72,77,0.35)'; c.beginPath(); c.arc(x + 60, y + 60, 16, 0, 7); c.fill();
    c.font = '400 34px "IDX"'; c.fillStyle = CR; c.textAlign = 'left'; c.textBaseline = 'middle'; c.fillText('ЖОНЛИ КАДР', x + 90, y + 61);
    txt(c, 'бу ерда — гуруҳдан', W / 2, y + h / 2 - 30, 46, CR, 'IDX'); txt(c, '15–20 сония видео', W / 2, y + h / 2 + 35, 46, GL, 'IDX'); c.restore(); }
  function finale(c, t) { const a = CTA; bg(c, t);
    const lk = E.outBack(prog(t, a + 0.1, a + 0.7), 1.5), lw = 420 * lk, lh = lw * 875 / 840; if (lk > 0) c.drawImage(img.emblem, W / 2 - lw / 2, 470 - lh / 2, lw, lh);
    const s1 = E.out3(prog(t, a + 0.6, a + 1.0)), s2 = E.out3(prog(t, a + 0.75, a + 1.15)); c.save(); c.globalAlpha = s1; txt(c, 'ҲАР КУНИ —', W / 2, 800 + (1 - s1) * 30, 84, CR); c.globalAlpha = s2; txt(c, 'ГУРУҲИМИЗДА', W / 2, 900 + (1 - s2) * 30, 84, GOLD); c.restore();
    const tk = E.out3(prog(t, a + 1.2, a + 1.6)); c.save(); c.globalAlpha = tk;
    c.fillStyle = GOLD; rr(c, 110, 1010, W - 220, 120, 60); c.fill(); txt(c, '👥 @UmraXojaobod', W / 2, 1072, 56, BOR, 'IDB');
    txt(c, '🤖 Бот: @VolidamUmraBot', W / 2, 1210, 46, CR, 'IDX'); txt(c, '+998 90 766 82 84', W / 2, 1290, 56, GL, 'IDB');
    txt(c, 'VOLIDAM · SAFO MARVA TOUR ҲАМКОРИ', W / 2, 1400, 34, 'rgba(246,240,222,0.7)', 'IDX'); c.restore(); }
  window.__seek = async (t) => {
    await MK.warm(); await ready(); for (const f of ['IDB', 'IDX']) await document.fonts.load(`400 60px "${f}"`);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    if (t < CTA) { bg(ctx, t);
      title(ctx, 'ОНАНГИЗ', t, 0.0, 1.7, 330, 118, CR); title(ctx, 'БУГУН ҚАЕРДА?', t, 0.15, 1.7, 460, 104, GOLD);
      let d = null; for (const x of DAYS) if (t >= x[0] - 0.4) d = x;
      if (d) MK.day(ctx, { x: W / 2, y: 330, n: d[2], place: d[3], note: d[4], t, t0: DAYS[0][0] - 0.4, tn: d[0] - 0.4, out: OUT, size: 130, bg: BOR, fg: CR, accent: GOLD });
      frame(ctx, t);
      MK.route(ctx, { x0: 160, x1: W - 160, y: 1460, stops: STOPS, at: AT, t, t0: 1.4, out: OUT, size: 48, done: GOLD, ink: CR, dot: BOR });
      title(ctx, 'Оилангиз уйда ҳар кунини кўради', t, 2.2, OUT, 1720, 44, CR);
      ctx.save(); ctx.font = '400 26px "IDX"'; ctx.fillStyle = 'rgba(246,240,222,0.45)'; ctx.textAlign = 'left'; ctx.fillText('НАМУНА · демо', 60, 1890); ctx.restore(); }
    if (t >= 9.7 && t < 10.3) MK.wipe(ctx, { t, t0: 9.7, dur: 0.6, color: GOLD });
    if (t >= CTA) finale(ctx, t);
    if (!/nograin/.test(location.search)) MK.grain(ctx, { t, amt: 0.02 });
  };
})();
