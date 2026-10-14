'use strict';
const $=id=>document.getElementById(id);
let snapshot={queue:{},devices:[]};let taskCache=[];let auditCache=[];
const labels={gateway_health:'Диагностика шлюза',host_health:'Диагностика сервера',policy_verify:'Проверка правил',policy_repair:'Восстановление правил',genplan_probe:'Проверка GENPLAN',urgent_prepare:'Срочный пост (подготовка)',device_health:'Диагностика устройства',startup_audit:'Автозагрузка',process_snapshot:'Процессы устройства',genplan_status:'GENPLAN Лондон',restart_service_request:'Запрос перезапуска',deploy_request:'Запрос развёртывания',telegram_publish_request:'Запрос публикации',os_repair_request:'Запрос ремонта ОС',delete_data_request:'Запрос удаления',rotate_secret_request:'Смена секрета'};
const statusText={succeeded:'Готово',queued:'В очереди',running:'В работе',awaiting_approval:'Ждёт вас',approved_not_executable:'Одобрено',failed:'Ошибка',expired:'Истекла'};
const statusClass={succeeded:'ok',queued:'warn',running:'warn',awaiting_approval:'bad',failed:'bad'};
const views={overview:['Сервер под вашим контролем','Frankfurt · диагностика и безопасные задачи'],tasks:['Задачи','Безопасное — сразу, критическое — после вас'],devices:['Устройства','Агенты подключаются сами, без открытых портов'],protocol:['Публикации','GENPLAN 5 · реальная отправка отключена'],audit:['Журнал','Кто, когда и что сделал']};
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const cookie=n=>document.cookie.split('; ').find(x=>x.startsWith(n+'='))?.split('=')[1]||'';
const when=ts=>{try{return new Date(ts).toLocaleString('ru-RU',{timeZone:'Asia/Tashkent',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'})}catch{return ts}};
const chip=(cls,text)=>`<span class="chip ${cls}">${esc(text)}</span>`;
function toast(m){const el=$('toast');el.textContent=m;el.classList.add('show');clearTimeout(toast.t);toast.t=setTimeout(()=>el.classList.remove('show'),4000)}
async function request(path,opts={}){
  const headers={'Accept':'application/json',...(opts.body?{'Content-Type':'application/json'}:{}),...(opts.method&&opts.method!=='GET'?{'X-CSRF-Token':decodeURIComponent(cookie('nexus_csrf'))}:{}),...(opts.headers||{})};
  const r=await fetch('/api/'+path,{...opts,headers,credentials:'same-origin'});
  let data;try{data=await r.json()}catch{data={detail:'Некорректный ответ сервера'}}
  if(!r.ok)throw new Error(typeof data.detail==='string'?data.detail:(data.error||'HTTP '+r.status));
  return data;
}
function selectView(view){
  document.querySelectorAll('.view').forEach(x=>x.classList.toggle('active',x.id===view));
  document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('active',x.dataset.view===view));
  const t=views[view]||views.overview;$('page-title').textContent=t[0];$('page-sub').textContent=t[1];$('page-label').textContent=view;
  window.scrollTo({top:0,behavior:'smooth'});
}
function showLogin(){$('login').classList.remove('hidden');$('app').classList.add('hidden')}
function showApp(){$('login').classList.add('hidden');$('app').classList.remove('hidden')}
function summary(x){try{const o=JSON.parse(x.result||'{}');
  if(o.memory_available_bytes)return `Память свободна: ${Math.round(o.memory_available_bytes/1048576)} МБ · Диск: ${Math.round(o.disk_free_bytes/1073741824)} ГБ`;
  if(o.healthy!==undefined)return o.healthy?'Шлюз исправен':'Шлюз неисправен';
  if(o.reason)return o.reason==='compliant'?'Правила в порядке':String(o.reason);
  if(o.error)return 'Ошибка: '+o.error;
  return ''}catch{return ''}}
function taskRows(tasks,limit=60){
  if(!tasks.length)return '<div class="empty">Задач пока нет. Нажмите «Проверить».</div>';
  return tasks.slice(0,limit).map(x=>{const s=summary(x);return `<div class="row"><div><strong>${esc(labels[x.operation]||x.operation)}</strong><small>${esc(when(x.created_at))} · ${esc(x.target)}${x.requested_by?' · '+esc(x.requested_by):''}</small>${s?`<small>${esc(s)}</small>`:''}</div><div class="right">${chip(statusClass[x.status]||'',statusText[x.status]||x.status)}${x.status==='awaiting_approval'?`<button class="mini" data-approve="${esc(x.id)}">Подтвердить</button>`:''}</div></div>`}).join('')}
function deviceRows(devices){
  if(!devices.length)return '<div class="empty">Агенты ещё не подключены</div>';
  return devices.map(x=>`<div class="row"><div><strong>${esc(x.hostname)}</strong><small>${esc(x.id)} · ${esc(x.platform)}</small></div>${chip(x.online?'ok':'',x.online?'Онлайн':'Офлайн')}</div>`).join('')}
function render(){
  const online=snapshot.gateway==='online';
  $('core-state').className='chip '+(online?'ok':'bad');$('core-state').textContent=online?'Работает':'Нет связи';
  const on=snapshot.devices.filter(d=>d.online).length;
  $('online-count').className='chip '+(on?'ok':'');$('online-count').textContent=`${on} / ${snapshot.devices.length} онлайн`;
  $('queue-count').textContent=(snapshot.queue.queued||0)+(snapshot.queue.running||0)+(snapshot.queue.awaiting_approval||0);
  $('done-count').textContent=snapshot.queue.succeeded||0;
  $('device-summary').innerHTML=deviceRows(snapshot.devices.slice(0,3));
  $('all-devices').innerHTML=deviceRows(snapshot.devices);
  $('recent-tasks').innerHTML=taskRows(taskCache,4);
  $('all-tasks').innerHTML=taskRows(taskCache);
  $('audit-list').innerHTML=auditCache.length?auditCache.map(e=>`<div class="row"><div><strong>${esc(e.action)}</strong><small>${esc(e.actor)}${e.info?' · '+esc(e.info):''}</small></div><small>${esc(when(e.ts))}</small></div>`).join(''):'<div class="empty">Записей пока нет</div>';
}
async function refresh(){try{const [status,tasks,audit]=await Promise.all([request('status'),request('tasks'),request('audit')]);snapshot=status;taskCache=tasks.tasks;auditCache=audit.events;render()}catch(e){if(e.message==='authentication_required')showLogin();else toast('Ошибка обновления: '+e.message)}}
async function createTask(op,target='cloud',payload={}){try{const idempotency_key=(globalThis.crypto?.randomUUID?.()||`${Date.now()}-${Math.random()}`);const out=await request('tasks',{method:'POST',body:JSON.stringify({operation:op,target,payload,idempotency_key})});toast(out.status==='awaiting_approval'?'Запрос ждёт вашего подтверждения':'Задача запущена');await refresh();setTimeout(refresh,1500);return out}catch(e){toast('Не удалось: '+e.message)}}
async function approve(id){const expected='APPROVE:'+id;const typed=prompt('В V2 критическое действие не выполнится даже после согласия. Чтобы записать согласие, введите точно:\n'+expected);if(!typed)return;try{const out=await request('tasks/'+encodeURIComponent(id)+'/approve',{method:'POST',body:JSON.stringify({confirmation:typed})});toast(out.executed?'Выполнено':'Согласие записано. Исполнение отключено.');await refresh()}catch(e){toast('Отклонено: '+e.message)}}
$('login-form').addEventListener('submit',async e=>{e.preventDefault();$('login-error').textContent='';try{await request('login',{method:'POST',body:JSON.stringify({password:$('password').value})});$('password').value='';showApp();await refresh()}catch(err){$('login-error').textContent=err.message==='temporarily_locked'?'Слишком много попыток. Подождите 15 минут.':'Неверный пароль'}});
$('logout').addEventListener('click',async()=>{try{await request('logout',{method:'POST',body:'{}'})}catch{}showLogin()});
document.querySelectorAll('[data-view]').forEach(el=>el.addEventListener('click',()=>selectView(el.dataset.view)));
document.querySelectorAll('[data-goto]').forEach(el=>el.addEventListener('click',()=>selectView(el.dataset.goto)));
document.querySelectorAll('[data-op]').forEach(el=>el.addEventListener('click',()=>createTask(el.dataset.op,el.dataset.target||'cloud')));
['all-tasks','recent-tasks'].forEach(id=>$(id).addEventListener('click',e=>{const el=e.target.closest('[data-approve]');if(el)approve(el.dataset.approve)}));
const agentOps=new Set(['device_health','startup_audit','process_snapshot','genplan_status']);const restrictedOps=new Set(['restart_service_request']);
$('task-operation').addEventListener('change',()=>{const op=$('task-operation').value;$('task-target').value=op==='genplan_status'?'london':agentOps.has(op)?'office-windows':'cloud';$('post-row').classList.toggle('hidden',op!=='urgent_prepare');$('reason-row').classList.toggle('hidden',!restrictedOps.has(op))});
$('task-form').addEventListener('submit',async e=>{e.preventDefault();const op=$('task-operation').value;const target=$('task-target').value.trim();let payload={};if(op==='urgent_prepare')payload.post_id=Number($('task-post-id').value);if(restrictedOps.has(op))payload.reason=$('task-reason').value.trim();await createTask(op,target,payload)});
$('refresh').addEventListener('click',()=>{refresh();toast('Обновлено')});
function theme(m){document.documentElement.dataset.theme=m;try{localStorage.setItem('nexus-theme',m)}catch{}}
let saved='light';try{saved=localStorage.getItem('nexus-theme')||'light'}catch{}theme(saved);
$('theme').addEventListener('click',()=>theme(document.documentElement.dataset.theme==='dark'?'light':'dark'));
function tick(){$('time').textContent=new Date().toLocaleTimeString('ru-RU',{timeZone:'Asia/Tashkent',hour:'2-digit',minute:'2-digit'})+' · Ташкент'}tick();setInterval(tick,30000);
(async()=>{try{await request('me');showApp();await refresh()}catch{showLogin()}})();
setInterval(()=>{if(!$('app').classList.contains('hidden'))refresh()},15000);
