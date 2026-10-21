/* mebel_kit.js — моушн-приёмы для мебели/товаров (Canvas 2D, без зависимостей). Каждый приём — чистая функция времени t (секунды):
 * один и тот же t всегда даёт один и тот же кадр → покадровый рендер (capture.mjs) точный. t0 — момент появления, out — момент ухода (необязательно).
 * Подключение: <script src="mebel_kit.js"></script> → window.MK. Цвета по умолчанию — Shodiyona (зелёный, дуб, орех, крем); MK.setPalette({...}) для другого бренда.
 * Тексты — узбекская кириллица; шрифты подключать локально (paper-collage-film/scripts/fonts_local.py), по умолчанию Montserrat 900 / Inter Tight.
 *
 * Приёмы:
 *  size(ctx,{x0,y0,x1,y1,label,t,t0,out,side})        размерная линия: растёт из центра к концам, засечки, плашка «120 см»
 *  pointer(ctx,{x,y,tx,ty,title,sub,t,t0,out})         выноска: точка-пульс на детали → ломаная линия → карточка (материал/деталь)
 *  swatches(ctx,{x,y,items:[{color,name}],t,t0,out,size,gap}) образцы материалов: фишки выезжают по очереди
 *  badge(ctx,{x,y,r,lines,t,t0,out,color,ink})          звезда-бейдж с вращением («ЎРТАКАШСИЗ», «−20%»)
 *  price(ctx,{x,y,price,cur,note,t,t0,out})            ценник на нитке: качается и успокаивается
 *  counter(ctx,{x,y,from,to,suffix,label,t,t0,dur,size}) счётчик «5 ЙИЛ», «1000+ БУЮРТМА»
 *  panels(ctx,{n,t,t0,out,draw:(ctx,i,rect,t)=>{},gap,focus,tf}) «живые панели»: вертикальные окна 9:16 в кадре 16:9, выезд по очереди, в tf одна раскрывается на весь кадр
 *  lower(ctx,{name,role,t,t0,out})                      плашка имени (интервью шефа)
 *  subs(ctx,{words:[[слово,t0,t1],...],t,y,size})      субтитры по словам с подсветкой текущего
 *  cta(ctx,{phone,lines,t,t0,logo:(ctx,x,y,s)=>{}})     финал: лого, телефон печатается цифрами, адрес/призыв
 *  wipe(ctx,{t,t0,dur,dir,color})                       шторка-переход фирменным цветом (две полосы)
 *  grain(ctx,{t,amt})                                   плёночное зерно, меняется на двойках
 */
(function () {
  'use strict';
  const W = () => (window.ENG && ENG.W) || 1920, H = () => (window.ENG && ENG.H) || 1080;
  let P = { green: '#1F3A28', oak: '#B8814A', walnut: '#74421E', cream: '#FBF8F1', ink: '#16130F', accent: '#E9B44C', white: '#FFFFFF' };
  let F = { head: '"Montserrat 900", "Montserrat", "Inter Tight", sans-serif', body: '"Inter Tight", "Montserrat", sans-serif' };
  const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v)), lerp = (a, b, k) => a + (b - a) * k;
  const prog = (t, a, b) => clamp((t - a) / (b - a));
  const E = { out3: (k) => 1 - Math.pow(1 - k, 3), inOut3: (k) => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2), outBack: (k, s = 1.6) => 1 + (s + 1) * Math.pow(k - 1, 3) + s * Math.pow(k - 1, 2), outExpo: (k) => (k >= 1 ? 1 : 1 - Math.pow(2, -10 * k)) };
  // вход/выход: k ∈ 0..1 (0 — нет, 1 — полностью), с уходом за `out`
  const life = (t, t0, out, din = 0.45, dout = 0.3) => (t < t0 ? 0 : out != null && t >= out ? 1 - E.inOut3(prog(t, out, out + dout)) : E.out3(prog(t, t0, t0 + din)));
  const rr = (ctx, x, y, w, h, r) => { ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath(); };
  const shadow = (ctx, a = 0.35, b = 24, dy = 10) => { ctx.shadowColor = `rgba(0,0,0,${a})`; ctx.shadowBlur = b; ctx.shadowOffsetY = dy; };
  const noShadow = (ctx) => { ctx.shadowColor = 'transparent'; ctx.shadowBlur = 0; ctx.shadowOffsetY = 0; };
  function pill(ctx, x, y, text, o = {}) { // плашка с текстом, центр (x,y)
    const size = o.size || 38; ctx.font = `${o.weight || 800} ${size}px ${o.font || F.body}`; const tw = ctx.measureText(text).width, w = tw + size * 1.1, h = size * 1.6;
    ctx.save(); if (o.shadow !== false) shadow(ctx, 0.3, 18, 8); ctx.fillStyle = o.bg || P.cream; rr(ctx, x - w / 2, y - h / 2, w, h, h * (o.round ?? 0.5)); ctx.fill(); noShadow(ctx);
    ctx.fillStyle = o.fg || P.ink; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(text, x, y + size * 0.04); ctx.restore(); return { w, h };
  }

  /* ---------- размерная линия ---------- */
  function size(ctx, o) {
    const k = life(o.t, o.t0, o.out, 0.55), lk = E.outExpo(prog(o.t, o.t0, o.t0 + 0.6)); if (k <= 0) return;
    const { x0, y0, x1, y1 } = o, cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, ang = Math.atan2(y1 - y0, x1 - x0), len = Math.hypot(x1 - x0, y1 - y0) / 2 * lk;
    ctx.save(); ctx.globalAlpha *= k; ctx.translate(cx, cy); ctx.rotate(ang);
    ctx.strokeStyle = o.color || P.green; ctx.lineWidth = o.lw || 4; ctx.lineCap = 'round'; shadow(ctx, 0.45, 10, 3);
    ctx.beginPath(); ctx.moveTo(-len, 0); ctx.lineTo(len, 0); ctx.stroke();
    const tk = 18 * E.out3(prog(o.t, o.t0 + 0.35, o.t0 + 0.6)); for (const s of [-1, 1]) { ctx.beginPath(); ctx.moveTo(s * len, -tk); ctx.lineTo(s * len, tk); ctx.stroke(); }
    // стрелки
    for (const s of [-1, 1]) { ctx.beginPath(); ctx.moveTo(s * len, 0); ctx.lineTo(s * (len - 16), -9); ctx.moveTo(s * len, 0); ctx.lineTo(s * (len - 16), 9); ctx.stroke(); }
    noShadow(ctx); ctx.restore();
    const lp = E.outBack(prog(o.t, o.t0 + 0.3, o.t0 + 0.7)); if (lp <= 0) return;
    const nx = -Math.sin(ang) * (o.side ?? -1) * 46, ny = Math.cos(ang) * (o.side ?? -1) * 46;
    ctx.save(); ctx.globalAlpha *= k; ctx.translate(cx + nx, cy + ny); ctx.scale(lp, lp); pill(ctx, 0, 0, o.label, { size: o.fz || 40, bg: o.bg || P.oak, fg: P.white, font: F.head, weight: 400 }); ctx.restore();
  }

  /* ---------- выноска ---------- */
  function pointer(ctx, o) {
    const k = life(o.t, o.t0, o.out, 0.4); if (k <= 0) return;
    const pulse = 1 + 0.25 * Math.sin((o.t - o.t0) * 6), lk = E.inOut3(prog(o.t, o.t0 + 0.15, o.t0 + 0.6)), ck = E.outBack(prog(o.t, o.t0 + 0.45, o.t0 + 0.85));
    const mx = o.tx, my = o.y + (o.ty - o.y) * 0; // излом: сначала по вертикали до ty, потом по горизонтали
    const pts = [[o.x, o.y], [o.x, o.ty], [o.tx, o.ty]], seg = [Math.abs(o.ty - o.y), Math.abs(o.tx - o.x)], tot = seg[0] + seg[1]; let rem = tot * lk;
    ctx.save(); ctx.globalAlpha *= k; shadow(ctx, 0.4, 10, 3);
    ctx.fillStyle = o.color || P.accent; ctx.beginPath(); ctx.arc(o.x, o.y, 11, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = o.color || P.accent; ctx.lineWidth = 3; ctx.globalAlpha *= 0.6; ctx.beginPath(); ctx.arc(o.x, o.y, 11 + 14 * pulse, 0, Math.PI * 2); ctx.stroke(); ctx.globalAlpha /= 0.6;
    ctx.strokeStyle = o.line || P.green; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(pts[0][0], pts[0][1]);
    for (let i = 0; i < 2 && rem > 0; i++) { const d = Math.min(rem, seg[i]), a = pts[i], b = pts[i + 1], L = seg[i] || 1; ctx.lineTo(a[0] + (b[0] - a[0]) * d / L, a[1] + (b[1] - a[1]) * d / L); rem -= d; }
    ctx.stroke(); noShadow(ctx);
    if (ck > 0) {
      const left = o.tx < o.x, fz = o.fz || 40; ctx.font = `400 ${fz}px ${F.head}`; const tw = Math.max(ctx.measureText(o.title).width, (ctx.font = `600 ${fz * 0.62}px ${F.body}`, ctx.measureText(o.sub || '').width));
      const w = tw + fz * 1.2, h = fz * (o.sub ? 2.5 : 1.6), x = left ? o.tx - w : o.tx, y = o.ty - h / 2;
      ctx.save(); ctx.translate(left ? o.tx : o.tx, o.ty); ctx.scale(ck, ck); ctx.translate(-(left ? o.tx : o.tx), -o.ty);
      shadow(ctx, 0.35, 20, 8); ctx.fillStyle = P.green; rr(ctx, x, y, w, h, 14); ctx.fill(); noShadow(ctx);
      ctx.fillStyle = o.color || P.accent; ctx.fillRect(left ? x + w - 8 : x, y + 12, 8, h - 24);
      ctx.fillStyle = P.cream; ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic'; ctx.font = `400 ${fz}px ${F.head}`; ctx.fillText(o.title, x + fz * 0.6, y + fz * 1.15);
      if (o.sub) { ctx.font = `600 ${fz * 0.62}px ${F.body}`; ctx.fillStyle = 'rgba(251,248,241,0.8)'; ctx.fillText(o.sub, x + fz * 0.6, y + fz * 1.95); }
      ctx.restore();
    }
    ctx.restore();
  }

  /* ---------- образцы материалов ---------- */
  function swatches(ctx, o) {
    const s = o.size || 120, g = o.gap || 26;
    o.items.forEach((it, i) => {
      const k = life(o.t, o.t0 + i * 0.12, o.out, 0.45); if (k <= 0) return;
      const x = o.x + i * (s + g), y = o.y + (1 - E.outBack(prog(o.t, o.t0 + i * 0.12, o.t0 + i * 0.12 + 0.5))) * 120;
      ctx.save(); ctx.globalAlpha *= k; shadow(ctx, 0.35, 16, 8); ctx.fillStyle = P.cream; rr(ctx, x, y, s, s * 1.35, 16); ctx.fill(); noShadow(ctx);
      if (typeof it.color === 'function') { ctx.save(); rr(ctx, x + 10, y + 10, s - 20, s - 20, 10); ctx.clip(); it.color(ctx, x + 10, y + 10, s - 20, s - 20); ctx.restore(); }
      else { ctx.fillStyle = it.color; rr(ctx, x + 10, y + 10, s - 20, s - 20, 10); ctx.fill(); }
      ctx.fillStyle = P.ink; ctx.font = `700 ${s * 0.15}px ${F.body}`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(it.name, x + s / 2, y + s * 1.17); ctx.restore();
    });
  }
  // текстуры для образцов: дерево (волокна), металл (штрих), ткань (сетка)
  const TEX = {
    wood: (base, line) => (ctx, x, y, w, h) => { ctx.fillStyle = base; ctx.fillRect(x, y, w, h); ctx.strokeStyle = line; ctx.lineWidth = 2; ctx.globalAlpha = 0.5; for (let i = 0; i < 14; i++) { ctx.beginPath(); for (let u = 0; u <= w; u += 6) ctx.lineTo(x + u, y + (i + 0.5) * h / 14 + Math.sin(u / 17 + i * 1.7) * 3 + Math.sin(u / 5 + i) * 0.8); ctx.stroke(); } ctx.globalAlpha = 1; },
    metal: (base) => (ctx, x, y, w, h) => { const g = ctx.createLinearGradient(x, y, x + w, y + h); g.addColorStop(0, base); g.addColorStop(0.5, '#F2F4F6'); g.addColorStop(1, base); ctx.fillStyle = g; ctx.fillRect(x, y, w, h); ctx.strokeStyle = 'rgba(0,0,0,0.08)'; for (let i = 0; i < h; i += 3) { ctx.beginPath(); ctx.moveTo(x, y + i); ctx.lineTo(x + w, y + i); ctx.stroke(); } },
    fabric: (base) => (ctx, x, y, w, h) => { ctx.fillStyle = base; ctx.fillRect(x, y, w, h); ctx.fillStyle = 'rgba(255,255,255,0.12)'; for (let i = 0; i < w; i += 6) for (let j = (i / 6) % 2 * 3; j < h; j += 6) ctx.fillRect(x + i, y + j, 3, 3); },
  };

  /* ---------- бейдж-звезда ---------- */
  function badge(ctx, o) {
    const k = life(o.t, o.t0, o.out, 0.5); if (k <= 0) return;
    const r = o.r || 150, sc = E.outBack(prog(o.t, o.t0, o.t0 + 0.5), 2.2), rot = (o.t - o.t0) * 0.35;
    ctx.save(); ctx.globalAlpha *= k; ctx.translate(o.x, o.y); ctx.scale(sc, sc);
    ctx.save(); ctx.rotate(rot); shadow(ctx, 0.4, 24, 10); ctx.fillStyle = o.color || P.accent; ctx.beginPath();
    const n = 20; for (let i = 0; i < n * 2; i++) { const a = i * Math.PI / n, rr2 = i % 2 ? r * 0.84 : r; ctx.lineTo(Math.cos(a) * rr2, Math.sin(a) * rr2); } ctx.closePath(); ctx.fill(); ctx.restore();
    ctx.rotate(-0.12); ctx.fillStyle = o.ink || P.green; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    const L = o.lines; L.forEach((s, i) => { const fz = (i === 0 ? 0.3 : 0.2) * r; ctx.font = `400 ${fz}px ${F.head}`; ctx.fillText(s, 0, (i - (L.length - 1) / 2) * r * 0.3); });
    ctx.restore();
  }

  /* ---------- ценник ---------- */
  function price(ctx, o) {
    const k = life(o.t, o.t0, o.out, 0.3); if (k <= 0) return;
    const lt = o.t - o.t0, swing = Math.exp(-lt * 2.6) * Math.sin(lt * 9) * 0.35, drop = (1 - E.outBack(prog(o.t, o.t0, o.t0 + 0.55))) * -260;
    ctx.save(); ctx.globalAlpha *= k; ctx.translate(o.x, o.y + drop);
    ctx.strokeStyle = o.line || P.green; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(0, -140); ctx.lineTo(0, 0); ctx.stroke();
    ctx.rotate(swing); const fz = o.fz || 64; ctx.font = `400 ${fz}px ${F.head}`; const tw = ctx.measureText(o.price).width, w = tw + fz * 1.4, h = fz * (o.note ? 2.3 : 1.7);
    shadow(ctx, 0.4, 24, 10); ctx.fillStyle = P.cream; ctx.beginPath(); ctx.moveTo(-w / 2 + 34, 0); ctx.lineTo(w / 2, 0); ctx.lineTo(w / 2, h); ctx.lineTo(-w / 2, h); ctx.lineTo(-w / 2, 34); ctx.closePath(); ctx.fill(); noShadow(ctx);
    ctx.fillStyle = P.green; ctx.beginPath(); ctx.arc(-w / 2 + 30, 30, 9, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = P.green; ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic'; ctx.fillText(o.price, 10, fz * 1.25);
    if (o.cur) { ctx.font = `700 ${fz * 0.34}px ${F.body}`; ctx.fillStyle = P.walnut; ctx.fillText(o.cur, 10, fz * 1.66); }
    if (o.note) { ctx.font = `700 ${fz * 0.3}px ${F.body}`; ctx.fillStyle = P.walnut; ctx.fillText(o.note, 10, fz * (o.cur ? 2.02 : 1.7)); }
    ctx.restore();
  }

  /* ---------- счётчик ---------- */
  function counter(ctx, o) {
    const k = life(o.t, o.t0, o.out, 0.35); if (k <= 0) return;
    const v = Math.round(lerp(o.from || 0, o.to, E.outExpo(prog(o.t, o.t0, o.t0 + (o.dur || 1.2))))), fz = o.size || 220;
    ctx.save(); ctx.globalAlpha *= k; ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic'; shadow(ctx, 0.4, 24, 8);
    ctx.font = `400 ${fz}px ${F.head}`; ctx.fillStyle = o.color || P.cream; ctx.fillText(v.toLocaleString('ru-RU') + (o.suffix || ''), o.x, o.y);
    if (o.label) { ctx.font = `800 ${fz * 0.2}px ${F.body}`; ctx.fillStyle = o.labelColor || P.accent; ctx.fillText(o.label, o.x, o.y + fz * 0.36); }
    ctx.restore();
  }

  /* ---------- живые панели: вертикальные кадры в 16:9 ---------- */
  function panels(ctx, o) {
    const n = o.n || 3, gap = o.gap ?? 28, ph = H() - 2 * (o.pad ?? 70), pw = ph * 9 / 16, total = n * pw + (n - 1) * gap, x0 = (W() - total) / 2, y0 = (H() - ph) / 2;
    const fk = o.tf != null ? E.inOut3(prog(o.t, o.tf, o.tf + 0.6)) : 0, fi = o.focus ?? Math.floor(n / 2);
    for (let i = 0; i < n; i++) {
      const k = life(o.t, o.t0 + i * 0.12, o.out != null ? o.out + (n - 1 - i) * 0.08 : null, 0.55); if (k <= 0) continue;
      const fromY = (i % 2 ? -1 : 1) * (H() * 0.9); let x = x0 + i * (pw + gap), y = y0 + (1 - k) * fromY, w = pw, h = ph, r = 22;
      if (fk > 0) { if (i === fi) { x = lerp(x, 0, fk); y = lerp(y, 0, fk); w = lerp(w, W(), fk); h = lerp(h, H(), fk); r = lerp(r, 0, fk); } else { x += (i < fi ? -1 : 1) * fk * W() * 0.6; } }
      ctx.save(); { shadow(ctx, 0.45, 30, 14); ctx.fillStyle = P.ink; rr(ctx, x, y, w, h, r); ctx.fill(); noShadow(ctx); ctx.clip(); o.draw(ctx, i, [x, y, w, h], o.t); }
      ctx.restore(); ctx.globalAlpha = 1;
    }
    if (fk > 0 && fk < 1) return; // во время раскрытия поверх ничего
  }

  /* ---------- плашка имени ---------- */
  function lower(ctx, o) {
    const k = life(o.t, o.t0, o.out, 0.5); if (k <= 0) return;
    const fz = o.size || 54, x = o.x ?? 110, y = o.y ?? H() - 230; ctx.save();
    ctx.font = `400 ${fz}px ${F.head}`; const w1 = ctx.measureText(o.name).width + fz; ctx.font = `700 ${fz * 0.55}px ${F.body}`; const w2 = ctx.measureText(o.role).width + fz;
    const bk = E.outExpo(prog(o.t, o.t0, o.t0 + 0.5)), tk = E.out3(prog(o.t, o.t0 + 0.15, o.t0 + 0.6));
    ctx.globalAlpha *= k; shadow(ctx, 0.35, 18, 6); ctx.fillStyle = P.green; ctx.fillRect(x, y, w1 * bk, fz * 1.5); ctx.fillStyle = P.oak; ctx.fillRect(x, y + fz * 1.5, w2 * bk, fz * 0.95); noShadow(ctx);
    ctx.fillStyle = P.accent; ctx.fillRect(x - 12, y, 12, fz * 2.45 * bk);
    ctx.save(); ctx.beginPath(); ctx.rect(x, y, Math.max(w1, w2) * bk, fz * 2.45); ctx.clip();
    ctx.fillStyle = P.cream; ctx.textBaseline = 'middle'; ctx.font = `400 ${fz}px ${F.head}`; ctx.fillText(o.name, x + fz * 0.5 - (1 - tk) * 60, y + fz * 0.8);
    ctx.font = `700 ${fz * 0.55}px ${F.body}`; ctx.fillStyle = P.white; ctx.fillText(o.role, x + fz * 0.5 - (1 - tk) * 60, y + fz * 1.98); ctx.restore(); ctx.restore();
  }

  /* ---------- субтитры по словам ---------- */
  function subs(ctx, o) {
    const act = o.words.filter((w) => o.t >= w[1] - 0.05 && o.t < (o.hold ?? 0.6) + w[2]); if (!act.length) return;
    // показываем «строку» = слова в окне ±2.2 с вокруг текущего, не больше maxWords
    const cur = o.words.findIndex((w) => o.t >= w[1] && o.t < w[2]), ci = cur >= 0 ? cur : o.words.indexOf(act[act.length - 1]), per = o.maxWords || 4, s0 = Math.floor(ci / per) * per, line = o.words.slice(s0, s0 + per);
    const fz = o.size || 64, y = o.y ?? H() - 140; ctx.save(); ctx.font = `400 ${fz}px ${F.head}`; ctx.textBaseline = 'middle';
    const ws = line.map((w) => ctx.measureText(w[0]).width), sp = fz * 0.32, tot = ws.reduce((a, b) => a + b, 0) + sp * (line.length - 1); let x = W() / 2 - tot / 2;
    line.forEach((w, i) => {
      const on = o.t >= w[1], now = o.t >= w[1] && o.t < w[2], pk = E.outBack(prog(o.t, w[1], w[1] + 0.18));
      ctx.save(); ctx.translate(x + ws[i] / 2, y); const s = now ? lerp(0.9, 1.06, pk) : 1; ctx.scale(s, s);
      if (now) { ctx.fillStyle = P.accent; rr(ctx, -ws[i] / 2 - 12, -fz * 0.62, ws[i] + 24, fz * 1.24, 12); ctx.fill(); }
      ctx.lineWidth = fz * 0.14; ctx.strokeStyle = 'rgba(0,0,0,0.55)'; ctx.lineJoin = 'round'; ctx.textAlign = 'center';
      if (!now) ctx.strokeText(w[0], 0, fz * 0.04); ctx.fillStyle = now ? P.green : on ? P.white : 'rgba(255,255,255,0.55)'; ctx.fillText(w[0], 0, fz * 0.04); ctx.restore();
      x += ws[i] + sp;
    });
    ctx.restore();
  }

  /* ---------- финал: лого + телефон ---------- */
  function cta(ctx, o) {
    const k = life(o.t, o.t0, null, 0.5); if (k <= 0) return;
    ctx.save(); ctx.globalAlpha *= k; ctx.fillStyle = P.green; ctx.fillRect(0, 0, W(), H());
    const g = ctx.createRadialGradient(W() / 2, H() * 0.4, 50, W() / 2, H() * 0.4, W() * 0.7); g.addColorStop(0, 'rgba(184,129,74,0.35)'); g.addColorStop(1, 'rgba(0,0,0,0)'); ctx.fillStyle = g; ctx.fillRect(0, 0, W(), H());
    const lk = E.outBack(prog(o.t, o.t0 + 0.1, o.t0 + 0.7)); if (o.logo && lk > 0) o.logo(ctx, W() / 2, H() * 0.34, lk);
    const ph = o.phone || '', n = Math.floor(clamp((o.t - o.t0 - 0.6) / 0.05, 0, ph.length)), fz = o.size || 104;
    if (n > 0) { ctx.font = `400 ${fz}px ${F.head}`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; const full = ctx.measureText(ph).width;
      ctx.fillStyle = P.cream; ctx.textAlign = 'left'; ctx.fillText(ph.slice(0, n), W() / 2 - full / 2, H() * 0.62);
      if (n < ph.length || Math.floor(o.t * 2) % 2) { const cw = ctx.measureText(ph.slice(0, n)).width; ctx.fillStyle = P.accent; ctx.fillRect(W() / 2 - full / 2 + cw + 8, H() * 0.62 - fz * 0.45, 8, fz * 0.9); } }
    (o.lines || []).forEach((s, i) => { const lk2 = E.out3(prog(o.t, o.t0 + 1.4 + i * 0.15, o.t0 + 1.9 + i * 0.15)); if (lk2 <= 0) return;
      ctx.globalAlpha = k * lk2; ctx.font = `700 ${fz * 0.38}px ${F.body}`; ctx.textAlign = 'center'; ctx.fillStyle = i ? 'rgba(251,248,241,0.8)' : P.accent; ctx.fillText(s, W() / 2, H() * 0.75 + i * fz * 0.55 + (1 - lk2) * 20); });
    ctx.restore();
  }

  /* ---------- шторка ---------- */
  function wipe(ctx, o) {
    const d = o.dur || 0.6, k = prog(o.t, o.t0, o.t0 + d); if (k <= 0 || k >= 1) return;
    const a = E.inOut3(clamp(k * 2)), b = E.inOut3(clamp(k * 2 - 1));
    ctx.save(); for (const [c, off] of [[o.color || P.oak, 0], [P.green, 0.12]]) { const a2 = E.inOut3(clamp(k * 2 - off)), b2 = E.inOut3(clamp(k * 2 - 1 - off));
      ctx.fillStyle = c; ctx.beginPath(); const x0 = lerp(-W() * 0.3, W() * 1.3, b2), x1 = lerp(-W() * 0.3, W() * 1.3, a2); ctx.moveTo(x0, 0); ctx.lineTo(x1 + 300, 0); ctx.lineTo(x1, H()); ctx.lineTo(x0 - 300, H()); ctx.closePath(); ctx.fill(); }
    ctx.restore(); return { a, b };
  }

  /* ---------- зерно ---------- */
  const GR = [];
  function grain(ctx, o) { // 4 полнокадровых шумовых холста (создаются один раз), меняются на двойках
    const idx = Math.floor(o.t * 12) % 4;
    if (!GR[idx]) { const c = document.createElement('canvas'); c.width = W(); c.height = H(); const x = c.getContext('2d'), d = x.createImageData(c.width, c.height), a = d.data; let r = idx * 7919 + 17;
      for (let i = 0; i < a.length; i += 4) { r ^= r << 13; r ^= r >>> 17; r ^= r << 5; const v = 128 + ((r >>> 0) % 96) - 48; a[i] = a[i + 1] = a[i + 2] = v; a[i + 3] = 255; } x.putImageData(d, 0, 0); GR[idx] = c; }
    ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = o.amt ?? 0.05; ctx.globalCompositeOperation = 'overlay'; ctx.drawImage(GR[idx], 0, 0); ctx.restore();
  }

  // прогрев: шумовые холсты создать и «прокачать» в GPU ДО первого кадра — иначе в headless Chromium (swiftshader) первый кадр с только что созданным холстом
  // может показать мусор из видеопамяти (кадр «размножается» плиткой). В __seek: `await MK.warm()` первой строкой.
  let WARMED = null;
  const warm = () => WARMED || (WARMED = (async () => { const s = document.createElement('canvas'); s.width = 64; s.height = 64; const x = s.getContext('2d');
    for (let i = 0; i < 4; i++) grain(x, { t: i / 12 + 1e-4, amt: 0.01 });
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))); })());

  window.MK = { warm, size, pointer, swatches, TEX, badge, price, counter, panels, lower, subs, cta, wipe, grain, pill, life, E, prog, clamp, lerp, rr,
    get P() { return P; }, setPalette: (p) => { P = Object.assign({}, P, p); }, setFonts: (f) => { F = Object.assign({}, F, f); } };
})();
