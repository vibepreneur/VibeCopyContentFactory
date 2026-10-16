export const BASE_FPS=30;
// Every stage has its own local normalized timeline. Optional stages are removed
// entirely rather than rendered as blank seconds.
const BLOCKS=[
 ['start',1.8,'show_start_screen'],
 ['welcome',2.9],
 ['galleryOriginal',3.0,'show_gallery'],
 ['original',2.5],
 ['galleryReference',3.0,'show_gallery'],
 ['reference',3.0],
 ['processing',4.8],
 ['result',3.6],
 ['viewer',3.4,'show_fullscreen_result'],
 ['profile',3.5,'show_bot_profile']
];
export function createTimeline(cfg){
 const active=BLOCKS.filter(([name,sec,flag])=>!flag||cfg[flag]!==false).map(([name,sec,flag])=>[name,name==='profile'?1.7+Math.max(0,Math.min(20,cfg.cta?.pause_seconds??1.8)):sec,flag]);
 const sum=active.reduce((s,[,sec])=>s+sec,0);
 const scale=(cfg.duration||31.5)/sum;
 let cursor=0;
 const stages={};
 for(const [name,seconds] of active){
   let len=seconds*scale*BASE_FPS;
   stages[name]={start:cursor,end:cursor+len,length:len};cursor+=len;
 }
 const absent={start:false,welcome:false,galleryOriginal:false,original:false,galleryReference:false,reference:false,processing:false,result:false,viewer:false,profile:false};
 const present=Object.fromEntries(Object.keys(absent).map(k=>[k,!!stages[k]]));
 const when=(name,portion=0)=>stages[name]?(stages[name].start+stages[name].length*portion):null;
 const currentStage=(frame)=>{
   for (const [name, st] of Object.entries(stages)) {
     if (frame >= st.start && frame <= st.end) return {name, ...st};
   }
   const keys=Object.keys(stages);
   if (!keys.length) return null;
   const last=keys[keys.length-1];
   return {name:last,...stages[last]};
 };
 return {stages,present,when,currentStage,end:Math.ceil(cursor),fps:BASE_FPS};
}
export function ease(x){const t=Math.max(0,Math.min(1,x));return t*t*(3-2*t);}
export function clamp(x){return Math.max(0,Math.min(1,x));}
