import {createTimeline,ease,clamp} from './timeline.mjs';
const publicPath=p=>'/'+String(p).replace(/^\/+/, '');
const esc=s=>String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
const br=s=>esc(s).replace(/\n/g,'<br/>');
const img=(p,cls='',resolver=publicPath)=>`<img alt="" draggable="false" class="${cls}" src="${esc(resolver(p))}"/>`;
const animate=(f,start,frames=12)=>start===null?0:ease((f-start)/frames);
const icons={
 gallery:'<svg viewBox="0 0 28 28" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="3" y="5" width="22" height="19" rx="4"/><circle cx="10" cy="11" r="2.2"/><path d="M5 21l7-7 4 4 4-5 5 6"/></svg>',
 file:'<svg viewBox="0 0 28 28" fill="none" stroke="currentColor" stroke-width="2.1"><path d="M7 2h10l6 6v17H7z"/><path d="M17 2v7h6"/></svg>',
 location:'<svg viewBox="0 0 28 28" fill="none" stroke="currentColor" stroke-width="2.3"><path d="M14 26C6 16 6 13 6 10a8 8 0 0 1 16 0c0 3-1 6-8 16z"/><circle cx="14" cy="10" r="2.4"/></svg>',
 poll:'<svg viewBox="0 0 28 28" fill="currentColor"><rect x="3" y="14" width="5" height="11" rx="2"/><rect x="11" y="4" width="5" height="21" rx="2"/><rect x="19" y="9" width="5" height="16" rx="2"/></svg>',
 check:'<svg viewBox="0 0 28 28" fill="none" stroke="currentColor" stroke-width="2.6"><rect x="3" y="3" width="22" height="22" rx="5"/><path d="M8 14l4.5 4.5L21 9"/></svg>',
 smile:'<svg viewBox="0 0 28 28" fill="none" stroke="currentColor" stroke-width="2"><circle cx="14" cy="14" r="10.5"/><circle cx="10" cy="12" r="1.2" fill="currentColor" stroke="none"/><circle cx="18" cy="12" r="1.2" fill="currentColor" stroke="none"/><path d="M9.2 16.2c1.6 1.9 3.2 2.6 4.8 2.6 1.7 0 3.2-.7 4.8-2.6"/></svg>',
 send:'<svg viewBox="0 0 28 28" fill="currentColor"><path d="M24.5 13.1 5.7 4.4c-1.6-.7-3 .8-2.3 2.4l3.1 6.4c.2.3.2.7 0 1L3.4 21c-.7 1.5.7 3 2.3 2.3l18.8-8.7a1 1 0 0 0 0-1.5z"/></svg>'
};
const useContinuousClock=c=>c.times?.mode==='continuous';
const uniformTime=c=>c.times?.continuous_time||'15:40';
const msgTime=(c,key,def)=>useContinuousClock(c)?uniformTime(c):(c.times?.messages?.[key]||def);
const phoneTime=(c,key)=>useContinuousClock(c)?uniformTime(c):(c.times?.phone?.[key]||c.ui?.phone_time||'15:36');
const stamp=(t,sent=false)=>`<span class="stamp">${esc(t)}${sent?'<span class="check-pair">✓✓</span>':''}</span>`;
const bubble=(message,{outgoing=false,wide=false,time='15:37',special=''}={})=>`<div class="bubble ${outgoing?'outgoing':'incoming'} ${wide?'wide':''} ${special}"><div class="bubble-copy">${br(message)}</div>${stamp(time,outgoing)}</div>`;
const sentPhoto=(kind,c,resolve)=>`<div class="photo-message" style="--photo-width:${Math.min(490,Math.max(250,Number(c.ui?.photo_max_width)||400))}px;--photo-max-height:${Math.min(630,Math.max(260,Number(c.ui?.photo_max_height)||535))}px">${img(c.photos[kind],'photo-fit',resolve)}<div class="photo-time">${kind==='original'?msgTime(c,'original','15:36'):msgTime(c,'reference','15:37')} ✓✓</div></div>`;
function attachFile(c,resolve){const r=c.result_file||{};return `<div class="file-message"><div class="file-preview">${img(c.photos.result,'fill',resolve)}</div><div class="file-meta"><span class="file-label">${esc(r.name||'result.png')}</span><span class="file-length">${esc(r.size||'1,7 МБ')}</span></div>${stamp(msgTime(c,'result','15:40'))}</div>`;}
const feedback=c=>`<div class="feedback-buttons">${(c.buttons||[]).map(s=>`<div class="feedback-item">${esc(s)}</div>`).join('')}</div>`;
function timelineItems(t,c){
 const a=[];const push=(key,at,fn)=>{if(at!==null)a.push({key,at,fn});};
 push('date',t.when('welcome',.02),()=>'<div class="date-label">Сегодня</div>');
 push('startcmd',t.when('welcome',.06),()=>bubble('/start',{outgoing:true,time:msgTime(c,'start','15:30')}));
 push('hello',t.when('welcome',.31),()=>bubble(c.messages.welcome,{wide:true,time:msgTime(c,'welcome','15:32')}));
 push('originalphoto',t.when('original',.08),r=>sentPhoto('original',c,r));
 push('originalAck',t.when('original',.42),()=>bubble(c.messages.original_received,{wide:true,time:msgTime(c,'original_ack','15:36')}));
 push('referencephoto',t.when('reference',.08),r=>sentPhoto('reference',c,r));
 push('referenceAck',t.when('reference',.40),()=>bubble(c.messages.reference_received,{wide:true,time:msgTime(c,'reference_ack','15:37')}));
 push('progress',t.when('processing',.10),(r,frame)=>{
  const cut=t.when('processing',.54);
  const fade=clamp((frame-cut)/9);
  const text=fade<.48?c.messages.processing_first:c.messages.processing_second;
  const opacity=fade<.48?1-ease(fade/.48):ease((fade-.48)/.52);
  return `<div class="processing-box" style="opacity:${Math.max(.12,opacity)}">${bubble(text,{wide:true,time:msgTime(c,'processing','15:37'),special:'processing-bubble'})}</div>`;
 });
 push('resultfile',t.when('result',.08),r=>attachFile(c,r));
 push('ready',t.when('result',.30),()=>bubble(c.messages.ready,{wide:true,time:msgTime(c,'ready','15:40')}));
 push('buttons',t.when('result',.53),()=>feedback(c));
 return a;
}
function chatMessages(frame,c,resolve,t){
 const items=timelineItems(t,c).filter(row=>frame>=row.at);
 return `<div class="chat-viewport"><div class="chat-stream">${items.map(m=>{
 const progress=animate(frame,m.at,12);
 return `<div class="chat-row" data-message="${m.key}" style="grid-template-rows:${Math.max(.00001,progress)}fr;opacity:${Math.min(1,.15+progress)}"><div class="chat-row-clip"><div class="chat-row-content ${['startcmd','originalphoto','referencephoto'].includes(m.key)?'to-right':m.key==='date'?'to-center':''}">${m.fn(resolve,frame)}</div></div></div>`;
 }).join('')}</div></div>`;
}
function ripple(x,y,frame,at,fill='#007aff'){
 if(at===null||frame<at||frame>at+14)return '';
 let k=(frame-at)/14,rad=20+35*k;
 return `<div class="touch-ripple" style="left:${x-rad}px;top:${y-rad}px;width:${rad*2}px;height:${rad*2}px;opacity:${(1-k)*.55};border-color:${fill}"></div>`;
}
// A single, screen-level iOS status bar. Every source screenshot has its original
// statusbar graphics removed in the preprocessed *-clean assets; no time stickers.
const signalIcon=`<svg class="status-signal" viewBox="0 0 32 22" aria-hidden="true"><rect x="1" y="14" width="6" height="8" rx="1.5"/><rect x="9" y="10" width="6" height="12" rx="1.5"/><rect x="17" y="6" width="6" height="16" rx="1.5"/><rect x="25" y="2" width="6" height="20" rx="1.5"/></svg>`;
const wifiIcon=`<svg class="status-wifi" viewBox="0 0 32 26" aria-hidden="true"><path d="M1 8Q16 -5 31 8M6 14Q16 5 26 14M11 20Q16 15 21 20" stroke="currentColor" fill="none" stroke-width="3.4" stroke-linecap="round"/><circle cx="16" cy="24" r="2.2"/></svg>`;
const planeIcon=`<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M21.4 2.1 2.7 10.3c-1.1.5-1 2.1.2 2.4l6.3 2.1 2.4 6.3c.4 1.1 1.9 1.2 2.5.2l8.1-18.7c.4-1-.1-1.5-.8-.5ZM11 13.6l7.9-7.3-6.3 10.3-1.1-3z"/></svg>`;
function currentTime(frame,c,t){
 if(useContinuousClock(c)) return uniformTime(c);
 const phase=t.currentStage(frame)?.name||'welcome';
 if(phase==='welcome'){
   const helloAt=t.when('welcome',.30);
   return frame >= helloAt ? msgTime(c,'welcome','15:32') : msgTime(c,'start','15:30');
 }
 // Before the photo is selected, the time may have advanced while the user navigates.
 return phoneTime(c,phase);
}
function systemStatusBar(frame,c,t){
 const phase=t.currentStage(frame)?.name||'welcome';
 const viewerProgress=phase==='viewer'?(frame-t.stages.viewer.start)/t.stages.viewer.length:0;
 const viewerDark=phase==='viewer'&&viewerProgress>.105&&viewerProgress<.905;
 const dark=viewerDark||phase==='profile';
 const time=currentTime(frame,c,t);
 const battery=Math.max(1,Math.min(100,Math.round(c.ui?.battery_percent??92)));
 const network=esc(c.ui?.network||'LTE');
 return `<div class="ios-status-bar ${dark?'dark':'light'}" aria-label="Время iPhone ${esc(time)}">
   <span class="ios-clock">${esc(time)}</span>
   <span class="ios-return-pill">${planeIcon}<span>TELEGRAM</span></span>
   <span class="ios-signal">${signalIcon}</span>
   <span class="ios-network">${network}</span>
   <span class="ios-battery"><span>${battery}</span></span>
 </div>`;
}
const arrowBack=`<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 5 9 16l11 11"/></svg>`;
const paperclip=`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.95" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 1 1-2.82-2.83l8.49-8.48"/></svg>`;
const microphone=`<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="2.25" stroke-linecap="round"><rect x="11" y="3" width="10" height="17" rx="5"/><path d="M6.7 15.5a9.3 9.3 0 0 0 18.6 0M16 25v5m-5 0h10"/></svg>`;
const stickers=`<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><circle cx="16" cy="16" r="11"/><path d="M16 5v11l7.7 7.7"/></svg>`;

const viewerChevron=`<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="2.7" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 10 16l10 10"/></svg>`;
const viewerDots=`<svg viewBox="0 0 32 32" fill="currentColor"><circle cx="8" cy="16" r="2.2"/><circle cx="16" cy="16" r="2.2"/><circle cx="24" cy="16" r="2.2"/></svg>`;
const viewerShare=`<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 20V7"/><path d="M11.5 11.5 16 7l4.5 4.5"/><path d="M9 16.5v7h14v-7"/><rect x="8" y="16" width="16" height="9" rx="2.8" opacity="0"/></svg>`;
const viewerEdit=`<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="M8 22.5 22.8 7.7a2.8 2.8 0 0 1 4 4L12 26.5 7 27z"/><path d="m20.2 10.3-4-4"/></svg>`;
const viewerTrash=`<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="M10 10h12"/><path d="M12 10V8.5A1.5 1.5 0 0 1 13.5 7h5A1.5 1.5 0 0 1 20 8.5V10"/><path d="M11.2 12.5 12 24a2 2 0 0 0 2 1.8h4a2 2 0 0 0 2-1.8l.8-11.5"/><path d="M14 15.5v6M18 15.5v6"/></svg>`;
function telegramHeader(c,resolve){
  return `<div class="chat-native-header"><div class="chat-header-left"><span class="nav-chevron">${arrowBack}</span><span class="nav-count">1156</span></div>`+
   `<div class="chat-header-title"><strong>${esc(c.bot?.name||'Vibe Copy')}</strong><small>бот</small></div>`+
   `<div class="chat-header-avatar">${img(c.bot?.avatar||'assets/bot-avatar.png','avatar-photo',resolve)}</div></div>`;
}
function telegramFooter(){
 return `<div class="chat-footer-ui"><div class="footer-menu"><span class="hamburger">☰</span> Меню</div>`+
 `<div class="footer-clip">${paperclip}</div>`+
 `<div class="footer-field"><span>Сообщение</span><span class="sticker-icon">${stickers}</span></div>`+
 `<div class="footer-mic">${microphone}</div></div>`;
}
function chat(frame,c,resolve,t){
 const stage=t.currentStage(frame);
 const stageName=stage?.name||'welcome';
 let html=`<div class="chat-root">${img(c.ui?.wallpaper||'assets/telegram-wallpaper.png','wallpaper',resolve)}${chatMessages(frame,c,resolve,t)}`+
 `<div class="chat-header-glass"></div>`+telegramHeader(c,resolve)+
 `<div class="chat-footer-glass"></div>`+telegramFooter();
 for(const gallery of ['galleryOriginal','galleryReference'])if(t.present[gallery])html+=ripple(218,1198,frame,t.when(gallery,.02));
 if(t.present.profile)html+=ripple(538,111,frame,t.when('profile',.0));
 return html+'</div>';
}
function gallery(frame,c,resolve,t,which,socialFill=false){
 const key=which==='original'?'galleryOriginal':'galleryReference';
 if(!t.present[key])return '';
 const stage=t.stages[key];
 if(frame<stage.start||frame>stage.end)return '';
 const norm=clamp((frame-stage.start)/stage.length);
 const open=ease(norm/.16),close=ease((norm-.84)/.16);
 const travel=(1-open)*860+close*860;
 const selected=norm>=.28;
 const selection=ease((norm-.28)/.055);
 const extras=(c.gallery_extras||[]);
 const paths=[c.photos.original,c.photos.reference,...extras].slice(0,30);
 const target=which==='original'?0:1;
 // Photos always form one natural grid under the translucent caption/tray.
 // A case may specify intentional scrolling; no forced movement when target is already visible.
 const scroll=Math.max(0,Math.min(530,c.ui?.gallery_scroll_pixels??0))*ease((norm-.38)/.28);
 const tiles=paths.map((path,i)=>{
   const isSelected=selected&&i===target;
   const pulse=isSelected?1+.07*Math.sin(Math.PI*clamp((norm-.28)/.08)):1;
   return `<div class="gallery-tile">${img(path,'gallery-photo',resolve)}`+
     `<div class="ios-selection ${isSelected?'active':''}" style="transform:scale(${pulse})">${isSelected?'<span>1</span>':''}</div></div>`;
 }).join('');
 // The selected layout mimics the reference screenshot. Before selection the normal
 // Telegram attachment toolbar is shown instead of a prematurely enabled Send icon.
 const cameraTile=c.ui?.gallery_camera_tile===false?'':`<div class="gallery-tile gallery-camera" aria-label="Камера"><svg class="gallery-camera-icon" viewBox="0 0 32 32" fill="none" stroke="white" stroke-width="2.3"><rect x="4" y="4" width="24" height="24" rx="7"/><circle cx="16" cy="16" r="6"/><circle cx="24" cy="9" r="1.6" fill="white" stroke="none"/></svg></div>`;
 const bottomNav=[['gallery','Галерея'],['file','Файл'],['location','Геопозиция'],['poll','Опрос'],['check','Список']]
   .map(([id,label],i)=>`<div class="gallery-tool ${i===0?'active':''}">${icons[id]}<span>${label}</span></div>`).join('');
 const blur=clamp((c.ui?.gallery_background_blur??6)/12)*12;
 return `<div class="gallery-overlay"><div class="gallery-overlay-dim" style="opacity:${.22*open*(1-close)};backdrop-filter:blur(${blur*open*(1-close)}px);-webkit-backdrop-filter:blur(${blur*open*(1-close)}px)"></div>`+
 `<div class="gallery-sheet" style="transform:translateY(${travel}px)">`+
 `<div class="gallery-grabber"></div>`+
 `<div class="gallery-topbar"><div class="gallery-circle-btn close">×</div>`+
 `<div class="gallery-selection-summary" style="opacity:${selection}"><span class="summary-check">✓</span>1</div>`+
 `<div class="gallery-top-title">Недавние<i></i></div>`+
 `<div class="gallery-circle-btn more">•••</div></div>`+
 `<div class="gallery-photos-window"><div class="gallery-photos-grid" style="transform:translateY(${-scroll}px)">${cameraTile}${tiles}</div></div>`+
 `<div class="gallery-tools-glass" style="opacity:${1-selection};pointer-events:none">${bottomNav}</div>`+
 `<div class="gallery-caption-glass" style="opacity:${selection};pointer-events:none">`+
 `<div class="gallery-caption-placeholder">Добавить подпись...</div>`+
 `<div class="gallery-emoji">${icons.smile}</div><div class="gallery-blue-send">${icons.send}</div></div>`+
 ripple((c.ui?.gallery_camera_tile===false?95:285)+target*191,198,frame,t.when(key,.28)+1)+ripple(516,771,frame,t.when(key,.79))+
 `</div></div>`;
}
function imageViewer(frame,c,resolve,t,socialFill=false){
 if(!t.present.viewer)return '';
 const stage=t.stages.viewer;if(frame<stage.start||frame>stage.end)return '';
 const progress=clamp((frame-stage.start)/stage.length);
 // A true shared-element transition: the photo expands from the file thumbnail,
 // the chat remains visible underneath until the black viewer backdrop fades in,
 // and the sequence ends by returning the thumbnail into the conversation.
 const opening=ease(progress/.16),closing=ease((progress-.84)/.16);
 const expanded=opening*(1-closing);
 // Thumbnail coordinates (in the 591x1280 design space) match the result.png
 // document at the end of the result scene. Do not start at a blank black screen.
 const from={x:20,y:socialFill?430:530,w:101,h:90};
 const to={x:0,y:socialFill?125:252,w:591,h:socialFill?778:776};
 const mix=(a,b,u)=>a+(b-a)*u;
 const x=mix(from.x,to.x,expanded),y=mix(from.y,to.y,expanded);
 const w=mix(from.w,to.w,expanded),h=mix(from.h,to.h,expanded);
 const backdrop=ease(progress/.2)*(1-ease((progress-.83)/.17));
 const chrome=ease((progress-.12)/.1)*(1-ease((progress-.77)/.13));
 return `<div class="viewer-layer"><div class="viewer-black" style="opacity:${backdrop}"></div>`+
 `<div class="viewer-image" style="left:${x}px;top:${y}px;width:${w}px;height:${h}px;border-radius:${Math.round(8*(1-expanded))}px">`+
 img(c.photos.result,'contain',resolve)+`</div>`+
 `<div class="viewer-chrome-transparent" style="opacity:${chrome}">`+
 img('assets/viewer-chrome-transparent.png','screen-fit',resolve)+`</div>`+
 (socialFill?`<div class="viewer-social-header" style="opacity:${chrome}"><span class="viewer-reference-btn viewer-social-back">${img('assets/viewer-ios-back.png','viewer-native-button',resolve)}</span><span class="viewer-social-title"><strong>${esc(c.bot?.name||'Vibe Copy')}</strong><small>сегодня в ${msgTime(c,'result','15:40')}</small></span><span class="viewer-reference-btn viewer-social-more">${img('assets/viewer-ios-more.png','viewer-native-button',resolve)}</span></div><div class="viewer-social-footer" style="opacity:${chrome}"><span class="viewer-reference-btn viewer-footer-btn">${img('assets/viewer-ios-share.png','viewer-native-button',resolve)}</span><span class="viewer-reference-btn viewer-footer-btn">${img('assets/viewer-ios-edit.png','viewer-native-button',resolve)}</span><span class="viewer-reference-btn viewer-footer-btn">${img('assets/viewer-ios-trash.png','viewer-native-button',resolve)}</span></div>`:'')+
 ripple(50,112,frame,t.when('viewer',.86))+
 `</div>`;
}
function profile(frame,c,resolve,t,socialFill=false){
 if(!t.present.profile)return '';
 const s=t.stages.profile;if(frame<s.start)return '';
 const p=clamp((frame-s.start)/s.length),enter=ease(p/.14),zoom=1+((c.cta?.zoom||1.035)-1)*ease((p-.32)/.34);
 const name= c.bot?.name||'Vibe Copy', username=c.bot?.username||'@vibecopy_bot';
 const namePatch=name==='Vibe Copy'?'':`<div class="profile-name-patch">${esc(name)}</div>`;
 const userPatch=username==='@vibecopy_bot'?'':`<div class="profile-username-patch">${esc(username)}</div>`;
 const descr=c.bot?.description||'';
 const descPatch=descr==='Перенесу понравившуюся тебе обработку с любого фото на твоё фото'?'':`<div class="profile-description-patch">${br(descr)}</div>`;
 return `<div class="profile-layer" style="transform:translateX(${(1-enter)*591}px)">`+
 `<div class="profile-inner" style="transform:translateY(${socialFill?-205:0}px) scale(${zoom})">${img('assets/profile-screen-clean.jpg','screen-fit',resolve)}${namePatch}${userPatch}${descPatch}</div>`+
 (socialFill?`<div class="profile-social-back">‹</div>`:``)+`</div>`;
}
function startScreen(frame,c,resolve,t){
 if(!t.present.start)return '';
 const s=t.stages.start;if(frame>s.end)return '';
 const exit=ease((frame-(s.end-s.length*.14))/(s.length*.14));
 return `<div class="start-layer" style="opacity:${1-exit};transform:translateX(${-30*exit}px)">`+
 `${img('assets/start-screen-clean.jpg','screen-fit',resolve)}${ripple(294,1182,frame,t.when('start',.70))}</div>`;
}
export function renderScene(frame,c,resolveAsset,options={}){
 const resolve=resolveAsset||publicPath;
 const t=createTimeline(c);
 const socialFill=options.socialFill??(c.ui?.video_layout==='social_fill_1080x1920');
 const chatVisible=!t.present.start||frame>=t.stages.start.end-t.stages.start.length*.14;
 const statusVisible=!socialFill&&c.ui?.show_status_bar!==false;
 return `<div class="iphone-screen ${socialFill?'social-fill':''}">${chatVisible?chat(frame,c,resolve,t):''}`+
 startScreen(frame,c,resolve,t)+gallery(frame,c,resolve,t,'original',socialFill)+gallery(frame,c,resolve,t,'reference',socialFill)+
 imageViewer(frame,c,resolve,t,socialFill)+profile(frame,c,resolve,t,socialFill)+
 (statusVisible?systemStatusBar(frame,c,t):'')+'</div>';
}
