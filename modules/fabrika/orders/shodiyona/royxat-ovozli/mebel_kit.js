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
 *  fill(ctx,{box:{x,y,w,h},items:[{name,color}],t,t0,every,cols,rest,slots:[[x,y,w,h]],drawItem,counter:{x,y,size,label},out}) → число приземлившихся  «Ичига қаранг»: вещи по дуге влетают в шкаф, счётчик «+N» прыгает на каждой
 *  proof(ctx,{i,n,title,sub,t,t0,out,x,y})              «6 исбот»: полоса глав сверху + «2/6 МАТОСИ»
 *  meter(ctx,{x,y,value|from,to,dur,digits,size,unit,label,t,t0,out}) «литромер»: барабанные цифры как на колонке/счётчике воды — младшая крутится
 *                                                       плавно, старшие перекатываются только на переносе 9→0 (живой счёт «Андижон бугун ичди: 12 480 л»)
 *  checklist(ctx,{x,y,w,items:[{name,note}],t,t0,every,rowH,size,out,rowBg,done,ink,inkDone,box,boxLine,tally:{x,y,size,label,color,full,bg,fg}}) → число отмеченных
 *                                                       «Сеп рўйхати»: строки списка выезжают, галочка рисуется штрихом, строка «загорается»,
 *                                                       счётчик «4/6» прыгает на каждой галочке (разведка «Мебель» 06.11, по мотиву IKEA PH «One Piece at a Time»)
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
    if (o.band) { ctx.save(); shadow(ctx, 0.3, 20, 6); ctx.fillStyle = o.band === true ? 'rgba(22,19,15,0.6)' : o.band; rr(ctx, x - fz * 0.5, y - fz * 0.85, tot + fz, fz * 1.7, fz * 0.4); ctx.fill(); ctx.restore(); } // 04.11: подложка — читается на любом фоне
    line.forEach((w, i) => {
      const on = o.t >= w[1], now = o.t >= w[1] && o.t < w[2], pk = E.outBack(prog(o.t, w[1], w[1] + 0.18));
      ctx.save(); ctx.translate(x + ws[i] / 2, y); const s = now ? lerp(0.9, 1.06, pk) : 1; ctx.scale(s, s);
      if (now) { ctx.fillStyle = o.hiBg || P.accent; rr(ctx, -ws[i] / 2 - 12, -fz * 0.62, ws[i] + 24, fz * 1.24, 12); ctx.fill(); }
      ctx.lineWidth = fz * 0.14; ctx.strokeStyle = 'rgba(0,0,0,0.55)'; ctx.lineJoin = 'round'; ctx.textAlign = 'center';
      if (!now) ctx.strokeText(w[0], 0, fz * 0.04); ctx.fillStyle = now ? (o.hiFg || P.green) : on ? P.white : 'rgba(255,255,255,0.55)'; ctx.fillText(w[0], 0, fz * 0.04); ctx.restore();
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


  /* ---------- «Ичига қаранг»: вещи влетают в шкаф + счётчик (разведка «Мебель» 03.11, по мотиву IKEA Tidy Billboards) ---------- */
  // box: проём шкафа {x,y,w,h}; items: [{name,color}] — в настоящем ролике вместо цветных «свёртков» реальные вещи на видео, а fill даёт счётчик/подписи.
  // every — интервал между вещами; cols — сколько в ряд; counter: {x,y,size,label}; from: точка вылета (по умолчанию снизу из-за кадра)
  function fill(ctx, o) {
    const b = o.box, n = o.items.length, cols = o.cols || 3, rows = Math.ceil(n / cols), cw = b.w / cols, ch = b.h / rows, ev = o.every || 0.25, fly = o.fly || 0.55;
    let landed = 0, lastLand = -9;
    o.items.forEach((it, i) => {
      const ts = o.t0 + i * ev, k = prog(o.t, ts, ts + fly); if (k <= 0) return;
      const r = rows - 1 - Math.floor(i / cols), c = i % cols; // заполняем снизу вверх
      let tx = b.x + c * cw + cw / 2, ty = b.y + r * ch + ch * (o.rest ?? 0.58); // rest: где центр вещи по высоте ячейки (0.66 — лежит на полке)
      if (o.slots && o.slots[i]) { tx = o.slots[i][0]; ty = o.slots[i][1]; } // 04.11: точные места — полки на настоящем фото товара
      const fx = o.from ? o.from[0] : tx + (c - (cols - 1) / 2) * 260, fy = o.from ? o.from[1] : H() + 160;
      const e = E.inOut3(k), x = lerp(fx, tx, e), y = lerp(fy, ty, e) - Math.sin(Math.PI * e) * (o.arc ?? 380), rot = (1 - E.outBack(k)) * (i % 2 ? 0.9 : -0.9);
      const sq = k >= 1 ? 1 + 0.12 * Math.exp(-(o.t - ts - fly) * 9) * Math.cos((o.t - ts - fly) * 30) : 1;
      if (k >= 1) { landed++; lastLand = ts + fly; }
      const w = (o.slots && o.slots[i] && o.slots[i][2]) || cw * 0.82, h = (o.slots && o.slots[i] && o.slots[i][3]) || ch * 0.62;
      ctx.save(); ctx.translate(x, y); ctx.rotate(rot); ctx.scale(sq, 2 - sq); shadow(ctx, 0.35, 14, 6);
      if (o.drawItem) { noShadow(ctx); o.drawItem(ctx, it, w, h, i); ctx.restore(); return; } // своя отрисовка вещи (одеяло, подушка, коробка…)
      ctx.fillStyle = it.color || P.oak; rr(ctx, -w / 2, -h / 2, w, h, h * 0.28); ctx.fill(); noShadow(ctx);
      ctx.fillStyle = 'rgba(255,255,255,0.22)'; for (let j = 1; j < 3; j++) ctx.fillRect(-w / 2 + 8, -h / 2 + j * h / 3 - 2, w - 16, 4); // складки
      if (it.name) { ctx.fillStyle = P.white; ctx.font = `800 ${Math.min(h * 0.3, 30)}px ${F.body}`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(it.name, 0, 2); }
      ctx.restore();
    });
    const C = o.counter; if (!C) return landed;
    const ck = life(o.t, o.t0 + fly, o.out, 0.3); if (ck <= 0 || landed === 0) return landed; // «+0» не показываем
    const pop = 1 + 0.18 * Math.exp(-(o.t - lastLand) * 8), fz = C.size || 200;
    ctx.save(); ctx.globalAlpha *= ck; ctx.translate(C.x, C.y); ctx.scale(pop, pop); ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic'; shadow(ctx, 0.45, 24, 8);
    ctx.font = `400 ${fz}px ${F.head}`; ctx.fillStyle = C.color || P.cream; ctx.fillText('+' + landed, 0, 0); ctx.restore();
    if (C.label) { ctx.save(); ctx.globalAlpha *= ck; pill(ctx, C.x, C.y + fz * 0.42, C.label, { size: fz * (C.labelSize || 0.2), bg: P.accent, fg: P.green, font: F.head, weight: 400 }); ctx.restore(); }
    return landed;
  }

  /* ---------- «6 исбот»: глава-доказательство сверху (разведка «Мебель» 03.11, DesignerBox «6 форматов») ---------- */
  // Сегменты 1..n, текущий i заполняется за 0.5 с; номер «2/6» и название главы («МАТОСИ»). Вызывать в каждой главе со своим i и t0.
  function proof(ctx, o) {
    const k = life(o.t, o.t0, o.out, 0.35), n = o.n || 6, i = o.i; if (k <= 0) return;
    const x = o.x ?? 90, y = o.y ?? 290, w = o.w ?? (W() - 2 * x - 60), g = 12, sw = (w - g * (n - 1)) / n, fk = E.out3(prog(o.t, o.t0, o.t0 + 0.5));
    const fz0 = o.size || 96; ctx.save(); ctx.globalAlpha *= k;
    if (o.panel !== false) { shadow(ctx, 0.35, 24, 8); ctx.fillStyle = o.panelColor || 'rgba(31,58,40,0.9)'; rr(ctx, x - 34, y - 34, w + 68, 40 + fz0 * (o.sub ? 1.75 : 1.3) + 34, 26); ctx.fill(); noShadow(ctx); }
    shadow(ctx, 0.35, 10, 3);
    for (let j = 1; j <= n; j++) { const sx = x + (j - 1) * (sw + g); ctx.fillStyle = 'rgba(251,248,241,0.35)'; rr(ctx, sx, y, sw, 14, 7); ctx.fill();
      const f = j < i ? 1 : j === i ? fk : 0; if (f > 0) { ctx.fillStyle = P.accent; rr(ctx, sx, y, Math.max(14, sw * f), 14, 7); ctx.fill(); } }
    noShadow(ctx);
    const tk = E.outBack(prog(o.t, o.t0 + 0.08, o.t0 + 0.5)), fz = o.size || 96;
    ctx.translate(x, y + 40 + fz * 0.85); ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic';
    ctx.font = `400 ${fz}px ${F.head}`; const num = `${i}/${n}`, nw = ctx.measureText(num).width;
    ctx.save(); ctx.translate(0, (1 - tk) * 40); ctx.globalAlpha *= clamp(tk); shadow(ctx, 0.5, 20, 6); ctx.fillStyle = P.accent; ctx.fillText(num, 0, 0);
    ctx.fillStyle = P.cream; ctx.font = `400 ${fz * 0.62}px ${F.head}`; ctx.fillText(o.title, nw + fz * 0.3, 0);
    if (o.sub) { ctx.font = `800 ${fz * 0.36}px ${F.body}`; ctx.fillStyle = "rgba(251,248,241,0.95)"; ctx.fillText(o.sub, nw + fz * 0.32, fz * 0.46); }
    ctx.restore(); ctx.restore();
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

  /* ---------- «литромер»: барабан цифр (разведка «Вода» 05.11, по мотиву Yo-Chi «живой счёт за воду» на экранах) ---------- */
  // value: число или функция (t)=>число; иначе from→to за dur (линейно, как колонка). digits — сколько барабанов (ведущие нули тусклые).
  function meter(ctx, o) {
    const k = life(o.t, o.t0, o.out, 0.4); if (k <= 0) return;
    const v = Math.max(0, typeof o.value === 'function' ? o.value(o.t) : o.value != null ? o.value : lerp(o.from || 0, o.to, prog(o.t, o.t0 + 0.3, o.t0 + 0.3 + (o.dur || 3))));
    const n = o.digits || 5, fz = o.size || 170, cw = fz * 0.74, ch = fz * 1.18, gap = fz * 0.08, tw = n * cw + (n - 1) * gap, x0 = o.x - tw / 2, y0 = o.y - ch / 2;
    const grp = o.group !== false ? fz * 0.16 : 0; // промежуток между тысячами
    ctx.save(); ctx.globalAlpha *= k; ctx.translate(0, (1 - E.outBack(prog(o.t, o.t0, o.t0 + 0.45))) * 60);
    shadow(ctx, 0.45, 30, 12); ctx.fillStyle = o.frame || '#0A0F18'; rr(ctx, x0 - fz * 0.18 - grp / 2, y0 - fz * 0.16, tw + grp + fz * 0.36, ch + fz * 0.32, fz * 0.16); ctx.fill(); noShadow(ctx);
    ctx.strokeStyle = P.accent; ctx.lineWidth = Math.max(3, fz * 0.025); ctx.stroke();
    const lead = Math.floor(v).toString().length;
    for (let i = 0; i < n; i++) { // i — разряд справа
      const p = Math.pow(10, i), rem = v % p, d = Math.floor(v / p) % 10 + (i === 0 ? v % 1 : clamp(rem - (p - 1), 0, 1));
      const x = x0 + (n - 1 - i) * (cw + gap) + (i >= 3 ? -grp / 2 : grp / 2);
      ctx.save(); rr(ctx, x, y0, cw, ch, fz * 0.08); ctx.fillStyle = o.cell || '#F7F3EA'; ctx.fill(); ctx.clip();
      ctx.font = `400 ${fz}px ${F.head}`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillStyle = i >= lead ? 'rgba(22,19,15,0.18)' : (o.ink || P.ink);
      const base = Math.floor(d), f = d - base; // f — доля прокрутки к следующей цифре
      for (const j of [0, 1]) ctx.fillText(String((base + j) % 10), x + cw / 2, y0 + ch / 2 + fz * 0.04 + (j - f) * ch);
      const g = ctx.createLinearGradient(0, y0, 0, y0 + ch); g.addColorStop(0, 'rgba(0,0,0,0.38)'); g.addColorStop(0.22, 'rgba(0,0,0,0)'); g.addColorStop(0.5, 'rgba(255,255,255,0.10)'); g.addColorStop(0.78, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(0,0,0,0.42)');
      ctx.fillStyle = g; ctx.fillRect(x, y0, cw, ch); ctx.restore(); }
    if (o.unit) { ctx.font = `400 ${fz * 0.42}px ${F.head}`; ctx.textAlign = 'left'; ctx.textBaseline = 'middle'; ctx.fillStyle = P.accent; ctx.fillText(o.unit, x0 + tw + grp / 2 + fz * 0.34, o.y); }
    if (o.label) { ctx.font = `800 ${fz * 0.24}px ${F.body}`; ctx.textAlign = 'center'; ctx.textBaseline = 'top'; ctx.fillStyle = o.labelColor || P.cream; ctx.fillText(o.label, o.x, y0 + ch + fz * 0.36); }
    ctx.restore(); return v;
  }

  /* ---------- «Сеп рўйхати»: чек-лист с галочками (разведка «Мебель» 06.11, IKEA Philippines «One Piece at a Time» — жизнь «по одной вещи») ---------- */
  // Строка i выезжает в t0 + i*every, через 0.45 с рисуется галочка (штрих), строка заливается акцентом. note — справа мелко («✓ бор», «3 ранг»).
  function checklist(ctx, o) {
    const n = o.items.length, ev = o.every || 0.7, rh = o.rowH || 150, fz = o.size || 54, x = o.x ?? 90, w = o.w ?? (W() - 2 * x), lag = o.lag ?? 0.45;
    let done = 0, last = -9;
    o.items.forEach((it, i) => {
      const ts = o.times ? o.times[i] - lag : o.t0 + i * ev, k = life(o.t, ts, o.out, 0.4); if (k <= 0) return;
      const tc = ts + lag, ck = E.out3(prog(o.t, tc, tc + 0.35)); if (ck >= 1) { done++; last = tc + 0.35; }
      const y = (o.y ?? 500) + i * rh, slide = (1 - E.out3(prog(o.t, ts, ts + 0.4))) * 120, h = rh * 0.8;
      ctx.save(); ctx.globalAlpha *= k; ctx.translate(slide, 0);
      shadow(ctx, 0.22, 18, 6); ctx.fillStyle = o.rowBg || 'rgba(251,248,241,0.94)'; rr(ctx, x, y, w, h, h * 0.22); ctx.fill(); noShadow(ctx);
      if (ck > 0) { ctx.save(); ctx.globalAlpha *= ck; ctx.fillStyle = o.done || P.accent; rr(ctx, x, y, w, h, h * 0.22); ctx.fill(); ctx.restore(); } // строка «загорается»
      const bs = h * 0.56, bx = x + h * 0.22, by = y + (h - bs) / 2; // квадрат-галочка
      ctx.lineWidth = Math.max(4, bs * 0.09); ctx.strokeStyle = o.boxLine || P.green; rr(ctx, bx, by, bs, bs, bs * 0.2); ctx.stroke();
      if (ck > 0) { const pop = 1 + 0.25 * Math.exp(-(o.t - tc) * 7) * Math.sin(clamp((o.t - tc) / 0.35) * Math.PI);
        ctx.save(); ctx.translate(bx + bs / 2, by + bs / 2); ctx.scale(pop, pop); ctx.fillStyle = o.box || P.green; rr(ctx, -bs / 2, -bs / 2, bs, bs, bs * 0.2); ctx.fill();
        const pts = [[-0.28, 0.02], [-0.07, 0.24], [0.3, -0.24]], L1 = Math.hypot(0.21, 0.22), L2 = Math.hypot(0.37, 0.48), d = ck * (L1 + L2);
        ctx.strokeStyle = P.cream; ctx.lineWidth = bs * 0.14; ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.beginPath(); ctx.moveTo(pts[0][0] * bs, pts[0][1] * bs);
        if (d <= L1) ctx.lineTo(lerp(pts[0][0], pts[1][0], d / L1) * bs, lerp(pts[0][1], pts[1][1], d / L1) * bs);
        else { ctx.lineTo(pts[1][0] * bs, pts[1][1] * bs); const q = (d - L1) / L2; ctx.lineTo(lerp(pts[1][0], pts[2][0], q) * bs, lerp(pts[1][1], pts[2][1], q) * bs); }
        ctx.stroke(); ctx.restore(); }
      ctx.font = `800 ${fz * 0.55}px ${F.body}`; const nw = it.note ? ctx.measureText(it.note).width + h * 0.45 : h * 0.25, nx0 = bx + bs + h * 0.28; // место под note
      ctx.font = `400 ${fz}px ${F.head}`; const fit = Math.min(1, (x + w - nw - nx0) / Math.max(1, ctx.measureText(it.name).width)); // длинное имя — ужимаем, не наезжает на note
      ctx.fillStyle = ck > 0.5 ? (o.inkDone || P.green) : (o.ink || P.ink); ctx.font = `400 ${fz * fit}px ${F.head}`; ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
      ctx.fillText(it.name, nx0, y + h / 2 + fz * 0.04);
      if (it.note) { const nk = E.outBack(prog(o.t, tc + 0.15, tc + 0.5)); if (nk > 0) { ctx.save(); ctx.translate(x + w - h * 0.25, y + h / 2); ctx.scale(nk, nk);
        ctx.font = `800 ${fz * 0.55}px ${F.body}`; ctx.textAlign = 'right'; ctx.fillStyle = o.inkDone || P.green; ctx.fillText(it.note, 0, fz * 0.03); ctx.restore(); } }
      ctx.restore();
    });
    const T = o.tally; if (T && done > 0) { const tk = life(o.t, o.t0 + lag + 0.35, o.out, 0.3), pop = 1 + 0.2 * Math.exp(-(o.t - last) * 8), tz = T.size || 150;
      ctx.save(); ctx.globalAlpha *= tk; ctx.translate(T.x, T.y); ctx.scale(pop, pop); ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic'; shadow(ctx, 0.45, 24, 8);
      ctx.font = `400 ${tz}px ${F.head}`; ctx.fillStyle = done === n ? (T.full || P.accent) : (T.color || P.cream); ctx.fillText(`${done}/${n}`, 0, 0); ctx.restore();
      if (T.label) { ctx.save(); ctx.globalAlpha *= tk; pill(ctx, T.x, T.y + tz * 0.42, T.label, { size: tz * 0.22, bg: T.bg || P.accent, fg: T.fg || P.green, font: F.head, weight: 400 }); ctx.restore(); } }
    return done;
  }

  window.MK = { warm, fill, proof, meter, checklist, size, pointer, swatches, TEX, badge, price, counter, panels, lower, subs, cta, wipe, grain, pill, life, E, prog, clamp, lerp, rr,
    get P() { return P; }, setPalette: (p) => { P = Object.assign({}, P, p); }, setFonts: (f) => { F = Object.assign({}, F, f); } };
})();
