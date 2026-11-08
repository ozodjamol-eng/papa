/* «Слово-удар» (PAPA, 08.11.2026) — компоненты моушна в стиле aslani edits / Claude-промо.
   Всё через одну тайм-линию GSAP (seek), без Math.random (Motion.rand). Размер кадра — из data-size.
   SU.word(tl, el, [[t,'СЛОВО'],...])  — одно место, слово меняется на удар (блюр→резко, лёгкий скейл)
   SU.dots(tl, host, t, box)          — 4 пиксель-точки по углам слова + чёрточка сверху (мигают)
   SU.square(tl, host, t, a, b, d)    — белый пиксель-квадрат летит из a в b и растёт (переход)
   SU.blink(tl, host, times, rand)    — одиночные квадраты мигают на ударах в темноте
   SU.star(tl, host, t, cx, cy, r, n) — точки разлетаются → собираются в звезду с лучами из центра
   SU.whip(tl, el, t)                 — «влёт камеры»: размытие + скейл 1.25→1
   SU.glitch(tl, el, t)               — RGB-расслоение текста → чисто
   SU.brackets(tl, host, t, box)      — рамка-уголки вокруг области */
(function(){
const W=()=>window.__size[0], H=()=>window.__size[1];
const mk=(host,cls,css)=>{const d=document.createElement('div');d.className=cls;Object.assign(d.style,css||{});host.appendChild(d);return d;};
window.SU={
 word(tl,el,list,o={}){
   list.forEach(([t,txt],i)=>{
     tl.set(el,{innerHTML:txt},t);
     tl.fromTo(el,{filter:'blur(14px)',scale:o.scale||1.18,opacity:.2},{filter:'blur(0px)',scale:1,opacity:1,duration:o.dur||.22,ease:'power3.out'},t);
   });
 },
 dots(tl,host,t,b,o={}){
   const s=o.size||14, pts=[[b.x,b.y],[b.x+b.w,b.y],[b.x,b.y+b.h],[b.x+b.w,b.y+b.h]];
   const els=pts.map(([x,y])=>mk(host,'su-px',{left:(x-s/2)+'px',top:(y-s/2)+'px',width:s+'px',height:s+'px'}));
   const dash=mk(host,'su-px',{left:(b.x+b.w/2-28)+'px',top:(b.y-60)+'px',width:'56px',height:'8px'});
   tl.fromTo([...els,dash],{opacity:0},{opacity:1,duration:.01,stagger:.04},t);
   if(o.out) tl.to([...els,dash],{opacity:0,duration:.01,stagger:.03},o.out);
   return [...els,dash];
 },
 square(tl,host,t,a,b,o={}){
   const q=mk(host,'su-px',{left:'0px',top:'0px',width:'40px',height:'40px',opacity:0});
   tl.set(q,{opacity:1,x:a[0]-20,y:a[1]-20,scale:1},t);
   tl.to(q,{x:b[0]-20,y:b[1]-20,duration:o.fly||.18,ease:'power2.in'},t);
   tl.to(q,{scale:o.grow||8,duration:o.growDur||.12,ease:'power3.out'},t+(o.fly||.18));
   if(o.out!==false) tl.to(q,{scale:.4,opacity:0,duration:.14,ease:'power2.in'},t+(o.fly||.18)+(o.hold||.12));
   return q;
 },
 blink(tl,host,times,seed=7){
   const r=Motion.rand(seed);
   times.forEach(t=>{const s=18+Math.round(r()*26);const q=mk(host,'su-px',{left:Math.round(r()*(W()-200)+100)+'px',top:Math.round(r()*(H()-500)+250)+'px',width:s+'px',height:s+'px',opacity:0});
     tl.set(q,{opacity:1},t);tl.set(q,{opacity:0},t+.12);});
 },
 star(tl,host,t,cx,cy,R,n=14,o={}){
   const r=Motion.rand(o.seed||3), NS='http://www.w3.org/2000/svg';
   const svg=document.createElementNS(NS,'svg');svg.setAttribute('width',W());svg.setAttribute('height',H());
   Object.assign(svg.style,{position:'absolute',left:0,top:0,overflow:'visible'});host.appendChild(svg);
   const c=mk(host,'su-px',{left:(cx-22)+'px',top:(cy-22)+'px',width:'44px',height:'44px',opacity:0});
   const nodes=[],lines=[];
   for(let i=0;i<n;i++){const a=i/n*Math.PI*2+(r()-.5)*.25, rr=R*(.82+r()*.3);
     const x=cx+Math.cos(a)*rr, y=cy+Math.sin(a)*rr;
     const sx=r()*W(), sy=r()*H();
     const ln=document.createElementNS(NS,'line');['x1','y1'].forEach((k,j)=>ln.setAttribute(k,j?cy:cx));ln.setAttribute('x2',x);ln.setAttribute('y2',y);
     ln.setAttribute('stroke',o.line||'rgba(255,255,255,.75)');ln.setAttribute('stroke-width',3);ln.setAttribute('pathLength',1);ln.style.strokeDasharray=1;ln.style.strokeDashoffset=1;svg.appendChild(ln);lines.push(ln);
     const p=mk(host,'su-px',{left:'0px',top:'0px',width:'16px',height:'16px',opacity:0});
     tl.set(p,{opacity:1,x:sx-8,y:sy-8},t+i*.015);
     tl.to(p,{x:x-8,y:y-8,duration:.45,ease:'power3.inOut'},t+.15);nodes.push(p);}
   tl.set(c,{opacity:1},t+.35);
   tl.to(lines,{strokeDashoffset:0,duration:.35,stagger:.02,ease:'power2.out'},t+.55);
   return {svg,center:c,nodes,lines};
 },
 whip(tl,el,t,o={}){tl.fromTo(el,{filter:'blur(18px)',scale:o.from||1.28},{filter:'blur(0px)',scale:o.to||1,duration:o.dur||.35,ease:'power3.out'},t);},
 glitch(tl,el,t){tl.fromTo(el,{textShadow:'-14px 0 rgba(255,40,60,.9), 14px 0 rgba(40,160,255,.9)',filter:'blur(6px)',opacity:.4},{textShadow:'0px 0 rgba(255,40,60,0), 0px 0 rgba(40,160,255,0)',filter:'blur(0px)',opacity:1,duration:.3,ease:'power2.out'},t);},
 brackets(tl,host,t,b,o={}){const L=o.len||46,T=o.th||6,c=o.color||'#fff';
   const tl1=mk(host,'',{position:'absolute',left:(b.x+b.w-L)+'px',top:b.y+'px',width:L+'px',height:L+'px',borderTop:T+'px solid '+c,borderRight:T+'px solid '+c,opacity:0});
   const bl=mk(host,'',{position:'absolute',left:b.x+'px',top:(b.y+b.h-L)+'px',width:L+'px',height:L+'px',borderBottom:T+'px solid '+c,borderLeft:T+'px solid '+c,opacity:0});
   tl.fromTo(tl1,{opacity:0,x:-30,y:30},{opacity:1,x:0,y:0,duration:.3,ease:'power3.out'},t);
   tl.fromTo(bl,{opacity:0,x:30,y:-30},{opacity:1,x:0,y:0,duration:.3,ease:'power3.out'},t+.05);}
};
})();
