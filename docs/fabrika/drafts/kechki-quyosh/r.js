const {chromium}=require('playwright');const {spawn}=require('child_process');
const mode=process.argv[2]||'stills',fps=30;
(async()=>{const b=await chromium.launch();const pg=await b.newPage({viewport:{width:1080,height:1920}});
await pg.goto('file:///home/claude/evening/ev.html');await pg.evaluate(()=>document.fonts.ready);
if(mode==='stills'){for(const t of [0.5,2,3.6,5.5,8,10.5,13.5,15.6]){await pg.evaluate(t=>render(t),t);await pg.screenshot({path:`s_${t}.jpg`,type:'jpeg',quality:80});}await b.close();return}
const N=16*fps;const ff=spawn('ffmpeg',['-y','-loglevel','error','-f','image2pipe','-framerate',String(fps),'-i','-','-c:v','libx264','-preset','veryfast','-crf','17','-pix_fmt','yuv420p','silent.mp4'],{stdio:['pipe','inherit','inherit']});
for(let i=0;i<N;i++){await pg.evaluate(t=>render(t),i/fps);const buf=await pg.screenshot({type:'jpeg',quality:94});if(!ff.stdin.write(buf))await new Promise(r=>ff.stdin.once('drain',r));}
ff.stdin.end();await new Promise(r=>ff.on('close',r));await b.close();console.log('done');})();
