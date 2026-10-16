import http from 'node:http';import fs from 'node:fs';import path from 'node:path';import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');const port=Number(process.env.PORT||8088);
const mime={'.html':'text/html; charset=utf-8','.mjs':'text/javascript; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.json':'application/json'};
http.createServer((req,res)=>{
 const uri=new URL(req.url||'/',`http://localhost:${port}`);const name=decodeURIComponent(uri.pathname==='/'?'/preview/index.html':uri.pathname);
 const f=path.resolve(root,name.startsWith('/assets/')?'public'+name:'.'+name);
 if(!f.startsWith(root+path.sep)){res.writeHead(403).end('Forbidden');return;}
 fs.stat(f,(err,st)=>{if(err||!st.isFile()){res.writeHead(404).end('Not found');return;}
 res.writeHead(200,{'Content-Type':mime[path.extname(f)]||'application/octet-stream','Cache-Control':'no-store'});fs.createReadStream(f).pipe(res);
 });
}).listen(port,'127.0.0.1',()=>console.log(`http://127.0.0.1:${port}/preview/index.html`));
