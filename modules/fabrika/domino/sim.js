// Физика домино PAPA (Rapier). Один и тот же код — в Node (проверка таймингов) и в браузере (рендер).
// Единицы: высота обычной костяшки = 1. Гравитация подобрана под темп ролика.
// Схема: герой-костяшка → змейка (trunk) → клин, который расширяется → поле цепочек (столбцы картинки).
export const P = {
  g: 100, dt: 1 / 240, fps: 30,
  H: 1, T: 0.16, W: 0.5, step: 0.5,
  hero: { H: 3.2, T: 0.45, W: 1.8, push: 1.15, spin: -6.5 },
  trunkN: 78, trunkAmp: 3.2,
  wedgeN: 14,
  rowPitch: 0.6, fieldStep: 0.5,
};

// bitmap: {cols, rows, on(c,r)} — c слева направо (по +z), r сверху вниз (сверху = дальше по +x)
export function buildWorld(R, bitmap) {
  const world = new R.World({ x: 0, y: -P.g, z: 0 });
  world.timestep = P.dt;
  const ground = world.createCollider(R.ColliderDesc.cuboid(200, 0.5, 200).setTranslation(60, -0.5, 0).setFriction(0.6));
  const bodies = []; // {body, hx, hy, hz, kind, on, order}
  const add = (x, z, yaw, w, h, t, kind, extra = {}) => {
    const q = { x: 0, y: Math.sin(yaw / 2), z: 0, w: Math.cos(yaw / 2) };
    const rb = world.createRigidBody(R.RigidBodyDesc.dynamic().setTranslation(x, h / 2 + 0.001, z).setRotation(q).setCanSleep(true));
    world.createCollider(R.ColliderDesc.cuboid(t / 2, h / 2, w / 2).setFriction(0.45).setRestitution(0.02).setDensity(1), rb);
    const b = { body: rb, hx: t / 2, hy: h / 2, hz: w / 2, kind, order: bodies.length, ...extra };
    bodies.push(b); return b;
  };
  const hero = add(0, 0, 0, P.hero.W, P.hero.H, P.hero.T, 'hero');
  // змейка: x вперёд, z = A*sin²(πu) — начинается и заканчивается курсом +x
  const L = P.trunkN * P.step * 1.02, x0 = 2.25;
  const pts = []; const N = 4000;
  for (let i = 0; i <= N; i++) { const u = i / N; pts.push([x0 + u * L, P.trunkAmp * Math.sin(Math.PI * u) ** 2 * (u < 0.5 ? 1 : 1)]); }
  // по длине дуги
  let acc = 0, next = 0, k = 0; const trunk = [];
  for (let i = 1; i < pts.length && k < P.trunkN; i++) {
    const dx = pts[i][0] - pts[i - 1][0], dz = pts[i][1] - pts[i - 1][1]; const s = Math.hypot(dx, dz);
    if (acc + s >= next) { const yaw = -Math.atan2(dz, dx); trunk.push(add(pts[i][0], pts[i][1], yaw, P.W, P.H, P.T, 'trunk')); k++; next += P.step; }
    acc += s;
  }
  let x = trunk[trunk.length - 1].body.translation().x;
  const fieldW = bitmap.cols * P.rowPitch;
  const wedge = [];
  for (let i = 1; i <= P.wedgeN; i++) {
    const w = P.W * Math.pow((fieldW + 0.3) / P.W, i / P.wedgeN);
    x += P.step;
    wedge.push(add(x, 0, 0, w, P.H, P.T, 'wedge'));
  }
  const fx0 = x + P.step + 0.05;
  const field = [];
  for (let c = 0; c < bitmap.cols; c++) {
    const z = -fieldW / 2 + (c + 0.5) * P.rowPitch;
    for (let j = 0; j < bitmap.rows; j++) {
      const r = bitmap.rows - 1 - j;
      field.push(add(fx0 + j * P.fieldStep, z, 0, P.W, P.H, P.T, 'field', { on: bitmap.on(c, r), c, j }));
    }
  }
  const fieldBox = { x0: fx0, x1: fx0 + (bitmap.rows - 1) * P.fieldStep + 1, z0: -fieldW / 2, z1: fieldW / 2 };
  return { world, bodies, hero, trunk, wedge, field, fieldBox };
}

// Прогон: на каждый кадр — позиции/повороты всех тел + «фронт волны»
export function simulate(R, W, dur) {
  const { world, bodies, hero } = W;
  const nb = bodies.length, nf = Math.round(dur * P.fps), sub = Math.round(1 / (P.fps * P.dt));
  const data = new Float32Array(nf * nb * 7);
  const front = []; let pushed = false, t = 0;
  const chain = [W.hero, ...W.trunk, ...W.wedge];
  for (let f = 0; f < nf; f++) {
    for (let s = 0; s < sub; s++) {
      if (!pushed && t >= P.hero.push) { hero.body.wakeUp(); hero.body.setAngvel({ x: 0, y: 0, z: P.hero.spin }, true); pushed = true; }
      world.step(); t += P.dt;
    }
    let o = f * nb * 7;
    for (const b of bodies) {
      const p = b.body.translation(), q = b.body.rotation();
      data[o++] = p.x; data[o++] = p.y; data[o++] = p.z; data[o++] = q.x; data[o++] = q.y; data[o++] = q.z; data[o++] = q.w;
    }
    // фронт: последняя упавшая (наклон > 25°) костяшка в цепи; в поле — средняя дальность волны
    let fr = null;
    for (const b of chain) { const q = b.body.rotation(); const up = 1 - 2 * (q.x * q.x + q.z * q.z); if (up < 0.9) fr = b; }
    let fx = fr ? fr.body.translation().x : 0, fz = fr ? fr.body.translation().z : 0, inField = 0;
    let sum = 0, cnt = 0;
    for (const b of W.field) { const q = b.body.rotation(); const up = 1 - 2 * (q.x * q.x + q.z * q.z); if (up < 0.9) { sum += b.body.translation().x; cnt++; } }
    if (cnt) { inField = cnt / W.field.length; fx = Math.max(fx, sum / cnt); fz = 0; }
    front.push({ x: fx, z: fz, inField });
  }
  return { data, nb, nf, front };
}
