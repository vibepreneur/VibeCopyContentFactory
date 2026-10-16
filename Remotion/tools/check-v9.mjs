import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createTimeline} from '../src/timeline.mjs';
import {renderScene} from '../src/scene.mjs';
for (const path of ['cases/CASE_001.json','cases/CASE_SHORT.json']) {
 const c=JSON.parse(fs.readFileSync(path,'utf8'));
 assert.equal(c.ui.video_layout,'social_fill_1080x1920');
 assert.equal(c.show_start_screen,false);
 assert.equal(c.ui.show_status_bar,false);
 const t=createTimeline(c);
 for (const frame of [0,Math.round(t.end*.18),Math.round(t.end*.38),Math.round(t.end*.78),t.end-1]) {
   const html=renderScene(frame,c);
   assert(html.includes('iphone-screen social-fill'));
   assert(!html.includes('class="ios-status-bar'));
   assert(!html.includes('NaN'));
 }
 const g=renderScene(Math.round(t.when('galleryOriginal',.5)),c);
 assert(g.includes('gallery-camera'));
 assert(!g.includes('ios-status-bar'));
 const viewer=renderScene(Math.round(t.when('viewer',.45)),c);
 if(t.present.viewer) assert(viewer.includes('viewer-social-footer'));
 console.log('PASS',path,'duration frames',t.end);
}
