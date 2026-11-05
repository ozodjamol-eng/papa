// GOLD WATER — «Шиша» (glass product film). Движок: three.js, стиль Glass Product (Lemo-Opuscar, MIT) + фирменный стиль GOLD WATER.
// Детерминированный рендер: window.renderAt(t) рисует кадр на время t (сек).
import * as THREE from 'three';
import { Reflector } from 'three/addons/objects/Reflector.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

const W = 1080, H = 1920;
export const DUR = 29.9; window.DUR = DUR;
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const seg = (t, a, b) => clamp((t - a) / (b - a));
const eio = x => x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
const eo = x => 1 - Math.pow(1 - x, 3);
const ei = x => x * x * x;
const back = x => { const c = 1.7; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); };
const lerp = (a, b, x) => a + (b - a) * x;
let seed = 7; const R = () => (seed = (seed * 16807) % 2147483647) / 2147483647;

// Бренд
const NAVY = new THREE.Color('#001A43'), BLUE = new THREE.Color('#0494F9'), GOLD = new THREE.Color('#F2C14E'), GOLD_L = new THREE.Color('#FAE289');

const SC = [[0, 4.35, 'drop1'], [4.35, 10.0, 'stack'], [10.0, 13.75, 'macro'], [13.75, 17.0, 'drop2'], [17.0, 20.35, 'machine'], [20.35, 24.45, 'cities'], [24.45, DUR, 'logo']];
const sceneAt = t => SC.find(s => t >= s[0] && t < s[1]) || SC[SC.length - 1];

// —— Renderer ——
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
const RS = .75; renderer.setPixelRatio(RS); renderer.setSize(W, H);
renderer.toneMapping = THREE.NeutralToneMapping; renderer.toneMappingExposure = 1.0;
document.getElementById('stage').appendChild(renderer.domElement);
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(30, W / H, 1, 3000);

// —— Студия: полосы света → карта окружения (запекается каждый кадр) ——
const env = new THREE.Scene(); env.background = new THREE.Color('#000');
const strip = (w, h, col) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: new THREE.Color(col), side: THREE.DoubleSide })); env.add(m); return m; };
const L = {
  left: strip(22, 170, '#f4f8ff'), right: strip(22, 170, '#fff8ec'), top: strip(160, 70, '#ffffff'),
  back: strip(260, 14, '#dfeaff'), sweep: strip(26, 260, '#ffffff'), aura: strip(150, 150, '#0494F9'), gold: strip(30, 170, '#F2C14E'),
};
const face = (m, p) => { m.position.set(...p); m.lookAt(0, 0, 0); };
face(L.left, [-150, 40, -60]); face(L.right, [150, 40, -70]); face(L.top, [0, 170, 10]); face(L.back, [0, 20, -190]); face(L.aura, [0, -60, 120]); face(L.gold, [120, 10, 90]);
const pmrem = new THREE.PMREMGenerator(renderer); let envRT = null;
function setEnv(o) {
  const I = (m, c, k) => m.material.color.set(c).multiplyScalar(k);
  I(L.left, '#f4f8ff', 3.2 * (o.side ?? 1)); I(L.right, '#fff8ec', 3.2 * (o.side ?? 1)); I(L.top, '#ffffff', 1.1 * (o.top ?? 1)); I(L.back, '#dfeaff', 1.4 * (o.back ?? 1));
  L.sweep.visible = (o.sweepI || 0) > 0;
  if (L.sweep.visible) { const a = (o.az || 0) + Math.PI + o.sweepX * 1.3, r = 170; L.sweep.position.set(Math.sin(a) * r, 30, Math.cos(a) * r); L.sweep.lookAt(0, 0, 0); L.sweep.rotateZ(.25); L.sweep.material.color.setScalar(o.sweepI); }
  L.aura.visible = (o.aura || 0) > 0; if (L.aura.visible) L.aura.material.color.copy(o.auraCol || BLUE).multiplyScalar(o.aura);
  L.gold.visible = (o.gold || 0) > 0; if (L.gold.visible) L.gold.material.color.copy(GOLD).multiplyScalar(o.gold);
  const rt = pmrem.fromScene(env, 0, 1, 1000); scene.environment = rt.texture; if (envRT) envRT.dispose(); envRT = rt;
}
// Фон: глубокий navy бренда → чёрный (радиальный), без линии горизонта
const bgc = document.createElement('canvas'); bgc.width = 540; bgc.height = 960;
{ const g = bgc.getContext('2d'), gr = g.createRadialGradient(270, 380, 10, 270, 440, 620); gr.addColorStop(0, '#0b2a5c'); gr.addColorStop(.38, '#04163a'); gr.addColorStop(.75, '#010818'); gr.addColorStop(1, '#000000'); g.fillStyle = gr; g.fillRect(0, 0, 540, 960); }
const bgTex = new THREE.CanvasTexture(bgc); bgTex.colorSpace = THREE.SRGBColorSpace; scene.background = bgTex;

// —— Пол: чёрный глянец + размытое отражение + каустика + кольца ——
const floorShader = {
  name: 'GWFloor',
  uniforms: {
    color: { value: null }, tDiffuse: { value: null }, textureMatrix: { value: null },
    uRefl: { value: .4 }, uFade: { value: 230 }, uTime: { value: 0 },
    uC: { value: new THREE.Vector4(0, 0, 40, 0) },
    uWave: { value: Array.from({ length: 6 }, () => new THREE.Vector4(0, 0, 0, 0)) },
    uA: { value: BLUE.clone() }, uB: { value: GOLD.clone() }, uCenter: { value: new THREE.Vector2(0, 0) },
    uBg: { value: bgTex }, uRes: { value: new THREE.Vector2(W * .75, H * .75) },
  },
  vertexShader: `uniform mat4 textureMatrix; varying vec4 vUv; varying vec3 vW;
    void main(){ vUv = textureMatrix * vec4(position, 1.); vec4 w = modelMatrix * vec4(position, 1.); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`,
  fragmentShader: `uniform sampler2D tDiffuse; uniform float uRefl, uFade, uTime; uniform vec4 uC; uniform vec4 uWave[6]; uniform vec3 uA, uB; uniform vec2 uCenter; uniform sampler2D uBg; uniform vec2 uRes;
    varying vec4 vUv; varying vec3 vW;
    vec2 h2(vec2 p){ p = vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3))); return fract(sin(p) * 43758.5453); }
    float vor(vec2 p, float t){ vec2 i = floor(p), f = fract(p); float d1 = 8., d2 = 8.;
      for (int y = -1; y <= 1; y++) for (int x = -1; x <= 1; x++) { vec2 g = vec2(float(x), float(y)); vec2 o = h2(i + g); o = .5 + .45 * sin(t + 6.2831 * o);
        float d = length(g + o - f); if (d < d1) { d2 = d1; d1 = d; } else if (d < d2) d2 = d; }
      return d2 - d1; }
    float caus(vec2 p, float t){ vec2 q = p + .55 * vec2(sin(p.y * 1.3 + t), cos(p.x * 1.1 - t * .8)); float e = vor(q * 1.4, t); return exp(-e * 14.); }
    void main(){
      vec2 xz = vW.xz; float r0 = length(xz - uCenter);
      vec3 refl = vec3(0.);
      for (int i = 0; i < 8; i++) { float a = float(i) * 2.39996; float rr = sqrt((float(i) + .5) / 8.) * 4.;
        refl += texture2DProj(tDiffuse, vUv + vec4(cos(a) * rr, sin(a) * rr, 0., 0.) * vUv.w / 600.).rgb; }
      refl /= 8.;
      vec3 col = refl * uRefl * exp(-r0 * r0 / (uFade * uFade));
      col += vec3(.012, .02, .04) * exp(-r0 * r0 / 9000.);
      if (uC.w > 0.) { vec2 d = xz - uC.xy; float r = length(d) / uC.z; float m = exp(-r * r * 1.6);
        vec2 p = d / uC.z * 3.2; vec3 c3 = vec3(caus(p * .985, uTime), caus(p, uTime), caus(p * 1.015, uTime));
        vec3 rr3 = vec3(exp(-pow((r - .70) / .06, 2.)), exp(-pow((r - .72) / .06, 2.)), exp(-pow((r - .74) / .06, 2.)));
        col += (c3 * m * .6 + rr3 * 1.1) * uC.w * mix(vec3(1.), uA * 1.3, .35); }
      for (int k = 0; k < 6; k++) { vec4 Wv = uWave[k]; if (Wv.w <= 0.) continue;
        float r = length(xz - Wv.xy); float x = (r - Wv.z) / (.9 + Wv.z * .025);
        vec3 band = vec3(exp(-pow(x + .35, 2.) * 3.), exp(-x * x * 3.), exp(-pow(x - .35, 2.) * 3.));
        col += band * mix(uA, uB, clamp(Wv.z / 120., 0., 1.)) * Wv.w * exp(-r * r / 12000.); }
      vec3 bgc = texture2D(uBg, gl_FragCoord.xy / uRes).rgb;
      col = mix(bgc, col + bgc * .25, exp(-r0 * r0 / (uFade * uFade * 2.2)));
      gl_FragColor = vec4(col, 1.);
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
    }`
};
const floor = new Reflector(new THREE.PlaneGeometry(3000, 3000), { shader: floorShader, textureWidth: 540, textureHeight: 960, clipBias: .002 });
floor.rotation.x = -Math.PI / 2; scene.add(floor);
const reflUpdate = floor.onBeforeRender.bind(floor); floor.onBeforeRender = () => { };
const FU = floor.material.uniforms;

// —— Материалы ——
const glass = (o = {}) => new THREE.MeshPhysicalMaterial(Object.assign({ color: '#ffffff', roughness: .015, transmission: 1, thickness: 3, ior: 1.5, dispersion: 4, attenuationColor: new THREE.Color('#eef6ff'), attenuationDistance: 200, specularIntensity: 1, envMapIntensity: 1.3, side: THREE.DoubleSide }, o));
const glow = (col) => new THREE.ShaderMaterial({
  uniforms: { uCol: { value: col.clone() }, uI: { value: 0 } },
  vertexShader: `varying vec3 vN; varying vec3 vV; void main(){ vec4 w = modelViewMatrix * vec4(position,1.); vN = normalize(normalMatrix*normal); vV = normalize(-w.xyz); gl_Position = projectionMatrix*w; }`,
  fragmentShader: `uniform vec3 uCol; uniform float uI; varying vec3 vN; varying vec3 vV; void main(){ float f = pow(max(dot(vN,vV),0.), 1.5); gl_FragColor = vec4(uCol * uI * (.35 + f * 1.4) + vec3(f*f*f) * uI * .6, 1.); }`,
});

// —— Капля ——
function dropGeo(Rr = 40, Ht = 88) {
  const pts = [];
  for (let i = 0; i <= 40; i++) { const a = -Math.PI / 2 + (Math.PI / 2) * i / 40; pts.push(new THREE.Vector2(Rr * Math.cos(a), Rr * Math.sin(a))); }
  for (let i = 1; i <= 60; i++) { const s = i / 60; pts.push(new THREE.Vector2(Math.max(.01, Rr * Math.pow(Math.cos(s * Math.PI / 2), 1.35)), s * Ht)); }
  const g = new THREE.LatheGeometry(pts, 160); g.translate(0, -18, 0); g.computeVertexNormals(); return g;
}
const gDrop = new THREE.Group(); scene.add(gDrop);
const dropMat = glass({ thickness: 45, ior: 1.33, dispersion: 6, attenuationColor: new THREE.Color('#d9eeff'), attenuationDistance: 140 });
const drop = new THREE.Mesh(dropGeo(), dropMat); gDrop.add(drop);
const core = new THREE.Mesh(new THREE.SphereGeometry(5.5, 48, 32), glow(GOLD)); core.position.y = -14; gDrop.add(core);
// ифлосликлар (непрозрачные тёмные частицы — видны сквозь стекло)
const NS = 70;
const speckMat = new THREE.MeshStandardMaterial({ color: '#3b2c1c', roughness: .55, metalness: .1 });
const specks = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(1.7, 1), speckMat, NS); scene.add(specks);
const SP = Array.from({ length: NS }, () => {
  const r = 26 * Math.cbrt(R()), th = R() * 6.283, ph = Math.acos(2 * R() - 1);
  return { p: new THREE.Vector3(r * Math.sin(ph) * Math.cos(th), r * Math.cos(ph) * .9 - 12, r * Math.sin(ph) * Math.sin(th)), ph: R() * 6.28, s: .6 + R() * .9,
    disc: Math.min(8, Math.floor(Math.pow(R(), 1.6) * 9)), rr: 8 + R() * 36, ra: R() * 6.283, sy: 150 + R() * 70, t0: R() * .9 };
});

// —— Стек фильтров (10 ступеней) ——
const gStack = new THREE.Group(); scene.add(gStack);
const DISC_R = 55, NDISC = 10;
const discs = [], rims = [];
for (let k = 0; k < NDISC; k++) {
  let m;
  if (k < 3) m = new THREE.MeshPhysicalMaterial({ color: '#dfe8f2', roughness: .3, metalness: 0, clearcoat: 1, clearcoatRoughness: .1, transparent: true, opacity: .42, envMapIntensity: 1.4, depthWrite: false }); // мембраны (матовое стекло, дёшево)
  else if (k < 6) m = new THREE.MeshPhysicalMaterial({ color: '#0d0f12', roughness: .5, metalness: .2, clearcoat: .5, clearcoatRoughness: .25, envMapIntensity: .55 }); // уголь
  else m = glass({ thickness: 6, dispersion: 5 });                                                                        // чистое стекло
  const d = new THREE.Mesh(new THREE.CylinderGeometry(DISC_R, DISC_R, 4.5, 128, 1), m); gStack.add(d); discs.push(d);
  const rim = new THREE.Mesh(new THREE.TorusGeometry(DISC_R + .6, 1.25, 16, 160), glow(BLUE.clone().lerp(GOLD, k / 9))); rim.rotation.x = Math.PI / 2; gStack.add(rim); rims.push(rim);
}
// центральный поток воды (свет внутри стеклянной трубки)
const streamMat = new THREE.ShaderMaterial({
  uniforms: { uHead: { value: 0 }, uI: { value: 0 }, uA: { value: BLUE.clone() }, uB: { value: GOLD.clone() } },
  vertexShader: `varying vec2 vUv; varying float vY; void main(){ vUv = uv; vY = position.y; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.); }`,
  fragmentShader: `uniform float uHead, uI; uniform vec3 uA, uB; varying vec2 vUv; varying float vY;
    void main(){ float d = vY - uHead; float head = exp(-d*d/60.); float tail = d > 0. ? exp(-d/90.) * .7 : 0.;
      float k = max(head, tail); vec3 c = mix(uB, uA, clamp((vY + 130.)/260., 0., 1.)); gl_FragColor = vec4((c * k * 1.8 + vec3(head*head) * .9) * uI, 1.); }`,
});
const stream = new THREE.Mesh(new THREE.CylinderGeometry(2.4, 2.4, 420, 24, 60, true), streamMat); gStack.add(stream);
const tube = new THREE.Mesh(new THREE.CylinderGeometry(5.5, 5.5, 420, 48, 1, true), new THREE.MeshPhysicalMaterial({ color: '#cfe6ff', roughness: .05, transparent: true, opacity: .18, envMapIntensity: 2, depthWrite: false })); gStack.add(tube);
const LIT = Array.from({ length: NDISC }, (_, k) => 6.3 + k * .32);   // время вспышки ступени k (по голосу «ҳар бир томчи … ўтади»)
const SNAP = [13.42, 13.68];

// —— Аппарат (настоящее фото, вырезка) ——
const loader = new THREE.TextureLoader();
const texM = loader.load('v1.png'); texM.colorSpace = THREE.SRGBColorSpace; texM.anisotropy = 8;
const mMat = new THREE.MeshBasicMaterial({ map: texM, transparent: true, alphaTest: .35, toneMapped: false });
const glintU = { uG: { value: -2 }, uGI: { value: 0 }, uDim: { value: 1 } };
mMat.onBeforeCompile = sh => {
  Object.assign(sh.uniforms, glintU);
  sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nuniform float uG, uGI, uDim;')
    .replace('#include <map_fragment>', `#include <map_fragment>
      diffuseColor.rgb *= uDim;
      { float x = vMapUv.x * .55 + (1. - vMapUv.y) * .45; float b = exp(-pow((x - uG) / .045, 2.)); diffuseColor.rgb += vec3(1., .96, .85) * b * uGI * .55; }`);
};
const MH = 150, MW = MH * 442 / 895;
const machine = new THREE.Mesh(new THREE.PlaneGeometry(MW, MH), mMat);
const gMachine = new THREE.Group(); gMachine.add(machine); scene.add(gMachine);
const mGlow = new THREE.Mesh(new THREE.PlaneGeometry(330, 330), new THREE.ShaderMaterial({
  transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, uniforms: { uI: { value: 0 }, uC: { value: GOLD.clone() } },
  vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.); }',
  fragmentShader: 'uniform float uI; uniform vec3 uC; varying vec2 vUv; void main(){ float r = length(vUv-.5)*2.; gl_FragColor = vec4(uC * exp(-r*r*9.) * uI, 1.); }'
}));
mGlow.position.z = -30; gMachine.add(mGlow);

// —— Логотип: медальон в стеклянном кольце ——
const texL = loader.load('logo.png'); texL.colorSpace = THREE.SRGBColorSpace; texL.anisotropy = 8;
const gLogo = new THREE.Group(); scene.add(gLogo);
const logo = new THREE.Mesh(new THREE.CircleGeometry(52, 128), new THREE.MeshBasicMaterial({ map: texL, toneMapped: false }));
gLogo.add(logo);
const ring = new THREE.Mesh(new THREE.TorusGeometry(64, 5, 48, 220), glass({ thickness: 14, dispersion: 7, ior: 1.55 })); gLogo.add(ring);
const lGlow = mGlow.clone(); lGlow.material = mGlow.material.clone(); lGlow.position.z = -25; gLogo.add(lGlow);

// —— Постобработка ——
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const bloom = new UnrealBloomPass(new THREE.Vector2(W / 2, H / 2), .55, .5, .92); composer.addPass(bloom);
composer.addPass(new OutputPass());

// —— Оверлей: титры (стиль «Б»: Raleway 800 разрядка, Montserrat 800 цифры), жирно ——
const ov = document.getElementById('ov'), g2 = ov.getContext('2d');
function spaced(txt, x, y, font, size, col, track = .14, a = 1, align = 'center') {
  g2.save(); g2.globalAlpha = a; g2.font = `800 ${size}px ${font}`; g2.fillStyle = col; g2.textBaseline = 'alphabetic';
  g2.fontVariantNumeric = 'lining-nums';
  const chars = [...txt]; const ws = chars.map(c => g2.measureText(c).width); const tr = size * track;
  const tot = ws.reduce((s, w) => s + w, 0) + tr * (chars.length - 1);
  let cx = align === 'center' ? x - tot / 2 : x;
  g2.shadowColor = 'rgba(0,8,30,.65)'; g2.shadowBlur = size * .35;
  chars.forEach((c, i) => { g2.fillText(c, cx, y); cx += ws[i] + tr; });
  g2.restore(); return tot;
}
function goldLine(y, w, a) { g2.save(); g2.globalAlpha = a; const gr = g2.createLinearGradient(540 - w / 2, 0, 540 + w / 2, 0); gr.addColorStop(0, 'rgba(242,193,78,0)'); gr.addColorStop(.5, '#F2C14E'); gr.addColorStop(1, 'rgba(242,193,78,0)'); g2.fillStyle = gr; g2.fillRect(540 - w / 2, y, w, 4); g2.restore(); }
// появление: подъём + прозрачность (пружина)
const inA = (t, a, d = .45) => clamp((t - a) / d);
const rise = (t, a) => (1 - back(inA(t, a, .55))) * 40;
function title(lines, t, a0, a1, y0) {   // lines: [[txt, size, col, font, track]]
  const o = Math.min(inA(t, a0, .4), 1 - seg(t, a1 - .3, a1));
  if (o <= 0) return;
  let y = y0;
  lines.forEach(([txt, size, col, font, tr], i) => { const st = a0 + i * .18; const oo = Math.min(o, inA(t, st, .4)); spaced(txt, 540, y + rise(t, st), font || 'Raleway', size, col || '#ffffff', tr ?? .14, oo); y += size * 1.32; });
}
function pill(txt, cx, cy, t, a0, a1) {
  const o = Math.min(inA(t, a0, .35), 1 - seg(t, a1 - .3, a1)); if (o <= 0) return;
  const s = .7 + .3 * back(inA(t, a0, .5));
  g2.save(); g2.globalAlpha = o; g2.translate(cx, cy); g2.scale(s, s);
  g2.font = '800 40px Raleway'; const tw = [...txt].reduce((w, c) => w + g2.measureText(c).width + 40 * .12, -40 * .12);
  const w = tw + 76, h = 82;
  g2.fillStyle = 'rgba(4,22,58,.72)'; g2.beginPath(); g2.roundRect(-w / 2, -h / 2, w, h, 41); g2.fill();
  g2.lineWidth = 3; g2.strokeStyle = '#F2C14E'; g2.stroke();
  g2.fillStyle = '#F2C14E'; g2.beginPath(); g2.arc(-w / 2 + 34, 0, 7, 0, 7); g2.fill();
  g2.restore();
  spaced(txt, cx + 14 * s, cy + 14 * s, 'Raleway', 40 * s, '#ffffff', .12, o);
}
function drawOverlay(t) {
  g2.clearRect(0, 0, W, H);
  { const gr = g2.createLinearGradient(0, 1150, 0, 1650); gr.addColorStop(0, 'rgba(0,6,20,0)'); gr.addColorStop(.45, 'rgba(0,6,20,.55)'); gr.addColorStop(1, 'rgba(0,6,20,.35)'); g2.fillStyle = gr; g2.fillRect(0, 1150, W, 500); }
  // S1
  title([['СИЗ ИЧАЁТГАН СУВ', 58], ['ҚАНЧАЛИК ТОЗА?', 74, '#F2C14E', 'Montserrat', .08]], t, 1.0, 4.35, 1330);
  // S2 счётчик ступеней
  if (t >= LIT[0] && t < 10.0) {
    const o = Math.min(inA(t, LIT[0], .25), 1 - seg(t, 9.7, 10.0));
    let n = 0; LIT.forEach(l => { if (t >= l) n++; });
    const pop = n > 0 ? 1 + .18 * Math.exp(-(t - LIT[n - 1]) * 9) : 1;
    g2.save(); g2.globalAlpha = o; g2.translate(540, 1405); g2.scale(pop, pop);
    g2.font = '900 190px Montserrat'; g2.textAlign = 'center'; g2.fontVariantNumeric = 'lining-nums tabular-nums';
    const gr = g2.createLinearGradient(0, -150, 0, 10); gr.addColorStop(0, '#FAE289'); gr.addColorStop(1, '#C89334');
    g2.shadowColor = 'rgba(242,193,78,.45)'; g2.shadowBlur = 40; g2.fillStyle = gr; g2.fillText(String(n).padStart(2, '0'), 0, 0); g2.restore();
    spaced('БОСҚИЧЛИ ТОЗАЛАШ', 540, 1490, 'Raleway', 44, '#ffffff', .16, o);
  }
  // S3
  title([['КЎЗГА КЎРИНМАС', 56], ['ИФЛОСЛИКЛАР', 56], ['ОРТДА ҚОЛАДИ', 62, '#F2C14E', 'Montserrat', .1]], t, 10.15, 13.5, 1290);
  // вспышка «щелчок»
  if (t >= SNAP[1] && t < SNAP[1] + .6) { g2.fillStyle = `rgba(230,244,255,${.55 * Math.exp(-(t - SNAP[1]) * 7)})`; g2.fillRect(0, 0, W, H); }
  // S4
  title([['ТИНИҚ ВА ТОЗА', 66], ['СУВ', 66, '#F2C14E', 'Montserrat', .2]], t, 14.85, 17.0, 1360);
  // S5 цена
  if (t >= 17.1 && t < 20.35) {
    const o = 1 - seg(t, 20.05, 20.35);
    spaced('10 ЛИТР', 540, 1360 + rise(t, 17.2), 'Montserrat', 64, '#ffffff', .12, Math.min(o, inA(t, 17.2)));
    goldLine(1392, 420, Math.min(o, inA(t, 17.6)));
    const s = 1 + .12 * Math.exp(-Math.max(0, t - 18.95) * 8) * (t > 18.95 ? 1 : 0);
    g2.save(); g2.globalAlpha = Math.min(o, inA(t, 18.9, .3)); g2.translate(540, 1500); g2.scale(s, s);
    g2.font = '900 104px Montserrat'; g2.textAlign = 'center'; g2.fontVariantNumeric = 'lining-nums';
    const gr = g2.createLinearGradient(0, -90, 0, 10); gr.addColorStop(0, '#FAE289'); gr.addColorStop(1, '#C89334');
    g2.shadowColor = 'rgba(242,193,78,.4)'; g2.shadowBlur = 30; g2.fillStyle = gr; g2.fillText('5 000 СЎМ', 0, 0); g2.restore();
  }
  // S6 адреса
  const C = [['АНДИЖОН', 20.46], ['АСАКА', 21.26], ['ХЎЖАОБОД', 21.94], ['ФАРҒОНА', 22.86]];
  const pos = [[540 - 205, 1330], [540 + 205, 1330], [540 - 205, 1440], [540 + 205, 1440]];
  C.forEach(([n, a], i) => pill(n, pos[i][0], pos[i][1], t, a - .05, 24.45));
  // S7 финал
  title([['ТОЗА СУВ —', 58], ['СОҒЛОМ ҲАЁТ!', 70, '#F2C14E', 'Montserrat', .1]], t, 25.8, DUR + 1, 1300);
  if (t >= 27.4) { const o = inA(t, 27.4, .4); goldLine(1438, 520, o); spaced('+998 97 290 10 40', 540, 1505 + rise(t, 27.4) * .5, 'Montserrat', 54, '#ffffff', .06, o); }
  // финальное затемнение под концовку OZOD JAMOL (чёрная)
  const fo = seg(t, DUR - .45, DUR); if (fo > 0) { g2.fillStyle = `rgba(0,0,0,${fo})`; g2.fillRect(0, 0, W, H); }
}

// —— Камера ——
function orbit(az, el, dist, look, fov = 30) {
  camera.fov = fov; camera.updateProjectionMatrix();
  camera.position.set(look[0] + Math.sin(az) * Math.cos(el) * dist, look[1] + Math.sin(el) * dist, look[2] + Math.cos(az) * Math.cos(el) * dist);
  camera.lookAt(...look);
}

// —— Кадр ——
const dummy = new THREE.Object3D();
function stackGap(t) {
  if (t < 4.35) return 6;
  if (t < SNAP[0]) return lerp(6, 24, eo(seg(t, 4.35, 6.1)));
  return lerp(24, 6.2, ei(seg(t, SNAP[0], SNAP[1])));
}
window.renderAt = (t) => {
  const [a0, a1, name] = sceneAt(t); const u = seg(t, a0, a1);
  gDrop.visible = name === 'drop1' || name === 'drop2';
  gStack.visible = name === 'stack' || name === 'macro';
  gMachine.visible = name === 'machine' || name === 'cities';
  gLogo.visible = name === 'logo';
  floor.visible = !(name === 'drop1' || name === 'stack' || name === 'macro');
  specks.visible = name === 'drop1' || name === 'stack' || name === 'macro';
  FU.uTime.value = t * .9; FU.uC.value.w = 0; FU.uWave.value.forEach(v => v.w = 0);
  let envO = { side: 1, top: 1, back: 1, sweepI: 0, sweepX: 0, aura: 0, gold: 0, az: 0 };
  let az = 0, el = 0, dist = 300, look = [0, 0, 0];
  bloom.strength = .55;

  if (name === 'drop1') {
    gDrop.position.set(0, 8, 0); gDrop.rotation.set(0, t * .22, Math.sin(t * .8) * .03);
    dropMat.roughness = .015; dropMat.thickness = 45; core.material.uniforms.uI.value = 0;
    az = lerp(-.35, .05, eio(u)); el = .1; dist = lerp(520, 440, eio(u)); look = [0, -30, 0];
    envO.side = lerp(.15, 1, eo(seg(t, .2, 2.2))); envO.top = lerp(.1, .8, seg(t, .5, 3)); envO.back = envO.side;
    envO.sweepI = 6 * Math.sin(Math.PI * seg(t, .3, 3.6)); envO.sweepX = lerp(-1, 1, eio(seg(t, .3, 3.6)));
    // частицы внутри капли
    for (let i = 0; i < NS; i++) { const s = SP[i]; dummy.position.copy(s.p).add(new THREE.Vector3(Math.sin(t * .7 + s.ph) * 2.5, Math.sin(t * .5 + s.ph * 2) * 3, Math.cos(t * .6 + s.ph) * 2.5));
      dummy.position.applyEuler(gDrop.rotation).add(gDrop.position); dummy.scale.setScalar(s.s); dummy.rotation.set(s.ph, t + s.ph, 0); dummy.updateMatrix(); specks.setMatrixAt(i, dummy.matrix); }
    specks.instanceMatrix.needsUpdate = true;
  }
  if (name === 'stack' || name === 'macro') {
    const gap = stackGap(t);
    gStack.position.set(0, 0, 0); gStack.rotation.set(0, t * .12, 0);
    discs.forEach((d, k) => { const y = (4.5 - k) * gap; d.position.y = y; rims[k].position.y = y;
      d.rotation.z = Math.sin(k * 1.7) * .05 * (gap - 6) / 18; rims[k].rotation.y = d.rotation.z;
      const lt = t - LIT[k]; const I = lt < 0 ? .04 : (.8 + 2.6 * Math.exp(-lt * 5));
      rims[k].material.uniforms.uI.value = I * (t > SNAP[1] - .02 ? 1.6 : 1); });
    // голова потока проходит ступени
    let head;
    if (t < LIT[0]) head = lerp(4.5 * gap + 170, 4.5 * gap, eio(seg(t, LIT[0] - .45, LIT[0])));
    else head = (4.5 - Math.min(9.8, (t - LIT[0]) / .32)) * gap;
    if (t > 9.5) head = 200 - ((t - 9.5) * 240 % 420);   // дальше вода течёт непрерывно
    streamMat.uniforms.uHead.value = head; streamMat.uniforms.uI.value = seg(t, 5.7, 6.0) * (t > 9.5 ? .7 : 1);
    if (name === 'stack') { az = lerp(.2, 1.0, eio(u)); el = lerp(.62, .74, u); dist = lerp(880, 820, eio(u)); look = [0, -40, 0]; }
    else { az = lerp(1.0, 1.5, eio(u)); el = lerp(.45, .34, u); dist = lerp(560, 470, eio(seg(t, 10, 13.3))); look = [0, lerp(-10, 5, u), 0];
      if (t > SNAP[1]) { dist += Math.sin((t - SNAP[1]) * 70) * 2 * Math.exp(-(t - SNAP[1]) * 12); } }
    envO.top = 1; envO.sweepI = name === 'stack' ? 5 * Math.sin(Math.PI * seg(t, 4.5, 6.6)) : 0; envO.sweepX = lerp(-1, 1, seg(t, 4.5, 6.6)); envO.az = az;
    envO.aura = .35 * seg(t, 6.3, 9.5); envO.auraCol = BLUE;
    // частицы падают с потоком и застревают на ступенях, потом исчезают
    for (let i = 0; i < NS; i++) { const s = SP[i];
      const k = s.disc; const stopY = (4.5 - k) * gap + 3.2; const t0 = LIT[0] - .4 + s.t0 * .7;
      const y = Math.max(stopY, (4.5 * gap + s.sy) - Math.max(0, t - t0) * 190);
      const fade = 1 - eio(seg(t, 12.25 + s.t0 * .5, 12.95 + s.t0 * .5));
      const x = Math.cos(s.ra) * s.rr, z = Math.sin(s.ra) * s.rr;
      dummy.position.set(x, y - (1 - fade) * 4, z).applyEuler(gStack.rotation); dummy.scale.setScalar(s.s * fade + .0001); dummy.rotation.set(s.ph, s.ph * 2, 0); dummy.updateMatrix(); specks.setMatrixAt(i, dummy.matrix); }
    specks.instanceMatrix.needsUpdate = true;
  }
  if (name === 'drop2') {
    gDrop.position.set(0, 4, 0); gDrop.rotation.set(0, t * .3, 0);
    const c = seg(t, 13.8, 14.95); dropMat.roughness = lerp(.32, .015, eo(c)); dropMat.thickness = 45;
    core.material.uniforms.uI.value = .6 + .15 * Math.sin(t * 3); core.material.uniforms.uCol.value.copy(BLUE).lerp(GOLD, .55 + .3 * Math.sin(t * 1.3));
    floor.position.y = -64; FU.uRefl.value = .45; FU.uFade.value = 210;
    FU.uC.value.set(0, 0, 46, 1.1 * eo(seg(t, 13.75, 14.6))); FU.uCenter.value.set(0, 0);
    [13.78, 14.9, 16.0].forEach((w, i) => { const r = (t - w) * 75; if (t > w) FU.uWave.value[i].set(0, 0, r, 1.4 * Math.exp(-(t - w) * 1.1)); });
    az = lerp(.35, -.25, eio(u)); el = lerp(.02, .09, u); dist = lerp(540, 480, eio(u)); look = [0, -30, 0];
    envO.aura = .9; envO.auraCol = BLUE.clone().lerp(GOLD, .4); envO.gold = .8;
    envO.sweepI = 5.5 * Math.sin(Math.PI * seg(t, 14.6, 16.4)); envO.sweepX = lerp(-1, 1, eio(seg(t, 14.6, 16.4))); envO.az = az;
    bloom.strength = .7;
  }
  if (name === 'machine' || name === 'cities') {
    floor.position.y = -75; FU.uRefl.value = .55; FU.uFade.value = 260; FU.uCenter.value.set(0, 0);
    gMachine.position.set(0, -75 + MH / 2 + .5, 0); gMachine.rotation.set(0, 0, 0);
    glintU.uDim.value = lerp(.0, 1, eo(seg(t, 17.0, 17.5)));
    glintU.uG.value = lerp(-.2, 1.25, eio(seg(t, 17.25, 18.15))); glintU.uGI.value = t < 18.3 ? 1 : 0;
    if (t > 22.9 && t < 23.9) { glintU.uG.value = lerp(-.2, 1.25, eio(seg(t, 22.95, 23.8))); glintU.uGI.value = .7; }
    mGlow.material.uniforms.uI.value = .22 * eo(seg(t, 17.0, 18.0));
    const tt = seg(t, 17.0, 24.45);
    az = lerp(-.12, .14, eio(tt)); el = lerp(.03, .09, tt); dist = lerp(600, 520, eio(tt)); look = [0, -36, 0];
    if (name === 'cities') { [20.46, 21.26, 21.94, 22.86].forEach((w, i) => { if (t > w) FU.uWave.value[i].set(0, 8, (t - w) * 90 + 30, 1.2 * Math.exp(-(t - w) * 1.3)); }); }
    else { if (t > 18.95) FU.uWave.value[0].set(0, 8, (t - 18.95) * 90 + 30, 1.3 * Math.exp(-(t - 18.95) * 1.3)); }
    envO.side = .6;
  }
  if (name === 'logo') {
    floor.position.y = -75; FU.uRefl.value = .5; FU.uFade.value = 240;
    const ap = eo(seg(t, 24.45, 25.4));
    gLogo.position.set(0, lerp(-10, 2, ap), 0); gLogo.scale.setScalar(lerp(.82, 1, back(ap)));
    ring.rotation.set(Math.sin(t * .7) * .1, Math.sin(t * .55) * .38, 0);
    logo.material.color.setScalar(lerp(0, 1, seg(t, 24.45, 25.0)));
    lGlow.material.uniforms.uI.value = .3 * ap;
    FU.uC.value.set(0, 6, 60, .6 * ap);
    if (t > 24.5) FU.uWave.value[0].set(0, 6, (t - 24.5) * 80 + 20, 1.3 * Math.exp(-(t - 24.5) * 1.2));
    if (t > 25.86) FU.uWave.value[1].set(0, 6, (t - 25.86) * 80 + 20, 1.1 * Math.exp(-(t - 25.86) * 1.2));
    az = lerp(.18, -.1, eio(u)); el = .06; dist = lerp(680, 620, eio(u)); look = [0, -62, 0];
    envO.sweepI = 6 * Math.sin(Math.PI * seg(t, 24.7, 26.6)); envO.sweepX = lerp(-1, 1, eio(seg(t, 24.7, 26.6))); envO.az = az; envO.gold = 1.2;
  }
  orbit(az, el, dist, look);
  if (gMachine.visible) gMachine.lookAt(camera.position.x, gMachine.position.y, camera.position.z);
  if (gLogo.visible) gLogo.lookAt(camera.position.x, gLogo.position.y, camera.position.z);
  setEnv(envO);
  scene.updateMatrixWorld(); camera.updateMatrixWorld();
  if (floor.visible) reflUpdate(renderer, scene, camera);
  composer.render();
  drawOverlay(t);
};

Promise.all([document.fonts.load('800 40px Raleway'), document.fonts.load('900 40px Montserrat'), document.fonts.load('800 40px Montserrat'),
  new Promise(r => { const c = () => (texM.image && texL.image && texM.image.complete && texL.image.complete) ? r() : setTimeout(c, 50); c(); })])
  .then(() => { window.renderAt(0); window.ready = true; });
