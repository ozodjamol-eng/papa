import React from 'react';
import {Composition} from 'remotion';
import {Digest} from './Digest.jsx';
import {timeline} from './scene.js';
import demo from './demo.json';

const FPS = 60;
// Длина ролика считается из данных (курс есть/нет, сколько новостей)
export const Root = () => (
  <Composition id="Digest" component={Digest} width={1080} height={1920} fps={FPS}
    durationInFrames={Math.round(timeline(demo).DUR * FPS)} defaultProps={{data: demo}}
    calculateMetadata={({props}) => ({durationInFrames: Math.round(timeline(props.data).DUR * FPS)})} />
);
