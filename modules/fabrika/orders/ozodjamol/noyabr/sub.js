const {chromium}=require('playwright');
const L=["Ноябрь келди — жимгина, секин,","Шамолда учар сариқ барглар.","Туманда йўлим кўринмас, лекин","Қалбимда ёруғ умид порлар.","Ёмғир ювар тор кўчаларни,","Кузнинг ҳам ўз чиройи бор.","Фонус нури иситар қалбни —","Ҳар бир баргда бир хотира бор."];
(async()=>{const b=await chromium.launch({args:['--allow-file-access-from-files']});const p=await b.newPage({viewport:{width:1080,height:300}});
await p.goto('file:///home/claude/nov/sub.html');
for(let i=0;i<L.length;i++){await p.evaluate(s=>{document.getElementById('t').textContent=s},L[i]);await p.evaluate(()=>document.fonts.ready);
 await p.screenshot({path:`/home/claude/nov/sub/s${i+1}.png`,omitBackground:true});}
await b.close();})();
