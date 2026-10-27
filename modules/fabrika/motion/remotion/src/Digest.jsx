import React, {useLayoutEffect, useMemo, useRef, useState} from 'react';
import {AbsoluteFill, continueRender, delayRender, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {createScene} from './scene.js';

const FONTS = [['IDB', 'InterDisplay-Black.otf'], ['IDX', 'InterDisplay-ExtraBold.otf'],
  ['IDS', 'InterDisplay-SemiBold.otf'], ['IDM', 'InterDisplay-Medium.otf']];

export const Digest = ({data}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const ref = useRef(null);
  const [handle] = useState(() => delayRender('fonts'));
  const [ready, setReady] = useState(false);
  useLayoutEffect(() => {
    Promise.all(FONTS.map(([n, f]) => new FontFace(n, `url(${staticFile(f)})`).load().then(ff => document.fonts.add(ff))))
      .then(() => { setReady(true); continueRender(handle); });
  }, [handle]);
  // физическая пружина Remotion (как в интерфейсах Vercel/Linear) вместо формулы
  const SPRING = u => spring({frame: u * fps, fps, config: {damping: 13, stiffness: 120, mass: 0.9}});
  const scene = useMemo(() => (ref.current ? createScene(ref.current.getContext('2d'), data, SPRING) : null), [ready, data]);
  useLayoutEffect(() => { if (ready && scene) scene.renderAt(frame / fps); }, [frame, ready, scene]);
  return <AbsoluteFill style={{background: '#000'}}><canvas ref={ref} width={1080} height={1920} /></AbsoluteFill>;
};
