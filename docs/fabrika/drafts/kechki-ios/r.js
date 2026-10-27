const {chromium}=require('playwright');const {spawn}=require('child_process');
const mode=process.argv[2]||'stills',fps=30;
(async()=>{const b=await chromium.launch();const pg=await b.newPage({viewport:{width:1080,height:1920}});
await pg.goto('file:///home/claude/ios/ios.html');await pg.evaluate(()=>document.fonts.ready);
const fr=i=>`file:///home/claude/ios/f/${String(Math.min(600,i+1)).padStart(4,'0')}.jpg`;
if(mode==='stills'){for(const t of [1.6,4.0,6,8,10.2,12.6,14.3,15.9,17.5,19.6]){await pg.evaluate(async([t,s])=>{await setBg(s);render(t)},[t,fr(Math.round(t*fps))]);await pg.screenshot({path:`s_${t}.jpg`,type:'jpeg',quality:85});}await b.close();return}
const N=20*fps;
const ff=spawn('ffmpeg',['-y','-loglevel','error','-f','image2pipe','-framerate',String(fps),'-i','-','-ss','0','-t','20','-i','/home/claude/music/smooth_soul.mp3',
 '-filter_complex','[0:v]format=yuv420p[v];[1:a]afade=t=in:d=0.8,afade=t=out:st=17.8:d=2.2[a]','-map','[v]','-map','[a]',
 '-c:v','libx264','-preset','veryfast','-crf','16','-c:a','aac','-b:a','256k','-t','20','KECHKI_DAYJEST_IOS.mp4'],{stdio:['pipe','inherit','inherit']});
for(let i=0;i<N;i++){await pg.evaluate(async([t,s])=>{await setBg(s);render(t)},[i/fps,fr(i)]);const buf=await pg.screenshot({type:'jpeg',quality:94});if(!ff.stdin.write(buf))await new Promise(r=>ff.stdin.once('drain',r));}
ff.stdin.end();await new Promise(r=>ff.on('close',r));await b.close();console.log('done');})();
