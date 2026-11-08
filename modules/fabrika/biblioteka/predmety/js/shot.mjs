import { chromium } from '/home/claude/ext/awesome-ai-motion/node_modules/playwright/index.mjs';
import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path';
const root='/home/claude/obj';
const srv=http.createServer((q,s)=>{const p=path.join(root,decodeURIComponent(q.url.split('?')[0]));if(!fs.existsSync(p)||fs.statSync(p).isDirectory()){s.writeHead(404);return s.end();}
 const ext=path.extname(p);s.writeHead(200,{'Content-Type':ext=='.js'?'text/javascript':ext=='.html'?'text/html':'application/octet-stream'});fs.createReadStream(p).pipe(s);}).listen(8771);
const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const pg=await b.newPage({viewport:{width:1024,height:1024}});
pg.on('console',m=>{if(m.type()==='error')console.log('ERR',m.text())});
await pg.goto('http://127.0.0.1:8771/index.html');await pg.waitForFunction(()=>window.ready===true,null,{timeout:60000});
const names=await pg.evaluate(()=>window.names);
for(const n of names){const u=await pg.evaluate(x=>window.renderObj(x),n);fs.writeFileSync(`${root}/out/${n}.png`,Buffer.from(u.split(',')[1],'base64'));console.log('ok',n);}
await b.close();srv.close();
