const {chromium}=require('playwright');const {spawn}=require('child_process');
const mode=process.argv[2]||'stills',fps=30;
(async()=>{const b=await chromium.launch();const pg=await b.newPage({viewport:{width:1080,height:1920}});
await pg.goto('file:///home/claude/bg/ov2.html');await pg.evaluate(()=>document.fonts.ready);
if(mode==='stills'){for(const t of [1.6,4.2,6,8,10.2,12.6,14.3,15.9,17.5,19.6]){await pg.evaluate(t=>render(t),t);await pg.screenshot({path:`o_${t}.png`,omitBackground:true});}await b.close();return}
const N=20*fps;
const ff=spawn('ffmpeg',['-y','-loglevel','error','-i','bg20.mp4','-f','image2pipe','-framerate',String(fps),'-i','-','-ss','0','-t','20','-i','/home/claude/music/smooth_soul.mp3',
 '-filter_complex','[0:v][1:v]overlay=0:0:format=auto,format=yuv420p[v];[2:a]afade=t=in:d=0.8,afade=t=out:st=17.8:d=2.2[a]','-map','[v]','-map','[a]',
 '-c:v','libx264','-preset','veryfast','-crf','16','-c:a','aac','-b:a','256k','-t','20','KECHKI_DAYJEST_V3.mp4'],{stdio:['pipe','inherit','inherit']});
for(let i=0;i<N;i++){await pg.evaluate(t=>render(t),i/fps);const buf=await pg.screenshot({type:'png',omitBackground:true});if(!ff.stdin.write(buf))await new Promise(r=>ff.stdin.once('drain',r));}
ff.stdin.end();await new Promise(r=>ff.on('close',r));await b.close();console.log('done');})();
