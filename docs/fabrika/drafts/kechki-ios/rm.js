const {chromium}=require('playwright');const {spawn}=require('child_process');
const mode=process.argv[2]||'stills',fps=30;
(async()=>{const b=await chromium.launch();const pg=await b.newPage({viewport:{width:1080,height:1920}});
await pg.goto('file:///home/claude/ios/ios_morning.html');await pg.evaluate(()=>document.fonts.ready);
const fr=i=>`file:///home/claude/ios/fm/${String(Math.min(648,i+1)).padStart(4,'0')}.jpg`;
if(mode==='stills'){for(const t of [1.6,4.5,8.8,12.5,16,18.8]){await pg.evaluate(async([t,s])=>{await setBg(s);render(t)},[t,fr(Math.round(t*fps))]);await pg.screenshot({path:`s_${t}.jpg`,type:'jpeg',quality:85});}await b.close();return}
const N=648;
const ff=spawn('ffmpeg',['-y','-loglevel','error','-f','image2pipe','-framerate',String(fps),'-i','-','-ss','15','-t','21.6','-i','/home/claude/music/sunset_house.mp3',
 '-filter_complex','[0:v]format=yuv420p[v];[1:a]afade=t=in:d=0.8,afade=t=out:st=20.4:d=1.2[a]','-map','[v]','-map','[a]',
 '-c:v','libx264','-preset','veryfast','-crf','16','-c:a','aac','-b:a','256k','-t','21.6','morning_main.mp4'],{stdio:['pipe','inherit','inherit']});
for(let i=0;i<N;i++){await pg.evaluate(async([t,s])=>{await setBg(s);render(t)},[i/fps,fr(i)]);const buf=await pg.screenshot({type:'jpeg',quality:94});if(!ff.stdin.write(buf))await new Promise(r=>ff.stdin.once('drain',r));}
ff.stdin.end();await new Promise(r=>ff.on('close',r));await b.close();console.log('done');})();
