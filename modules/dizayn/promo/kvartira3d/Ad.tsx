import React, {useMemo} from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig, staticFile, Easing} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import * as THREE from 'three';

const NAVY = '#001A43', ROYAL = '#01439A', GOLD = '#C89334', GOLD_HI = '#FAE289', WATER = '#0494F9';
const font = `@font-face{font-family:IDB;src:url(${staticFile('InterDisplay-Black.otf')})}@font-face{font-family:IDX;src:url(${staticFile('InterDisplay-ExtraBold.otf')})}`;

// studio environment for metal reflections
const useEnv = () => useMemo(() => {
  const c = document.createElement('canvas'); c.width = 512; c.height = 256;
  const g = c.getContext('2d')!;
  const gr = g.createLinearGradient(0, 0, 0, 256);
  gr.addColorStop(0, '#0a2a66'); gr.addColorStop(0.45, '#000814'); gr.addColorStop(1, '#02122e');
  g.fillStyle = gr; g.fillRect(0, 0, 512, 256);
  g.fillStyle = '#fff6d8'; g.fillRect(60, 40, 90, 120);   // softbox warm
  g.fillStyle = '#cfe6ff'; g.fillRect(330, 30, 60, 160);  // softbox cool
  g.fillStyle = '#ffffff'; g.fillRect(200, 8, 120, 14);   // top strip
  const t = new THREE.CanvasTexture(c); t.mapping = THREE.EquirectangularReflectionMapping; t.colorSpace = THREE.SRGBColorSpace;
  return t;
}, []);

const dropGeo = () => {
  const pts: THREE.Vector2[] = [];
  for (let i = 64; i >= 0; i--) {
    const a = (i / 64) * Math.PI;
    const r = 0.62 * (1 - Math.cos(a)) * Math.sin(a) * 0.9;
    const y = Math.cos(a) * 1.05;
    pts.push(new THREE.Vector2(Math.max(r, 0.0001), y));
  }
  return new THREE.LatheGeometry(pts, 96);
};

const Scene3D: React.FC<{f: number}> = ({f}) => {
  const env = useEnv();
  const drop = useMemo(dropGeo, []);
  const intro = interpolate(f, [0, 40], [0, 1], {extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
  const ringScale = spring({frame: f - 4, fps: 30, config: {damping: 11, stiffness: 90}});
  const rot = f * 0.022 + (1 - intro) * 2.2;
  const camZ = interpolate(f, [0, 90, 180, 300], [10.5, 7.4, 7.8, 8.6], {easing: Easing.inOut(Easing.cubic)});
  const camY = interpolate(f, [0, 150, 300], [-0.6, 0.3, 0.55]);
  const sweep = ((f % 90) / 90) * 10 - 5;
  const dropY = interpolate(f, [8, 38], [4.5, 0.6], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(.2,.9,.3,1.15)});
  const lift = interpolate(f, [150, 300], [0, 0.25], {extrapolateLeft: 'clamp'});
  const bubbles = useMemo(() => Array.from({length: 40}, (_, i) => ({x: (Math.sin(i * 12.9) * 2.6), z: Math.cos(i * 7.3) * 1.2 - 0.5, s: 0.03 + (i % 5) * 0.012, sp: 0.012 + (i % 7) * 0.003, o: i * 0.37})), []);
  return (
    <>
      <color attach="background" args={[NAVY]} />
      <fog attach="fog" args={[NAVY, 7, 16]} />
      <perspectiveCamera />
      <ambientLight intensity={0.25} />
      <directionalLight position={[3, 5, 4]} intensity={2.2} color={'#fff1cc'} />
      <directionalLight position={[-4, 1, 2]} intensity={1.2} color={'#9cc8ff'} />
      <pointLight position={[sweep, 1.5, 3]} intensity={18} distance={8} color={'#ffffff'} />
      <group position={[0, 0.55 + lift, 0]} rotation={[0.18, rot, 0]}>
        <mesh scale={ringScale}>
          <torusGeometry args={[1.55, 0.16, 64, 200]} />
          <meshPhysicalMaterial color={GOLD} metalness={1} roughness={0.18} envMap={env} envMapIntensity={1.6} clearcoat={1} clearcoatRoughness={0.08} />
        </mesh>
        <mesh scale={ringScale * 0.86} rotation={[Math.PI / 2, 0, 0]}>
          <torusGeometry args={[1.55, 0.035, 32, 200]} />
          <meshPhysicalMaterial color={GOLD_HI} metalness={1} roughness={0.25} envMap={env} />
        </mesh>
      </group>
      <mesh geometry={drop} position={[0, dropY + lift, 0]} rotation={[0, -rot * 0.6, 0]} scale={0.95}>
        <meshPhysicalMaterial color={WATER} metalness={0} roughness={0.04} transmission={0.85} thickness={1.2} ior={1.33} envMap={env} envMapIntensity={2.2} clearcoat={1} transparent opacity={0.92} attenuationColor={ROYAL} attenuationDistance={1.6} />
      </mesh>
      {bubbles.map((b, i) => {
        const y = ((f * b.sp + b.o) % 6) - 3;
        return <mesh key={i} position={[b.x, y, b.z]}><sphereGeometry args={[b.s, 16, 16]} /><meshPhysicalMaterial color={'#cfe9ff'} roughness={0.05} transmission={0.6} envMap={env} transparent opacity={interpolate(f, [20, 60], [0, 0.85], {extrapolateRight: 'clamp', extrapolateLeft: 'clamp'})} /></mesh>;
      })}
      <CamRig z={camZ} y={camY} />
    </>
  );
};
const CamRig: React.FC<{z: number; y: number}> = ({z, y}) => {
  // @ts-ignore
  const {useThree} = require('@react-three/fiber');
  const {camera} = useThree();
  camera.position.set(0, y, z); camera.lookAt(0, -0.15, 0); camera.fov = 38; camera.updateProjectionMatrix();
  return null;
};

const pop = (f: number, at: number) => spring({frame: f - at, fps: 30, config: {damping: 13, stiffness: 140, mass: 0.7}});
const out = (f: number, at: number) => interpolate(f, [at, at + 8], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
const goldText: React.CSSProperties = {background: `linear-gradient(180deg, ${GOLD_HI} 0%, ${GOLD} 55%, #8a5f1c 100%)`, WebkitBackgroundClip: 'text', color: 'transparent', filter: 'drop-shadow(0 6px 18px rgba(0,0,0,.55))'};

export const Ad: React.FC = () => {
  const f = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const T = (s: number) => Math.round(s * 30);
  const sheen = interpolate(f % 60, [0, 60], [-120, 220]);
  const p1 = pop(f, T(0.9)), o1 = out(f, T(3.4));
  const p2 = pop(f, T(3.7)), o2 = out(f, T(6.0));
  const p3 = pop(f, T(6.3));
  const strike = interpolate(f, [T(6.9), T(7.3)], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const p4 = pop(f, T(7.5));
  const p5 = pop(f, T(8.4));
  return (
    <AbsoluteFill style={{fontFamily: 'IDB', color: 'white'}}>
      <style>{font}</style>
      <ThreeCanvas width={width} height={height} gl={{antialias: true, toneMapping: THREE.ACESFilmicToneMapping}}>
        <Scene3D f={f} />
      </ThreeCanvas>
      <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 38%, rgba(1,67,154,.0) 30%, rgba(0,6,20,.85) 100%), linear-gradient(180deg, rgba(0,0,0,0) 55%, rgba(0,8,26,.9) 100%)'}} />
      {/* brand top-left small */}
      <div style={{position: 'absolute', top: 230, width: '100%', textAlign: 'center', fontFamily: 'IDB', fontSize: 64, letterSpacing: 18, ...goldText, opacity: interpolate(f, [10, 30], [0, 1], {extrapolateRight: 'clamp'})}}>GOLD WATER</div>
      {/* S1 */}
      <div style={{position: 'absolute', bottom: 470, width: '100%', textAlign: 'center', opacity: o1, transform: `translateY(${(1 - p1) * 80}px) scale(${0.85 + 0.15 * p1})`}}>
        <div style={{fontSize: 120, lineHeight: 1, letterSpacing: -2}}>ТОЗА СУВ</div>
        <div style={{fontSize: 74, marginTop: 18, ...goldText}}>СОҒЛОМ ҲАЁТ</div>
      </div>
      {/* S2 */}
      <div style={{position: 'absolute', bottom: 470, width: '100%', textAlign: 'center', opacity: o2 * Math.min(1, p2 * 1.4), transform: `translateY(${(1 - p2) * 80}px)`}}>
        <div style={{fontSize: 210, lineHeight: 0.9, ...goldText}}>10</div>
        <div style={{fontSize: 70, marginTop: 10}}>БОСҚИЧЛИ ТОЗАЛАШ</div>
      </div>
      {/* S3 price */}
      <div style={{position: 'absolute', bottom: 430, width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', opacity: Math.min(1, p3 * 1.4)}}>
        <div style={{display: 'inline-block', fontSize: 60, padding: '10px 34px', borderRadius: 60, background: `linear-gradient(90deg, ${GOLD}, ${GOLD_HI})`, color: NAVY, transform: `scale(${p3})`}}>НОЯБРЬ АКЦИЯСИ</div>
        <div style={{position: 'relative', display: 'inline-block', fontSize: 96, marginTop: 34, opacity: 0.75, transform: `scale(${0.8 + 0.2 * p3})`}}>
          $2700
          <div style={{position: 'absolute', left: -10, top: '52%', height: 10, width: `${strike * 110}%`, background: '#ff3b3b', borderRadius: 6, transform: 'rotate(-8deg)'}} />
        </div>
        <div style={{fontSize: 210, lineHeight: 1, marginTop: 6, transform: `scale(${p4})`, ...goldText}}>$2300</div>
      </div>
      {/* contact */}
      <div style={{position: 'absolute', bottom: 300, width: '100%', textAlign: 'center', opacity: Math.min(1, p5 * 1.3), transform: `translateY(${(1 - p5) * 40}px)`}}>
        <div style={{display: 'inline-block', fontFamily: 'IDX', fontSize: 64, padding: '18px 44px', borderRadius: 24, background: 'rgba(255,255,255,.08)', border: `3px solid ${GOLD}`, backdropFilter: 'blur(10px)'}}>+998 97 290 10 40</div>
      </div>
      {/* light sheen on brand */}
      <div style={{position: 'absolute', top: 215, left: `${sheen}%`, width: 120, height: 100, background: 'linear-gradient(90deg,transparent,rgba(255,255,255,.35),transparent)', transform: 'skewX(-20deg)', mixBlendMode: 'overlay'}} />
    </AbsoluteFill>
  );
};
