const {chromium}=require('playwright');
const FPS=30,END=54.0,N=Math.round(END*FPS),W=+process.argv[2],K=+process.argv[3];
(async()=>{const b=await chromium.launch({args:['--allow-file-access-from-files']});const p=await b.newPage({viewport:{width:1080,height:1920}});
await p.goto('file:///home/claude/v3b/index.html');await p.evaluate(()=>window.ready);
for(let f=W;f<N;f+=K){await p.evaluate(t=>render(t),f/FPS);await p.evaluate(()=>Promise.all([...document.images].map(i=>i.complete?1:new Promise(r=>{i.onload=i.onerror=r}))));
 await p.screenshot({path:`/home/claude/v3b/fr/${String(f).padStart(5,'0')}.jpg`,type:'jpeg',quality:93});}
await b.close();console.log('done',W)})();
