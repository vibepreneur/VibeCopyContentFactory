import React from 'react';
import {Composition} from 'remotion';
import {VibeCopy} from './VibeCopy';
import {videoConfig} from './case.generated.mjs';
import {createTimeline} from './timeline.mjs';
export const Root:React.FC=()=>{
 const {end,fps}=createTimeline(videoConfig);
 return <>
  <Composition id="VibeCopySocialFill" component={VibeCopy} width={1080} height={1920} fps={fps} durationInFrames={end} defaultProps={{layout:'socialFill'}}/>
  <Composition id="VibeCopy1080" component={VibeCopy} width={1080} height={1920} fps={fps} durationInFrames={end} defaultProps={{layout:'socialFill'}}/>
  <Composition id="VibeCopyNative" component={VibeCopy} width={887} height={1920} fps={fps} durationInFrames={end} defaultProps={{layout:'native'}}/>
 </>;
};
