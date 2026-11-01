// «3 бота» — OZOD JAMOL. Детерминированный таймлайн: render(t) рисует кадр t (сек).
const cl=(x,a=0,b=1)=>Math.min(b,Math.max(a,x));
const lin=(t,a,b)=>cl((t-a)/(b-a));
const eio=x=>x<.5?4*x*x*x:1-Math.pow(-2*x+2,3)/2;
const eo=x=>1-Math.pow(1-x,3);
const spr=(t,k=7,w=12)=>t<=0?0:1-Math.exp(-k*t)*Math.cos(w*t);
const $=id=>document.getElementById(id);
function el(tag,cls,parent,html,style){const e=document.createElement(tag);if(cls)e.className=cls;if(html!=null)e.innerHTML=html;if(style)Object.assign(e.style,style);if(parent)parent.appendChild(e);return e}
function kf(keys,t){ // keys: [[t,{..}],..] плавно (ease-in-out) между ключами
  if(t<=keys[0][0])return {...keys[0][1]};
  for(let i=0;i<keys.length-1;i++){const[a,A]=keys[i],[b,B]=keys[i+1];if(t<=b){const p=eio(lin(t,a,b));const o={};for(const k in A)o[k]=A[k]+((B[k]??A[k])-A[k])*p;return o}}
  return {...keys[keys.length-1][1]};
}
const fade=(t,a,b,fi=.35,fo=.3)=>Math.min(lin(t,a,a+fi),1-lin(t,b-fo,b));
const A='a/';
const PW=528, PH=1118; // экран телефона

// ---------- фоны ----------
const BG=[['bgWhite',5.3],['bgCream',8.8],['bgNavy',20.9],['bgDz',31.6],['bgS6',41.3],['bgBlack',47.45]];
// боке ночного города
const bokeh=[];(function(){let s=7;const r=()=>(s=(s*9301+49297)%233280)/233280;
 for(let i=0;i<34;i++){const d=el('div','bk',$('Lbk'));const sz=20+r()*120;const c=['255,190,110','120,170,255','255,120,90','200,220,255'][i%4];
  Object.assign(d.style,{width:sz+'px',height:sz+'px',left:(r()*1180-50)+'px',top:(r()*1900)+'px',background:`radial-gradient(circle,rgba(${c},.55) 0%,rgba(${c},.0) 70%)`,filter:`blur(${2+r()*6}px)`});
  bokeh.push({d,z:.3+r()*1.2,x0:parseFloat(d.style.left),y0:parseFloat(d.style.top)})}})();

// ---------- телефон ----------
function makePhone(parent,id){const p=el('div','phone',parent);p.id=id;const s=el('div','scr',p);el('div','island',p);el('div','glare',p);return s}
const scr=makePhone($('Lmid'),'ph');

function statusBar(app,dark){el('div','status',app,`<span>02:14</span><span>▂▄▆ 🔋</span>`,{color:dark?'#fff':'#111'})}
function makeApp(id,o){
  const a=el('div','app',scr);a.id=id;if(o.bg)a.style.background=o.bg;
  statusBar(a);
  el('div','hdr',a,`<span class="back">‹</span><div class="av" style="background-image:url(${o.av});${o.avs||''}"></div><div><b>${o.name}</b><small>бот</small></div>`);
  const chat=el('div','chat',a);const kb=el('div','kb',a);
  (o.kb||[]).forEach(b=>{const d=el('div',b.w?'w':'',kb,b.t);if(b.w)d.classList.add('w');if(b.st)Object.assign(d.style,b.st)});
  const msgs=o.msgs.map(m=>{const w=el('div','msg '+m.s,chat);const bub=el('div','bub'+(m.img?' ph':''),w);
    if(m.typing)bub.innerHTML='<span class="typing"><i></i><i></i><i></i></span>';
    else bub.innerHTML=(m.img?`<img src="${m.img}" style="height:${m.ih||260}px;object-fit:cover">`:'')+`<div class="tx">${m.h}</div>`+(m.btn?`<div class="ibtns" style="${m.cols?'grid-template-columns:repeat('+m.cols+',1fr)':''}">${m.btn.map(x=>`<div>${x}</div>`).join('')}</div>`:'')+`<span class="tm">02:14${m.s=='out'?' ✓✓':''}</span>`;
    return {...m,w,bub}});
  return {a,chat,kb,msgs,o,kbt:o.kbt??-1,taps:o.taps||[]};
}
// экран блокировки
const lock=el('div','app',scr);lock.id='lock';statusBar(lock,true);
el('div','date',lock,'Якшанба, 1 ноябрь');el('div','clock',lock,'02:14');
const n1=el('div','ntf',lock,`<div class="ic">${planeSvg(34,'#fff')}</div><div><b>Мижоз</b><span>Ассалому алайкум, нархи қанча? 🙏</span></div><small>ҳозир</small>`,{top:'360px'});
const n2=el('div','ntf',lock,`<div class="ic">${planeSvg(34,'#fff')}</div><div><b>Мижоз</b><span>Ҳозир олсам бўладими?</span></div><small>ҳозир</small>`,{top:'360px'});
const flash=el('div','',scr,'',{position:'absolute',inset:0,background:'#fff',opacity:0,zIndex:50});
function planeSvg(s,c){return `<svg width="${s}" height="${s}" viewBox="0 0 24 24"><path fill="${c}" d="M21.4 3.6 2.9 10.8c-1 .4-1 1.8.1 2.1l4.6 1.4 1.8 5.6c.2.7 1.1.9 1.6.4l2.6-2.5 4.6 3.4c.6.4 1.4.1 1.6-.6l3.2-15.3c.2-1-.8-1.8-1.7-1.5zM9.8 14.6l-.4 3.6-1.2-3.9 9.6-7-8 7.3z"/></svg>`}

const GEN=makeApp('gen',{av:'',avs:'background:linear-gradient(150deg,#ff5a6e,#c2102a);',name:'Сизнинг дўконингиз',bg:'#eef1f5',
 msgs:[{t:-1,s:'out',h:'Ассалому алайкум, нархи қанча? 🙏'},{t:-1,s:'out',h:'Ҳозир олсам бўладими?'},
  {t:5.75,end:6.35,s:'in',typing:1},
  {t:6.35,s:'in',h:'Ваалайкум ассалом! 👋<br>Нархлар, каталог ва буюртма — <b>пастдаги тугмаларда</b> 👇'}],
 kbt:6.85,kb:[{t:'🛍 Каталог'},{t:'💰 Нархлар'},{t:'📝 Буюртма'},{t:'📞 Алоқа'}]});
$('gen').querySelector('.av').innerHTML='<div style="width:100%;height:100%;display:grid;place-items:center;font-size:38px">🤖</div>';

const CAR=['n13','n11','n12','n16','n19','n09','n01','n23','k31','n13'];
const CART=['Куб стеллаж — оқ','Стеллаж «Тетрис»','Стеллаж «Тетрис» — тилла','«Арка» стеллажлари','Катта стеллаж-девор','Журнал столи «Поғона»','Ярим айлана стул','Икки қаватли каравот','Куб стеллаж','Куб стеллаж — оқ'];
const SH=makeApp('sh',{av:A+'sh_logo.png',avs:'background-color:#FBF8F1;background-size:80%;background-repeat:no-repeat',name:'Shodiyona Mebel Markazi',bg:'#F2ECE1',
 msgs:[{t:8.7,s:'in',img:A+'sh_welcome.jpg',ih:220,h:'Ассалому алайкум! 👋<br><b>Мебель — бевосита ишлаб чиқарувчидан</b>'},
  {t:10.1,s:'in',h:'🛋 Каталог — бўлимни танланг 👇',btn:['🗄 Стеллажлар (13)','🪑 Стуллар (5)','🪵 Столлар (2)','🏠 Меҳмонхона (8)']},
  {t:10.75,s:'in',img:A+'b_n13.jpg',ih:300,h:'<b id="cart">Куб стеллаж — оқ</b>',btn:['◀️','<span id="carn">1/13</span>','▶️'],cols:3,car:1},
  {t:12.25,s:'out',img:A+'b_u10.jpg',ih:230,h:'Шунақаси керак, нархи қанча? 👆'},
  {t:14.15,s:'in',h:'✅ Худди шундайини <b>арзонроқ</b> ясаб берамиз — воситачисиз 🤝'},
  {t:15.85,s:'in',h:'📏 Ўлчовчи уйингизга <b>бепул</b> боради. Қайси кун қулай? 👇',btn:['Душанба, 2.11','Сешанба, 3.11','Чоршанба, 4.11','Пайшанба, 5.11']},
  {t:17.15,s:'in',h:'🕐 Қайси вақт қулай? 👇',btn:['10:00','12:00','14:00','16:00'],cols:4},
  {t:18.6,s:'in',h:'✅ Ўлчовга ёзилдингиз:<br><b>Сешанба, 14:00</b>'}],
 kbt:9.05,kb:[{t:'🛋 Каталог'},{t:'📐 Буюртма бериш'},{t:'💰 Арзонроқ топамиз'},{t:'🪄 Хонангизда кўринг'},{t:'📏 Бепул ўлчов'},{t:'📦 Буюртмам қаерда?'},{t:'🛍 Онлайн каталог — барча моделлар',w:1}],
 taps:[{t:9.85,kb:0},{t:10.45,m:1,b:0},{t:16.9,m:5,b:1},{t:18.3,m:6,b:2}]});

const GW=makeApp('gw',{av:A+'gw_logo.png',name:'GOLD WATER Андижон',bg:'#E6F0FB',
 msgs:[{t:20.8,s:'in',h:'Ассалому алайкум! 💧<br><b>GOLD WATER</b> — тоза сув аппаратлари. Бўлимни танланг 👇'},
  {t:23.15,s:'in',img:A+'gw_v1.jpg',ih:300,h:'<b>10 босқичли тозалаш</b> ✅<br>Тоза сув — соғлом ҳаёт!'},
  {t:25.3,s:'in',h:'💰 <b>Нарх ва тўлов</b><br>✅ Нақд ёки ҳалол насия'},
  {t:26.5,s:'in',h:'🎁 <b>Ноябрь акцияси!</b><br>Шартлари — менежердан 👇'},
  {t:27.75,s:'out',h:'📱 +998 90 ••• •• ••'},
  {t:28.15,s:'in',h:'✅ Раҳмат! Менежеримиз тез орада қўнғироқ қилади.'}],
 kbt:21.15,kb:[{t:'💧 Аппарат ҳақида'},{t:'💰 Нархлар'},{t:'🎁 Акция'},{t:'📍 Манзиллар'},{t:'📝 Ариза қолдириш'},{t:'📞 Менежер'}].map(b=>({...b,st:{color:'#01439A'}})),
 taps:[{t:22.85,kb:0},{t:25.0,kb:1},{t:26.2,kb:2},{t:27.45,kb:4}]});

const DZ=makeApp('dz',{av:A+'oj_avatar.png',name:'OZOD JAMOL Дизайн',bg:'#F1EDE7',
 msgs:[{t:31.5,s:'in',h:'Ассалому алайкум! 🏠<br>Уй, квартира ва офис учун <b>дизайн ва ишончли усталар</b>. Хизматни танланг 👇'},
  {t:33.2,s:'in',h:'🏠 <b>3D дизайн</b><br>Бўш қутидан — тайёр уйгача 👇'},
  {t:36.0,s:'in',h:'👷 <b>Текширилган усталар</b> — шу ботда 👇'},
  {t:39.3,s:'in',h:'✅ <b>Ҳаммаси — битта ботда</b>'}],
 kbt:31.85,kb:[{t:'🏠 3D дизайн — $3/м²',w:1},{t:'🔨 Таъмир (уй, квартира)',w:1},{t:'🏡 Фасад эскизи'},{t:'⚡ Электрик'},{t:'🚿 Сантехник'},{t:'🪑 Мебель буюртма'}].map(b=>({...b,st:b.w?{background:'#fff',color:'#222'}:{}})),
 taps:[{t:32.95,kb:0}]});
const APPS=[GEN,SH,GW,DZ];
// смена приложений: [время, откуда, куда]
const SW=[[8.75,GEN,SH],[20.85,SH,GW],[31.55,GW,DZ]];
const touch=el('div','',scr,'',{position:'absolute',width:'70px',height:'70px',borderRadius:'50%',background:'rgba(120,120,130,.35)',border:'3px solid rgba(255,255,255,.8)',zIndex:60,opacity:0});

// ---------- плавающие предметы ----------
const F={}; // name -> {e, layer factor}
function fl(name,layer,html,st,cls){F[name]=el('div',cls||'',$(layer),html,{position:'absolute',...st});return F[name]}
// S2
fl('b247','Lback','24/7',{left:'0',right:'0',top:'70px',textAlign:'center',font:'900 330px/1 Montserrat',letterSpacing:'-10px',color:'#141416',opacity:0});
// S3
fl('cN12','Lback',`<img src="${A}c_n12.webp" style="height:640px">`,{left:'-60px',top:'560px',filter:'blur(3px) drop-shadow(0 40px 30px rgba(60,40,20,.25))'});
fl('cN01','Lfront',`<img src="${A}c_n01.webp" style="height:430px">`,{left:'770px',top:'1030px'},'cut');
fl('cN09','Lfront',`<img src="${A}c_n09.webp" style="width:360px">`,{left:'-40px',top:'1240px'},'cut');
fl('k42','Lfront',`<div style="font:900 150px/0.9 Montserrat;color:#1F3A28;letter-spacing:-4px"><span id="n42">0</span></div><div style="font:800 26px Montserrat;letter-spacing:.3em;color:#B8814A;margin-top:8px">МОДЕЛЬ</div>`,{left:'40px',top:'250px',padding:'28px 34px',borderRadius:'34px',background:'rgba(255,255,255,.94)',boxShadow:'0 40px 80px -30px rgba(60,40,20,.5)'});
fl('tagA','Lfront',`<div style="font:900 50px/1 Montserrat;color:#fff;letter-spacing:1px">АРЗОНРОҚ</div><div style="font:800 22px Montserrat;color:#FBF8F1;letter-spacing:.2em;margin-top:10px;opacity:.9">ВОСИТАЧИСИЗ</div>`,{left:'640px',top:'640px',padding:'26px 34px',borderRadius:'26px',background:'#B8814A',boxShadow:'0 40px 70px -25px rgba(116,66,30,.7)'});
fl('tagM','Lfront',`<div style="font:900 44px/1.05 Montserrat;color:#1F3A28">📏 БЕПУЛ<br>ЎЛЧОВ</div><div style="font:800 21px Montserrat;color:#B8814A;letter-spacing:.2em;margin-top:10px">КУН ВА СОАТНИ ТАНЛАНГ</div>`,{left:'24px',top:'900px',padding:'26px 32px',borderRadius:'28px',background:'#fff',boxShadow:'0 40px 80px -30px rgba(60,40,20,.5)'});
// S4
fl('mach','Lback',`<img src="${A}gw_machine.png" style="height:1020px">`,{left:'-150px',top:'420px',filter:'drop-shadow(0 50px 50px rgba(0,0,0,.55))'});
fl('t10','Lfront',`<div style="font:900 64px/0.95 Montserrat;color:#FAE289">10</div><div style="font:900 30px/1.1 Montserrat;color:#fff;margin-top:6px">БОСҚИЧЛИ<br>ТОЗАЛАШ</div>`,{left:'36px',top:'260px',padding:'26px 32px',borderRadius:'28px',background:'linear-gradient(150deg,rgba(255,255,255,.18),rgba(255,255,255,.06))',border:'2px solid rgba(250,226,137,.6)',backdropFilter:'blur(8px)'});
fl('gift','Lfront',`<img src="${A}gw_gift.png" style="width:250px;display:block;margin:0 auto"><div style="font:900 46px Montserrat;color:#001A43;text-align:center;letter-spacing:.06em;margin-top:6px">АКЦИЯ</div>`,{left:'760px',top:'860px',padding:'22px 26px 20px',borderRadius:'30px',background:'linear-gradient(160deg,#FAE289,#C89334)',boxShadow:'0 40px 80px -25px rgba(0,0,0,.6)'});
const owner=makePhone($('Lmid'),'owner');$('owner').style.opacity=0;
el('div','app',owner,'',{background:'linear-gradient(170deg,#1b2440,#05070d)'});
el('div','',owner,'02:15',{position:'absolute',top:'150px',width:'100%',textAlign:'center',color:'#fff',font:'800 150px/1 Montserrat'});
const ownN=el('div','ntf',owner,`<div class="ic" style="background:linear-gradient(160deg,#FAE289,#C89334)">🔥</div><div><b>ЯНГИ МИЖОЗ</b><span>📱 +998 90 ••• •• ••<br>💧 GOLD WATER — аппарат</span></div><small>ҳозир</small>`,{top:'380px',opacity:0});
fl('ownL','Lmid','ЭГАСИ',{left:'0',width:'1080px',textAlign:'center',top:'600px',font:'800 34px Raleway',letterSpacing:'.3em',color:'#FAE289',opacity:0});
fl('lead','Lfront',`<div style="display:flex;gap:14px;align-items:center"><div style="font-size:44px">🔥</div><div><div style="font:900 30px Montserrat;color:#001A43">ЯНГИ МИЖОЗ</div><div style="font:800 21px Montserrat;color:#01439A;margin-top:4px">📱 +998 90 ••• •• ••</div></div></div>`,{left:'0',top:'0',padding:'20px 26px',borderRadius:'24px',background:'#fff',boxShadow:'0 30px 60px -20px rgba(0,0,0,.6)',opacity:0});
// S5
fl('dzp','Lback',`<img id="dzimg" src="${A}dz/0001.jpg" style="width:470px;height:836px;display:block;border-radius:30px">`,{left:'20px',top:'470px',borderRadius:'34px',padding:'8px',background:'#fff',boxShadow:'0 50px 90px -30px rgba(60,40,20,.55)'});
const MAS=[['🚿','САНТЕХНИК'],['⚡','ЭЛЕКТРИК'],['🎨','ПАРДОЗЧИ']];
MAS.forEach((m,i)=>fl('m'+i,'Lfront',`<div style="display:flex;gap:18px;align-items:center"><div style="width:84px;height:84px;border-radius:50%;background:#F1ECE5;display:grid;place-items:center;font-size:46px">${m[0]}</div><div><div style="font:900 32px Montserrat;color:#1d1d1f">${m[1]}</div><div style="font:800 19px Montserrat;color:#2e8b3a;letter-spacing:.12em;margin-top:6px">✅ ТЕКШИРИЛГАН</div></div></div>`,{left:'26px',top:(560+i*200)+'px',padding:'22px 26px',borderRadius:'28px',background:'#fff',boxShadow:'0 40px 80px -30px rgba(60,40,20,.5)'}));
// S6 мини-телефоны
function miniScreen(s,o){const a=el('div','app',s,'',{background:o.bg});statusBar(a);
 el('div','hdr',a,`<span class="back">‹</span><div class="av" style="background-image:url(${o.av});${o.avs||''}"></div><div><b>${o.name}</b><small>бот</small></div>`);
 el('div','',a,`<img src="${o.img}" style="width:100%;height:100%;object-fit:cover;border-radius:22px">`,{position:'absolute',left:'16px',right:'16px',top:'206px',height:'560px'});
 const kb=el('div','kb',a);o.kb.forEach(t=>el('div','',kb,t));
 return el('div','ntf',s,`<div class="ic" style="background:linear-gradient(160deg,#43d36b,#22a447)">✅</div><div><b>Янги ариза</b><span>Мижоз рақамини қолдирди</span></div><small>ҳозир</small>`,{top:'96px',opacity:0,zIndex:20});}
const p1=makePhone($('Lmid'),'p1'),p2=makePhone($('Lmid'),'p2');
const N1=miniScreen(p1,{bg:'#F2ECE1',av:A+'sh_logo.png',avs:'background-color:#FBF8F1;background-size:80%;background-repeat:no-repeat',name:'Shodiyona Mebel',img:A+'b_n13.jpg',kb:['🛋 Каталог','📐 Буюртма бериш','💰 Арзонроқ','📏 Бепул ўлчов']});
const N2=miniScreen(p2,{bg:'#E6F0FB',av:A+'gw_logo.png',name:'GOLD WATER',img:A+'gw_v1.jpg',kb:['💧 Аппарат','💰 Нархлар','🎁 Акция','📝 Ариза']});
const N3=el('div','ntf',scr,`<div class="ic" style="background:linear-gradient(160deg,#43d36b,#22a447)">✅</div><div><b>Янги ариза</b><span>Мижоз рақамини қолдирди</span></div><small>ҳозир</small>`,{top:'96px',opacity:0,zIndex:55});
[p1,p2].forEach(p=>p.parentNode.style.opacity=0);
fl('k6','Lui','',{left:'0',right:'0',top:'250px',textAlign:'center'});
const K6=[['3 БИЗНЕС',41.7,42.5],['3 БОТ',42.5,43.6],['1 НАТИЖА',43.6,44.85]].map(([s,a,b])=>({e:el('div','kin',F.k6,s,{top:'0',fontSize:'130px'}),a,b}));
const K6b=el('div','kin',F.k6,'БИРОНТА МИЖОЗ<br><span style="color:#22a447">ЙЎҚОЛМАЙДИ</span>',{top:'-20px',fontSize:'84px'});
// S7
fl('k7','Lui','',{left:'0',right:'0',top:'0',height:'1920px'});
const K7=[['БИЗНЕСИНГИЗГА',48.0,540],['ҲАМ ШУНДАЙ <span style="color:#FF1024">БОТ</span>',48.75,665],['КЕРАКМИ?',49.4,790]].map(([s,a,y])=>({e:el('div','kin',F.k7,s,{top:y+'px',color:'#fff',fontSize:'86px',whiteSpace:'nowrap'}),a}));
const pill=el('div','',F.k7,`<div style="display:flex;align-items:center;gap:22px">${planeSvg(70,'#fff')}<span>@Ozodjamol</span></div>`,{position:'absolute',left:'50%',top:'1010px',transform:'translateX(-50%)',padding:'30px 54px',borderRadius:'90px',background:'#FF1024',color:'#fff',font:'900 76px Montserrat',whiteSpace:'nowrap',boxShadow:'0 40px 90px -20px rgba(255,16,36,.6)'});
const tgl=el('div','',F.k7,'ТЕЛЕГРАМДА ЁЗИНГ',{position:'absolute',left:'0',right:'0',top:'1215px',textAlign:'center',font:'800 34px Raleway',letterSpacing:'.32em',color:'#fff',paddingLeft:'.32em'});
const ozl=el('div','',F.k7,'OZOD JAMOL',{position:'absolute',left:'0',right:'0',top:'1330px',textAlign:'center',font:'800 46px Raleway',letterSpacing:'.42em',color:'rgba(255,255,255,.9)',paddingLeft:'.42em'});
// подписи
const cap=el('div','cap',$('Lui'),'<b></b><small></small>');
const CAPS=[[0.7,4.9,'ТУНГИ 02:14','МИЖОЗ ЖАВОБ КУТЯПТИ','#fff'],[6.1,8.6,'ҲЕЧ ҚАЧОН УХЛАМАЙДИ','СОТУВЧИНГИЗ — БОТ','#141416'],
 [9.3,20.6,'SHODIYONA MEBEL','МЕБЕЛЬ ДЎКОНИ БОТИ','#1F3A28'],[21.6,28.0,'GOLD WATER','СУВ АППАРАТЛАРИ БОТИ','#fff'],
 [32.2,41.0,'OZOD JAMOL ДИЗАЙН','УЙ ТАЪМИРИ БОТИ','#1d1d1f']];

// ---------- камера ----------
const PK=[[0,{x:0,y:80,s:.9,rx:16,ry:-26,rz:5}],[4.7,{x:0,y:20,s:1,rx:7,ry:-12,rz:2}],[5.4,{x:0,y:0,s:1.03,rx:0,ry:0,rz:0}],
 [8.5,{x:0,y:0,s:1,rx:3,ry:7,rz:0}],[9.3,{x:0,y:0,s:1,rx:4,ry:-8,rz:0}],[12,{x:-10,y:0,s:1,rx:3,ry:7,rz:0}],[15,{x:20,y:0,s:1,rx:2,ry:-7,rz:0}],
 [18,{x:0,y:0,s:1,rx:5,ry:6,rz:0}],[20.6,{x:0,y:0,s:1,rx:2,ry:-5,rz:0}],[21.6,{x:60,y:0,s:1,rx:3,ry:-12,rz:0}],[24.5,{x:80,y:0,s:1,rx:2,ry:-6,rz:0}],
 [27.5,{x:20,y:0,s:1,rx:2,ry:0,rz:0}],[28.6,{x:-180,y:10,s:.9,rx:3,ry:12,rz:0}],[30.8,{x:-170,y:10,s:.9,rx:2,ry:8,rz:0}],
 [31.8,{x:0,y:0,s:1,rx:3,ry:-6,rz:0}],[33.4,{x:215,y:0,s:.93,rx:3,ry:-16,rz:0}],[36,{x:230,y:0,s:.93,rx:2,ry:-11,rz:0}],[38.6,{x:215,y:0,s:.93,rx:2,ry:-7,rz:0}],
 [39.4,{x:0,y:0,s:1,rx:2,ry:0,rz:0}],[41.1,{x:0,y:0,s:1,rx:3,ry:5,rz:0}],[42.1,{x:340,y:150,s:.56,rx:4,ry:-10,rz:0}],[47.3,{x:340,y:150,s:.56,rx:2,ry:-4,rz:0}],[48.3,{x:340,y:1500,s:.56,rx:20,ry:-4,rz:6}]];
const CK=[[0,{p:1.0}],[4.9,{p:1.06}],[5.3,{p:1.0}],[8.7,{p:1.03}],[20.8,{p:1.04}],[21.0,{p:1.0}],[31.5,{p:1.04}],[31.7,{p:1.0}],[41.2,{p:1.03}],[42.4,{p:.98}],[47.4,{p:1.02}],[54,{p:1.05}]];

function phoneTf(e,o){e.style.transform=`translate(${o.x}px,${o.y}px) rotateX(${o.rx}deg) rotateY(${o.ry}deg) rotateZ(${o.rz}deg) scale(${o.s})`}
const sceneT=t=>t;
const ZB=[[6.3,8.5,1.13],[12.25,13.8,1.14],[14.1,15.7,1.16],[18.5,20.6,1.16],[23.1,24.9,1.12],[27.7,28.5,1.08],[39.2,41.2,1.2]];

function renderApp(ap,t){
  // клавиатура
  const kbh=ap.kb.offsetHeight||0;const kp=ap.kbt<0?0:spr(t-ap.kbt,8,10);
  ap.kb.style.transform=`translateY(${(1-cl(kp,0,1.2))*(kbh+20)}px)`;
  ap.chat.style.bottom=(kbh*cl(kp)+10)+'px';
  let acc=0;
  for(let i=ap.msgs.length-1;i>=0;i--){const m=ap.msgs[i];
    let g=m.t<0?1:eo(lin(t,m.t,m.t+.3));if(m.typing)g*=1-eo(lin(t,m.end,m.end+.2));
    const h=m.w.offsetHeight+12;
    if(g<=0){m.w.style.opacity=0;continue}
    m.w.style.bottom=acc+'px';acc+=h*g;
    const sp=m.t<0?1:spr(t-m.t,9,13);
    m.w.style.opacity=cl(sp*1.6);m.w.style.transformOrigin=m.s=='in'?'0% 100%':'100% 100%';
    m.w.style.transform=`scale(${.82+.18*sp})`;
    if(m.typing){m.w.querySelectorAll('i').forEach((d,k)=>d.style.transform=`translateY(${Math.sin(t*14-k*1.1)*5}px)`)}
  }
}
function tapAt(ap,t){ // ripple + касание
  let shown=false;
  ap.taps.forEach(tp=>{const d=t-tp.t;const target=tp.kb!=null?ap.kb.children[tp.kb]:ap.msgs[tp.m].bub.querySelectorAll('.ibtns div')[tp.b];
    if(!target)return;
    target.style.transform=(d>=0&&d<.25)?`scale(${.94+.06*lin(d,0,.25)})`:'';
    if(target.dataset.bg===undefined)target.dataset.bg=target.style.background||'';
    target.style.background=(d>=0&&d<.5)?'#d8dde5':target.dataset.bg;
    if(d>-.25&&d<.45){const r=target.getBoundingClientRect(),s=ap.a.getBoundingClientRect();
      // координаты внутри экрана без учёта 3D: используем offset
      let x=0,y=0,n=target;while(n&&n!==ap.a){x+=n.offsetLeft;y+=n.offsetTop;n=n.offsetParent}
      x+=target.offsetWidth/2;y+=target.offsetHeight/2;
      touch.style.left=(x-35)+'px';touch.style.top=(y-35)+'px';
      touch.style.opacity=d<0?lin(d,-.25,0):1-lin(d,.15,.45);touch.style.transform=`scale(${d<0?1.4-.4*lin(d,-.25,0):1-.15*lin(d,0,.1)})`;shown=true}
  });
  return shown;
}

window.render=function(t){
  // фоны: круговое раскрытие от центра телефона
  BG.forEach(([id,ts],i)=>{const e=$(id);const p=eio(lin(t,ts,ts+.75));e.style.opacity=p>0?1:0;e.style.clipPath=`circle(${p*1500}px at 50% 46%)`});
  $('bgNight').style.opacity=t<6.2?1:0;
  $('caus').style.opacity=fade(t,20.9,31.8,.8,.6)*.9;$('caus').style.backgroundPosition=`${t*18}px ${t*-30}px`;
  // камера-дрейф и параллакс
  const ck=kf(CK,t);const dx=Math.sin(t*.37)*16+Math.sin(t*.91)*5,dy=Math.cos(t*.29)*12;
  const L=[['Lbk',.35],['Lback',.6],['Lmid',1],['Lfront',1.45],['Lui',.15]];
  L.forEach(([id,f])=>{$(id).style.transform=`translate(${dx*f}px,${dy*f}px) scale(${1+(ck.p-1)*f})`});
  // боке только ночью
  bokeh.forEach(b=>{b.d.style.opacity=(1-lin(t,5.2,6.0))*(.6+.4*Math.sin(t*1.3+b.z*7));b.d.style.transform=`translate(${-t*6*b.z}px,${-t*10*b.z}px)`});
  // телефон
  const pk=kf(PK,t);const big=1-lin(t,41.1,42.1);pk.s*=1+.08*big;pk.y-=25*big;
  // наезды на ключевые ответы бота (читаемость + динамика)
  let z=0;ZB.forEach(([a,b,zz])=>{z+=(zz-1)*eio(lin(t,a,a+.55))*(1-eio(lin(t,b-.55,b)))});
  pk.s*=1+z;pk.y-=z*430;pk.rx*=1-z*3;pk.ry*=1-z*3;phoneTf($('ph'),pk);$('ph').style.opacity=1-lin(t,47.8,48.3);
  // экран блокировки / вспышка
  lock.style.opacity=t<5.3?1:0;flash.style.opacity=t>=5.25?Math.max(0,1-lin(t,5.3,5.75))*(t<5.3?lin(t,5.25,5.3):1):0;
  const s1=spr(t-1.0,8,12),s2=spr(t-2.75,8,12);
  n1.style.opacity=cl(s1*1.5);n1.style.transform=`translateY(${(1-s1)*-60 + cl(s2)*150}px) scale(${.9+.1*s1-.04*cl(s2)})`;
  n2.style.opacity=cl(s2*1.5);n2.style.transform=`translateY(${(1-s2)*-60}px) scale(${.9+.1*s2})`;
  // приложения
  APPS.forEach(ap=>{ap.a.style.display='none'});
  let cur=GEN,prev=null,sp=1;
  SW.forEach(([ts,a,b])=>{if(t>=ts){prev=a;cur=b;sp=eio(lin(t,ts,ts+.55))}});
  if(t>=5.3){cur.a.style.display='block';cur.a.style.transform=`translateX(${(1-sp)*PW}px)`;
    if(prev&&sp<1){prev.a.style.display='block';prev.a.style.transform=`translateX(${-sp*PW*.35}px)`;prev.a.style.filter=`brightness(${1-.3*sp})`}
    cur.a.style.filter='';
    renderApp(cur,t);if(prev&&sp<1)renderApp(prev,t);
    if(!tapAt(cur,t))touch.style.opacity=0;}
  else touch.style.opacity=0;
  // карусель Shodiyona
  const cm=SH.msgs[2];const ci=Math.min(CAR.length-1,Math.floor(Math.max(0,t-10.75)/.15));const im=cm.bub.querySelector('img');
  const want=A+'b_'+CAR[ci]+'.jpg';if(!im.src.endsWith(want))im.src=want;
  const ct=document.getElementById('cart');if(ct)ct.textContent=CART[ci];const cn=document.getElementById('carn');if(cn)cn.textContent=(ci%13+1)+'/13';
  // S2 «24/7»
  const b=spr(t-5.55,6,9);F.b247.style.opacity=cl(b)*(1-lin(t,8.5,8.9));F.b247.style.transform=`translateY(${(1-b)*80}px) scale(${.9+.1*b})`;
  // S3
  const s3in=t-8.9;
  F.cN12.style.opacity=fade(t,9.0,20.9,.6,.4)*.7;F.cN12.style.transform=`translate(${-40+ s3in*4}px,${Math.sin(t*.8)*12}px) rotate(${-3+Math.sin(t*.5)*2}deg)`;
  const pc=spr(t-9.3,6,9);F.cN01.style.opacity=cl(pc)*(1-lin(t,20.5,20.9));F.cN01.style.transform=`translate(${(1-pc)*260 - s3in*5}px,${Math.sin(t*1.1)*14}px) rotate(${(1-pc)*14+Math.sin(t*.7)*3}deg)`;
  const pt=spr(t-9.6,6,9);F.cN09.style.opacity=cl(pt)*(1-lin(t,20.5,20.9));F.cN09.style.transform=`translate(${(1-pt)*-260 + s3in*4}px,${Math.cos(t*.9)*12}px) rotate(${-(1-pt)*10}deg)`;
  const k=spr(t-10.6,7,10);F.k42.style.opacity=cl(k)*(1-lin(t,12.2,12.6));F.k42.style.transform=`translateY(${(1-k)*-80}px) scale(${.8+.2*k}) rotate(${-4+4*k}deg)`;
  $('n42').textContent=Math.round(42*eo(lin(t,10.65,12.0)));
  const ta=spr(t-14.2,6,11);F.tagA.style.opacity=cl(ta*1.5)*(1-lin(t,15.8,16.2));F.tagA.style.transform=`translate(${(1-ta)*200}px,${Math.sin(t*1.4)*8}px) rotate(${-8+ (1-ta)*20}deg) scale(${.7+.3*ta})`;
  const tm=spr(t-15.95,6,11);F.tagM.style.opacity=cl(tm*1.5)*(1-lin(t,18.2,18.55));F.tagM.style.transform=`translate(${(1-tm)*-200}px,${Math.sin(t*1.2)*8}px) rotate(${5-(1-tm)*15}deg) scale(${.7+.3*tm})`;
  // S4
  const ma=spr(t-21.5,5,7);F.mach.style.opacity=cl(ma)*(1-lin(t,27.6,28.2));F.mach.style.transform=`translate(${(1-ma)*-300+(t-21)*6}px,${Math.sin(t*.8)*10}px) rotateY(${18}deg) scale(${.85+.15*ma})`;
  const t10=spr(t-23.2,6,10);F.t10.style.opacity=cl(t10*1.5)*(1-lin(t,25.0,25.4));F.t10.style.transform=`translateY(${(1-t10)*-90}px) scale(${.8+.2*t10})`;
  const gf=spr(t-26.45,6,11);F.gift.style.opacity=cl(gf*1.5)*(1-lin(t,27.6,28.0));F.gift.style.transform=`translate(${(1-gf)*220}px,${Math.sin(t*1.6)*10}px) rotate(${6-(1-gf)*25}deg) scale(${.6+.4*gf})`;
  // владелец
  const ow=eio(lin(t,27.9,28.7))*(1-eio(lin(t,30.8,31.5)));const own=$('owner');own.style.opacity=ow>0?1:0;
  phoneTf(own,{x:330+(1-ow)*600,y:120,s:.62,rx:3,ry:-12,rz:0});
  const on=spr(t-29.45,8,12);ownN.style.opacity=cl(on*1.5);ownN.style.transform=`translateY(${(1-on)*-60}px) scale(${.9+.1*on})`;
  F.ownL.style.opacity=ow*lin(t,28.6,28.9);F.ownL.style.transform=`translateX(${330+(1-ow)*600}px)`;
  // лид-карточка летит дугой
  const lp=eio(lin(t,28.45,29.45));const lx=210+lp*600,ly=900-Math.sin(lp*Math.PI)*260+lp*-260;
  F.lead.style.opacity=t>=28.4&&t<29.5?Math.min(lin(t,28.4,28.55),1-lin(t,29.3,29.5)):0;F.lead.style.transform=`translate(${lx}px,${ly}px) rotate(${-8+lp*16}deg) scale(${1-.35*lp})`;
  // S5 дизайн
  const dp=spr(t-33.25,5,8);const dzOut=eio(lin(t,38.7,39.3));
  const dim=eio(lin(t,35.9,36.4));F.dzp.style.opacity=cl(dp*1.4)*(1-lin(t,39.1,39.35))*(1-.6*dim);F.dzp.style.filter=`blur(${dim*4}px)`;
  F.dzp.style.transform=`translate(${(1-dp)*-300 + dzOut*240}px,${dzOut*40}px) rotateY(${22-8*dzOut}deg) scale(${(.85+.15*dp)*(1-.75*dzOut)})`;
  const fi=Math.min(285,1+Math.floor(lin(t,33.3,38.0)*284));$('dzimg').src=A+'dz/'+String(fi).padStart(4,'0')+'.jpg';
  [36.2,37.0,37.75].forEach((ts,i)=>{const s=spr(t-ts,7,11);const e=F['m'+i];e.style.opacity=cl(s*1.5)*(1-lin(t,39.05,39.3));
    e.style.transform=`translate(${(1-s)*-300 + dzOut*520}px,${Math.sin(t*1.3+i)*6 + dzOut*(150-i*190)}px) rotate(${-(1-s)*12}deg) scale(${(.7+.3*s)*(1-.7*dzOut)})`});
  // S6
  const m6=eio(lin(t,41.4,42.3)),o6=1-eio(lin(t,47.6,48.3));
  [[p1,-340,41.55],[p2,0,41.75]].forEach(([p,x,ts])=>{const s=spr(t-ts,6,9);p.parentNode.style.opacity=t>41.3&&t<48.4?1:0;
    phoneTf(p.parentNode,{x:x,y:150+(1-cl(s))*1200+(1-o6)*1400,s:.56,rx:4-2*s,ry:(x<0?8:0)*s,rz:(1-o6)*-6});});
  K6.forEach(k=>{const s=spr(t-k.a,8,11);k.e.style.opacity=t<k.a?0:cl(s*1.5)*(1-lin(t,k.b-.12,k.b));k.e.style.transform=`translateY(${(1-s)*60}px) scale(${.85+.15*s})`});
  const kb6=spr(t-44.9,7,10);K6b.style.opacity=cl(kb6*1.5)*o6;K6b.style.transform=`translateY(${(1-kb6)*50}px)`;
  [[N1,44.9],[N2,45.1],[N3,45.3]].forEach(([n,ts])=>{const s=spr(t-ts,8,12);n.style.opacity=cl(s*1.5)*(t<48?1:0);n.style.transform=`translateY(${(1-s)*-70}px) scale(${.9+.1*s})`});
  // S7
  K7.forEach(k=>{const s=spr(t-k.a,7,10);k.e.style.opacity=cl(s*1.6);k.e.style.transform=`translateY(${(1-s)*70}px) scale(${.9+.1*s})`;k.e.style.filter=`blur(${(1-cl(s))*8}px)`});
  const ps=spr(t-50.2,6,10);const br=t>51?Math.sin((t-51)*3.2)*.025:0;pill.style.opacity=cl(ps*1.5);pill.style.transform=`translateX(-50%) scale(${(.6+.4*ps)*(1+br)}) rotate(${(1-ps)*-6}deg)`;
  pill.style.boxShadow=`0 40px ${90+br*1600}px -20px rgba(255,16,36,${.6+br*8})`;F.k7.style.transform=`scale(${1+.035*eio(lin(t,48,54))})`;
  tgl.style.opacity=lin(t,50.45,50.85);tgl.style.transform=`translateY(${(1-eo(lin(t,50.45,50.9)))*30}px)`;
  ozl.style.opacity=lin(t,51.4,51.9);ozl.style.letterSpacing=(.42+(1-eo(lin(t,51.4,52.4)))*.25)+'em';
  F.k7.style.opacity=t>=47.9?1:0;F.k6.style.opacity=t>41.5&&t<48.4?1:0;
  // подписи
  let c=null;CAPS.forEach(x=>{if(t>=x[0]-.1&&t<=x[1]+.1)c=x});
  if(c){cap.children[0].textContent=c[2];cap.children[1].textContent=c[3];cap.style.color=c[4];const o=fade(t,c[0],c[1],.45,.35);cap.style.opacity=o;
    cap.children[0].style.letterSpacing=(.2+(1-eo(lin(t,c[0],c[0]+1)))*.12)+'em';cap.style.transform=`translateY(${(1-eo(lin(t,c[0],c[0]+.5)))*20}px)`}
  else cap.style.opacity=0;
};
window.ready=document.fonts.ready.then(()=>Promise.all([...document.images].map(i=>i.complete?1:new Promise(r=>{i.onload=i.onerror=r}))));
