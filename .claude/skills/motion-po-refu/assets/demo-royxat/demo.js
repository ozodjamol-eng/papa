/* Демо 9:16 (13 с, 24 fps), фирменный стиль Shodiyona: «Янги уй рўйхати» (MK.checklist) — список мебели для нового дома, галочки по одной,
 * счётчик «N/6 ТАЙЁР», бейдж «ҲАММА БИР ЖОЙДА», финал с логотипом, слоганом и телефоном. Товар — только лофт-ассортимент Shodiyona (столы, стулья, стеллажи, кресла, парты).
 * Разведка «Мебель» 06.11.2026 (мотив: IKEA Philippines «One Piece at a Time», 10.2026 — поворотный момент жизни «по одной вещи»). Без цен — цены только от Shodiyona. «НАМУНА». */
(function () {
  const cv = document.getElementById('c'), ctx = cv.getContext('2d'), W = 1080, H = 1920, { E, prog, clamp, lerp, rr } = MK;
  MK.setFonts({ head: '"IDB"', body: '"IDX"' }); MK.setPalette({ accent: '#B8814A' }); const P = MK.P, G = P.green, OAK = P.oak, CR = P.cream;
  window.__comp = { width: W, height: H, fps: 24, duration: 13 };
  const img = {}; for (const n of ['logo', 'icon']) { img[n] = new Image(); img[n].src = n + '.png'; }
  const ready = () => Promise.all(Object.values(img).map((i) => (i.complete && i.naturalWidth ? 1 : new Promise((r) => { i.onload = r; i.onerror = r; }))));
  const ITEMS = [
    { name: 'Ошхона столи', note: 'ОШХОНА' }, { name: '4 та стул', note: 'ОШХОНА' }, { name: 'Китоб жавони', note: 'МЕҲМОНХОНА' },
    { name: 'Иш столи', note: 'ИШ ХОНАСИ' }, { name: 'Кресло', note: 'МЕҲМОНХОНА' }, { name: 'Болалар партаси', note: 'БОЛАЛАР ХОНАСИ' }];
  const T0 = 0.7, EV = 0.85, OUT = 8.7, CTA = 9.2;
  function studio(c, t) { const g = c.createLinearGradient(0, 0, 0, H); g.addColorStop(0, '#FFFFFF'); g.addColorStop(1, CR); c.fillStyle = g; c.fillRect(0, 0, W, H);
    c.save(); c.globalAlpha = 0.09; c.strokeStyle = OAK; c.lineWidth = 2; for (let i = -1; i < 9; i++) { const x = i * 150 + (t * 14) % 150; c.beginPath(); c.moveTo(x, 0); c.lineTo(x + 260, H); c.stroke(); } c.restore(); }
  const txt = (c, s, x, y, fz, col, fam = 'IDB') => { c.font = `400 ${fz}px "${fam}"`; c.fillStyle = col; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText(s, x, y); };
  const title = (c, s, t, t0, out, y, fz, col) => { const k = MK.life(t, t0, out, 0.4); if (k <= 0) return; c.save(); c.globalAlpha *= k; txt(c, s, W / 2, y + (1 - E.outBack(prog(t, t0, t0 + 0.45))) * 50, fz, col); c.restore(); };
  function finale(c, t) { const a = CTA; studio(c, t);
    const lk = E.outBack(prog(t, a + 0.1, a + 0.7), 1.5), lw = 700 * lk, lh = lw * 1635 / 1981; if (lk > 0) c.drawImage(img.logo, W / 2 - lw / 2, 560 - lh / 2, lw, lh);
    const s1 = E.out3(prog(t, a + 0.7, a + 1.1)), s2 = E.out3(prog(t, a + 0.85, a + 1.25)); c.save(); c.globalAlpha = s1; txt(c, 'ИШЛАБ ЧИҚАРУВЧИДАН —', W / 2, 960 + (1 - s1) * 30, 60, G); c.globalAlpha = s2; txt(c, 'ТЎҒРИДАН-ТЎҒРИ', W / 2, 1035 + (1 - s2) * 30, 60, OAK); c.restore();
    const ph = '+998 77 923 01 91', n = Math.floor(clamp((t - a - 1.3) / 0.05, 0, ph.length));
    if (n > 0) { c.save(); c.shadowColor = 'rgba(0,0,0,0.2)'; c.shadowBlur = 20; c.shadowOffsetY = 8; c.fillStyle = G; rr(c, 110, 1140, 860, 130, 65); c.fill(); c.restore();
      c.font = '400 70px "IDB"'; const full = c.measureText(ph).width; c.fillStyle = CR; c.textAlign = 'left'; c.textBaseline = 'middle'; c.fillText(ph.slice(0, n), W / 2 - full / 2, 1208);
      if (n < ph.length || Math.floor(t * 2) % 2) { const cw = c.measureText(ph.slice(0, n)).width; c.fillStyle = OAK; c.fillRect(W / 2 - full / 2 + cw + 8, 1178, 7, 60); } }
    const tk = E.out3(prog(t, a + 2.3, a + 2.7)); c.save(); c.globalAlpha = tk; txt(c, 'Рўйхатингизни юборинг — ҳаммасини йиғамиз', W / 2, 1345, 40, G, 'IDX'); txt(c, 'Telegram: @ShodiyonaMebelUz', W / 2, 1410, 40, OAK, 'IDX'); c.restore(); }
  window.__seek = async (t) => {
    await MK.warm(); await ready(); for (const f of ['IDB', 'IDX']) await document.fonts.load(`400 60px "${f}"`);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    if (t < CTA) { ctx.save(); const z = lerp(1, 1.04, E.inOut3(prog(t, 0, CTA))); ctx.translate(W / 2, H / 2); ctx.scale(z, z); ctx.translate(-W / 2, -H / 2); studio(ctx, t);
      const ik = MK.life(t, 0, OUT, 0.4), iw = 120 * ik; if (iw > 0) ctx.drawImage(img.icon, W / 2 - iw / 2, 95, iw, iw * 957 / 919);
      title(ctx, 'ЯНГИ УЙГА', t, 0.0, OUT, 300, 112, G); title(ctx, 'КЎЧЯПСИЗМИ?', t, 0.12, OUT, 415, 112, OAK);
      MK.checklist(ctx, { x: 70, w: W - 140, y: 530, rowH: 172, size: 60, items: ITEMS, t, t0: T0, every: EV, out: OUT,
        rowBg: '#FFFFFF', done: G, ink: G, inkDone: CR, box: OAK, boxLine: OAK, tally: { x: 300, y: 1760, size: 150, label: 'ТАЙЁР', color: G, full: OAK, bg: G, fg: CR } });
      MK.badge(ctx, { x: W - 270, y: 1730, r: 175, lines: ['ҲАММА', 'БИР ЖОЙДА'], t, t0: 6.5, out: OUT, color: OAK, ink: CR });
      ctx.save(); ctx.font = '400 26px "IDX"'; ctx.fillStyle = 'rgba(31,58,40,0.5)'; ctx.textAlign = 'left'; ctx.fillText('НАМУНА · демо', 60, 1890); ctx.restore(); ctx.restore(); }
    if (t >= 8.9 && t < 9.5) MK.wipe(ctx, { t, t0: 8.9, dur: 0.6, color: OAK });
    if (t >= CTA) finale(ctx, t);
    if (!/nograin/.test(location.search)) MK.grain(ctx, { t, amt: 0.025 });
  };
})();
