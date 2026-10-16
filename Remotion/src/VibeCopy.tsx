import React from 'react';
import {AbsoluteFill,Img,staticFile,useCurrentFrame} from 'remotion';
import {videoConfig} from './case.generated.mjs';
import {renderScene} from './scene.mjs';
import './telegram.css';

type Layout = 'native' | 'socialFill';
const SOURCE_WIDTH=591;
const SOURCE_HEIGHT=1280;
const SOCIAL_WIDTH=1080;
const SOCIAL_HEIGHT=1920;
const SOCIAL_SCALE=SOCIAL_WIDTH/SOURCE_WIDTH;
const SOCIAL_DESIGN_HEIGHT=SOCIAL_HEIGHT/SOCIAL_SCALE;

export const VibeCopy:React.FC<{layout:Layout}> = ({layout}) => {
 const frame=useCurrentFrame();
 const fill=layout==='socialFill';
 const scale=fill?SOCIAL_SCALE:1.5;
 const designHeight=fill?SOCIAL_DESIGN_HEIGHT:SOURCE_HEIGHT;
 const all=[...Object.values(videoConfig.photos),...(videoConfig.gallery_extras||[]),videoConfig.bot?.avatar,videoConfig.ui?.wallpaper,
  'assets/viewer-chrome-transparent.png', 'assets/profile-screen-clean.jpg'].filter(Boolean);
 return <AbsoluteFill style={{overflow:'hidden',backgroundColor:'#b8d9b0'}}>
    <div style={{position:'absolute',height:1,width:1,overflow:'hidden',opacity:0}}>
      {all.map((x,i)=><Img key={i} src={staticFile(String(x))}/>)}
    </div>
    <div style={{position:'absolute',left:0,top:0,width:SOURCE_WIDTH,height:designHeight,
      transform:`scale(${scale})`,transformOrigin:'top left',overflow:'hidden'}}
      dangerouslySetInnerHTML={{__html:renderScene(frame,videoConfig,staticFile,{socialFill:fill})}}/>
  </AbsoluteFill>;
};
