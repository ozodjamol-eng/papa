// Набор болванки PAPA: примитивы с понятными цветами + ключи камеры.
// Цвета: человек — синий, предмет в руках — жёлтый, товар/аппарат — белый с тёмным, окружение — серое, вода — голубая.
import * as THREE from 'three';

export const ease = (x) => { x = Math.min(Math.max(x, 0), 1); return x * x * (3 - 2 * x); };
export const easeOut = (x) => { x = Math.min(Math.max(x, 0), 1); return 1 - Math.pow(1 - x, 3); };
export const lerp = (a, b, k) => a + (b - a) * k;
export const lerp3 = (a, b, k) => [lerp(a[0], b[0], k), lerp(a[1], b[1], k), lerp(a[2], b[2], k)];

// keys: [[t, [x,y,z]], ...] — плавная интерполяция по отрезкам
export function track(keys, t) {
  if (t <= keys[0][0]) return keys[0][1];
  for (let i = 0; i < keys.length - 1; i++) {
    const [t0, a] = keys[i], [t1, b] = keys[i + 1];
    if (t <= t1) return lerp3(a, b, ease((t - t0) / (t1 - t0)));
  }
  return keys[keys.length - 1][1];
}

const mat = (c, o = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.75, metalness: 0.05, ...o });
export const COL = { person: 0x3b6fd8, skin: 0x8fb0f0, prop: 0xf2c230, product: 0xf4f4f2, productDark: 0x1d2a44,
  accent: 0x2f8ff0, gold: 0xc89334, env: 0x9a9a96, envDark: 0x6d6d69, ground: 0xb9b7ae, water: 0x7fd0ff };

export function stage(scene, { ground = true, sky = 0xd9dcd6 } = {}) {
  scene.background = new THREE.Color(sky);
  scene.fog = new THREE.Fog(sky, 18, 45);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x8a8a80, 0.9));
  const sun = new THREE.DirectionalLight(0xffffff, 2.0);
  sun.position.set(-6, 10, 7); sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  Object.assign(sun.shadow.camera, { left: -8, right: 8, top: 8, bottom: -8, near: 1, far: 40 });
  scene.add(sun);
  if (ground) {
    const g = new THREE.Mesh(new THREE.PlaneGeometry(80, 80), mat(COL.ground));
    g.rotation.x = -Math.PI / 2; g.receiveShadow = true; scene.add(g);
  }
}

export function box(scene, [w, h, d], [x, y, z], color, o = {}) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat(color, o));
  m.position.set(x, y, z); m.castShadow = true; m.receiveShadow = true; scene.add(m); return m;
}

// Человек 1,75 м: тело-капсула, голова, руки и ноги, шаг через walk(phase)
export function person(scene, { height = 1.75, color = COL.person } = {}) {
  const g = new THREE.Group(); const s = height / 1.75;
  const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.19 * s, 0.55 * s, 6, 12), mat(color));
  body.position.y = 1.15 * s; g.add(body);
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.12 * s, 20, 16), mat(COL.skin));
  head.position.y = 1.62 * s; g.add(head);
  const nose = new THREE.Mesh(new THREE.SphereGeometry(0.03 * s, 8, 8), mat(COL.skin));
  nose.position.set(0, 1.62 * s, 0.12 * s); g.add(nose); // показывает, куда смотрит
  const limb = (len, r) => { const p = new THREE.Group(); const m = new THREE.Mesh(new THREE.CapsuleGeometry(r, len, 4, 8), mat(color)); m.position.y = -len / 2 - r; p.add(m); m.castShadow = true; return p; };
  const legL = limb(0.72 * s, 0.07 * s), legR = limb(0.72 * s, 0.07 * s);
  legL.position.set(-0.1 * s, 0.86 * s, 0); legR.position.set(0.1 * s, 0.86 * s, 0);
  const armL = limb(0.55 * s, 0.055 * s), armR = limb(0.55 * s, 0.055 * s);
  armL.position.set(-0.26 * s, 1.42 * s, 0); armR.position.set(0.26 * s, 1.42 * s, 0);
  [legL, legR, armL, armR].forEach((p) => g.add(p));
  g.traverse((o) => { if (o.isMesh) { o.castShadow = true; } });
  scene.add(g);
  return {
    g, armL, armR, legL, legR,
    walk(phase, amt = 1) { const a = Math.sin(phase) * 0.45 * amt; legL.rotation.x = a; legR.rotation.x = -a; armL.rotation.x = -a * 0.6; body.position.y = 1.15 * s + Math.abs(Math.cos(phase)) * 0.02 * amt; },
    place(pos, yaw) { g.position.set(...pos); g.rotation.y = yaw; },
  };
}

// Баклажка 10 л (≈ 22×18×30 см) с ручкой
export function canister(scene, color = COL.prop) {
  const g = new THREE.Group();
  const b = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.3, 0.16), mat(color, { roughness: 0.35 }));
  b.position.y = 0.15; g.add(b);
  const neck = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.03, 0.05, 16), mat(color)); neck.position.set(0.05, 0.325, 0); g.add(neck);
  const h = new THREE.Mesh(new THREE.TorusGeometry(0.045, 0.012, 8, 16, Math.PI), mat(color)); h.position.set(-0.04, 0.3, 0); g.add(h);
  g.traverse((o) => { if (o.isMesh) o.castShadow = true; });
  scene.add(g); return g;
}

// Аппарат GOLD WATER в пропорциях реального (по фото модели 10L — 5 000 so'm):
// корпус ≈ 1,0 × 1,9 × 0,7 м, тёмный козырёк сверху, синяя панель цены, окно налива на высоте ≈ 0,8–1,25 м, правая колонка управления.
export function machineGoldWater(scene, [x, y, z] = [0, 0, 0]) {
  const g = new THREE.Group(); g.position.set(x, y, z);
  const add = (geo, color, p, o) => { const m = new THREE.Mesh(geo, mat(color, o)); m.position.set(...p); m.castShadow = true; m.receiveShadow = true; g.add(m); return m; };
  // корпус с настоящей нишей налива: задняя часть + передние плиты вокруг проёма
  add(new THREE.BoxGeometry(1.0, 1.65, 0.45), COL.product, [0, 0.95, -0.125]);
  const HX0 = -0.31, HX1 = 0.11, HY0 = 0.72, HY1 = 1.28, FZ = 0.225, FD = 0.25;
  add(new THREE.BoxGeometry(HX0 + 0.5, 1.65, FD), COL.product, [(-0.5 + HX0) / 2, 0.95, FZ]);
  add(new THREE.BoxGeometry(0.5 - HX1, 1.65, FD), COL.product, [(HX1 + 0.5) / 2, 0.95, FZ]);
  add(new THREE.BoxGeometry(HX1 - HX0, HY0 - 0.125, FD), COL.product, [(HX0 + HX1) / 2, (0.125 + HY0) / 2, FZ]);
  add(new THREE.BoxGeometry(HX1 - HX0, 1.775 - HY1, FD), COL.product, [(HX0 + HX1) / 2, (HY1 + 1.775) / 2, FZ]);
  add(new THREE.BoxGeometry(HX1 - HX0, HY1 - HY0, 0.01), 0x2a2d33, [(HX0 + HX1) / 2, (HY0 + HY1) / 2, 0.105]); // задняя стенка ниши
  add(new THREE.BoxGeometry(HX1 - HX0, 0.01, FD), 0x5a5e66, [(HX0 + HX1) / 2, HY0 + 0.005, FZ], { metalness: 0.6, roughness: 0.3 }); // поддон
  const fr = 0x8c9096, fo = { metalness: 0.6, roughness: 0.3 };
  add(new THREE.BoxGeometry(0.03, HY1 - HY0 + 0.06, 0.02), fr, [HX0 - 0.015, (HY0 + HY1) / 2, 0.36], fo);
  add(new THREE.BoxGeometry(0.03, HY1 - HY0 + 0.06, 0.02), fr, [HX1 + 0.015, (HY0 + HY1) / 2, 0.36], fo);
  add(new THREE.BoxGeometry(HX1 - HX0 + 0.06, 0.03, 0.02), fr, [(HX0 + HX1) / 2, HY1 + 0.015, 0.36], fo);
  add(new THREE.BoxGeometry(HX1 - HX0 + 0.06, 0.03, 0.02), fr, [(HX0 + HX1) / 2, HY0 - 0.015, 0.36], fo);
  add(new THREE.BoxGeometry(1.12, 0.26, 0.82), COL.productDark, [0, 1.9, 0.02]);   // козырёк
  add(new THREE.BoxGeometry(0.9, 0.17, 0.02), COL.accent, [0, 1.9, 0.44]);         // вывеска GOLD WATER
  add(new THREE.BoxGeometry(0.86, 0.2, 0.02), COL.accent, [0, 1.62, 0.36]);        // ценник 10L — 5 000
  add(new THREE.BoxGeometry(0.24, 0.95, 0.03), COL.productDark, [0.33, 1.0, 0.36]);// колонка управления
  add(new THREE.BoxGeometry(0.3, 0.12, 0.02), COL.accent, [-0.1, 1.4, 0.36]);      // инфо-панель
  const nozzle = add(new THREE.CylinderGeometry(0.015, 0.015, 0.06, 12), 0xcfd3d8, [-0.1, 1.25, 0.2], { metalness: 0.8, roughness: 0.2 });
  add(new THREE.BoxGeometry(1.0, 0.08, 0.72), COL.productDark, [0, 0.08, 0]);      // цоколь
  scene.add(g);
  return { g, nozzleWorld: new THREE.Vector3(x - 0.1, y + 1.22, z + 0.2), windowWorld: new THREE.Vector3(x - 0.15, y + 0.73, z + 0.2) };
}

// Струя воды: цилиндр от точки вниз, длина 0..len
export function stream(scene) {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(0.008, 0.01, 1, 12), mat(COL.water, { emissive: 0x2a7fb0, emissiveIntensity: 0.6, roughness: 0.1 }));
  m.visible = false; scene.add(m);
  return { m, set(top, len) { m.visible = len > 0.002; m.scale.y = Math.max(len, 0.001); m.position.set(top.x, top.y - len / 2, top.z); } };
}
