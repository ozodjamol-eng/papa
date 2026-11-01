import React, {useMemo} from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig, staticFile, Easing} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {useThree} from '@react-three/fiber';
import * as THREE from 'three';

const ff = (fam: string, file: string, range: string) => `@font-face{font-family:${fam};font-weight:800;src:url(${staticFile(file)}) format('woff2');unicode-range:${range}}`;
const R_LAT = 'U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+2000-206F,U+20AC,U+2122,U+2212';
const R_CYR = 'U+0301,U+0400-045F,U+0490-0491,U+04B0-04B1,U+2116';
const R_CYX = 'U+0460-052F,U+1C80-1C8A,U+20B4,U+2DE0-2DFF,U+A640-A69F,U+FE2E-FE2F';
const FONTS = [
  ff('RW', 'raleway-latin-800-normal.woff2', R_LAT), ff('RW', 'raleway-cyrillic-800-normal.woff2', R_CYR), ff('RW', 'raleway-cyrillic-ext-800-normal.woff2', R_CYX),
  ff('MS', 'montserrat-latin-800-normal.woff2', R_LAT), ff('MS', 'montserrat-cyrillic-800-normal.woff2', R_CYR), ff('MS', 'montserrat-cyrillic-ext-800-normal.woff2', R_CYX),
].join('');

const C = (s: number) => Math.round(s * 30);
const B = [0, 2.48, 5.53, 8.57, 11.59, 14.63, 17.67, 20.76, 23.78, 26.8]; // такты музыки (Smooth Soul)
const ease = Easing.bezier(0.45, 0, 0.2, 1);
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const mix = (a: string, b: string, t: number) => '#' + new THREE.Color(a).lerp(new THREE.Color(b), t).getHexString();

// План 10 × 8 м = 80 м² (x: -5..5, z: -4..4). Перегородки: [x0,z0,x1,z1]
const H = 2.7, T = 0.12;
const OUTER: number[][] = [[-5, -4, 5, -4], [5, -4, 5, 4], [-5, 4, 5, 4], [-5, -4, -5, 4]];
const PART: number[][] = [
  [-5, -0.5, -3.1, -0.5], [-2.3, -0.5, 0.4, -0.5], [1.3, -0.5, 2.3, -0.5], [3.2, -0.5, 5, -0.5], // поперёк
  [-2.2, -4, -2.2, -0.5], [1, -4, 1, -0.5],                       // санузел | детская | спальня
  [2, -0.5, 2, 1.2], [2, 2.1, 2, 4],                              // прихожая | гостиная
];
const Wall: React.FC<{w: number[]; h: number; color: string; t?: number}> = ({w, h, color, t = T}) => {
  const [x0, z0, x1, z1] = w; const len = Math.hypot(x1 - x0, z1 - z0) + t; const ang = Math.atan2(z1 - z0, x1 - x0);
  if (h <= 0.001) return null;
  return <mesh position={[(x0 + x1) / 2, h / 2, (z0 + z1) / 2]} rotation={[0, -ang, 0]} castShadow receiveShadow>
    <boxGeometry args={[len, h, t]} /><meshStandardMaterial color={color} roughness={0.9} />
  </mesh>;
};
const Box: React.FC<{p: number[]; s: number[]; c: string; drop: number; r?: number; e?: string; ei?: number}> = ({p, s, c, drop, r = 0.7, e, ei = 0}) => drop < 0.02 ? null : (
  <mesh position={[p[0], p[1] + (1 - Math.min(drop, 1)) * 1.6, p[2]]} castShadow receiveShadow>
    <boxGeometry args={s as any} /><meshStandardMaterial color={c} roughness={r} emissive={e || '#000'} emissiveIntensity={ei} />
  </mesh>
);

type Shot = {a: number; b: number; p0: number[]; p1: number[]; l0: number[]; l1: number[]; fov: number};
const V = (a: number[]) => new THREE.Vector3(a[0], a[1], a[2]);
const TOUR: Shot[] = [
  {a: B[3], b: B[4], p0: [-0.1, 1.55, 3.3], p1: [-0.7, 1.5, 3.1], l0: [-2.5, 1.0, -0.3], l1: [-2.9, 1.0, -0.3], fov: 66},   // меҳмонхона
  {a: B[4], b: B[5], p0: [-2.6, 1.75, 0.1], p1: [-2.1, 1.7, 0.5], l0: [0.9, 0.8, 3.2], l1: [1.0, 0.8, 3.0], fov: 64},      // ошхона
  {a: B[5], b: B[6], p0: [4.4, 1.8, -0.7], p1: [3.9, 1.75, -0.75], l0: [2.6, 0.5, -3.4], l1: [2.7, 0.5, -3.4], fov: 72},     // ётоқхона
  {a: B[6], b: B[7], p0: [0.75, 1.75, -0.65], p1: [0.6, 1.7, -0.8], l0: [-1.3, 0.4, -3.2], l1: [-1.5, 0.4, -3.1], fov: 74}, // болалар
];
const Cam: React.FC<{f: number}> = ({f}) => {
  const {camera} = useThree();
  const t = f / 30;
  const cl = (x: number) => Math.min(1, Math.max(0, x));
  let p: THREE.Vector3, look: THREE.Vector3, fov = 34;
  const tour = TOUR.find((sh) => t >= sh.a && t < sh.b);
  if (tour) {
    const k = ease(cl((t - tour.a) / (tour.b - tour.a)));
    p = V(tour.p0).lerp(V(tour.p1), k); look = V(tour.l0).lerp(V(tour.l1), k); fov = tour.fov;
  } else if (t >= B[7]) {
    const k = ease(cl((t - B[7]) / 2.6)); const ang = 0.55 + 0.35 * k;
    p = new THREE.Vector3(Math.sin(ang) * lerp(9, 15, k), lerp(9, 18, k), Math.cos(ang) * lerp(9, 15, k)); look = new THREE.Vector3(0, 0, 0); fov = 36;
  } else {
    const zt = interpolate(f, [0, C(2.4)], [24, 33], {extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
    const top = new THREE.Vector3(Math.sin(-0.5 + f * 0.006) * 2.2, zt, Math.cos(-0.5 + f * 0.006) * 2.2);
    const k1 = ease(cl((t - 2.2) / 2.6)); const orbit = f * 0.0016;
    const iso = new THREE.Vector3(Math.sin(0.55 + orbit) * 15.5, 19, Math.cos(0.55 + orbit) * 15.5);
    const k3 = ease(cl((t - 6.2) / 2.3));
    const close = new THREE.Vector3(Math.sin(0.9 + orbit) * 9.5, 10, Math.cos(0.9 + orbit) * 9.5);
    p = top.lerp(iso, k1).lerp(close, k3); look = new THREE.Vector3(0, 0, 0.3);
  }
  camera.position.copy(p); camera.lookAt(look);
  (camera as THREE.PerspectiveCamera).fov = fov; camera.updateProjectionMatrix();
  return null;
};

const Scene: React.FC<{f: number}> = ({f}) => {
  const {fps} = useVideoConfig();
  const rise = (i: number) => spring({frame: f - C(2.7) - i * 3, fps, config: {damping: 16, stiffness: 110}});
  const fin = interpolate(f, [C(5.55), C(6.6)], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: ease});
  const drop = (i: number) => spring({frame: f - C(6.3) - i * 3, fps, config: {damping: 14, stiffness: 120}});
  const glow = interpolate(f, [C(7.6), C(8.5)], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const wallC = mix('#9a9893', '#f3efe8', fin);
  const floorC = mix('#8f8d88', '#c9a27a', fin);
  const OAK = '#b98a5c', SOFA = '#c9c8c4', DARK = '#2b2b2e';
  const slats = useMemo(() => Array.from({length: 18}, (_, i) => -4.85 + i * 0.16), []);
  return (
    <>
      <color attach="background" args={['#e9e6e1']} />
      <hemisphereLight args={['#fff8ef', '#b9b2a8', 0.9]} />
      <directionalLight position={[6, 12, 5]} intensity={1.6} color={'#fff1dc'} castShadow shadow-mapSize-width={1024} shadow-mapSize-height={1024} shadow-camera-left={-8} shadow-camera-right={8} shadow-camera-top={8} shadow-camera-bottom={-8} />
      {/* земля и плита */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.02, 0]} receiveShadow><planeGeometry args={[60, 60]} /><meshStandardMaterial color={'#e4e0da'} roughness={1} /></mesh>
      <mesh position={[0, -0.01, 0]} receiveShadow><boxGeometry args={[10.2, 0.04, 8.2]} /><meshStandardMaterial color={floorC} roughness={0.75} /></mesh>
      {OUTER.map((w, i) => <Wall key={'o' + i} w={w} h={H} color={wallC} t={0.25} />)}
      {PART.map((w, i) => <Wall key={'p' + i} w={w} h={H * rise(i)} color={wallC} />)}
      {/* мебель: гостиная (x -5..2, z -0.5..4) */}
      <Box p={[-3.0, 0.42, 3.35]} s={[2.8, 0.84, 0.95]} c={SOFA} drop={drop(0)} r={0.95} />
      <Box p={[-3.0, 0.95, 3.75]} s={[2.8, 0.55, 0.2]} c={SOFA} drop={drop(0)} r={0.95} />
      {[-4.35, -1.65].map((x, i) => <Box key={'ar' + i} p={[x, 0.6, 3.35]} s={[0.18, 0.5, 0.95]} c={SOFA} drop={drop(0)} r={0.95} />)}
      {[-3.8, -2.2].map((x, i) => <Box key={'cu' + i} p={[x, 0.95, 3.55]} s={[0.5, 0.4, 0.14]} c={i ? '#b98a5c' : '#e7dccb'} drop={drop(1)} r={1} />)}
      <Box p={[-3.0, 0.2, 2.2]} s={[1.2, 0.4, 0.7]} c={OAK} drop={drop(1)} r={0.5} />
      <Box p={[-3.0, 0.03, 2.5]} s={[3.4, 0.02, 2.4]} c={'#d9d2c7'} drop={drop(1)} r={1} />
      {slats.map((x, i) => <Box key={'s' + i} p={[x + 1.25, 1.35, -0.38]} s={[0.1, 2.7, 0.06]} c={OAK} drop={drop(2)} r={0.55} />)}
      <Box p={[-2.35, 1.3, -0.33]} s={[1.6, 0.9, 0.05]} c={DARK} drop={drop(3)} r={0.3} />
      <Box p={[-2.35, 0.25, -0.25]} s={[2.4, 0.4, 0.4]} c={'#ece7df'} drop={drop(3)} />
      {/* кухня-столовая */}
      <Box p={[0.9, 0.45, 3.65]} s={[2.0, 0.9, 0.6]} c={'#ece7df'} drop={drop(4)} />
      <Box p={[0.9, 0.92, 3.65]} s={[2.04, 0.04, 0.64]} c={'#3a3836'} drop={drop(4)} r={0.3} />
      <Box p={[0.6, 0.38, 1.6]} s={[1.6, 0.06, 0.9]} c={OAK} drop={drop(5)} r={0.5} />
      {/* спальня (x 1..5, z -4..-0.5) */}
      <Box p={[3.2, 0.28, -2.6]} s={[1.8, 0.56, 2.1]} c={'#e8e3db'} drop={drop(6)} r={0.95} />
      <Box p={[3.2, 0.6, -3.65]} s={[2.2, 1.2, 0.12]} c={OAK} drop={drop(6)} r={0.55} />
      {[2.75, 3.65].map((x, i) => <Box key={'pw' + i} p={[x, 0.72, -3.35]} s={[0.7, 0.18, 0.35]} c={'#f7f4ee'} drop={drop(7)} r={1} />)}
      {/* детская (x -2.2..1) */}
      <Box p={[-0.6, 0.25, -3.0]} s={[0.95, 0.5, 1.9]} c={'#dfe6ea'} drop={drop(7)} r={0.95} />
      <Box p={[-0.6, 0.57, -3.7]} s={[0.6, 0.14, 0.32]} c={'#ffffff'} drop={drop(8)} r={1} />
      <Box p={[-0.6, 0.53, -2.5]} s={[0.97, 0.05, 0.9]} c={'#9fb7c4'} drop={drop(8)} r={1} />
      <Box p={[0.45, 0.38, -1.2]} s={[0.9, 0.76, 0.55]} c={OAK} drop={drop(7)} />
      {/* санузел */}
      <Box p={[-4.3, 0.28, -3.2]} s={[1.3, 0.56, 0.75]} c={'#f7f7f5'} drop={drop(8)} r={0.2} />
      {/* прихожая: шкаф */}
      <Box p={[4.65, 1.2, 1.8]} s={[0.6, 2.4, 3.2]} c={'#ece7df'} drop={drop(8)} />
      {/* окна */}
      {[[-3.0, 1.65, 3.86, 2.4, 1.4, 0.04], [-4.86, 1.65, 1.6, 0.04, 1.4, 1.8], [4.86, 1.65, -2.2, 0.04, 1.4, 1.6], [-0.6, 1.65, -3.86, 1.6, 1.4, 0.04], [4.86, 1.65, 0.9, 0.04, 1.4, 1.2]].map((w, i) => (
        <mesh key={'w' + i} position={[w[0], w[1], w[2]]}><boxGeometry args={[w[3], w[4], w[5]]} /><meshStandardMaterial color={mix('#7d8a95', '#dcebf5', fin)} emissive={'#cfe6ff'} emissiveIntensity={0.25 + 0.5 * fin} /></mesh>))}
      {/* кухня: верхние шкафы, стулья, подвесы */}
      <Box p={[0.9, 1.95, 3.78]} s={[2.0, 0.7, 0.35]} c={'#ece7df'} drop={drop(9)} />
      {[[0.1, 1.05, -1], [1.1, 1.05, -1], [0.1, 2.15, 1], [1.1, 2.15, 1]].map((c, i) => <React.Fragment key={'ch' + i}>
        <Box p={[c[0], 0.46, c[1]]} s={[0.44, 0.05, 0.42]} c={'#d8cdbd'} drop={drop(10)} r={0.8} />
        <Box p={[c[0], 0.7, c[1] + c[2] * 0.2]} s={[0.44, 0.45, 0.04]} c={'#d8cdbd'} drop={drop(10)} r={0.8} />
      </React.Fragment>)}
      {[0.2, 1.0].map((x, i) => <Box key={'pl' + i} p={[x, 1.95, 1.6]} s={[0.22, 0.22, 0.22]} c={'#f2d9b0'} drop={glow} e={'#ffb860'} ei={2 * glow} />)}
      <pointLight position={[0.6, 1.8, 1.6]} intensity={4 * glow} distance={4} color={'#ffcf8a'} />
      {/* спальня: тумбы, лампы, ковёр, шкаф */}
      {[1.95, 4.45].map((x, i) => <Box key={'ns' + i} p={[x, 0.25, -3.3]} s={[0.5, 0.5, 0.45]} c={OAK} drop={drop(11)} r={0.5} />)}
      {[1.95, 4.45].map((x, i) => <Box key={'lp' + i} p={[x, 0.65, -3.3]} s={[0.22, 0.3, 0.22]} c={'#f6e4c4'} drop={glow} e={'#ffb860'} ei={1.6 * glow} />)}
      <pointLight position={[3.2, 1.6, -3.0]} intensity={3 * glow} distance={4} color={'#ffcf8a'} />
      <Box p={[3.2, 0.03, -2.2]} s={[2.8, 0.02, 2.0]} c={'#d4c8b8'} drop={drop(11)} r={1} />
      <Box p={[4.65, 1.2, -1.4]} s={[0.6, 2.4, 1.6]} c={'#ece7df'} drop={drop(12)} />
      <Box p={[3.2, 0.62, -2.55]} s={[1.75, 0.12, 1.4]} c={'#c9c8c4'} drop={drop(12)} r={1} />
      {/* детская: стол, полки, ковёр */}
      <Box p={[-1.6, 0.38, -1.0]} s={[1.1, 0.06, 0.55]} c={OAK} drop={drop(12)} r={0.5} />
      <Box p={[-1.6, 1.5, -0.62]} s={[1.1, 0.04, 0.22]} c={OAK} drop={drop(13)} />
      <Box p={[-1.6, 1.85, -0.62]} s={[1.1, 0.04, 0.22]} c={OAK} drop={drop(13)} />
      <Box p={[-0.5, 0.03, -2.2]} s={[1.8, 0.02, 1.4]} c={'#cfdbe2'} drop={drop(13)} r={1} />
      <pointLight position={[-0.6, 2.2, -2.2]} intensity={3 * glow} distance={4} color={'#fff0d8'} />
      <pointLight position={[-2.8, 2.2, 2.4]} intensity={3 * glow} distance={5} color={'#fff0d8'} />
      {/* тёплая LED-подсветка карниза в гостиной */}
      <Box p={[-1.5, 2.6, 3.88]} s={[6.8, 0.04, 0.04]} c={'#ffd9a0'} drop={glow} e={'#ffb860'} ei={2.5 * glow} />
      <pointLight position={[-2.8, 2.3, 2.2]} intensity={6 * glow} distance={6} color={'#ffcf8a'} />
      <Cam f={f} />
    </>
  );
};

const Title: React.FC<{f: number; a: number; b: number; main: string; sub?: string}> = ({f, a, b, main, sub}) => {
  const {fps} = useVideoConfig();
  const inn = spring({frame: f - a, fps, config: {damping: 20, stiffness: 120}});
  const out = interpolate(f, [b - 8, b], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  if (f < a - 1 || f > b) return null;
  return <div style={{position: 'absolute', left: 0, right: 0, bottom: 300, textAlign: 'center', opacity: Math.min(inn, out)}}>
    <div style={{fontFamily: 'RW', fontWeight: 800, fontSize: 70, letterSpacing: '0.16em', color: '#1d1c1a', transform: `translateY(${(1 - inn) * 26}px)`, textShadow: '0 2px 18px rgba(255,255,255,.65)'}}>{main}</div>
    {sub && <div style={{fontFamily: 'MS', fontWeight: 800, fontSize: 32, letterSpacing: '0.22em', color: '#8a6a45', marginTop: 16, transform: `translateY(${(1 - inn) * 18}px)`}}>{sub}</div>}
  </div>;
};

export const Kvartira: React.FC = () => {
  const f = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const endIn = spring({frame: f - C(B[8]), fps: 30, config: {damping: 20, stiffness: 110}});
  return (
    <AbsoluteFill style={{background: '#e9e6e1'}}>
      <style>{FONTS + '*{font-feature-settings:"lnum" 1,"pnum" 1}'}</style>
      <ThreeCanvas width={width} height={height} shadows gl={{antialias: true, toneMapping: THREE.ACESFilmicToneMapping}}>
        <Scene f={f} />
      </ThreeCanvas>
      <AbsoluteFill style={{background: 'linear-gradient(180deg, rgba(233,230,225,0) 62%, rgba(233,230,225,.88) 86%, rgba(233,230,225,.95) 100%)'}} />
      <Title f={f} a={C(0.35)} b={C(B[1])} main="БЎШ ҚУТИ" sub="80 м²" />
      <Title f={f} a={C(B[1] + 0.25)} b={C(B[2])} main="ДЕВОРЛАР" sub="ХОНАЛАРГА БЎЛАМИЗ" />
      <Title f={f} a={C(B[2] + 0.25)} b={C(B[3])} main="3D ДИЗАЙН" sub="МЕБЕЛЬ · РАНГ · ЁРУҒЛИК" />
      <Title f={f} a={C(B[3] + 0.2)} b={C(B[4])} main="МЕҲМОНХОНА" sub="ИЛИҚ МИНИМАЛИЗМ" />
      <Title f={f} a={C(B[4] + 0.2)} b={C(B[5])} main="ОШХОНА" sub="ОВҚАТЛАНИШ ЗОНАСИ" />
      <Title f={f} a={C(B[5] + 0.2)} b={C(B[6])} main="ЁТОҚХОНА" sub="ТИНЧЛИК ВА ҚУЛАЙЛИК" />
      <Title f={f} a={C(B[6] + 0.2)} b={C(B[7])} main="БОЛАЛАР ХОНАСИ" sub="ЁРУҒ ВА ХАВФСИЗ" />
      <Title f={f} a={C(B[7] + 0.25)} b={C(B[8])} main="ЭКРАНДА ҚАНДАЙ" sub="ҲАЁТДА ШУНДАЙ" />
      {f >= C(B[8]) && <AbsoluteFill style={{background: `rgba(243,239,232,${0.92 * endIn})`, alignItems: 'center', justifyContent: 'center'}}>
        <div style={{textAlign: 'center', opacity: endIn, transform: `translateY(${(1 - endIn) * 30}px)`}}>
          <div style={{fontFamily: 'RW', fontWeight: 800, fontSize: 64, letterSpacing: '0.16em', color: '#1d1c1a'}}>3D ДИЗАЙН</div>
          <div style={{fontFamily: 'RW', fontWeight: 800, fontSize: 150, color: '#8a6a45', margin: '18px 0 6px'}}>$3</div>
          <div style={{fontFamily: 'MS', fontWeight: 800, fontSize: 36, letterSpacing: '0.2em', color: '#1d1c1a'}}>1 м² УЧУН</div>
          <div style={{fontFamily: 'MS', fontWeight: 800, fontSize: 38, letterSpacing: '0.06em', color: '#1d1c1a', marginTop: 70, padding: '18px 36px', border: '3px solid #1d1c1a', borderRadius: 14}}>@ozodjamoldizaynbot</div>
        </div>
      </AbsoluteFill>}
    </AbsoluteFill>
  );
};
