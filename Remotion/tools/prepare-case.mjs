import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const input=process.argv[2] || 'cases/CASE_001.json';
const file=path.resolve(root,input);
if(!file.startsWith(root+path.sep))throw Error('Case config must be inside project');
const cfg=JSON.parse(fs.readFileSync(file,'utf8'));
for(const k of ['original','reference','result']){
 const value=cfg.photos?.[k]; if(typeof value!=='string'||!value)throw Error('Missing photos.'+k);
 const dest=path.resolve(root,'public',value);
 if(!dest.startsWith(path.resolve(root,'public')+path.sep)||!fs.existsSync(dest))throw Error(`Missing asset for ${k}: ${value}`);
}
if(!Number.isFinite(cfg.duration)||cfg.duration<8||cfg.duration>180)throw Error('duration must be 8–180 seconds');
if(cfg.fps!==30)throw Error('Current template requires fps=30');
for(const [label,p] of Object.entries({avatar:cfg.bot?.avatar,wallpaper:cfg.ui?.wallpaper})) {
 if(p&&!fs.existsSync(path.resolve(root,'public',p)))throw Error(`Missing ${label} file: ${p}`);
}
fs.writeFileSync(path.join(root,'src','case.generated.mjs'),`// Generated from ${input} – edit JSON instead.\nexport const videoConfig=${JSON.stringify(cfg,null,2)};\n`);
console.log(`Case ${cfg.case_id||'untitled'} loaded; duration ${cfg.duration}s; source ${input}`);
