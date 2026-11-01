import React from 'react';
import {Composition} from 'remotion';
import {Ad} from './Ad';
import {Kvartira} from './Kvartira';
export const Root: React.FC = () => (<>
  <Composition id="GW" component={Ad} durationInFrames={300} fps={30} width={1080} height={1920} />
  <Composition id="KV" component={Kvartira} durationInFrames={804} fps={30} width={1080} height={1920} />
</>);
