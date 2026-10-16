import assert from 'node:assert/strict';
import fs from 'node:fs';import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {videoConfig} from '../src/case.generated.mjs';
import {renderScene} from '../src/scene.mjs';
import {createTimeline} from '../src/timeline.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
for(const filename of ['cases/CASE_001.json','cases/CASE_SHORT.json']){
 const cfg=JSON.parse(fs.readFileSync(path.join(root,filename),'utf8'));
 const t=createTimeline(cfg);assert(Math.abs(t.end-cfg.duration*30)<2);const frames=[0,Math.round(t.end*.15),Math.round(t.end*.35),Math.round(t.end*.6),t.end-1];
 for(const f of frames){const html=renderScene(f,cfg);assert(html.includes('iphone-screen'));assert(!html.includes('undefined'));assert(!html.includes('NaN'));}
 assert(t.present.galleryOriginal===cfg.show_gallery);assert(t.present.profile===cfg.show_bot_profile);
 for(const p of Object.values(cfg.photos))assert(fs.existsSync(path.join(root,'public',p)),p);
 if(cfg.show_gallery){const g=Math.round(t.when('galleryOriginal',.5));const html=renderScene(g,cfg);assert(html.includes('gallery-photos-grid'));assert(html.includes(cfg.photos.original));assert(html.includes(cfg.photos.reference));assert(!html.includes(cfg.photos.result));}
 const viewer=t.when('viewer',.5); if(viewer!==null){const h=renderScene(Math.round(viewer),cfg); assert(h.includes('viewer-chrome-transparent.png')); assert(!h.includes('time-patch')); }
 const r=Math.round(t.when('result',.7));const html=renderScene(r,cfg);assert(html.includes(cfg.photos.result));
 console.log(filename, 'OK',t.end,'frames');
}
assert(videoConfig.case_id==='CASE_001'||videoConfig.case_id==='CASE_SHORT');
console.log('Frame and asset smoke tests passed');
