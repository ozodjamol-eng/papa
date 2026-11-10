/* Shodiyona «Трендни кўрдингизми? — Худди шундайини ясаймиз» (10.11.2026), 9:16, 30 к/с, с озвучкой (главный диктор, timing.js по словам).
 * Идея владельца (по роликам шефа Shodiyona): человек увидел трендовое видео мебели → Shodiyona сделает такую же → видео шлёт в бот / Telegram / телефон.
 * Сцены: телефон-лента с «тренд»-роликами → «қаердан топаман?» → логотип + «ХУДДИ ШУНДАЙ ЯСАЙМИЗ» → «ЎЗ ЦЕХИМИЗ» + товар Shodiyona, ўлчам/ранг/материал
 * → чат: видео отправлено в бот + 3 канала связи → финал. Образцы в телефоне — ролики, присланные шефом (ref/), только как «тренд из интернета». */
(function () {
  const cv = document.getElementById('c'), ctx = cv.getContext('2d'), W = 1080, H = 1920, { E, prog, clamp, lerp, rr } = MK;
  MK.setFonts({ head: '"IDB"', body: '"IDX"' }); MK.setPalette({ accent: '#B8814A' }); const P = MK.P, G = P.green, OAK = P.oak, WAL = P.walnut, CR = P.cream;
  const T = window.TIMING, V = T.V, TOTAL = T.total, WD = T.words;
  const at = (p, w) => V[p] + w; // момент слова: фраза + смещение из align.json
  window.__comp = { width: W, height: H, fps: 30, duration: TOTAL };
  const IM = {}; for (const n of ['logo', 'icon', 'u04', 'u06', 'u09', 'k27', 'u13', 'u02']) { IM[n] = new Image(); IM[n].src = 'img/' + n + '.png'; }
  const ready = () => Promise.all(Object.values(IM).map((i) => (i.complete && i.naturalWidth ? 1 : new Promise((r) => { i.onload = r; i.onerror = r; }))));
  // кадры роликов-образцов: загрузка по требованию (кэш на несколько кадров)
  const CL = { a: 240, b: 180, c: 180 }, cache = new Map();
  function frame(clip, i) { const n = clamp(Math.floor(i), 0, CL[clip] - 1) + 1, key = clip + n; if (cache.has(key)) return cache.get(key);
    const im = new Image(); im.src = `ref/${clip}/${String(n).padStart(4, '0')}.jpg`; const p = new Promise((r) => { im.onload = () => r(im); im.onerror = () => r(null); });
    cache.set(key, p); if (cache.size > 40) cache.delete(cache.keys().next().value); return p; }

  // ключевые моменты (из align.json)
  const K = { kord: at('p1', 1.76), trend: at('p1', 2.93), hamma: at('p1', 4.04), havas: at('p2', 0), qayer: at('p2', 2.48), oyla: at('p2', 3.68),
    shod: at('p3', 0), orzu: at('p3', 1.44), xuddi: at('p3', 3.04), yasab: at('p3', 4.0), oz: at('p4', 0), olcham: at('p4', 1.6), rang: at('p4', 2.48),
    mat: at('p4', 3.24), tanla: at('p4', 3.98), video: at('p5', 0), bot: at('p5', 1.36), tg: at('p5', 2.37), tel: at('p5', 3.92), fin: at('p6', 0),
    ishlab: at('p6', 1.12), togri: at('p6', 2.64) };
  const S3 = K.shod - 0.35, S4 = K.oz - 0.3, S5 = K.video - 0.3, S6 = K.fin - 0.3;

  function studio(c, t) { const g = c.createLinearGradient(0, 0, 0, H); g.addColorStop(0, '#FFFFFF'); g.addColorStop(1, CR); c.fillStyle = g; c.fillRect(0, 0, W, H);
    c.save(); c.globalAlpha = 0.08; c.strokeStyle = OAK; c.lineWidth = 2; for (let i = -1; i < 9; i++) { const x = i * 150 + (t * 14) % 150; c.beginPath(); c.moveTo(x, 0); c.lineTo(x + 260, H); c.stroke(); } c.restore(); }
  const txt = (c, s, x, y, fz, col, fam = 'IDB', al = 'center') => { c.font = `400 ${fz}px "${fam}"`; c.fillStyle = col; c.textAlign = al; c.textBaseline = 'middle'; c.fillText(s, x, y); };
  const fit = (c, s, x, y, fz, col, maxW, fam = 'IDB') => { c.font = `400 ${fz}px "${fam}"`; const k = Math.min(1, maxW / c.measureText(s).width); txt(c, s, x, y, fz * k, col, fam); };
  const pop = (c, t, t0, out, x, y, draw, dur = 0.45) => { const k = MK.life(t, t0, out, 0.3); if (k <= 0) return; const s = E.outBack(prog(t, t0, t0 + dur), 1.8);
    c.save(); c.globalAlpha *= k; c.translate(x, y); c.scale(s, s); draw(c); c.restore(); };
  const rise = (c, t, t0, out, draw) => { const k = MK.life(t, t0, out, 0.35); if (k <= 0) return; c.save(); c.globalAlpha *= k; c.translate(0, (1 - E.out3(prog(t, t0, t0 + 0.4))) * 50); draw(c); c.restore(); };
  function pillBox(c, s, fz, bg, fg) { c.font = `400 ${fz}px "IDB"`; const w = c.measureText(s).width + fz * 1.8, h = fz * 1.75;
    c.save(); c.shadowColor = 'rgba(0,0,0,0.22)'; c.shadowBlur = 22; c.shadowOffsetY = 8; c.fillStyle = bg; rr(c, -w / 2, -h / 2, w, h, h / 2); c.fill(); c.restore(); txt(c, s, 0, fz * 0.05, fz, fg); return w; }
  const prod = (c, n, cx, by, h) => { const im = IM[n]; if (!im.naturalWidth) return; const w = h * im.naturalWidth / im.naturalHeight;
    c.save(); c.globalAlpha *= 0.18; c.fillStyle = '#000'; c.beginPath(); c.ellipse(cx, by, w * 0.42, h * 0.04, 0, 0, Math.PI * 2); c.fill(); c.restore(); c.drawImage(im, cx - w / 2, by - h, w, h); };

  // ---------- телефон с роликом ----------
  // какой ролик и кадр в момент t: a (кровать-трансформер) → свайп на b (кресло) на «ҳамма» → свайп на c (ряд кресел) на «қаердан»
  const SW1 = K.hamma, SW2 = K.qayer;
  function clipAt(t) { if (t < SW1) return ['a', (t - 0.4) * 30]; if (t < SW2) return ['b', (t - SW1) * 30]; return ['c', (t - SW2) * 30]; }
  async function phone(c, t, cx, cy, s, ui = true) {
    const pw = 560 * s, ph = 1060 * s, x = cx - pw / 2, y = cy - ph / 2, R = 70 * s, bz = 16 * s;
    c.save(); c.shadowColor = 'rgba(0,0,0,0.35)'; c.shadowBlur = 50 * s; c.shadowOffsetY = 24 * s; c.fillStyle = '#111'; rr(c, x, y, pw, ph, R); c.fill(); c.restore();
    c.save(); rr(c, x + bz, y + bz, pw - 2 * bz, ph - 2 * bz, R - bz); c.clip(); c.fillStyle = '#000'; c.fillRect(x, y, pw, ph);
    const sx = x + bz, sy = y + bz, sw = pw - 2 * bz, sh = ph - 2 * bz;
    const draw = async (clip, fi, off) => { const im = await frame(clip, fi); if (!im) return; const k = Math.max(sw / im.width, sh / im.height), iw = im.width * k, ih = im.height * k;
      c.drawImage(im, sx + (sw - iw) / 2, sy + (sh - ih) / 2 + off, iw, ih); };
    // свайп вверх 0.4 с
    const swp = (ts) => E.inOut3(prog(t, ts - 0.2, ts + 0.2));
    if (t >= SW1 - 0.2 && t < SW1 + 0.2) { const k = swp(SW1); await draw('a', (SW1 - 0.6) * 30, -k * sh); await draw('b', 0, (1 - k) * sh); }
    else if (t >= SW2 - 0.2 && t < SW2 + 0.2) { const k = swp(SW2); await draw('b', (SW2 - SW1 - 0.2) * 30, -k * sh); await draw('c', 0, (1 - k) * sh); }
    else { const [cl, fi] = clipAt(t); await draw(cl, fi, 0); }
    if (ui) { // интерфейс ленты: сердце/коммент/поделиться справа, полоска снизу (без цифр — не выдумываем)
      const ix = sx + sw - 50 * s; c.fillStyle = 'rgba(0,0,0,0.25)'; c.fillRect(sx, sy + sh * 0.72, sw, sh * 0.28);
      const icons = ['♥', '💬', '➦']; icons.forEach((ic, i) => { const iy = sy + sh * 0.55 + i * 95 * s; c.font = `${46 * s}px "IDB"`; c.textAlign = 'center'; c.fillStyle = i === 0 ? '#FF3B5C' : '#fff'; c.fillText(ic, ix, iy); });
      c.fillStyle = 'rgba(255,255,255,0.9)'; c.fillRect(sx + 30 * s, sy + sh - 120 * s, sw * 0.45, 14 * s); c.fillStyle = 'rgba(255,255,255,0.55)'; c.fillRect(sx + 30 * s, sy + sh - 92 * s, sw * 0.65, 12 * s);
      c.fillStyle = 'rgba(255,255,255,0.35)'; c.fillRect(sx, sy + sh - 6 * s, sw, 6 * s); c.fillStyle = '#fff'; const [, fi] = clipAt(t); c.fillRect(sx, sy + sh - 6 * s, sw * ((fi / 180) % 1), 6 * s);
      // взлетающие сердечки после «трендга»
      for (let i = 0; i < 9; i++) { const t0 = K.trend + i * 0.32, k = prog(t, t0, t0 + 1.6); if (k <= 0 || k >= 1) continue;
        c.save(); c.globalAlpha = 1 - k; c.font = `${(40 + (i % 3) * 10) * s}px "IDB"`; c.fillStyle = '#FF3B5C'; c.textAlign = 'center';
        c.fillText('♥', ix + Math.sin(i * 1.7 + k * 4) * 30 * s, sy + sh * 0.55 - k * 380 * s); c.restore(); }
    }
    c.restore();
    // «ТРЕНД» на телефоне
    pop(c, t, K.trend, S3, x + pw * 0.3, y + 120 * s, (cc) => pillBox(cc, '🔥 ТРЕНД', 44 * s, '#FF3B5C', '#FFFFFF'));
  }

  // ---------- сцены ----------
  async function s12(c, t) { // 0 → S3: телефон-лента + вопросы
    studio(c, t);
    const out1 = K.havas - 0.1;
    rise(c, t, 0.4, out1, (cc) => fit(cc, 'ИНТЕРНЕТДА', W / 2, 150, 92, G, 980));
    rise(c, t, at('p1', 0.96), out1, (cc) => fit(cc, 'ЧИРОЙЛИ МЕБЕЛЬ', W / 2, 250, 92, OAK, 980));
    rise(c, t, K.kord, out1, (cc) => fit(cc, 'КЎРДИНГИЗМИ?', W / 2, 350, 92, G, 980));
    rise(c, t, K.havas, S3, (cc) => fit(cc, 'ҲАВАС ҚИЛДИНГИЗ —', W / 2, 160, 84, G, 980));
    rise(c, t, K.qayer, S3, (cc) => fit(cc, 'ҚАЕРДАН ТОПАМАН?', W / 2, 265, 92, OAK, 980));
    const pk = E.out3(prog(t, 0.2, 0.9)), cy = lerp(1500, 1110, pk); await phone(c, t, W / 2, cy, 0.98 * (0.9 + 0.1 * pk));
    // вопросительные знаки вокруг телефона на «ўйладингизми»
    [[170, 900, -0.2], [920, 820, 0.25], [140, 1400, 0.15], [940, 1350, -0.2]].forEach(([x, y, r], i) => pop(c, t, K.oyla - 0.2 + i * 0.12, S3, x, y, (cc) => { cc.rotate(r); txt(cc, '?', 0, 0, 170, OAK); }));
  }
  async function s3(c, t) { // логотип + «худди шундай ясаймиз»
    studio(c, t);
    const lk = E.outBack(prog(t, S3 + 0.25, S3 + 0.8), 1.4), lw = 520 * lk; if (lw > 0) c.drawImage(IM.logo, W / 2 - lw / 2, 230 - lw * 1635 / 1981 / 2, lw, lw * 1635 / 1981);
    // телефон слева (тренд) → стрелка → справа «ЯСАЙМИЗ»
    const pin = E.out3(prog(t, S3, S3 + 0.6)); c.save(); c.globalAlpha = pin; await phone(c, t, 300, 1090, 0.6, false); c.restore();
    const ak = E.out3(prog(t, K.xuddi - 0.1, K.xuddi + 0.4)); if (ak > 0) { c.save(); c.strokeStyle = OAK; c.lineWidth = 14; c.lineCap = 'round'; const x0 = 520, x1 = lerp(x0, 690, ak);
      c.beginPath(); c.moveTo(x0, 1090); c.lineTo(x1, 1090); c.stroke(); if (ak > 0.9) { c.beginPath(); c.moveTo(x1 - 30, 1060); c.lineTo(x1, 1090); c.lineTo(x1 - 30, 1120); c.stroke(); } c.restore(); }
    pop(c, t, K.yasab, S4, 870, 1090, (cc) => { cc.rotate(-0.08); cc.save(); cc.shadowColor = 'rgba(0,0,0,0.3)'; cc.shadowBlur = 24; cc.fillStyle = G; rr(cc, -170, -170, 340, 340, 170); cc.fill(); cc.restore();
      cc.strokeStyle = OAK; cc.lineWidth = 8; cc.beginPath(); cc.arc(0, 0, 150, 0, Math.PI * 2); cc.stroke(); txt(cc, 'ЯСАЙМИЗ', 0, -18, 54, CR); txt(cc, '✓', 0, 52, 70, OAK); });
    rise(c, t, K.orzu, S4, (cc) => fit(cc, 'ОРЗУЙИНГИЗДАГИ МЕБЕЛНИ', W / 2, 1560, 66, G, 980));
    rise(c, t, K.xuddi, S4, (cc) => fit(cc, 'ХУДДИ ШУНДАЙ ЯСАБ БЕРАМИЗ', W / 2, 1650, 66, OAK, 980));
  }
  function s4(c, t) { // ўз цехимиз + товар, ўлчам/ранг/материал
    studio(c, t);
    rise(c, t, K.oz, S5, (cc) => { fit(cc, 'ЎЗ ЦЕХИМИЗ', W / 2, 170, 110, G, 980); });
    // товар Shodiyona выезжает по очереди
    const items = [['u04', 240, 860, 600], ['k27', 640, 860, 380], ['u06', 300, 1250, 340], ['u09', 770, 1250, 250]];
    items.forEach(([n, x, by, h], i) => { const t0 = K.oz + 0.35 + i * 0.22, k = MK.life(t, t0, S5, 0.4); if (k <= 0) return;
      c.save(); c.globalAlpha = k; c.translate((1 - E.out3(prog(t, t0, t0 + 0.45))) * (i % 2 ? 300 : -300), 0); prod(c, n, x, by, h); c.restore(); });
    MK.size(c, { x0: 80, y0: 885, x1: 400, y1: 885, label: 'ЎЛЧАМ', t, t0: K.olcham, out: S5, color: G, bg: OAK, fz: 38 });
    MK.size(c, { x0: 50, y0: 270, x1: 50, y1: 850, label: 'СИЗДАН', t, t0: K.olcham + 0.25, out: S5, color: G, bg: G, fz: 34, side: -1 });
    MK.swatches(c, { x: 150, y: 1330, size: 120, gap: 30, items: [{ color: '#1E1E1E', name: 'ҚОРА' }, { color: '#F2F0EA', name: 'ОҚ' }, { color: '#B8814A', name: 'ДУБ' }, { color: '#74421E', name: 'ЁНҒОҚ' }, { color: '#C8A64B', name: 'ОЛТИН' }], t, t0: K.rang, out: S5 });
    pop(c, t, K.mat, S5, W / 2, 1585, (cc) => pillBox(cc, 'МЕТАЛЛ · ЁҒОЧ · ЮМШОҚ', 46, CR, G));
    pop(c, t, K.tanla, S5, W / 2, 1720, (cc) => pillBox(cc, 'ЎЗИНГИЗ ТАНЛАЙСИЗ', 58, G, CR));
  }
  async function s5(c, t) { // чат: видео → бот + 3 канала
    studio(c, t);
    rise(c, t, K.video, S6, (cc) => { fit(cc, 'ВИДЕОНИ ЮБОРИНГ', W / 2, 170, 96, G, 980); });
    // окно чата
    const ck = E.out3(prog(t, S5, S5 + 0.5)); c.save(); c.globalAlpha = ck; c.translate(0, (1 - ck) * 60);
    c.save(); c.shadowColor = 'rgba(0,0,0,0.2)'; c.shadowBlur = 30; c.shadowOffsetY = 10; c.fillStyle = '#FFFFFF'; rr(c, 110, 290, 860, 700, 46); c.fill(); c.restore();
    c.fillStyle = G; rr(c, 110, 290, 860, 120, 46); c.fill(); c.fillRect(110, 360, 860, 50); if (IM.icon.naturalWidth) c.drawImage(IM.icon, 140, 312, 76, 76 * 957 / 919);
    txt(c, 'Shodiyona Mebel', 240, 333, 40, CR, 'IDB', 'left'); txt(c, 'бот', 240, 380, 30, '#CFE3D3', 'IDX', 'left'); c.restore();
    // сообщение с видео (кадр из «тренда»)
    const mk = E.outBack(prog(t, K.video + 0.5, K.video + 0.95), 1.4); if (mk > 0) { c.save(); c.translate(900, 470); c.scale(mk, mk);
      c.fillStyle = '#DCF3D8'; rr(c, -420, 0, 420, 480, 30); c.fill(); const im = await frame('c', 60); if (im) { c.save(); rr(c, -404, 16, 388, 330, 20); c.clip(); const k = Math.max(388 / im.width, 330 / im.height); c.drawImage(im, -404 + (388 - im.width * k) / 2, 16 + (330 - im.height * k) / 2, im.width * k, im.height * k); c.restore();
        c.fillStyle = 'rgba(0,0,0,0.45)'; c.beginPath(); c.arc(-210, 181, 46, 0, Math.PI * 2); c.fill(); c.fillStyle = '#fff'; c.beginPath(); c.moveTo(-226, 155); c.lineTo(-226, 207); c.lineTo(-182, 181); c.fill(); }
      txt(c, 'Шундайини ясаб', -390, 392, 36, G, 'IDX', 'left'); txt(c, 'берасизми? 🙏', -390, 440, 36, G, 'IDX', 'left'); c.restore(); }
    // 3 канала
    const CH = [['🤖', 'БОТ', '@ShodiyonaMebelUzBot', K.bot], ['✈️', 'TELEGRAM', '@ShodiyonaMebelUz', K.tg], ['📞', 'ТЕЛЕФОН', '+998 77 923 01 91', K.tel]];
    CH.forEach(([ic, a, b, t0], i) => { const y = 1130 + i * 215; pop(c, t, t0, S6, W / 2, y, (cc) => { cc.save(); cc.shadowColor = 'rgba(0,0,0,0.2)'; cc.shadowBlur = 22; cc.shadowOffsetY = 8;
      cc.fillStyle = i === 2 ? G : '#FFFFFF'; rr(cc, -430, -88, 860, 176, 44); cc.fill(); cc.restore(); cc.font = '70px "IDB"'; cc.textAlign = 'center'; cc.textBaseline = 'middle'; cc.fillText(ic, -340, 4);
      txt(cc, a, -250, -30, 40, i === 2 ? '#CFE3D3' : OAK, 'IDB', 'left'); fit(cc, b, 60, 32, 54, i === 2 ? CR : G, 600); }); });
  }
  function s6(c, t) { // финал
    studio(c, t); const z = lerp(1, 1.05, prog(t, S6, TOTAL)); c.save(); c.translate(W / 2, H * 0.45); c.scale(z, z); c.translate(-W / 2, -H * 0.45);
    const lk = E.outBack(prog(t, S6 + 0.1, S6 + 0.6), 1.5), lw = 680 * lk; if (lw > 0) c.drawImage(IM.logo, W / 2 - lw / 2, 520 - lw * 1635 / 1981 / 2 + Math.sin((t - S6) * 1.6) * 6, lw, lw * 1635 / 1981);
    rise(c, t, K.ishlab, TOTAL + 1, (cc) => txt(cc, 'ИШЛАБ ЧИҚАРУВЧИДАН —', W / 2, 920, 62, G));
    rise(c, t, K.togri, TOTAL + 1, (cc) => txt(cc, 'ТЎҒРИДАН-ТЎҒРИ', W / 2, 1000, 62, OAK));
    pop(c, t, K.togri + 0.6, TOTAL + 1, W / 2, 1180, (cc) => pillBox(cc, '+998 77 923 01 91', 66, G, CR));
    rise(c, t, K.togri + 0.9, TOTAL + 1, (cc) => { txt(cc, '🤖 @ShodiyonaMebelUzBot', W / 2, 1340, 44, G, 'IDX'); txt(cc, '✈️ @ShodiyonaMebelUz', W / 2, 1410, 44, OAK, 'IDX'); });
    c.restore();
  }
  function curtain(c, t, t0) { // зелёная шторка со знаком
    const k = prog(t, t0, t0 + 0.7); if (k <= 0 || k >= 1) return; const x = k < 0.5 ? lerp(-W, 0, E.inOut3(k * 2)) : lerp(0, W, E.inOut3((k - 0.5) * 2));
    c.save(); c.fillStyle = G; c.fillRect(x, 0, W, H); const iw = 260; c.globalAlpha = 1 - Math.abs(k - 0.5) * 2; if (IM.icon.naturalWidth) c.drawImage(IM.icon, x + W / 2 - iw / 2, H / 2 - iw / 2, iw, iw * 957 / 919); c.restore(); }

  window.__seek = async (t) => {
    await MK.warm(); await ready(); for (const f of ['IDB', 'IDX']) await document.fonts.load(`400 60px "${f}"`);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    if (t < S3) await s12(ctx, t); else if (t < S4) await s3(ctx, t); else if (t < S5) s4(ctx, t); else if (t < S6) await s5(ctx, t); else s6(ctx, t);
    curtain(ctx, t, S3 - 0.35); MK.wipe && t >= S5 - 0.3 && t < S5 + 0.3 && MK.wipe(ctx, { t, t0: S5 - 0.3, dur: 0.6, color: OAK }); curtain(ctx, t, S6 - 0.35);
    if (t >= S4 - 0.3 && t < S4 + 0.3) MK.wipe(ctx, { t, t0: S4 - 0.3, dur: 0.6, color: OAK });
    // субтитры — зелёная плашка снизу (фирменный стиль), кроме финала
    const PS = Object.values(V).sort((a, b) => a - b), pi = PS.filter((v) => v <= t + 0.05).length - 1, pa = PS[Math.max(0, pi)], pb = PS[pi + 1] ?? 99; // субтитры — только слова текущей фразы
    if (t < S6) MK.subs(ctx, { words: T.words.filter((w) => w[1] >= pa - 0.05 && w[1] < pb - 0.05), t, y: 1840, size: 50, maxWords: 3, band: G, hiBg: OAK, hiFg: CR });
    MK.grain(ctx, { t, amt: 0.02 });
  };
})();
