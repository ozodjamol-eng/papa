const {chromium}=require('playwright');const {spawn}=require('child_process');
const [V,mode,fps]=[+process.argv[2],process.argv[3]||'video',+(process.argv[4]||30)];
(async()=>{const b=await chromium.launch();const pg=await b.newPage({viewport:{width:1080,height:1920}});
await pg.goto('file:///home/claude/motion/digest.html');await pg.evaluate(()=>document.fonts.ready);
if(mode==='stills'){for(const t of [2.2,2.5,4.8,7.2,10.25,10.5,19.9]){await pg.evaluate(([t,V])=>render(t,V),[t,V]);await pg.screenshot({path:`out/s${V}_${t}.jpg`,type:'jpeg',quality:80});}await b.close();return;}
const DUR=await pg.evaluate(()=>DUR);const N=Math.round(DUR*fps);
const ff=spawn('ffmpeg',['-y','-loglevel','error','-f','image2pipe','-framerate',String(fps),'-i','-','-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p',`out/v${V}_silent.mp4`],{stdio:['pipe','inherit','inherit']});
for(let i=0;i<N;i++){await pg.evaluate(([t,V])=>render(t,V),[i/fps,V]);const buf=await pg.screenshot({type:'jpeg',quality:93});if(!ff.stdin.write(buf))await new Promise(r=>ff.stdin.once('drain',r));}
ff.stdin.end();await new Promise(r=>ff.on('close',r));await b.close();console.log('done',V,N);})();
