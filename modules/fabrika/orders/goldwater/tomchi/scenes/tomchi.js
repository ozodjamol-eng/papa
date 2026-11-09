// «Томчи» — стеклянная капля + грузы. t: 0–CLIPA_END клип A (знакомство, грузы прилипают), далее клип B (грузы падают, капля сияет)
export const T = {
  aEnd: 11.0, attach: [7.7, 8.4, 9.2], sink: [4.1, 6.3], fall: [12.05, 13.85, 15.75], shine: 17.9,
};
export const DURATION = 21.2;
const ease = (x) => { x = Math.min(Math.max(x, 0), 1); return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
const eo = (x) => { x = Math.min(Math.max(x, 0), 1); return 1 - Math.pow(1 - x, 3); };
const lerp = (a, b, k) => a + (b - a) * k;

function backdrop(THREE) {
  const c = document.createElement('canvas'); c.width = 1024; c.height = 1820; const g = c.getContext('2d');
  const gr = g.createLinearGradient(0, 0, 0, c.height); gr.addColorStop(0, '#0b2a5c'); gr.addColorStop(0.55, '#061a3d'); gr.addColorStop(1, '#020a1c');
  g.fillStyle = gr; g.fillRect(0, 0, c.width, c.height);
  const rnd = (s => () => (s = (s * 16807) % 2147483647) / 2147483647)(7);
  for (let i = 0; i < 46; i++) {
    const x = rnd() * c.width, y = rnd() * c.height, r = 18 + rnd() * 90, gold = rnd() < 0.35;
    const rg = g.createRadialGradient(x, y, 0, x, y, r);
    const col = gold ? '250,210,120' : '90,170,255';
    rg.addColorStop(0, `rgba(${col},${0.10 + rnd() * 0.22})`); rg.addColorStop(1, `rgba(${col},0)`);
    g.fillStyle = rg; g.beginPath(); g.arc(x, y, r, 0, 7); g.fill();
  }
  const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace;
  const m = new THREE.Mesh(new THREE.PlaneGeometry(9, 16), new THREE.MeshBasicMaterial({ map: tex }));
  m.position.z = -4; return m;
}
function label(THREE, text) {
  const c = document.createElement('canvas'); c.width = 512; c.height = 160; const g = c.getContext('2d');
  g.fillStyle = 'rgba(14,16,24,0.88)'; const r = 60; g.beginPath(); g.roundRect(16, 20, 480, 120, r); g.fill();
  g.strokeStyle = 'rgba(236,190,92,0.9)'; g.lineWidth = 5; g.stroke();
  g.fillStyle = '#ffffff'; g.font = '900 72px Inter'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(text, 256, 84);
  const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace;
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthTest: false }));
  s.scale.set(1.0, 0.31, 1); s.renderOrder = 10; return s;
}
function clump(THREE, color, seed) {
  const g = new THREE.Group(); const rnd = ((s) => () => (s = (s * 16807) % 2147483647) / 2147483647)(seed * 1000 + 11);
  const base = new THREE.Color(color);
  for (let i = 0; i < 26; i++) {
    const r = 0.035 + rnd() * 0.07;
    const geo = new THREE.IcosahedronGeometry(r, 4); const p = geo.attributes.position;
    for (let k = 0; k < p.count; k++) { const x = p.getX(k), y = p.getY(k), z = p.getZ(k); const n = 1 + 0.25 * Math.sin(x * 60 + i) * Math.cos(y * 50 - i); p.setXYZ(k, x * n, y * n, z * n); }
    geo.computeVertexNormals();
    const c = base.clone().offsetHSL(0, (rnd() - 0.5) * 0.1, (rnd() - 0.5) * 0.14);
    const m = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color: c, roughness: 0.9 }));
    const a = rnd() * 6.28, b = rnd() * 3.14, d = rnd() * 0.17;
    m.position.set(Math.cos(a) * Math.sin(b) * d, Math.cos(b) * d, Math.sin(a) * Math.sin(b) * d * 0.6);
    g.add(m);
  }
  return g;
}

export function build(THREE, scene, renderer) {
  scene.add(backdrop(THREE));
  const key = new THREE.DirectionalLight(0xffffff, 2.2); key.position.set(3, 4, 5); scene.add(key);
  const rim = new THREE.DirectionalLight(0x9fd0ff, 2.5); rim.position.set(-4, 1, -2); scene.add(rim);
  const gold = new THREE.PointLight(0xffc860, 6, 8); gold.position.set(2, -1, 2); scene.add(gold);

  // teardrop profile
  const pts = []; const m = 1.15;
  for (let i = 0; i <= 64; i++) { const t = Math.PI * i / 64; pts.push(new THREE.Vector2(Math.sin(t) * Math.pow(Math.sin(t / 2), m) * 0.95, Math.cos(t) * 1.25)); }
  const dropGeo = new THREE.LatheGeometry(pts, 96);
  const mat = new THREE.MeshPhysicalMaterial({ transmission: 1, thickness: 1.6, ior: 1.33, roughness: 0.03, metalness: 0,
    clearcoat: 1, clearcoatRoughness: 0.02, specularIntensity: 1, envMapIntensity: 1.6,
    attenuationColor: new THREE.Color('#bfe6ff'), attenuationDistance: 3.0, color: 0xffffff });
  const drop = new THREE.Mesh(dropGeo, mat); drop.scale.setScalar(0.72); const grp = new THREE.Group(); grp.add(drop); scene.add(grp);
  // glow behind drop (shine phase)
  const gc = document.createElement('canvas'); gc.width = gc.height = 256; const gg = gc.getContext('2d');
  const rg = gg.createRadialGradient(128, 128, 0, 128, 128, 128); rg.addColorStop(0, 'rgba(160,220,255,0.9)'); rg.addColorStop(0.4, 'rgba(120,190,255,0.35)'); rg.addColorStop(1, 'rgba(120,190,255,0)');
  gg.fillStyle = rg; gg.fillRect(0, 0, 256, 256);
  const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(gc), transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
  glow.scale.set(3.6, 3.6, 1); glow.position.z = -1.2; grp.add(glow);

  const specks = []; const rs = ((s) => () => (s = (s * 16807) % 2147483647) / 2147483647)(99);
  for (let i = 0; i < 48; i++) {
    const r = 0.008 + rs() * 0.018; const yy = -0.75 + rs() * 1.1; const rad = 0.42 * (1 - Math.max(0, yy) / 0.95) * Math.sqrt(rs());
    const a = rs() * 6.28; const m = new THREE.Mesh(new THREE.IcosahedronGeometry(r, 1), new THREE.MeshStandardMaterial({ color: new THREE.Color().setHSL(0.07 + rs() * 0.04, 0.5, 0.16 + rs() * 0.14), roughness: 1, transparent: true }));
    m.position.set(Math.cos(a) * rad, yy, Math.sin(a) * rad); m.userData.ph = rs() * 6.28; grp.add(m); specks.push(m);
  }
  const names = ['ОҲАК', 'ХЛОР', 'ҚУМ'];
  const cols = [0xb9b2a2, 0x7c8a6c, 0xa9844f];
  const anchors = [[-0.56, -0.42, 0.35], [0.58, -0.15, 0.3], [0.0, -0.98, 0.45]];
  const fromPos = [[-2.2, 2.2, 1], [2.2, 2.5, 1], [0.3, -3.5, 1]];
  const loads = names.map((n, i) => { const g = new THREE.Group(); const c = clump(THREE, cols[i], i * 1.7); const l = label(THREE, n);
    l.position.set(0, i === 2 ? -0.3 : 0.3, 0.3); l.scale.set(0.62, 0.19, 1); g.add(c); g.add(l); scene.add(g); return g; });

  const dirty = new THREE.Color('#c08a40'), clean = new THREE.Color('#bfe6ff');
  return { update(t) {
    // drop vertical: bob + sink while loaded + rise when clean
    const bob = Math.sin(t * 1.6) * 0.06;
    let y = 0.15 + bob;
    const sinkK = ease((t - T.sink[0]) / (T.sink[1] - T.sink[0])) * (t < T.aEnd ? 1 : 1 - ease((t - T.fall[0]) / (T.shine - T.fall[0])));
    const loadsOn = t >= T.attach[0];
    y -= 0.55 * (loadsOn ? 1 : sinkK * 0.4) * (t < T.aEnd ? ease((t - T.attach[0]) / 2.0) : 1 - ease((t - T.fall[0]) / (T.shine + 1 - T.fall[0])));
    y += 0.35 * ease((t - T.shine) / 1.6);
    grp.position.y = y; grp.rotation.y = t * 0.35;
    // dirt tint follows loads
    let dirt = t < T.aEnd ? ease((t - T.attach[0]) / 2.2) : 1 - ease((t - T.fall[0]) / (T.fall[2] + 0.6 - T.fall[0]));
    mat.attenuationColor.copy(clean).lerp(dirty, dirt * 0.85); mat.attenuationDistance = lerp(3.0, 1.2, dirt);
    mat.roughness = lerp(0.03, 0.12, dirt);
    specks.forEach((m) => { m.visible = dirt > 0.02; m.material.opacity = dirt; m.position.y += Math.sin(t * 2 + m.userData.ph) * 0.0008; });
    const sh = ease((t - T.shine) / 1.2); glow.material.opacity = sh * 0.9; mat.envMapIntensity = 1.6 + sh * 1.2;
    // loads
    loads.forEach((g, i) => {
      const a = T.attach[i]; const k = eo((t - a) / 0.6);
      const an = anchors[i]; const fp = fromPos[i];
      if (t < a) { g.visible = false; return; }
      g.visible = true;
      let p = [lerp(fp[0], an[0], k), lerp(fp[1], an[1] + y, k), lerp(fp[2], an[2], k)];
      if (t >= T.aEnd) {
        const fi = [2, 1, 0].indexOf(i); const ft = T.fall[fi]; const f = Math.max(0, t - ft);
        p = [an[0] * (1 + f * 0.4), an[1] + y - 4.9 * f * f, an[2]];
        g.visible = p[1] > -6;
      }
      g.position.set(...p); g.children[0].rotation.set(t * 0.4 + i, t * 0.3, 0);
    });
  } };
}
export function camera(t) {
  const z = 7.2 - 0.6 * ease(t / 11) * (t < 11 ? 1 : 0) - (t >= 11 ? 0.3 : 0);
  return { pos: [0, 0.1, z], look: [0, -0.1, 0] };
}
