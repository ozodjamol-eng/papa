/* КАТТА ДАВРА — «ТАКСИ БОЗОРИ: КИМ КИМНИКИ?» (06.11.2026), 9:16, 30 к/с. Сценарий утверждён владельцем.
 * Стиль серии КАТТА ДАВРА (как «ОГОҲ БЎЛИНГ»): тёмно-синий #0D1220, белый, жёлтый #FFB000, красный #FF3B47, зелёный #22C55E, Inter Display Black/ExtraBold.
 * Дерево: ствол = рынок, ветки = сервисы; камера наезжает на ветку, пока диктор говорит о ней. Только факты, без логотипов компаний. */
(function () {
  const cv = document.getElementById('c'), c = cv.getContext('2d'), W = 1080, H = 1920;
  const BG = '#0D1220', Y = '#FFB000', R = '#FF3B47', GR = '#22C55E', WH = '#FFFFFF';
  const TM = window.TM, P = TM.P, K = TM.K; window.__comp = { width: W, height: H, fps: 30, duration: TM.total };
  const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v)), lerp = (a, b, k) => a + (b - a) * k, prog = (t, a, b) => clamp((t - a) / (b - a));
  const out3 = (k) => 1 - Math.pow(1 - k, 3), inOut = (k) => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2), back = (k, s = 1.7) => 1 + (s + 1) * Math.pow(k - 1, 3) + s * Math.pow(k - 1, 2);
  const kw = (n, w) => K[n + ':' + w] ?? P[n][0];
  const rr = (x, y, w, h, r) => { c.beginPath(); c.moveTo(x + r, y); c.arcTo(x + w, y, x + w, y + h, r); c.arcTo(x + w, y + h, x, y + h, r); c.arcTo(x, y + h, x, y, r); c.arcTo(x, y, x + w, y, r); c.closePath(); };
  const T = (s, x, y, fz, col, fam = 'IB', al = 'center') => { c.font = `400 ${fz}px "${fam}"`; c.fillStyle = col; c.textAlign = al; c.textBaseline = 'middle'; c.fillText(s, x, y); };
  function pill(s, x, y, fz, bg, fg, fam = 'IB') { c.font = `400 ${fz}px "${fam}"`; const w = c.measureText(s).width + fz * 1.4, h = fz * 1.7;
    c.save(); c.shadowColor = 'rgba(0,0,0,0.45)'; c.shadowBlur = 24; c.shadowOffsetY = 10; c.fillStyle = bg; rr(x - w / 2, y - h / 2, w, h, h / 2); c.fill(); c.restore(); T(s, x, y + fz * 0.04, fz, fg, fam); }
  const pop = (t0, x, y, fn, t1 = null) => { if (t < t0) return; const s = back(prog(tt, t0, t0 + 0.45)), a = t1 != null ? 1 - prog(tt, t1, t1 + 0.3) : 1; if (a <= 0) return; c.save(); c.globalAlpha *= a * clamp(s); c.translate(x, y); c.scale(s, s); fn(); c.restore(); };
  let tt = 0, t = 0, ZOOM = 1;

  // дерево: ствол x=540, от корня 1430 вверх до 420; узлы веток
  const TRUNK = { x: 540, y0: 1430, y1: 420 };
  const NODES = [
    { id: 't03', name: 'YANDEX GO', tag: 'РОССИЯ', side: -1, y: 520, col: R },
    { id: 't04', name: 'UKLON', tag: 'УКРАИНА', side: 1, y: 700, col: Y },
    { id: 't05', name: 'MYTAXI', tag: 'ЎЗБЕКИСТОН', side: -1, y: 880, col: GR },
    { id: 't06', name: 'WB TAXI', tag: 'WILDBERRIES', side: 1, y: 1060, col: '#A855F7' },
    { id: 'cn', name: 'ХИТОЙ', tag: 'ЯНГИ ЎЙИНЧИ', side: -1, y: 1240, col: '#38BDF8', dashed: true }];
  const nodeX = (n) => 540 + n.side * 290;
  const born = (n) => (n.id === 'cn' ? kw('t06', 'хитой') - 0.3 : P[n.id][0] - 0.1);

  function bg() { c.fillStyle = BG; c.fillRect(0, 0, W, H);
    const g = c.createRadialGradient(540, 800, 50, 540, 800, 1100); g.addColorStop(0, 'rgba(255,176,0,0.10)'); g.addColorStop(1, 'rgba(0,0,0,0)'); c.fillStyle = g; c.fillRect(0, 0, W, H);
    c.save(); c.globalAlpha = 0.05; c.strokeStyle = WH; c.lineWidth = 1; for (let x = 0; x <= W; x += 90) { c.beginPath(); c.moveTo(x, 0); c.lineTo(x, H); c.stroke(); } for (let y = 0; y <= H; y += 90) { c.beginPath(); c.moveTo(0, y); c.lineTo(W, y); c.stroke(); } c.restore(); }

  function tree() {
    const g0 = P.t02[0] - 0.2, gk = inOut(prog(t, g0, g0 + 1.4)); if (gk <= 0) return;
    // ствол
    c.save(); c.lineCap = 'round'; c.strokeStyle = 'rgba(255,255,255,0.85)'; c.lineWidth = 16; c.beginPath(); c.moveTo(TRUNK.x, TRUNK.y0); c.lineTo(TRUNK.x, lerp(TRUNK.y0, TRUNK.y1, gk)); c.stroke(); c.restore();
    // корень — рынок (прячется, пока камера на ветке)
    c.save(); c.globalAlpha *= 1 - clamp((ZOOM - 1.05) / 0.3);
    pop(g0 + 0.3, 540, 1520, () => { c.fillStyle = Y; rr(-330, -95, 660, 190, 34); c.fill(); T('7,16 ТРЛН СЎМ', 0, -26, 74, BG); T('8 ОЙ · 242 АГРЕГАТОР', 0, 46, 36, BG, 'IE'); });
    pop(g0 + 0.9, 540, 1660, () => T('Манба: Солиқ қўмитаси', 0, 0, 30, 'rgba(255,255,255,0.6)', 'IE'));
    c.restore();
    // ветки
    for (const n of NODES) {
      const b = born(n), bk = inOut(prog(t, b, b + 0.6)); if (bk <= 0) continue;
      const x = nodeX(n), sx = TRUNK.x + n.side * 8;
      c.save(); c.strokeStyle = n.col; c.lineWidth = 9; c.lineCap = 'round'; if (n.dashed) c.setLineDash([22, 18]);
      c.beginPath(); c.moveTo(sx, n.y + 60); c.quadraticCurveTo(lerp(sx, x, 0.5), n.y + 60, lerp(sx, x - n.side * 190, bk), n.y); c.stroke(); c.restore();
      pop(b + 0.35, x, n.y, () => {
        c.save(); c.shadowColor = 'rgba(0,0,0,0.5)'; c.shadowBlur = 30; c.shadowOffsetY = 12; c.fillStyle = '#18213A'; rr(-200, -80, 400, 160, 28); c.fill(); c.restore();
        c.save(); c.lineWidth = 5; c.strokeStyle = n.col; if (n.dashed) c.setLineDash([16, 12]); rr(-200, -80, 400, 160, 28); c.stroke(); c.restore();
        T(n.name, 0, -18, n.name.length > 9 ? 54 : 64, WH); c.font = '400 26px "IE"'; const tw = c.measureText(n.tag).width + 34;
        c.fillStyle = n.col; rr(-tw / 2, 28, tw, 40, 20); c.fill(); T(n.tag, 0, 49, 26, BG, 'IE');
      });
    }
  }
  // факты-плашки у узлов (видны, пока камера на ветке и позже)
  function facts() {
    const N = Object.fromEntries(NODES.map((n) => [n.id, n]));
    const below = (n, dy = 140) => [nodeX(n), n.y + dy];
    let [x, y] = below(N.t03); pop(kw('t03', 'октябрда') - 0.3, x, y, () => pill('11 ОКТЯБРЬ: СБОЙ', 0, 0, 34, R, WH));
    [x, y] = below(N.t04); pop(kw('t04', 'устун') - 0.2, x, y, () => pill('УСТУН МАВҚЕ', 0, 0, 34, Y, BG));
    pop(kw('t04', 'андижон') - 0.2, x, y + 75, () => pill('АНДИЖОН · НАМАНГАН · ФАРҒОНА', 0, 0, 24, '#18213A', WH, 'IE'));
    [x, y] = below(N.t05); pop(kw('t05', 'баробар') - 0.9, x, y, () => { const k = prog(t, kw('t05', 'баробар') - 0.9, kw('t05', 'баробар')); pill('×' + Math.max(1, Math.round(15 * out3(k))), 0, 0, 48, GR, BG); });
    [x, y] = below(N.t06); pop(P.t06[0] + 1.2, x, y, () => pill('ТОШКЕНТ · САМАРҚАНД · БУХОРО', 0, 0, 24, '#18213A', WH, 'IE'));
    [x, y] = below(N.cn); pop(kw('t06', 'беш') - 0.2, x, y, () => pill('5 000 МАШИНА + ИЛОВА', 0, 0, 30, '#38BDF8', BG));
  }
  // камера: наезд на текущую ветку
  function cam() {
    const tg = [];
    tg.push([0, 540, 960, 1]);
    tg.push([P.t02[0], 540, 1050, 1.0]);
    const z = 1.55;
    tg.push([P.t03[0], nodeX(NODES[0]) * 0.55 + 540 * 0.45, NODES[0].y + 70, z]);
    tg.push([P.t04[0], nodeX(NODES[1]) * 0.55 + 540 * 0.45, NODES[1].y + 90, z]);
    tg.push([P.t05[0], nodeX(NODES[2]) * 0.55 + 540 * 0.45, NODES[2].y + 70, z]);
    tg.push([P.t06[0], nodeX(NODES[3]) * 0.55 + 540 * 0.45, NODES[3].y + 70, z]);
    tg.push([kw('t06', 'хитой') - 0.2, nodeX(NODES[4]) * 0.55 + 540 * 0.45, NODES[4].y + 70, z]);
    tg.push([P.t07[0], 540, 960, 0.92]);
    let a = tg[0], b = tg[0];
    for (let i = 0; i < tg.length; i++) if (t >= tg[i][0]) { a = tg[i]; b = tg[i + 1] || tg[i]; }
    const prev = tg[Math.max(0, tg.indexOf(a) - 1)], k = inOut(prog(t, a[0], a[0] + 0.8));
    return [lerp(prev[1], a[1], k), lerp(prev[2], a[2], k), lerp(prev[3], a[3], k)];
  }
  function subs() { const s = TM.subs.find((q) => t >= q[1] && t < q[2] + 0.05); if (!s) return;
    c.font = '400 44px "IE"'; const words = s[0].split(' '), lines = []; let cur = '';
    for (const w of words) { const tr = cur ? cur + ' ' + w : w; if (c.measureText(tr).width > 900 && cur) { lines.push(cur); cur = w; } else cur = tr; } lines.push(cur);
    const lh = 54, h = lines.length * lh + 34, y0 = 1760 - h / 2, mw = Math.max(...lines.map((l) => c.measureText(l).width)) + 56;
    c.fillStyle = 'rgba(0,0,0,0.62)'; rr(540 - mw / 2, y0, mw, h, 22); c.fill(); lines.forEach((l, i) => T(l, 540, y0 + 17 + lh / 2 + i * lh, 44, WH, 'IE')); }

  function header() { c.save(); c.globalAlpha = 0.9; T('КАТТА ДАВРА', 60, 90, 34, WH, 'IB', 'left'); T('@kattadavrauz', 60, 132, 26, Y, 'IE', 'left'); c.restore(); }

  function hook() { const k1 = out3(prog(t, 0.15, 0.6)), k2 = out3(prog(t, 0.45, 0.9)), o = 1 - prog(t, P.t02[0] - 0.4, P.t02[0]);
    if (o <= 0) return; c.save(); c.globalAlpha = o; const s = lerp(1, 0.6, prog(t, 3.2, P.t02[0]));
    c.translate(540, 820); c.scale(s, s);
    c.globalAlpha = o * k1; T('ТАКСИ БОЗОРИ:', 0, -90 + (1 - k1) * 60, 112, WH);
    c.globalAlpha = o * k2; T('КИМ КИМНИКИ?', 0, 40 + (1 - k2) * 60, 124, Y); c.restore();
    pop(1.9, 540, 1080, () => pill('5 ТА СЕРВИС · 1 ДАРАХТ', 0, 0, 38, R, WH), P.t02[0] - 0.4); }

  function tip() { const a = P.t07[0]; if (t < a) return; const o = 1 - prog(t, P.t08[0] - 0.3, P.t08[0]); if (o <= 0) return;
    c.save(); c.globalAlpha = o; c.fillStyle = 'rgba(13,18,32,0.78)'; c.fillRect(0, 0, W, H);
    pop(a + 0.1, 540, 520, () => pill('МАСЛАҲАТ', 0, 0, 44, Y, BG));
    for (const [i, x] of [[0, 380], [1, 700]]) pop(a + 0.5 + i * 0.4, x, 900, () => {
      c.fillStyle = '#18213A'; rr(-110, -200, 220, 400, 36); c.fill(); c.lineWidth = 5; c.strokeStyle = i ? GR : Y; rr(-110, -200, 220, 400, 36); c.stroke();
      c.fillStyle = i ? GR : Y; rr(-55, -70, 110, 110, 26); c.fill(); T('TAXI', 0, -15, 30, BG); T(`${i + 1}-ИЛОВА`, 0, 110, 30, WH, 'IE'); });
    pop(kw('t07', 'биттаси') - 0.1, 540, 1260, () => pill('БИТТАСИ ТЎХТАСА — ИККИНЧИСИ', 0, 0, 40, GR, BG));
    c.restore(); }

  function question() { const a = P.t08[0]; if (t < a) return; const o = 1 - prog(t, P.t09[0] - 0.3, P.t09[0]); if (o <= 0) return;
    c.save(); c.globalAlpha = o; c.fillStyle = BG; c.fillRect(0, 0, W, H);
    const k = out3(prog(t, a, a + 0.5)); c.globalAlpha = o * k; T('СИЗ ҚАЙСИ', 540, 700, 110, WH); T('ТАКСИДАН', 540, 820, 110, WH); T('ФОЙДАЛАНАСИЗ?', 540, 940, 100, Y);
    pop(kw('t08', 'изоҳда') - 0.1, 540, 1150, () => pill('ИЗОҲДА ЁЗИНГ ↓', 0, 0, 52, R, WH)); c.restore(); }

  function channel() { const a = P.t09[0]; if (t < a - 0.3) return; c.save(); c.globalAlpha = prog(t, a - 0.3, a); c.fillStyle = BG; c.fillRect(0, 0, W, H);
    pop(a, 540, 900, () => { c.fillStyle = 'rgba(255,255,255,0.08)'; rr(-420, -165, 840, 330, 48); c.fill(); c.strokeStyle = 'rgba(255,255,255,0.18)'; c.lineWidth = 2; rr(-420, -165, 840, 330, 48); c.stroke();
      const g = c.createLinearGradient(-374, -110, -154, 110); g.addColorStop(0, Y); g.addColorStop(1, '#ff7a00'); c.fillStyle = g; c.beginPath(); c.arc(-264, 0, 110, 0, Math.PI * 2); c.fill(); T('КД', -264, 4, 96, BG);
      T('КАТТА ДАВРА', -110, -42, 72, WH, 'IB', 'left'); T('@kattadavrauz', -110, 52, 46, Y, 'IE', 'left'); });
    pop(a + 0.8, 540, 1240, () => { const s = 1 + 0.04 * Math.sin((t - a) * 6); c.scale(s, s); pill('ОБУНА БЎЛИНГ', 0, 0, 56, R, WH); });
    c.restore(); }

  window.__seek = async (time) => {
    for (const f of ['IB', 'IE']) await document.fonts.load(`400 60px "${f}"`);
    t = tt = time; c.setTransform(1, 0, 0, 1, 0, 0); bg();
    const [cx, cy, z] = cam(); ZOOM = z; c.save(); c.translate(540, lerp(900, 980, clamp((z - 1) / 0.55))); c.scale(z, z); c.translate(-cx, -cy); tree(); facts(); c.restore();
    hook(); tip(); question(); channel(); header(); subs();
  };
})();
