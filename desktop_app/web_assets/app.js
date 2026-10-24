(() => {
'use strict';
const $ = id => document.getElementById(id);
const NS='http://www.w3.org/2000/svg';
const paths={plus:'M12 5v14M5 12h14',chat:'M21 11a8 8 0 0 1-8 8H5l-3 3V11a9 9 0 0 1 19 0Z',team:'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8M17 4a4 4 0 0 1 0 8M22 21v-2a4 4 0 0 0-3-4',todo:'M9 5h11v15H4V5h2M9 3h6v4H9zM8 12l2 2 5-5',clock:'M12 8v5l3 2M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0',activity:'M3 12h4l3-8 4 16 3-8h4',bell:'M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4',database:'M21 5c0 2-4 3-9 3S3 7 3 5s4-3 9-3 9 1 9 3ZM3 5v14c0 2 4 3 9 3s9-1 9-3V5M3 12c0 2 4 3 9 3s9-1 9-3',settings:'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M5 19l2-2M17 7l2-2',help:'M9 8a3 3 0 0 1 6 0c0 2-3 2-3 5M12 17h.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0',more:'M5 12h.01M12 12h.01M19 12h.01',collapse:'M9 3v18M15 8l-4 4 4 4M3 3h18v18H3z',sun:'M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10M12 1v2M12 21v2M1 12h2M21 12h2M4 4l2 2M18 18l2 2M4 20l2-2M18 6l2-2',spark:'m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z',info:'M12 11v6M12 7h.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0',document:'M14 2H4v20h16V8l-6-6v6h6M8 12h8M8 16h8',workflow:'M8 5h8M5 8v8M8 19h8M19 8v8M2 2h6v6H2zM16 2h6v6h-6zM2 16h6v6H2zM16 16h6v6h-6z',attach:'m9 13 6-6a3 3 0 0 1 4 4l-9 9a5 5 0 0 1-7-7L13 3',sliders:'M4 6h16M4 12h16M4 18h16M8 3v6M16 9v6M9 15v6','arrow-up':'M12 19V5M5 12l7-7 7 7',close:'m6 6 12 12M6 18 18 6',issue:'M12 8v5M12 17h.01M12 2 2 21h20Z'};
function icon(name){const s=document.createElementNS(NS,'svg');s.setAttribute('viewBox','0 0 24 24');s.setAttribute('aria-hidden','true');const p=document.createElementNS(NS,'path');p.setAttribute('d',paths[name]||paths.document);s.append(p);return s;}
document.querySelectorAll('[data-icon]').forEach(e=>e.replaceChildren(icon(e.dataset.icon)));$('collapse').append(icon('collapse'));
function el(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=String(text??'');return e;}
function button(text,fn,cls='button'){const b=el('button',cls,text);b.type='button';b.addEventListener('click',async()=>{if(b.disabled)return;b.disabled=true;try{await fn();}catch(e){notify(e.message,true);}finally{b.disabled=S.closing;}});return b;}
const S={ready:false,state:null,cid:null,page:'dialogue',mode:'chat',purpose:'chat',planned:false,seq:0,sending:false,composing:false,dirty:false,polling:false,closing:false,viewGeneration:0,editVersion:0,saveTimer:null,modalVersion:0,signatures:{}};
function sampleQuery(){const now=Date.now()+8*3600000,yesterday=new Date(now-86400000).toISOString().slice(0,10),today=new Date(now).toISOString().slice(0,10);return {text:'查昨天 A 類數量合計',query_id:'DEMO03',parameters:{from_date:yesterday,to_date:today,category:'A'}};}
const labels={dialogue:'對話',memories:'我的記憶',skills:'我的 Skills',orders:'交辦工作',chat:'規劃與分工',team:'助理團隊',todo:'我的待辦',schedule:'自動工作',activity:'活動紀錄',notice:'通知',query:'查資料',settings:'設定',help:'說明與關於',issue:'問題回報'};
const descriptions={team:'每位助理各有所長。先確認能力，再一起完成工作。',todo:'留下下一步，讓事情持續前進。',schedule:'核准一次，依固定流程執行。應用程式需要保持開啟。',activity:'查看真實的執行進度與成果。',notice:'工作有了新結果，從這裡繼續。',query:'1 選資料來源 → 2 填條件並確認 → 3 查看表格或交給助理。',settings:'設定你的助理連線與工作區外觀。',help:'離線手冊、資料說明與第三方授權。',issue:'問題與需求先保存本機，尚未送至管理平台。'};
const states={deleted:'成果已刪除',queued:'排隊中',running:'執行中',succeeded:'已完成',failed:'未完成',cancelled:'已取消',draft:'草稿',ready:'待確認',approved:'已批准',planning:'規劃中',executing:'執行中',todo:'待處理',ongoing:'進行中',done:'已完成',pass:'流程覆核通過',needs_attention:'需要處理'};
function rid(){return globalThis.crypto?.randomUUID?.()||'web-'+Date.now()+'-'+Math.random().toString(36).slice(2);}
function notify(text,error=false){$('toast').textContent=text;$('toast').classList.toggle('error',error);$('toast').hidden=false;clearTimeout(notify.timer);notify.timer=setTimeout(()=>$('toast').hidden=true,5000);}
async function call(name,payload={}){if(S.closing)throw Error('正在保存並關閉，請稍候。');if(!S.ready)throw Error('尚未連接桌面服務，請從桌面入口啟動。');const r=await window.pywebview.api.call(name,payload);if(!r||!r.ok)throw Error((r?.error||'操作未完成，請重試。')+(r?.incident?' · 問題編號 '+r.incident.id+(r.incident.saved?'':'（紀錄保存失敗）'):''));if(name==='table_export'&&payload.format==='tsv'&&typeof r.data?.text==='string')await copy(r.data.text);return r.data;}
async function action(name,payload={}){const value=await call(name,payload);await refresh();return value;}
function changed(key,value){const str=JSON.stringify(value);if(S.signatures[key]===str)return false;S.signatures[key]=str;return true;}
function time(value){if(!value)return '';const d=new Date(value);return Number.isNaN(d.valueOf())?String(value):d.toLocaleString('zh-TW',{timeZone:'Asia/Taipei',hour12:false});}
// State colors are presentation only; never infer authorization or success from copy.
const tones={queued:'working',running:'working',executing:'working',planning:'working',parsing:'working',ongoing:'working',ready:'attention',pending:'attention',needs_attention:'attention',todo:'attention',succeeded:'success',done:'success',pass:'success',failed:'danger',cancelled:'neutral',draft:'neutral',approved:'info','已驗證':'success','待驗證':'attention','已啟用':'info','未讀':'info'};
function tone(node,state){node.dataset.tone=tones[state]||'neutral';return node;}
function badge(value){const b=tone(el('span','pill'),value),mark=el('span','status-symbol',({working:'◷',attention:'◇',success:'✓',danger:'!',info:'•',neutral:'—'})[b.dataset.tone]);mark.setAttribute('aria-hidden','true');b.append(mark,el('span','status-label',states[value]||value));return b;}
function noticeRead(n){return n.is_read===true||n.is_read===1;}
function renderUnread(data){const b=document.querySelector('[data-page=notice] .badge');if(!b)return;const count=(data.notifications||[]).filter(n=>!noticeRead(n)).length;b.hidden=!count;b.textContent=count>99?'99+':String(count);b.setAttribute('aria-label',count+' 則未讀通知');}
function statusLegend(root){const legend=el('div','status-legend');legend.append(el('span','','狀態：'));['ready','running','succeeded','failed'].forEach(v=>legend.append(badge(v)));root.append(legend);}
const roleLabels={planner:'主代理 · 規劃',rag:'搜尋',analysis:'分析',review:'覆核',compose:'彙整'};
function empty(parent,title,description){const c=el('div','empty-state');c.append(el('h3','',title),el('p','',description));parent.append(c);}
function comparisonView(data){const area=el('div');if(!data)return area;if(data.reason)area.append(el('p','notice',data.reason));for(const g of data.groups||[]){area.append(el('h3','','查詢步驟 '+g.step_id));if(g.previous){area.append(el('p','muted','上次：'+time(g.previous.fetched_at_utc)+' ／ 本次：'+time(g.current.fetched_at_utc)),el('p','plain-text','上次條件：'+plain(g.previous.parameters)+'\n本次條件：'+plain(g.current.parameters)));}if(g.same_period)area.append(el('span','pill','同期間重跑'));if(g.reason){area.append(el('p','notice',g.reason));continue;}const wrap=el('div','table-wrap'),table=el('table','data-table'),head=el('tr');['指標','上次','本次','差值'].forEach(t=>head.append(el('th','',t)));table.append(head);for(const row of g.rows||[]){const tr=el('tr');row.forEach(v=>tr.append(el('td','',v)));table.append(tr);}wrap.append(table);area.append(wrap);}area.append(el('p','muted','數值變化不代表改善或惡化。比較只在本機進行。'));return area;}
function renderQuestions(card,questions){if(!questions?.length)return;const answers=[];for(const q of questions){if(q.type==='multi'){const box=el('div','field');box.append(el('label','',q.text));const values=[];for(const option of q.options||[]){const label=el('label','check-field'),input=el('input');input.type='checkbox';label.append(input,document.createTextNode(option));box.append(label);values.push([option,input]);}card.append(box);answers.push(()=>q.text+'：'+values.filter(v=>v[1].checked).map(v=>v[0]).join('、'));}else{const options=q.type==='boolean'?['請選擇','是','否']:q.type==='single'?['請選擇',...(q.options||[])]:null;const input=field(card,q.text,'','text',options);answers.push(()=>q.text+'：'+input.value);}}card.append(button('帶入回答',()=>{$('message-input').value=[$('message-input').value,...answers.map(a=>a())].filter(Boolean).join('\n');S.dirty=true;S.editVersion++;resizeInput();$('message-input').focus();return saveDraft();},'button'));}
function explicitIntent(text){if(/日報/.test(text)&&/查|每天|每日|自動|早上|排程/.test(text))return 'report';if(/每天|每日|每週|每周|定時|排程|自動查/.test(text))return 'schedule';if(/查詢|查資料|查數據|查.*(?:合計|庫存|訂單)/.test(text))return 'query';return null;}
function actionCard(a){const c=tone(el('div','workflow-card'),a.task?.state||a.status||a.state);c.append(el('h3','',a.request||'查詢工作'),badge(a.task?.state||a.status||a.state));if(a.error)c.append(el('p','error',a.error));if(a.parse_note)c.append(el('p','notice',a.parse_note));if(a.status==='parsing'){c.append(el('p','muted','正在整理條件，尚未查詢或啟用。'));return c;}const tools=el('div','card-actions');if(a.schedule_id){c.append(el('p','notice','自動工作已設定。只有應用開啟時執行，不會因啟用立即執行。'));tools.append(button('現在測試一次',()=>confirm('立即測試','將依核准條件執行一次，不改原定時間。','確認執行',()=>action('schedule_run',{id:a.schedule_id,request_id:rid()}))),button(a.schedule?.enabled?'暫停':'啟用',()=>action('schedule_toggle',{id:a.schedule_id,enabled:!a.schedule?.enabled})));}if(a.task){if(['queued','running'].includes(a.task.state))tools.append(button('取消工作',()=>action('cancel_task',{task_id:a.task.id})));else tools.append(button('查看結果',()=>showTask(a.task.id),'button primary'));const result=a.result?.query_result||a.result;if(result?.columns&&result?.rows){c.append(el('p','muted',result.rows.length+' 列 · '+time(result.fetched_at_utc)+' · 前五列預覽'));const wrap=el('div','table-wrap'),table=el('table','data-table'),head=el('tr');result.columns.forEach(x=>head.append(el('th','',x.label||x.name)));table.append(head);result.rows.slice(0,5).forEach(row=>{const tr=el('tr');result.columns.forEach((x,i)=>tr.append(el('td','',Array.isArray(row)?row[i]:row[x.name])));table.append(tr);});wrap.append(table);c.append(wrap);}}else if(!a.schedule_id)tools.append(button('補齊／修改條件',()=>editAction(a)));c.append(tools);return c;}
async function showTask(tid){const task=await call('task_result',{task_id:tid});if(task.kind==='assistant_briefing')return showBriefing(tid);if(task.kind==='workflow')return showOutcome(tid);if(task.result?.columns||task.result?.query_result?.columns)return showTable(tid);const body=modal('工作結果');body.append(badge(task.state),el('p','error',task.error||''),el('div','plain-text',task.result?.text||task.result?.report||plain(task.result||'尚無結果')));}
function plain(value){return typeof value==='string'?value:JSON.stringify(value,null,2);}
// Only renderer-sanitized HTML returned by the backend enters this sink.
function trustedMarkdown(node,html,fallback){if(typeof html==='string'){node.innerHTML=html;node.classList.add('markdown');}else node.textContent=fallback||'';}
document.addEventListener('click',e=>{const a=e.target.closest('a');if(a){e.preventDefault();notify('連結不會在工作區內開啟，請依組織流程查閱來源。');}});
function field(parent,label,value='',type='text',options=null){const wrap=el('div','field');const lab=el('label','',label);const input=el(options?'select':type==='textarea'?'textarea':'input');input.id=rid();lab.htmlFor=input.id;if(options){options.forEach(o=>{const option=el('option','',typeof o==='object'?o.label:o);option.value=typeof o==='object'?o.value:o;input.append(option);});}else if(type!=='textarea')input.type=type;input.value=value??'';wrap.append(lab,input);parent.append(wrap);return input;}
function modal(title){S.modalVersion++;$('modal-title').textContent=title;$('modal-body').replaceChildren();$('modal-actions').replaceChildren();if(!$('modal').open)$('modal').showModal();return $('modal-body');}
let workEntryDismiss=null;
function closeModal(){$('modal').close();S.modalVersion++;if(workEntryDismiss){const finish=workEntryDismiss;workEntryDismiss=null;finish();}}
function modalButtons(...items){$('modal-actions').replaceChildren(...items);}
// This palette only locates existing screens. It never dispatches or approves work.
const workEntries=[
 {id:'agent-work',icon:'workflow',title:'交辦一件工作',description:'說明目標、核對 Plan，再交給助理完成；可選 Skill',keywords:'交辦 主代理 agent plan 搜尋 整理'},
 {id:'skills',icon:'spark',title:'我的 Skills',description:'保存工作做法，用一位助理先規劃再執行',keywords:'skill 技能 模板 工作流程'},
 {id:'orders',icon:'clock',title:'既有每日交辦',description:'保留原本每日搜尋日報與歷史成果',keywords:'日報 舊交辦'},
 {id:'dialogue',icon:'chat',title:'繼續對話',description:'回到目前對話，保留尚未送出的內容',keywords:'聊天 chat assistant'},
 {id:'chat',icon:'workflow',title:'規劃與分工',description:'先討論需求與步驟，確認後才交給助理執行',keywords:'plan 多代理 multi agents 團隊'},
 {id:'team',icon:'team',title:'助理團隊',description:'管理 Assistant ID、角色與能力驗證',keywords:'assistant 設定 主代理 子代理'},
 {id:'briefing',icon:'document',title:'財經日報',description:'開啟日報設定與預覽；不會立即搜尋或啟用',keywords:'台股 美股 總經 每日 搜尋 search'},
 {id:'schedule',icon:'clock',title:'自動工作',description:'查看已設定的時間、最近結果與啟停狀態',keywords:'schedule 排程 每天'},
 {id:'activity',icon:'activity',title:'成果與活動',description:'查看實際進度、成果與失敗原因',keywords:'task result status 工作 紀錄'},
 {id:'todo',icon:'todo',title:'我的待辦',description:'記下下一步，手動更新完成狀態',keywords:'todo done ongoing'},
 {id:'query',icon:'database',title:'查資料',description:'選擇核准來源、填條件，再預覽確認',keywords:'database oracle 數據 查詢'},
 {id:'settings',icon:'settings',title:'設定連線與外觀',description:'設定 Endpoint、金鑰及工作區配色',keywords:'api key endpoint theme'},
];
function openWorkEntry(){
 if(S.closing)return;
 if($('modal').open){notify('請先完成或關閉目前視窗，再開啟工作入口。');return;}
 const previous=document.activeElement,body=modal('你想從哪件事開始？'),dialog=$('modal');
 dialog.classList.add('work-palette');dialog.setAttribute('aria-labelledby','modal-title');
 const search=field(body,'搜尋工作入口','','search');search.id='work-entry-search';search.previousElementSibling.htmlFor=search.id;search.placeholder='例如：規劃、日報、成果…';search.autocomplete='off';
 const hint=el('p','work-entry-hint','只開啟入口，不會自動送出、批准或啟用工作。'),list=el('div','work-entry-list'),status=el('p','muted');list.id='work-entry-list';status.setAttribute('role','status');body.append(hint,list,status);
 const dismiss=()=>{dialog.classList.remove('work-palette');if(previous?.isConnected&&!previous.closest('[hidden]'))previous.focus();};
 workEntryDismiss=dismiss;
 function draw(){
  list.replaceChildren();const term=search.value.trim().toLocaleLowerCase();
  const matches=workEntries.filter(item=>[item.title,item.description,item.keywords].join(' ').toLocaleLowerCase().includes(term));
  status.textContent=matches.length?matches.length+' 個入口 · ↑↓ 選擇，Enter 開啟，Esc 關閉':'沒有符合的入口，請換個關鍵字。';
  for(const item of matches){
   const row=button('',async()=>{
    // Existing input elements are retained; never fill or clear a draft here.
    workEntryDismiss=null;dialog.classList.remove('work-palette');closeModal();
    if(item.id==='agent-work'){navigate('dialogue');document.dispatchEvent(new Event('qa-agent-open'));return;}
    if(item.id==='briefing'){await showBriefing();return;}
    if(S.page!==item.id)navigate(item.id);
    if(item.id==='chat'){
     if(!$('message-input').value.trim()&&!S.sending)mode('workflow');
     else notify('已保留目前草稿與模式；準備好後可選「規劃工作」。');
     $('message-input').focus();
    }else if(item.id==='dialogue')$('dialogue-input').focus();
   },'work-entry-item');row.dataset.workEntry=item.id;
   const text=el('span','work-entry-copy');text.append(el('strong','',item.title),el('small','',item.description));row.append(icon(item.icon),text,el('span','work-entry-arrow','↗'));list.append(row);
  }
 }
 search.addEventListener('input',draw);
 body.addEventListener('keydown',event=>{
  if(event.isComposing||event.keyCode===229||event.repeat)return;
  const buttons=[...list.querySelectorAll('button')],index=buttons.indexOf(document.activeElement);
  if(event.key==='ArrowDown'||event.key==='ArrowUp'){
   event.preventDefault();if(!buttons.length)return;
   const next=event.key==='ArrowDown'?(index+1)%buttons.length:(index<0?buttons.length-1:(index-1+buttons.length)%buttons.length);buttons[next].focus();
  }else if(event.key==='Enter'&&event.target===search){event.preventDefault();buttons[0]?.click();}
 });
 draw();search.focus();
}
$('work-entry').addEventListener('click',openWorkEntry);
document.addEventListener('keydown',event=>{
 if(event.isComposing||event.keyCode===229)return;
 if(event.key==='Escape'&&$('modal').open&&$('modal').classList.contains('work-palette')){event.preventDefault();closeModal();return;}
 if(event.ctrlKey&&!event.altKey&&!event.shiftKey&&event.key.toLowerCase()==='k'){event.preventDefault();if(!event.repeat)openWorkEntry();}
});
function confirm(title,text,label,fn){const body=modal(title);body.append(el('p','plain-text',text));const cancel=button('取消',closeModal);modalButtons(cancel,button(label,async()=>{await fn();closeModal();},'button primary'));cancel.focus();}
function companyReadinessEntry(root){
 const card=el('section','card');card.style.marginTop='18px';
 card.append(el('h3','','連線啟用檢查'),el('p','muted','儲存設定不代表實測通過。先檢查本機缺少哪些設定，再依提示完成環境試跑。'));
 const tools=el('div','card-actions');tools.append(button('財經日報',()=>showBriefing(),'button primary'),button('檢查本機設定',showCompanyReadiness));card.append(tools);root.append(card);
}
async function showBriefing(existingTaskId=null){
 const body=modal('財經日報'),version=S.modalVersion;
 const active=()=>!S.closing&&version===S.modalVersion&&$('modal').open;
 let taskId=existingTaskId,clock='',polling=false;
 const close=()=>button('關閉',closeModal);
 modalButtons(close());
 if(String(S.state?.mode).toLowerCase().includes('groq')||S.state?.settings?.editable===false){body.append(el('p','notice','財經日報使用AI 助理，請以正式 start-app.bat 入口啟動後設定組織連線。'));return;}
 function scheduleReady(data){
  const enabled=data.enabled===true;
  body.append(el('p','notice',(enabled?'已啟用':'已暫停')+'每日 '+(data.time_hhmm||clock||'指定時間')+'（台北時間）。'+(enabled?'啟用不會立即再跑，只有 QA agent 保持開啟時才會執行。':'暫停期間不會依排程執行。')));
  if(enabled)body.append(el('p','muted','下次執行：'+(time(data.next_fire)||'請至自動工作查看')));
  const manage=button('管理自動工作',()=>{closeModal();navigate('schedule');});
  modalButtons(close(),manage,...(enabled?[button('暫停每日工作',async()=>{await call('schedule_toggle',{id:data.schedule_id,enabled:false});if(!active())return;body.replaceChildren(el('p','muted','正在讀取排程狀態…'));modalButtons(close(),manage);await poll();await refresh();})]:[]));
 }
 function ended(status){
  body.replaceChildren(badge(status.state));
  const searches=status.search_activity||[];
  body.append(el('p','muted',searches.length?'本次搜尋紀錄：'+searches.map(c=>c.name+' · '+(c.state==='completed'?(c.submitted?'結果已交回助理':'已取得結果，尚未確認提交'):c.state==='unknown'?'結果未明，不自動重送':'尚未派發')).join('；'):'本次沒有本機搜尋執行收據；不能據此認定已取得即時資料。'));
  if(status.error)body.append(el('p','error',status.error));
  const text=typeof status.result?.text==='string'?status.result.text:'';
  if(text)body.append(el('div','plain-text',text));
  if(status.state!=='succeeded'||!text){
   body.append(el('p','notice',status.state==='cancelled'?'已取消；不會啟用每日工作。取消不保證遠端立即停止。':'本次日報未完成，沒有啟用每日工作。只有核准的唯讀搜尋工具可執行；未知工具或參數不符時會停止，請查看原因後再處理。'));
   modalButtons(close(),button('連線啟用檢查',showCompanyReadiness));return;
  }
  body.append(tone(el('p','notice','AI 日報內容與來源需要核對。產生文字不代表搜尋能力已獨立驗收，請確認資料日期、來源及台股／美股／總經內容。'),'ready'));
  if(status.schedule_deleted){body.append(el('p','notice','來源自動工作已刪除，這份成果仍保留。'));modalButtons(close());return;}
  if(status.schedule_id){
   if(!status.schedule||typeof status.schedule.enabled!=='boolean'){body.append(el('p','notice','尚無法確認排程狀態，請至自動工作查看。'));modalButtons(close(),button('管理自動工作',()=>{closeModal();navigate('schedule');}));return;}
   scheduleReady({...status.schedule,schedule_id:status.schedule_id});return;
  }
  clock=status.payload?.spec?.time_hhmm||status.time_hhmm||status.result?.time_hhmm||clock;
  const label=el('label','check-field'),consent=el('input');consent.type='checkbox';
  label.append(consent,document.createTextNode('我已核對日報內容，並同意每天傳送此需求'));body.append(label);
  body.append(el('p','muted','確認後才會建立每日工作。只在 App 開啟時執行；關閉此視窗不代表已啟用。'));
  const enable=button(clock?'啟用每日 '+clock:'啟用每日自動工作',async()=>{
   if(!consent.checked)throw Error('請先核對日報並勾選每天傳送授權。');
   consent.disabled=true;
   try{await call('briefing_schedule',{task_id:taskId,consent:true,reviewed:true});if(!active())return;body.replaceChildren(el('p','muted','正在讀取排程狀態…'));modalButtons(close());await poll();await refresh();}
   catch(error){if(active()){consent.disabled=false;notify(error.message||'未完成每日工作設定，請重試。',true);}}
  },'button primary');enable.disabled=true;consent.addEventListener('change',()=>enable.disabled=!consent.checked);
  modalButtons(close(),enable);
 }
 async function poll(){
  if(!active()||polling)return;polling=true;
  try{
   const status=await call('briefing_status',{task_id:taskId});if(!active())return;
   clock=status.payload?.spec?.time_hhmm||clock;
   if(['queued','running'].includes(status.state)){
    body.replaceChildren(badge(status.state),el('p','plain-text','正在依已確認需求取得日報。'),el('p','muted','關閉視窗只停止顯示；背景工作仍可從活動紀錄查看。'));
    modalButtons(close(),button('取消本次試跑',async()=>{await call('cancel_task',{task_id:taskId});if(active())body.append(el('p','notice','已送出取消要求，正在讀取工作狀態。'));}));
    setTimeout(()=>{if(active())poll();},1000);
   }else ended(status);
  }catch(error){if(active()){body.append(el('p','error',error.message||'暫時無法取得工作狀態，尚未重送日報需求。'));modalButtons(close(),button('重新讀取狀態',poll));}}
  finally{polling=false;}
 }
 if(taskId){body.append(el('p','muted','正在讀取日報狀態…'));await poll();return;}
 const profiles=(S.state?.profiles||[]).filter(p=>p.id!=='demo'&&p.enabled!==false);
 if(!profiles.length){body.append(el('p','notice','請先新增組織的搜尋 Assistant ID。單一助理即可試跑，不需要先配置四個分工角色。'));modalButtons(close(),button('新增AI 助理',()=>readinessDestination('team')));return;}
 body.append(el('p','muted','正在載入財經日報需求…'));
 let defaults;
 try{defaults=await call('briefing_defaults');}catch(error){if(active()){body.replaceChildren(el('p','error',error.message||'無法載入日報需求。'));modalButtons(close(),button('重新開啟',()=>showBriefing()));}return;}
 if(!active())return;body.replaceChildren();
 body.append(el('p','notice','使用一位組織搜尋助理，先預覽、試跑並核對，再決定是否每天執行。此入口不需要先配置四個分工角色。'));
 const profile=field(body,'組織搜尋助理',profiles[0].id,'text',profiles.map(p=>({value:p.id,label:(p.name||'AI 助理')+' · '+p.assistant_id}))),prompt=field(body,'日報需求',defaults.prompt||'','textarea'),when=field(body,'每日時間（台北）',defaults.time_hhmm||'08:00','time');
 prompt.rows=7;prompt.required=true;when.required=true;
 const previewArea=el('div');body.append(previewArea);
 const lock=value=>[profile,prompt,when].forEach(input=>input.disabled=value);
 function previewButton(){return button('預覽試跑',async()=>{
  if(!prompt.value.trim()||!prompt.reportValidity()||!when.reportValidity())throw Error('請填寫日報需求與每日時間。');
  lock(true);previewArea.replaceChildren(el('p','muted','正在建立預覽，尚未執行。'));modalButtons(close());
  try{
   const draft=await call('briefing_preview',{profile_id:profile.value,prompt:prompt.value,time_hhmm:when.value});if(!active())return;
   clock=draft.time_hhmm;
   previewArea.replaceChildren(el('h3','','尚未執行'),el('p','plain-text','目的助理：'+draft.assistant_name+'\n每日時間：'+draft.time_hhmm+'（台北）'),el('div','plain-text',draft.prompt),el('p','notice',draft.message||'按「現在試跑」才會將上述需求傳送給AI 助理；不會自動啟用排程。'));
   previewArea.append(el('p','plain-text',Array.isArray(draft.search_tools)&&draft.search_tools.length?'本次允許的搜尋工具：'+draft.search_tools.join('、'):'本次未開放搜尋工具；只取得文字回覆，不能視為已查到即時資料。'));
   if(draft.search_tools?.length)previewArea.append(el('p','muted','搜尋上限：每批4個工具、最多3批、總等待600秒；单次工具回覆超128KiB即停止，不截斷。'));
   modalButtons(close(),button('修改需求',()=>{lock(false);previewArea.replaceChildren();modalButtons(close(),previewButton());}),button('現在試跑',async()=>{
    modalButtons(close());previewArea.append(el('p','muted','正在提交試跑…'));
    try{const result=await call('briefing_run',{token:draft.token});if(!active())return;taskId=result.task_id;await poll();await refresh();}
    catch(error){if(active()){previewArea.append(el('p','error',error.message||'提交未完成。'),el('p','notice','未自動重送。請先到活動紀錄確認是否已受理，再決定下一步。'));modalButtons(close(),button('查看活動紀錄',()=>{closeModal();navigate('activity');}));}}
   },'button primary'));
  }catch(error){if(active()){lock(false);previewArea.replaceChildren(el('p','error',error.message||'預覽未完成，尚未執行。'));modalButtons(close(),previewButton());}}
 },'button primary');}
 modalButtons(close(),previewButton());
}
function readinessDestination(action){
 closeModal();
 if(action==='plan'){navigate('chat');mode('workflow');$('message-input').focus();}
 else if(action==='settings'||action==='team')navigate(action);
}
function companyProbeSection(body,version,profileId=null){
 const section=el('section','card');section.append(el('h3','','檢查搜尋工具宣告'),el('p','plain-text','此檢查只讀取助理設定，不問模型、不執行搜尋，也不啟用任務。此檢查失敗不代表一般聊天不可用；可從助理卡片另行試用聊天。'));
 const profiles=(S.state?.profiles||[]).filter(p=>p.id!=='demo'&&p.enabled!==false);
 body.append(section);
 if(!profiles.length){section.append(el('p','notice','尚無已啟用的AI 助理。請先新增組織的搜尋 Assistant ID。'),button('新增AI 助理',()=>readinessDestination('team')));return;}
 const select=field(section,'選擇組織搜尋助理',profiles.some(p=>p.id===profileId)?profileId:profiles[0].id,'text',profiles.map(p=>({value:p.id,label:(p.name||'AI 助理')+' · '+p.assistant_id})));
 const current=el('div');section.append(current);
 const output=el('div');output.setAttribute('aria-live','polite');
 const active=()=>!S.closing&&version===S.modalVersion&&$('modal').open;
 const savedPolicies=new Map();
 let busy=false,clearButton=null;
 function setBusy(value){busy=value;select.disabled=value;run.disabled=value;if(clearButton)clearButton.disabled=value;}
 function currentPolicy(){
  const profile=(S.state?.profiles||[]).find(p=>p.id===select.value),names=savedPolicies.has(select.value)?savedPolicies.get(select.value):(profile?.search_policy?.tools||[]).map(t=>t.name);
  current.replaceChildren(el('p','plain-text',names.length?'目前核准的搜尋工具：'+names.join('、'):'尚未核准搜尋工具。'));
  clearButton=null;if(!names.length)return;
  current.append(el('p','muted','一般聊天搜尋：'+(profile?.chat_search_enabled?'已另行授權':'未授權')+'。核准不代表搜尋實測通過；任務草稿與主代理規劃停用工具。'));
  clearButton=button('移除搜尋核准',()=>{
   if(busy)return;
   const profileId=select.value;
   current.replaceChildren(el('p','notice','移除後，此助理的新搜尋工作將無法使用這些工具。連線版本會更新，舊 Plan 與排程綁定將失效，需要重新確認；不會刪除既有成果。'));
   const cancel=button('保留核准',currentPolicy),remove=button('確認移除核准',async()=>{
    if(busy)return;setBusy(true);cancel.disabled=true;output.replaceChildren();
    try{await call('search_policy_clear',{profile_id:profileId});savedPolicies.set(profileId,[]);await refresh();if(active()){currentPolicy();output.replaceChildren(el('p','notice','已移除搜尋核准。舊 Plan 需重建；未派發模型或搜尋。'));}}
    catch(error){if(active()){output.replaceChildren(el('p','error',error.message||'移除失敗，設定未確認變更。請重新檢查。'));cancel.disabled=false;}}
    finally{if(active())setBusy(false);}
   });
   const actions=el('div','card-actions');actions.append(cancel,remove);current.append(actions);cancel.focus();
  });current.append(clearButton);clearButton.disabled=busy;
 }
 function policyChoices(result,profileId){
  const candidates=Array.isArray(result.search_candidates)?result.search_candidates:[],unsupported=Array.isArray(result.unsupported_tools)?result.unsupported_tools:[];
  if(unsupported.length){const list=el('ul');unsupported.forEach(tool=>list.append(el('li','plain-text',(tool.name||'未提供名稱')+'：'+(tool.reason||'目前不支援此工具定義'))));output.append(el('h4','','目前不可核准的工具'),list);}
  if(!candidates.length||typeof result.policy_token!=='string'||!result.policy_token){output.append(el('p','notice','目前沒有可選擇的搜尋工具。請組織確認工具宣告及參數格式；不會自動執行其他工具。'));return;}
  output.append(el('h4','','選擇組織核准的唯讀搜尋'),el('p','notice','以下僅表示參數格式可驗證，不代表工具用途或能力已經核准。只勾選你確認是唯讀搜尋的工具；不確定時請關閉，向組織確認後再設定。'));
  const choices=[];
  for(const tool of candidates){
   const box=el('div','field'),label=el('label','check-field'),check=el('input');check.type='checkbox';check.dataset.searchTool=tool.name;
   label.append(check,document.createTextNode(tool.name));box.append(label);
   if(typeof tool.description==='string')box.append(el('p','plain-text',tool.description));
   const details=el('details');details.append(el('summary','','查看宣告參數（唯讀）'),el('pre','plain-text',plain(tool.parameters||{})));box.append(details);output.append(box);choices.push([tool.name,check]);
  }
  const label=el('label','check-field'),consent=el('input');consent.type='checkbox';consent.dataset.searchConsent='true';label.append(consent,document.createTextNode('我確認所選工具是組織核准的唯讀搜尋，允許在確認的搜尋工作中執行'));output.append(label);
  const chatLabel=el('label','check-field'),chat=el('input');chat.type='checkbox';chat.dataset.chatSearchConsent='true';chatLabel.append(chat,document.createTextNode('另允許一般聊天自動使用所選搜尋工具（任務草稿與規劃仍停用工具）'));output.append(chatLabel);
  output.append(el('p','muted','保存會更新助理連線版本、撤銷既有分工能力驗證，舊 Plan 需重建。保存本身不會呼叫模型、搜尋或啟用排程；此預覽十分鐘內有效。'));
  const save=button('核准所選搜尋工具',async()=>{
   if(busy)return;const names=choices.filter(([,check])=>check.checked).map(([name])=>name);
   if(!consent.checked||!names.length)throw Error('請選擇搜尋工具並確認唯讀搜尋授權。');
   setBusy(true);consent.disabled=true;chat.disabled=true;choices.forEach(([,check])=>check.disabled=true);
   try{
    const saved=await call('search_policy_save',{token:result.policy_token,names,consent:true,chat_enabled:chat.checked});savedPolicies.set(profileId,saved.names||names);await refresh();if(!active())return;
    currentPolicy();output.replaceChildren(el('p','notice','已保存搜尋核准：'+(saved.names||names).join('、')+'。搜尋仍尚未實測，舊 Plan 需重建。'),el('p','muted','下一步試跑財經日報，核對來源與日期，再決定是否建立每日工作。'),button('試跑財經日報',()=>showBriefing(),'button primary'));
   }catch(error){if(active()){consent.disabled=false;chat.disabled=false;choices.forEach(([,check])=>check.disabled=false);notify(error.message||'核准保存失敗，請重新檢查後重試。',true);}}
   finally{if(active())setBusy(false);}
  },'button primary');save.dataset.searchSave='true';save.disabled=true;
  const update=()=>save.disabled=!consent.checked||!choices.some(([,check])=>check.checked);consent.addEventListener('change',update);choices.forEach(([,check])=>check.addEventListener('change',update));
  const actions=el('div','card-actions');actions.append(save);output.append(actions);
 }
 const run=button('檢查搜尋助理連線',async()=>{
  if(busy)return;
  const profileId=select.value;
  if(!(S.state?.profiles||[]).some(p=>p.id===profileId&&p.id!=='demo'&&p.enabled!==false))throw Error('這位助理已停用或不存在，請關閉後重新檢查。');
  setBusy(true);output.replaceChildren(el('p','muted','正在讀取AI 助理設定，可能需要約 30 秒。關閉視窗只停止顯示，不能保證中止遠端請求。'));
  try{
   const result=await call('company_probe',{profile_id:profileId});
   if(S.closing||version!==S.modalVersion||!$('modal').open)return;
   if(result?.connection!=='passed'||!Array.isArray(result.tools))throw Error('連線檢查結果格式不符，請更新程式後重試。');
   output.replaceChildren(el('p','plain-text',result.message||'已讀取AI 助理設定。'),el('p','muted','連線讀取通過 · 搜尋與日報尚未實測'));
   const list=el('ul');
   for(const tool of result.tools){const type=typeof tool.type==='string'?tool.type:'未提供類型',name=typeof tool.name==='string'?tool.name:'';list.append(el('li','plain-text',type+(name?' · '+name:'')));}
   output.append(el('h4','','AI 助理宣告的工具'),result.tools.length?list:el('p','muted','未宣告工具；這不代表搜尋能力已驗證。'));
   output.append(el('p','notice','檢查成功不代表搜尋或日報成功。只有另行核准的搜尋工具可在已確認工作中執行；工具名稱不代表已核准使用。'));
   policyChoices(result,profileId);
  }catch(error){
   if(S.closing||version!==S.modalVersion||!$('modal').open)return;
   output.replaceChildren(el('p','error',error.message||'工具宣告檢查未完成。'),el('p','notice','工具宣告讀取失敗不代表一般聊天不可用；請從助理卡片另行試用一般聊天。'));
  }finally{if(active())setBusy(false);}
 });
 const tools=el('div','card-actions');tools.append(run);section.append(tools,output);
 select.addEventListener('change',()=>{output.replaceChildren();currentPolicy();});currentPolicy();
}
async function showCompanyReadiness(profileId=null){
 const body=modal('連線啟用檢查'),version=S.modalVersion;
 const close=button('關閉',closeModal);modalButtons(close);close.focus();
 body.append(el('p','notice','開啟此頁只檢查已保存的本機設定，不啟用任務。下方「檢查搜尋助理連線」需另行點擊，才會連線讀取AI 助理設定。'));
 if(String(S.state?.mode).toLowerCase().includes('groq')||S.state?.settings?.editable===false){
  body.append(el('p','plain-text','目前是外部試用工作區，無法在這裡檢查組織連線。請以正式 start-app.bat 入口啟動，再開啟此檢查。'));return;
 }
 companyProbeSection(body,version,profileId);
 const pending=el('p','muted','正在檢查本機設定…');pending.setAttribute('role','status');body.append(pending);
 try{
  const result=await call('company_readiness');
  if(S.closing||version!==S.modalVersion||!$('modal').open)return;
  if(result?.scope!=='local_only'||!Array.isArray(result.checks))throw Error('本機檢查結果格式不符，請更新程式後重試。');
  pending.remove();
  body.append(el('h3','',result.ready_for_company_test?'本機設定已備妥，可以安排環境試跑':'還有設定需要完成'));
  const statusLabels={ready:'本機已備妥',missing:'待補齊',not_tested:'尚未實測'};
  const destinations={settings:'前往設定',team:'前往助理團隊',plan:'開啟規劃工作'};
  for(const check of result.checks){
   const row=el('div','list-row'),info=el('div','grow');
   info.append(el('strong','',check.label||'檢查項目'),el('p','plain-text',check.detail||''));
   const state=Object.hasOwn(statusLabels,check.state)?check.state:'not_tested';
   row.append(info,el('span','pill'+(state==='missing'?' warning':''),statusLabels[state]));
   if(Object.hasOwn(destinations,check.action))row.append(button(destinations[check.action],()=>readinessDestination(check.action)));
   body.append(row);
  }
  body.append(el('h3','','下一步'),el('p','plain-text',result.next_step||'請先補齊設定，再由組織完成實際試跑。'),el('p','notice','儲存設定或核准搜尋不代表實測通過。助理 API、角色能力與資料查詢仍須實測；只有核准搜尋可在確認的工作中執行，這份檢查不代表已可查詢組織資料。'));
  modalButtons(button('關閉',closeModal),button('重新檢查',showCompanyReadiness));
 }catch(error){
  if(S.closing||version!==S.modalVersion||!$('modal').open)return;
  pending.remove();body.append(el('p','error',error.message||'本機檢查未完成，請重試。'));
  modalButtons(button('關閉',closeModal),button('重試檢查',showCompanyReadiness));
 }
}
function renderNav(){const nav=$('navigation');[['dialogue','chat'],['memories','document'],['skills','spark'],['chat','workflow'],['team','team'],['todo','todo'],['schedule','clock'],['activity','activity'],['notice','bell'],['query','database'],['issue','issue']].forEach(([page,i])=>{const b=button('',()=>navigate(page),'nav-item');b.dataset.page=page;b.title=labels[page];b.append(icon(i),el('span','nav-label',labels[page]));if(page==='notice'){const count=el('span','badge');count.hidden=true;b.append(count);}nav.append(b);});document.querySelectorAll('.sidebar-bottom [data-page]').forEach(b=>b.addEventListener('click',()=>navigate(b.dataset.page)));}
function navigate(page){if(page==='chat')delete S.signatures.recent;S.page=page;document.body.dataset.page=page;document.dispatchEvent(new CustomEvent('qa-sidebar-mode',{detail:page}));document.querySelectorAll('[data-page]').forEach(b=>b.classList.toggle('active',b.dataset.page===page));$('page-title').textContent=labels[page];$('chat-page').hidden=page!=='chat';$('dialogue-page').hidden=page!=='dialogue';$('orders-page').hidden=page!=='orders';$('skills-page').hidden=page!=='skills';$('memories-page').hidden=page!=='memories';$('content-page').hidden=['chat','dialogue','orders','skills','memories'].includes(page);if(page==='memories')document.dispatchEvent(new Event('qa-memories-enter'));else if(page==='skills')document.dispatchEvent(new Event('qa-skills-enter'));else if(page==='orders')document.dispatchEvent(new Event('qa-orders-enter'));else if(page==='dialogue'){document.dispatchEvent(new Event('qa-dialogue-enter'));$('connection').replaceChildren(el('span','status-dot'),document.createTextNode(document.body.dataset.dialogueMode||'示範模式 · 離線'));}else if(page!=='chat')renderPage(true);}
function applyPreferences(data){document.body.dataset.theme=data.theme||'dark';document.body.dataset.colorStyle=data.color_style||'ocean';syncAppearanceControls(data);const brand=document.querySelector('.brand img');brand.src=data.theme==='light'?brand.dataset.light:brand.dataset.dark;document.querySelector('.sidebar').classList.toggle('collapsed',!!data.sidebar_collapsed);$('collapse').title=data.sidebar_collapsed?'展開側欄':'收合側欄';$('collapse').setAttribute('aria-label',$('collapse').title);}
function paintState(data){S.state=data;applyPreferences(data);$('identity').textContent=data.identity?.mode==='company'?'已登入 · '+data.identity.name:data.identity?.mode==='demo_login'?'離線展示已登入 · 非 AD':'本機身分 · 未驗證 AD';$('logout').hidden=!['company','demo_login'].includes(data.identity?.mode);$('app-version').textContent='QA agent · '+(data.version||'');$('connection').classList.add('connected');$('connection').replaceChildren(el('span','status-dot'),document.createTextNode(S.page==='dialogue'?(document.body.dataset.dialogueMode||'示範模式 · 離線'):data.mode||'已連接桌面服務'));$('connection-error').hidden=true;renderUnread(data);renderRecent(data);renderProfiles(data);renderChat(data);if(S.page!=='chat')renderPage();}
async function refresh(){if(!S.ready||S.polling||S.closing)return;const requestedCid=S.cid,generation=S.viewGeneration;S.polling=true;try{const data=await call('state',{cid:requestedCid});if(S.closing||generation!==S.viewGeneration||requestedCid!==S.cid)return;const cid=typeof data.conversation==='string'?data.conversation:data.conversation?.id;if(requestedCid&&cid!==requestedCid)return;if(cid&&cid!==S.cid){S.cid=cid;restoreDraft(data.draft);S.signatures={};}paintState(data);}catch(e){if(generation===S.viewGeneration&&!S.closing){$('connection-error').hidden=false;$('connection-error').textContent=e.message;}}finally{S.polling=false;}}
function restoreDraft(draft){S.editVersion++;$('message-input').value=draft?.text||'';S.purpose=({'一般對話':'chat','整理重點':'summarize','改寫文字':'rewrite'})[draft?.purpose]||'chat';S.planned=!!draft?.planned;S.dirty=false;resizeInput();$('draft-status').textContent=draft?.had_attachment?'請重新選取上次的附件':'草稿保存在本機';}
function renderRecent(data){if(S.page!=='chat')return;if(!changed('recent',[data.conversations,S.cid]))return;const root=$('recent-chats');root.replaceChildren();(data.conversations||[]).forEach(c=>{const b=button(c.title||'新對話',()=>switchChat(c.id),'recent-item'+(c.id===S.cid?' active':''));b.title=c.title||'新對話';root.append(b);});}
function renderProfiles(data){if(!changed('profiles',[data.profiles,data.planners,S.mode,data.conversation?.binding]))return;const sel=$('assistant-select'),old=sel.value;sel.replaceChildren();const list=S.mode==='workflow'?data.planners:data.profiles;const available=(list||[]).filter(p=>p.enabled!==false);available.forEach(p=>{const o=el('option','',p.name);o.value=p.id;sel.append(o);});const bound=data.conversation?.binding?.profile_id;if(S.mode==='chat'&&bound&&!available.some(p=>p.id===bound)){const p=(data.profiles||[]).find(p=>p.id===bound);const o=el('option','',(p?.name||'來源助理')+' · 舊版本／停用');o.value=bound;sel.append(o);}if(!sel.options.length){const o=el('option','','尚無可用助理');o.value='';sel.append(o);}sel.value=S.mode==='chat'&&bound?bound:available.some(p=>p.id===old)?old:available[0]?.id||'';if(S.mode==='chat'&&!data.conversation?.binding){const unknown=el('option','','舊對話 · 助理未記錄');unknown.value='';sel.append(unknown);sel.value='';}updateAssistantNote();}
function updateAssistantNote(){const p=(S.state?.profiles||[]).find(p=>p.id===$('assistant-select').value),binding=S.state?.conversation?.binding;const old=S.mode==='chat'&&(!binding||!p||p.enabled===false||p.revision!==binding.revision);$('assistant-note').textContent=old?'此對話為舊版本或已停用，僅供閱讀；請另開對話':p?.notes||'用途尚未填寫';if(old){const option=$('assistant-select').selectedOptions[0];if(option&&!option.textContent.includes('唯讀'))option.textContent+=' · 唯讀';}}
function renderChat(data){const messages=data.messages||[];const scroll=$('chat-scroll'),nearBottom=scroll.scrollHeight-scroll.scrollTop-scroll.clientHeight<100;messages.forEach(m=>{const id='message-'+m.id;let node=$(id);if(!node){node=el('article','message '+(m.role==='user'?'user':'assistant'));node.id=id;node.append(el('div','message-header'),el('div','message-body'));$('messages').append(node);}if(!changed(id,m))return;node.children[0].replaceChildren(el('span','',m.role==='user'?'你':'QA agent'),el('time','',time(m.created_at)));trustedMarkdown(node.children[1],m.html,m.content||m.text);});const valid=new Set(messages.map(m=>'message-'+m.id));[...$('messages').children].forEach(n=>{if(!valid.has(n.id))n.remove();});$('welcome').hidden=messages.length>0||(data.workflows||[]).length>0||(data.actions||[]).length>0;if(!($('workflow-panel').contains(document.activeElement)&&document.activeElement.matches('input,select,textarea'))&&changed('workflow',[data.workflows,data.actions,data.plans]))renderWorkflows(data);if(nearBottom)scroll.scrollTop=scroll.scrollHeight;if(changed('attachment',data.attachment)){const a=$('attachment');a.replaceChildren();a.hidden=!data.attachment;if(data.attachment){a.append(el('span','',data.attachment.name||'已附加檔案'),button('移除',()=>action('attachment_remove',{cid:S.cid}),'button quiet'));}}const task=(data.tasks||[]).find(t=>t.conversation_id===S.cid&&['queued','running'].includes(t.state));$('cancel-work').hidden=!task;$('cancel-work').dataset.task=task?.id||'';}
async function switchChat(cid){if(S.closing)return;const generation=++S.viewGeneration;await saveDraft();if(S.closing||generation!==S.viewGeneration)return;const data=await call('state',{cid});if(S.closing||generation!==S.viewGeneration)return;S.cid=cid;restoreDraft(data.draft);S.signatures={};navigate('chat');paintState(data);}
async function newChat(){if(S.closing)return;const profileId=$('assistant-select').value||undefined,generation=++S.viewGeneration;await saveDraft();if(S.closing||generation!==S.viewGeneration)return;const result=await call('new_chat',{profile_id:profileId});if(S.closing||generation!==S.viewGeneration)return;const cid=typeof result==='string'?result:result.cid||result.id;const data=await call('state',{cid});if(S.closing||generation!==S.viewGeneration)return;S.cid=cid;restoreDraft(data.draft);S.signatures={};navigate('chat');paintState(data);}
function resizeInput(){const t=$('message-input');t.style.height='auto';t.style.height=Math.min(160,Math.max(65,t.scrollHeight))+'px';}
async function saveDraft(){clearTimeout(S.saveTimer);if(!S.dirty||!S.cid||!S.ready||S.closing)return;const cid=S.cid,text=$('message-input').value,purpose=S.purpose,planned=S.planned,version=S.editVersion,seq=++S.seq;try{const result=await call('save_draft',{cid,text,purpose,planned,seq});if(!result?.ignored&&cid===S.cid&&version===S.editVersion&&text===$('message-input').value){S.dirty=false;$('draft-status').textContent='草稿已保存於本機';}}catch(e){if(cid===S.cid)$('draft-status').textContent='保存失敗，點擊此處重試';throw e;}}
async function send(){
 if(S.sending||S.composing||S.closing)return;
 const context={cid:S.cid,text:$('message-input').value,mode:S.mode,purpose:S.purpose,planned:S.planned,editVersion:S.editVersion,plannerId:$('assistant-select').value,generation:S.viewGeneration};
 if(!context.text.trim())return;
 const w=(S.state.workflows||[]).find(w=>['draft','ready'].includes(w.state));context.wid=w?.id;context.revision=w?.revision;
 const example=sampleQuery(),sample=context.mode==='chat'&&context.text===example.text&&(S.state.catalog||[]).some(q=>q.id===example.query_id);
 const sameDraft=()=>S.cid===context.cid&&S.editVersion===context.editVersion&&$('message-input').value===context.text;
 S.sending=true;$('send').disabled=true;clearTimeout(S.saveTimer);
 try{
  await saveDraft();if(S.closing)return;
  if(S.cid!==context.cid||S.editVersion!==context.editVersion||S.viewGeneration!==context.generation)throw Error('對話或草稿已變動，尚未送出；請核對目前內容後再送出。');
  const seq=++S.seq;
  if(sample){const preview=await call('query_preview',{cid:context.cid,query_id:example.query_id,parameters:example.parameters});if(preview.ready===false)throw Error(preview.error||'查詢條件需要修正。');if(!S.closing&&sameDraft()){S.editVersion++;$('message-input').value='';S.dirty=true;S.editVersion++;await saveDraft();}if(!S.closing&&S.cid===context.cid&&S.viewGeneration===context.generation)await previewAction(preview);}
  else if(context.mode==='chat'&&context.purpose==='chat'&&!context.planned&&explicitIntent(context.text))await call('intent_prepare',{cid:context.cid,text:context.text,seq,kind:explicitIntent(context.text)});
  else if(context.mode==='workflow')await call('workflow_discuss',{cid:context.cid,wid:context.wid,revision:context.revision,text:context.text,seq,planner_id:context.plannerId});
  else await call('send',{cid:context.cid,text:context.text,purpose:context.purpose,planned:context.planned,seq,request_id:rid()});
  if(!S.closing&&sameDraft()){S.editVersion++;$('message-input').value='';S.dirty=false;resizeInput();}
  await refresh();
 }catch(e){notify(e.message,true);}finally{S.sending=false;if(!S.closing)$('send').disabled=false;}
}
function renderWorkflows(data){const panel=$('workflow-panel');panel.replaceChildren();(data.workflows||[]).forEach(w=>{const card=tone(el('div','workflow-card'),w.task?.state||w.state);const top=el('div','card-top');top.append(el('h3','',w.goal||'規劃工作'),badge(w.task?.state||w.state));card.append(top);if(w.error)card.append(el('p','error',w.error));const discussion=w.discussion||[];const latest=discussion.filter(m=>m.role==='assistant').slice(-1)[0];if(latest)card.append(el('div','plain-text',latest.content));if(discussion.length){const history=el('details');history.append(el('summary','','需求討論'));discussion.forEach(m=>history.append(el('p','plain-text',(m.role==='user'?'你：':'規劃助理：')+m.content)));card.append(history);}renderQuestions(card,w.questions);(w.steps||[]).forEach((step,i)=>{const r=el('div','workflow-step');const c=el('div');c.append(el('strong','',step.title),el('p','',step.instruction||'核准查詢'));r.append(el('span','step-number',i+1),c);const actual=(w.steps_status||[]).find(s=>s.step_id===step.id);if(actual){tone(r,actual.state);r.append(badge(actual.state));}if(step.role)c.append(el('span','team-role',roleLabels[step.role]||step.role));card.append(r);});const tools=el('div','card-actions');if(w.state==='ready'){tools.append(button('檢視並確認',()=>previewWorkflow(w),'button primary'),button('修改步驟',()=>editWorkflow(w)));}if(w.state==='planning'||['queued','running'].includes(w.task?.state))tools.append(button('取消工作',()=>action('workflow_cancel',{wid:w.id})));if(w.task&&['succeeded','failed','cancelled'].includes(w.task.state)){tools.append(button('查看成果',()=>showOutcome(w.task.id),'button primary'));if(w.recovery?.eligible){tools.append(button('檢查遠端狀態',async()=>{const r=await call('workflow_inspect',{task_id:w.task.id});notify(r.message);}),button('繼續工作',()=>confirm('恢復工作','只接續核准版本；結果不明時停止，不自動重送。','確認繼續',()=>action('workflow_resume',{task_id:w.task.id}))),button('放棄恢復',()=>confirm('放棄恢復','保留已有成果，將此工作標示取消。','放棄恢復',()=>action('workflow_abandon',{task_id:w.task.id}))));}else if(w.task.state==='failed')tools.append(button('重試未完成步驟',()=>confirm('重試工作','只重試尚未完成的步驟，已取得資料會保留。','確認重試',()=>action('workflow_retry',{task_id:w.task.id,request_id:rid()}))));if(w.task.state==='succeeded')tools.append(button('設為自動工作',()=>scheduleWorkflow(w)));}card.append(tools);panel.append(card);});(data.actions||[]).filter(a=>a.state!=='cancelled').forEach(a=>panel.append(actionCard(a)));(data.plans||[]).filter(p=>p.conversation_id===S.cid&&['draft','ready','pending'].includes(p.state)).forEach(p=>{const card=tone(el('div','workflow-card'),'ready');card.append(badge('ready'),el('h3','','待確認計畫'),button('檢視計畫',()=>previewPlan(p)));panel.append(card);});}
async function previewWorkflow(w){const p=await call('workflow_preview',{wid:w.id,revision:w.revision});const body=modal('確認分工與資料範圍');body.append(tone(el('p','notice','尚未執行。確認後，只有核准步驟的指定資料會傳給對應助理。'),'ready'));(p.search_tools||[]).forEach(s=>body.append(el('p','notice',s.step_id+' · '+(s.tools.length?'本步可呼叫核准搜尋：'+s.tools.join('、'):'本步沒有核准搜尋工具，僅取得助理文字。'))));body.append(el('div','plain-text',plain(p.steps)));if(p.error)body.append(el('p','error',p.error));modalButtons(button('返回修改',closeModal),...(p.ready===false?[]:[button('確認執行',async()=>{await action('workflow_confirm',{wid:w.id,revision:p.revision});closeModal();},'button primary')]));}
function editWorkflow(w){const body=modal('修改分工步驟');body.append(el('p','notice','修改會使舊批准失效。依序保留合法步驟與指定輸入。'));const input=field(body,'步驟 JSON',JSON.stringify(w.steps,null,2),'textarea');input.rows=15;modalButtons(button('取消',closeModal),button('保存修改',async()=>{await action('workflow_update',{wid:w.id,revision:w.revision,steps:JSON.parse(input.value)});closeModal();},'button primary'));}
async function previewAction(a){const automated=['schedule','report'].includes(a.kind),report=a.kind==='report';const body=modal(automated?'確認啟用自動工作':'確認查詢');body.append(tone(el('p','notice',report?'尚未執行。每次只將核准合計資料傳給試用助理整理日報，應用需保持開啟。':'尚未執行。資料只留在本機，不自動交給助理。'),'ready'),el('div','plain-text',describeSpec(a.spec||{})));let consent;if(report){const label=el('label','check-field');consent=el('input');consent.type='checkbox';label.append(consent,document.createTextNode('我授權每次執行時持續傳送上述合計資料給指定助理。'));body.append(label);}if(a.error)body.append(el('p','error',a.error));modalButtons(button('返回修改',()=>editAction(a)),...(a.ready===false?[]:[button(automated?'確認啟用':'確認查詢',async()=>{if(report&&!consent.checked)throw Error('請先確認持續傳送授權。');await action('action_confirm',{action_id:a.id,revision:a.revision,consent:report&&consent.checked});closeModal();},'button primary')]));}
function editAction(a){const body=modal('補齊工作條件');const choices=(S.state.catalog||[]).map(q=>({value:q.id,label:q.name}));const query=field(body,'核准查詢',a.spec?.query_id||choices[0]?.value,'text',choices);const params=el('div');body.append(params);let fields={};function form(){params.replaceChildren();fields={};const q=(S.state.catalog||[]).find(q=>q.id===query.value);Object.entries(q?.parameters||{}).forEach(([k,s])=>{let options=s.options;if(s.type==='boolean')options=[{value:'true',label:'是'},{value:'false',label:'否'}];fields[k]=[field(params,s.label||k,a.spec?.parameters?.[k]??s.default??'',s.type==='date'?'date':s.type==='integer'?'number':'text',options),s];});}query.addEventListener('change',form);form();const automated=['schedule','report'].includes(a.kind);const schedule=automated?scheduleFields(body,a.spec||{}):null;const dates=automated?field(body,'資料範圍',a.spec?.date_mode||'literal','text',[{value:'literal',label:'固定日期'},{value:'previous_day',label:'前一日（需模板支援）'}]):null;modalButtons(button('取消',closeModal),button('預覽',async()=>{const parameters={};for(const[k,[f,s]]of Object.entries(fields))parameters[k]=s.type==='integer'?Number(f.value):s.type==='boolean'?f.value==='true':f.value;const spec={...a.spec,query_id:query.value,parameters,...(schedule?schedule():{}),...(dates?{date_mode:dates.value}:{})};const updated=await call('action_update',{action_id:a.id,revision:a.revision,spec});const p=await call('action_preview',{action_id:a.id,revision:updated.revision});await refresh();await previewAction(p);},'button primary'));}
async function previewPlan(p){const value=await call('plan_preview',{plan_id:p.id});const body=modal('確認計畫');body.append(tone(el('p','notice','尚未執行，請核對目標與資料範圍。'),'ready'),el('div','plain-text',plain(value)));modalButtons(button('取消計畫',async()=>{await action('plan_cancel',{plan_id:p.id});closeModal();}),button('確認送出',async()=>{await action('plan_confirm',{plan_id:p.id,revision:value.revision||p.revision,request_id:rid()});closeModal();},'button primary'));}
function scheduleFields(body,defaults={}){const name=field(body,'名稱',defaults.name||'自動工作');const frequency=field(body,'頻率',defaults.frequency||'daily','text',[{value:'daily',label:'每日'},{value:'weekly',label:'每週'}]);const time=field(body,'台北時間',defaults.time_hhmm||'08:00','time');const weekday=field(body,'每週執行日',String(defaults.weekday??0),'text',['一','二','三','四','五','六','日'].map((v,i)=>({value:String(i),label:'星期'+v})));return()=>({name:name.value,frequency:frequency.value,time_hhmm:time.value,weekday:Number(weekday.value)});}
function scheduleWorkflow(w){const body=modal('設定自動工作');body.append(el('p','notice','應用程式需保持開啟。每次依相同核准版本，持續傳送指定資料給助理。'));const values=scheduleFields(body);const label=el('label','check-field');const check=el('input');check.type='checkbox';label.append(check,document.createTextNode('我授權此流程每次執行時，持續傳送上述指定資料。'));body.append(label);modalButtons(button('取消',closeModal),button('確認啟用',async()=>{if(!check.checked)throw Error('請先確認持續傳送授權。');await action('workflow_schedule',{wid:w.id,revision:w.revision,...values(),consent:true});closeModal();},'button primary'));}
async function showOutcome(tid){const data=await call('outcome',{task_id:tid});const body=modal('工作成果');body.append(badge(data.task.state),el('p','muted',(data.review||'')+' · AI 整理，請核對來源'));if(data.partial)body.append(tone(el('p','notice','未完成：以下只包含已取得的部分成果。'),'needs_attention'));if(data.task.error)body.append(el('p','error',data.task.error));const text=el('div','message-body');trustedMarkdown(text,data.text_html,data.text);body.append(text);const details=el('details');details.append(el('summary','','與上次比較'),comparisonView(data.comparison));body.append(details);const steps=el('details');steps.append(el('summary','','分工紀錄'));(data.steps||[]).forEach(s=>{steps.append(el('p','',s.step_id+' · '+(states[s.state]||s.state)),el('div','plain-text',s.output?.text||s.error||''));if(s.output?.query_result)steps.append(button('查看原始表格',()=>showTable(tid,s.step_id)));});body.append(steps);if(data.can_rate){const box=el('div','card');box.append(el('h3','','這份成果有幫助嗎？'));const note=field(box,'選填備註（最多 2,000 字）',data.feedback?.note||'','textarea');note.maxLength=2000;const status=el('p','muted',data.feedback?'已保存評價':'尚未評價');const tools=el('div','card-actions');[['可採用','usable'],['需修改','revise'],['無幫助','unhelpful']].forEach(([name,rating])=>tools.append(button(name,async()=>{await call('feedback',{task_id:tid,rating,note:note.value});status.textContent='已保存：'+name;})));tools.append(button('清除',async()=>{await call('feedback_clear',{task_id:tid});note.value='';status.textContent='已清除評價';}));box.append(tools,status);body.append(box);}modalButtons(button('關閉',closeModal),button('複製成果',()=>copy(data.text||'')));}
async function copy(text){await navigator.clipboard.writeText(text);notify('已複製');}
async function transferDialog(source){const body=modal('選擇接收助理');body.append(el('p','notice','只傳送選定內容與整理需求，另開新對話。下一步會顯示完整資料供你確認。'));const options=(S.state.profiles||[]).filter(p=>p.enabled!==false).map(p=>({value:p.id,label:p.name}));if(!options.length){body.append(el('p','error','尚無可用助理。'));return;}const target=field(body,'目的助理',options[0].value,'text',options),prompt=field(body,'整理需求','請依來源整理重點，明示限制，不補造未提供的資訊。','textarea');modalButtons(button('取消',closeModal),button('預覽傳送內容',async()=>{const p=await call('transfer_preview',{...source,profile_id:target.value,prompt:prompt.value});const view=modal('確認資料轉交');view.append(el('p','notice','目的助理：'+p.target+'\nAssistant ID：'+p.assistant_id),el('p','plain-text','來源：'+plain(p.source)),el('div','plain-text',p.text));modalButtons(button('取消',closeModal),button('確認送出',async()=>{const result=await call('transfer_confirm',{token:p.token});closeModal();await switchChat(result.cid);},'button primary'));},'button primary'));}
async function scheduleQuery(tid){const task=await call('task_result',{task_id:tid});const body=modal('設定自動查詢');body.append(el('p','notice','排程只查詢及通知，不自動將資料交給助理。應用程式需保持開啟。'));const values=scheduleFields(body);const template=(S.state.catalog||[]).find(q=>q.id===task.payload?.query_id);const dates=[{value:'literal',label:'沿用固定條件'}];if(template?.date_range)dates.push({value:'previous_day',label:'每次查前一日'});const dateMode=field(body,'資料範圍','literal','text',dates);modalButtons(button('取消',closeModal),button('預覽自動工作',async()=>{const p=await call('query_schedule',{cid:S.cid,source_task_id:tid,...values(),date_mode:dateMode.value});const view=modal('確認啟用自動查詢');view.append(el('div','plain-text',plain(p.spec||p)));if(p.error)view.append(el('p','error',p.error));modalButtons(button('取消',closeModal),...(p.ready===false?[]:[button('確認啟用',async()=>{await action('schedule_confirm',{token:p.token});closeModal();notify('已啟用，尚未立即執行');},'button primary')]));},'button primary'));}
async function showTable(tid,stepId){let raw;if(stepId){const o=await call('outcome',{task_id:tid});raw=o.steps.find(s=>s.step_id===stepId)?.output?.query_result;}else{const d=await call('task_result',{task_id:tid});raw=d.result||d.task?.result||d;}raw=raw?.query_result||raw;if(!raw?.columns||!raw?.rows)throw Error('此工作沒有可顯示的表格。');const body=modal('查詢結果 · 固定快照');if(raw.summary){body.append(el('h3','','日報整理'),el('div','plain-text',raw.summary));}if(raw.summary_error){body.append(el('p','error',raw.summary_error),el('p','notice','整理未完成，以下查詢資料仍可查看。'));}body.append(el('p','muted','資料時間：'+time(raw.fetched_at_utc)+' · '+raw.rows.length+' 列'),el('p','plain-text',Object.entries(raw.parameters||{}).map(([k,v])=>((S.state.catalog||[]).flatMap(q=>Object.entries(q.parameters||{})).find(([key])=>key===k)?.[1]?.label||k)+'：'+String(v)).join(' · ')));let page=0;const selected=new Set();const wrap=el('div','table-wrap');const controls=el('div','toolbar');body.append(controls,wrap);function draw(){wrap.replaceChildren();controls.replaceChildren();const table=el('table','data-table');const head=el('tr');head.append(el('th','','選取'));raw.columns.forEach(c=>head.append(el('th','',c.label||c.name)));table.append(head);raw.rows.slice(page*100,page*100+100).forEach((r,i)=>{const index=page*100+i,tr=el('tr');const check=el('input');check.type='checkbox';check.checked=selected.has(index);check.addEventListener('change',()=>{check.checked?selected.add(index):selected.delete(index);tr.classList.toggle('selected',check.checked);});const cell=el('td');cell.append(check);tr.append(cell);raw.columns.forEach((c,j)=>tr.append(el('td','',Array.isArray(r)?r[j]:r[c.name])));table.append(tr);});wrap.append(table);controls.append(button('上一頁',()=>{page=Math.max(0,page-1);draw();}),el('span','muted',(page+1)+' / '+Math.max(1,Math.ceil(raw.rows.length/100))),button('下一頁',()=>{page=Math.min(Math.max(0,Math.ceil(raw.rows.length/100)-1),page+1);draw();}));}draw();modalButtons(button('複製選取列',()=>{if(!selected.size)throw Error('請先選取資料列。');return call('table_export',{task_id:tid,step_id:stepId,format:'tsv',selected:[...selected]});}),button('複製全部',()=>call('table_export',{task_id:tid,step_id:stepId,format:'tsv'})),button('匯出 CSV',()=>call('table_export',{task_id:tid,step_id:stepId,format:'csv'})));$('modal-actions').append(button('交給助理整理',()=>transferDialog({task_id:tid,step_id:stepId,...(selected.size?{selected:[...selected]}:{})})));if(!stepId)$('modal-actions').append(button('每天自動查',()=>scheduleQuery(tid)));}
function renderPage(force=false){if(!S.state)return;const data=S.state,page=S.page;if(!force&&$('page-content').contains(document.activeElement)&&document.activeElement.matches('input,select,textarea'))return;const pageChanged=changed('page-'+page,[data[({team:'profiles',todo:'todos',schedule:'schedules',activity:'tasks',notice:'notifications',issue:'issues',query:'catalog',settings:'settings'})[page]],page,page==='notice'?data.tasks:page==='todo'?[data.work_inbox,data.conversations,taipeiToday()]:null]);if(!force&&!pageChanged)return;const saved={};if(!force)$('page-content').querySelectorAll('input,textarea,select').forEach((e,i)=>saved[i]={value:e.value,checked:e.checked});const scroll=$('content-page').scrollTop;$('section-title').textContent=labels[page];$('section-description').textContent=descriptions[page]||'';$('page-actions').replaceChildren();const root=$('page-content');root.replaceChildren();({team:renderTeam,todo:renderTodos,schedule:renderSchedules,activity:renderActivity,notice:renderNotices,query:renderQuery,settings:renderSettings,help:renderHelp,issue:renderIssues}[page]||(()=>{}))(root,data);if(!force){root.querySelectorAll('input,textarea,select').forEach((e,i)=>{if(saved[i]){e.value=saved[i].value;e.checked=saved[i].checked;e.dispatchEvent(new Event('input'));}});$('content-page').scrollTop=scroll;}}
function renderTeam(root,data){$('page-actions').append(button('連線啟用檢查',showCompanyReadiness));$('page-actions').append(button('新增助理',()=>editProfile(),'button primary'));const grid=el('div','card-grid');root.append(grid);(data.profiles||[]).forEach(p=>{const c=el('div','card team-card'),top=el('div','card-top');top.append(el('span','agent-symbol','✦'),badge(p.id==='demo'?'本機示範':p.enabled===false?'停用':p.workflow?.verified?'已驗證':'角色待驗證'));c.append(top,el('h3','',p.name),el('p','',p.notes||'用途尚未填寫'),el('p','muted','ID：'+p.assistant_id));if(p.id!=='demo')c.append(el('p','muted',(p.credential_mode==='individual'?'個別金鑰':'共用金鑰')+' · 一般聊天搜尋：'+(p.chat_search_enabled&&p.search_policy?.tools?.length?'已核准':'未核准')));(p.workflow?.roles||[]).forEach(r=>c.append(el('span','team-role',roleLabels[r]||r)));const tools=el('div','card-actions');tools.append(button('編輯',()=>editProfile(p)),button('分工角色',()=>profileRoles(p)),button('設為預設',()=>action('profile_default',{id:p.id})),...(p.id==='demo'?[]:[button('檢查此助理',()=>showCompanyReadiness(p.id)),button('試用一般聊天',()=>{navigate('dialogue');document.dispatchEvent(new CustomEvent('qa-dialogue-test',{detail:{assistant:'company:'+p.id+':'+p.revision}}));}),button('刪除助理',()=>confirm('刪除助理設定','保留歷史內容；使用此助理的舊對話及流程不能再派發。服務端助理不會刪除。','確認刪除',()=>action('profile_delete',{id:p.id,revision:p.revision})),'button danger')]));c.append(tools);grid.append(c);});if(!data.profiles?.length)empty(root,'建立你的助理團隊','加入組織核准的助理 ID，驗證能力後即可開始協作。');}
function editProfile(p={}){
 if(p.id==='demo')throw Error('內建示範助理不需編輯。');
 const body=modal(p.id?'編輯助理':'新增助理');const name=field(body,'名稱',p.name),id=field(body,'Assistant ID',p.assistant_id),notes=field(body,'用途與備註',p.notes,'textarea'),enabled=field(body,'啟用狀態',p.enabled===false?'false':'true','text',[{value:'true',label:'啟用'},{value:'false',label:'停用'}]);
 body.append(el('p','notice','新增或變更 ID 不會自動啟用協作能力，需由組織完成驗證。'));
 if(p.id){
  const section=el('section','card');body.append(section);section.append(el('h3','','此助理的金鑰與搜尋'),el('p','muted','金鑰只存 Windows 認證管理員。變更金鑰來源會更新連線版本，撤銷搜尋授權與分工驗證。'));
  const info=el('p','plain-text'),key=field(section,'新的個別 API key（不讀回既有值）','','password');key.autocomplete='new-password';
  const controls=el('div','card-actions');section.append(info,controls);
  function draw(){info.textContent='金鑰來源：'+(p.credential_mode==='individual'?'個別金鑰（缺少時不改用共用）':'共用金鑰')+' · 一般聊天搜尋：'+(p.chat_search_enabled&&p.search_policy?.tools?.length?'已核准':'未核准');remove.disabled=p.credential_mode!=='individual';}
  let changing=false;
  async function change(command){if(changing)return;if(command==='profile_key_save'&&!key.value.trim())throw Error('請填個別 API key。');changing=true;controls.querySelectorAll('button').forEach(b=>b.disabled=true);try{const saved=await action(command,{id:p.id,...(command==='profile_key_save'?{key:key.value}:{})});key.value='';p=(S.state.profiles||[]).find(row=>row.id===p.id)||p;draw();notify(saved?.cleanup_pending?'新金鑰來源已生效，舊金鑰不再使用；認證管理員殘留項目清理失敗，請聯絡維護者。':'金鑰設定已保存；舊對話需另開新對話。',!!saved?.cleanup_pending);}finally{changing=false;controls.querySelectorAll('button').forEach(b=>b.disabled=false);draw();}}
  const remove=button('移除個別金鑰',()=>change('profile_key_remove'),'button danger');controls.append(button('保存個別金鑰',()=>change('profile_key_save')),button('改用共用金鑰',()=>change('profile_key_shared')),remove);draw();
 }else body.append(el('p','muted','新助理預設使用共用金鑰；保存後可在編輯助理設定個別金鑰。'));
 modalButtons(button('取消',closeModal),button('保存助理資料',async()=>{await action('profile_save',{id:p.id,name:name.value,assistant_id:id.value,notes:notes.value,enabled:enabled.value==='true'});closeModal();},'button primary'));
}
function profileRoles(p){const body=modal('分工角色');body.append(el('p','notice','這是用途宣告，保存後仍需組織驗證，不代表能力已接通。'));const fields=['planner','analysis','review','compose','rag'].map(r=>{const label=el('label','check-field');const check=el('input');check.type='checkbox';check.checked=(p.workflow?.roles||[]).includes(r);label.append(check,document.createTextNode(roleLabels[r]||r));body.append(label);return [r,check];});modalButtons(button('取消',closeModal),button('保存角色',async()=>{await action('profile_roles',{id:p.id,roles:fields.filter(x=>x[1].checked).map(x=>x[0])});closeModal();}));}
const todoView={search:'',scope:'open'};
function taipeiToday(){return new Date(Date.now()+8*3600000).toISOString().slice(0,10);}
function renderTodos(root,data){
 $('page-actions').append(button('新增待辦',()=>editTodo(),'button primary'));
 const inbox=el('details','card work-inbox');inbox.open=true;inbox.append(el('summary','','需要我處理 · '+(data.work_inbox||[]).length));
 inbox.append(el('p','muted','來自真實工作與主對話；查看不會重新派發。最近未完成工作最多列出 50 筆，完整歷史見活動紀錄。'));
 for(const item of data.work_inbox||[]){
  const row=tone(el('div','list-row'),item.state);row.dataset.inboxKind=item.kind;row.dataset.inboxId=item.id;
  const info=el('div','grow');info.append(el('strong','',item.title),el('p','muted',item.source+' · '+time(item.created_at)),el('p','',item.note));row.append(info,badge(item.state));
  if(item.kind==='dialogue')row.append(button('回原對話',()=>{navigate('dialogue');document.dispatchEvent(new CustomEvent('qa-dialogue-open',{detail:{id:item.id}}));}));
  else if(item.kind==='task'){row.append(button('查看結果／阻塞',()=>showTask(item.id)));if(item.conversation_id)row.append(button('回原流程',()=>switchChat(item.conversation_id)));}
  else row.append(button('回來源處理',()=>switchChat(item.conversation_id),'button primary'));
  inbox.append(row);
 }
 if(!data.work_inbox?.length)inbox.append(el('p','muted','目前沒有待確認或未完成的工作。'));
 root.append(inbox,el('h2','','我的下一步'));
 const toolbar=el('div','toolbar');const search=field(toolbar,'搜尋標題或說明',todoView.search);
 const scope=field(toolbar,'顯示範圍',todoView.scope,'text',[{value:'open',label:'未完成'},{value:'due',label:'今天到期／逾期'},{value:'all',label:'全部'},{value:'done',label:'已完成'}]);root.append(toolbar);
 const summary=el('p','muted');summary.setAttribute('aria-live','polite');root.append(summary);const board=el('div','board');root.append(board);
 function draw(){
  todoView.search=search.value;todoView.scope=scope.value;board.replaceChildren();const today=taipeiToday(),term=search.value.trim().toLocaleLowerCase();
  const filtered=(data.todos||[]).filter(t=>(t.title+' '+t.description).toLocaleLowerCase().includes(term)&&(scope.value==='all'||scope.value==='done'&&t.state==='done'||scope.value==='open'&&t.state!=='done'||scope.value==='due'&&t.state!=='done'&&t.due_date&&t.due_date<=today));
  summary.textContent='符合 '+filtered.length+' 筆 · '+(data.todos||[]).filter(t=>t.state!=='done'&&t.due_date&&t.due_date<today).length+' 筆逾期 · 台北日期 '+today;
  const columns=scope.value==='done'?['done']:scope.value==='all'?['todo','ongoing','done']:['todo','ongoing'];board.style.gridTemplateColumns='repeat('+columns.length+', minmax(0, 1fr))';
  for(const state of columns){const rows=filtered.filter(t=>t.state===state).sort((a,b)=>(a.due_date||'9999').localeCompare(b.due_date||'9999')||b.updated_at.localeCompare(a.updated_at));const col=tone(el('div','board-column'),state);col.append(el('h3','',states[state]+' · '+rows.length));
   for(const t of rows){const c=el('div','card');c.dataset.todoId=t.id;c.append(button(t.title,()=>editTodo(t),'button quiet'));
    if(t.description)c.append(el('p','todo-description',t.description.slice(0,180)+(t.description.length>180?'…':'')));
    if(t.due_date)c.append(el('p',t.state!=='done'&&t.due_date<today?'error':'muted',(t.state!=='done'&&t.due_date<today?'逾期 · ':t.due_date===today?'今天到期 · ':'到期 · ')+t.due_date));
    const tools=el('div','card-actions');const next=state==='todo'?'ongoing':state==='ongoing'?'done':'todo';tools.append(button(state==='todo'?'開始處理':state==='ongoing'?'完成':'重新開啟',()=>action('todo_state',{id:t.id,state:next})));
    if(t.source_conversation_id){const source=(data.conversations||[]).find(x=>x.id===t.source_conversation_id);if(source)tools.append(button('回來源對話',()=>switchChat(source.id)));else c.append(el('p','muted','來源對話已刪除；待辦副本保留。'));}c.append(tools);col.append(c);
   }
   if(!rows.length)col.append(el('p','muted','沒有符合條件的待辦。'));board.append(col);
  }
 }
 search.addEventListener('input',draw);scope.addEventListener('change',draw);draw();
}
function editTodo(t={}){
 const body=modal(t.id?'待辦詳情':'新增待辦');body.append(el('p','muted','記錄下一個具體行動；狀態由你確認，不會派發 AI 工作。'));
 const title=field(body,'標題',t.title),desc=field(body,'下一步／阻塞與完成紀錄',t.description,'textarea'),due=field(body,'到期日',t.due_date,'date');title.maxLength=120;desc.maxLength=50000;title.required=true;
 const shortcuts=el('div','card-actions');shortcuts.append(button('今天',()=>{due.value=taipeiToday();}),button('明天',()=>{due.value=new Date(Date.now()+8*3600000+86400000).toISOString().slice(0,10);}),button('清除到期日',()=>{due.value='';}));body.append(shortcuts);
 const state=t.id?field(body,'處理狀態',t.state,'text',[{value:'todo',label:'待處理'},{value:'ongoing',label:'進行中'},{value:'done',label:'已完成'}]):null;
 if(t.source_conversation_id){const source=(S.state.conversations||[]).find(x=>x.id===t.source_conversation_id);if(source)body.append(button('查看來源',async()=>{await switchChat(source.id);closeModal();}));else body.append(el('p','muted','來源對話已刪除；待辦副本保留。'));}
 const request=rid();let saving=false;
 modalButtons(...(t.id?[button('刪除',()=>confirm('刪除待辦','確定永久刪除此待辦？不影響來源對話。','確認刪除',()=>action('todo_delete',{id:t.id})),'button danger')]:[]),button('取消',closeModal),button('保存',async()=>{
  if(saving)return;if(!title.reportValidity()||!due.reportValidity())return;saving=true;
  try{await action('todo_save',{id:t.id,title:title.value,description:desc.value,due_date:due.value||null,state:state?.value||'todo',source_conversation_id:t.source_conversation_id,request_id:request});closeModal();}finally{saving=false;}
 },'button primary'));
}
function renderSchedules(root,data){$('page-actions').append(button('財經日報',()=>showBriefing(),'button primary'));root.append(el('p','notice','只在 QA agent 開啟時執行。立即測試不改變原定時間。'));(data.schedules||[]).forEach(s=>{const row=el('div','list-row'),info=el('div','grow');info.append(el('strong','',s.name),el('p','','下次：'+time(s.next_fire)));row.append(info,badge(s.enabled?'已啟用':'已暫停'),button(s.enabled?'暫停':'啟用',()=>action('schedule_toggle',{id:s.id,enabled:!s.enabled})),button('現在測試一次',()=>confirm('立即測試','將依核准流程執行一次，原定時間保持不變。','確認執行',()=>action('schedule_run',{id:s.id,request_id:rid()}))),button('紀錄',async()=>{const runs=await call('schedule_history',{id:s.id});const body=modal('自動工作歷史');if(!runs.length)body.append(el('p','muted','尚無執行紀錄。'));for(const r of runs){const row=el('div','list-row');row.append(el('span','grow',String(r.scheduled_at||r.occurrence_key||'立即執行')),badge(r.state));if(r.task_id)row.append(button('查看成果',()=>showTask(r.task_id)));body.append(row);}}));row.append(button('刪除',()=>deleteRecords('schedules',[s.id]),'button danger'));root.append(row);});if(!data.schedules?.length)empty(root,'尚無自動工作','先完成一次查詢或流程，再從成果設定固定排程。');}
async function deleteRecords(kind,ids){
 const p=await call('cleanup_preview',{kind,ids});
 confirm('永久刪除'+p.label,p.items.map(i=>i.title).join('、')+'\n共 '+p.count+' 筆。\n'+p.notice,'確認刪除',async()=>{
  await call('cleanup_confirm',{token:p.token});closeModal();S.signatures={};await refresh();notify('已刪除選定內容');
 });
}
async function manageRecords(){
 const data=await call('cleanup_catalog'),body=modal('管理本機資料');
 body.append(el('p','notice','選擇類別與內容後刪除；不清除系統日誌、服務端資料、原檔或備份。執行中工作需先等待或取消收尾，排程需先暫停。'));
 const kind=field(body,'資料類別','tasks','text',Object.entries(data).map(([value,g])=>({value,label:g.label}))),search=field(body,'搜尋名稱'),list=el('div');body.append(list);
 const chosen=new Set();
 const matches=()=>data[kind.value].items.filter(i=>i.title.toLowerCase().includes(search.value.toLowerCase()));
 function draw(){list.replaceChildren();for(const i of matches()){const label=el('label','check-field'),c=el('input');c.type='checkbox';c.checked=chosen.has(i.id);c.onchange=()=>c.checked?chosen.add(i.id):chosen.delete(i.id);label.append(c,document.createTextNode(i.title+' · '+(states[i.state]||i.state)+' · '+time(i.created_at)));list.append(label);}if(!matches().length)list.append(el('p','muted','此類別沒有符合的資料。'));}
 kind.onchange=()=>{chosen.clear();draw();};search.oninput=()=>{chosen.clear();draw();};draw();
 modalButtons(button('關閉',closeModal),button('全選目前搜尋結果',()=>{matches().forEach(i=>chosen.add(i.id));draw();}),button('刪除選取項目',()=>deleteRecords(kind.value,[...chosen]),'button danger'));
}
function renderActivity(root,data){$('page-actions').append(button('管理／批次刪除',manageRecords));statusLegend(root);(data.tasks||[]).forEach(t=>{const row=tone(el('div','list-row'),t.state),info=el('div','grow');info.append(el('strong','',({workflow:'多助理協作',assistant_briefing:'財經日報',query:'資料查詢',chat:'助理對話',summarize:'整理重點',rewrite:'改寫文字',report:'查詢日報'})[t.kind]||'工作'),el('p','',time(t.created_at)),...(t.error?[el('p','error',t.error)]:[]));row.append(info,badge(t.state));if(['running','queued'].includes(t.state))row.append(button('取消',()=>action('cancel_task',{task_id:t.id})));else row.append(button('查看成果',()=>showTask(t.id)),button('刪除',()=>deleteRecords('tasks',[t.id]),'button danger'));root.append(row);});if(!data.tasks?.length)empty(root,'工作紀錄將出現在這裡','從對話開始一件事，即可追蹤實際進度。');}
function renderNotices(root,data){
 root.append(el('p','muted','青藍數字代表未讀；通知左側顏色與圖示代表工作狀態。只有按「查看」才會標為已讀。'));
 (data.notifications||[]).forEach(n=>{
  const task=(data.tasks||[]).find(t=>t.id===n.task_id),state=task?.state||'未讀';
  const row=tone(el('div','list-row'),state),info=el('div','grow'),mark=el('span','notice-icon');
  mark.append(icon(task?.state==='failed'?'issue':task?.state==='succeeded'?'todo':'bell'));mark.setAttribute('aria-hidden','true');
  info.append(el('strong','',n.text||n.message||n.title),el('p','',time(n.created_at)));
  row.append(mark,info);if(task)row.append(badge(task.state));
  row.append(button('刪除',()=>deleteRecords('notifications',[n.id]),'button quiet'),badge(noticeRead(n)?'已讀':'未讀'),button('查看',async()=>{
   await action('notification_read',{id:n.id});const body=modal('通知');
   if(task)body.append(badge(task.state));body.append(el('p','plain-text',n.text||n.message||n.title));
   if(n.task_id)body.append(button('查看工作',()=>showTask(n.task_id)));
  }));root.append(row);
 });
 if(!data.notifications?.length)empty(root,'目前沒有通知','新成果或執行問題會顯示在此。');
}

function showRecentQueries(){const body=modal('最近查詢成果');const tasks=(S.state.tasks||[]).filter(t=>t.result?.columns||t.result?.query_result?.columns);for(const t of tasks){const q=t.result.query_result||t.result,row=el('div','list-row');row.append(el('strong','grow',(S.state.catalog||[]).find(c=>c.id===q.query_id)?.name||'查詢結果'),el('span','muted',time(t.created_at)),button('開啟表格',()=>showTable(t.id)));body.append(row);}if(!tasks.length)body.append(el('p','muted','尚無已完成查詢。請先選擇下方來源，填條件並確認查詢。'));}
function describeSpec(spec={}){const q=(S.state.catalog||[]).find(q=>q.id===spec.query_id),names={query_id:'資料來源',date_mode:'日期方式',name:'工作名稱',frequency:'頻率',time_hhmm:'台北時間',weekday:'每週執行日',assistant_id:'目的助理',prompt:'整理需求',purpose:'用途'},values={daily:'每日',weekly:'每週',previous_day:'前一日',literal:'固定條件'};return Object.entries(spec).map(([k,v])=>{if(k==='parameters')return Object.entries(v||{}).map(([key,value])=>(q?.parameters?.[key]?.label||key)+'：'+String(value)).join('\n');return (names[k]||k)+'：'+(k==='query_id'?(q?.name||v):values[v]||plain(v));}).join('\n');}
function renderQuery(root,data){
 const intro=el('div','card');intro.append(el('h3','','先選一項查詢'),el('p','',data.mode.includes('合成資料')?'目前是合成資料，尚未接上組織資料庫。選擇下方範例即可了解操作，不會呼叫模型。':'選擇已核准的資料來源，填寫必要條件後先預覽。'));
 intro.append(button('查看最近查詢成果',showRecentQueries),button('整理文字／CSV',()=>{navigate('chat');mode('chat');$('message-input').focus();}));root.append(intro);
 const grid=el('div','card-grid');root.append(grid);(data.catalog||[]).forEach((q,i)=>{const c=el('div','card');c.append(el('span','pill','查詢 '+(i+1)),el('h3','',q.name),el('p','',q.description||'填入條件後先顯示預覽，確認才執行。'),button('選擇並填條件',()=>queryForm(q),'button primary'));grid.append(c);});
 if(!data.catalog?.length)empty(root,'尚無可用資料來源','組織尚未配置核准查詢，請先使用助理對話；這不代表連線失敗。');
}
function queryForm(q){const body=modal('填寫條件 · '+q.name),fields={};body.append(el('p','muted','填寫必要條件後按「預覽查詢」，核對範圍後才會執行。'));Object.entries(q.parameters||{}).forEach(([key,spec])=>{const type=spec.type==='date'?'date':spec.type==='integer'?'number':'text';let options=spec.options;if(spec.type==='boolean')options=[{value:'true',label:'是'},{value:'false',label:'否'}];const input=field(body,spec.label||key,spec.default??'',type,options);input.required=!!spec.required;if(spec.min!==undefined)input.min=spec.min;if(spec.max!==undefined)input.max=spec.max;fields[key]=[input,spec];});modalButtons(button('取消',closeModal),button('預覽查詢',async()=>{const parameters={};for(const[key,[input,spec]]of Object.entries(fields)){if(!input.reportValidity())return;const v=input.value;parameters[key]=spec.type==='integer'?Number(v):spec.type==='boolean'?v==='true':v;}const a=await call('query_preview',{cid:S.cid,query_id:q.id,parameters});await refresh();await previewAction(a);},'button primary'));}
const colorStyles=[{id:'ocean',name:'深海青藍',description:'清楚、專業，適合日常工作。'},{id:'violet',name:'星霧紫',description:'以紫色操作點綴 AI 工作台。'},{id:'forest',name:'森林青綠',description:'沉穩柔和，適合長時間使用。'}];
let appearanceBusy=false;
function syncAppearanceControls(data){
 document.querySelectorAll('[data-color-choice]').forEach(b=>{const selected=b.dataset.colorChoice===(data.color_style||'ocean');b.setAttribute('aria-pressed',String(selected));b.querySelector('.style-check').textContent=selected?'✓ 使用中':'';});
 document.querySelectorAll('[data-theme-choice]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.themeChoice===(data.theme||'dark'))));
 const status=$('appearance-status');if(status){const saved=data.appearance_saved!==false;status.dataset.saved=String(saved);status.textContent=saved?'選擇會自動保存於本機，下次開啟繼續使用。':'本次已套用，但保存失敗；請按「重試保存」，否則重開可能恢復舊設定。';}
 if($('appearance-retry'))$('appearance-retry').hidden=data.appearance_saved!==false;
}
async function setAppearance(changes){
 if(appearanceBusy)return;appearanceBusy=true;
 const controls=[...document.querySelectorAll('[data-color-choice],[data-theme-choice],#appearance-reset,#appearance-retry,#theme-toggle')];
 controls.forEach(b=>b.disabled=true);
 try{const wasSaved=S.state.appearance_saved!==false,result=await call('appearance',changes);Object.assign(S.state,{theme:result.theme,color_style:result.color_style,appearance_saved:result.saved});applyPreferences(S.state);if(!result.saved)notify('外觀已套用，但尚未保存。請在外觀設定重試。',true);else if(!wasSaved)notify('外觀已保存。');}
 finally{appearanceBusy=false;controls.forEach(b=>b.disabled=S.closing);}
}
function renderAppearance(root,data){
 const card=el('section','card appearance-card');card.setAttribute('aria-label','外觀設定');root.append(card);
 card.append(el('h3','','外觀'),el('p','muted','挑選工作區風格，點一下就套用。深淺外觀可獨立切換。'));
 const choices=el('div','appearance-options');choices.setAttribute('role','group');choices.setAttribute('aria-label','主題風格');
 colorStyles.forEach(style=>{
  const b=button('',()=>setAppearance({color_style:style.id}),'appearance-option');b.dataset.colorChoice=style.id;b.setAttribute('aria-label',style.name);
  const mini=el('span','style-mini');mini.dataset.style=style.id;mini.setAttribute('aria-hidden','true');const side=el('span','mini-side'),main=el('span','mini-main');
  for(let i=0;i<3;i++)side.append(el('i'));main.append(el('i'),el('span','mini-message'),el('i'),el('span','mini-button'));mini.append(side,main);
  const title=el('span','style-name');title.append(el('span','',style.name),el('span','style-check'));
  b.append(mini,title,el('small','',style.description));choices.append(b);
 });card.append(choices);
 const modes=el('div','appearance-modes');modes.setAttribute('role','group');modes.setAttribute('aria-label','深淺外觀');modes.append(el('span','muted','外觀：'));
 for(const[name,label]of [['dark','深色'],['light','淺色']]){const b=button(label,()=>setAppearance({theme:name}));b.dataset.themeChoice=name;modes.append(b);}
 const reset=button('恢復預設',()=>setAppearance({theme:'dark',color_style:'ocean'}),'button quiet');reset.id='appearance-reset';modes.append(reset);card.append(modes);
 const status=el('p','appearance-status muted');status.id='appearance-status';status.setAttribute('role','status');card.append(status);
 const retry=button('重試保存',()=>setAppearance({theme:document.body.dataset.theme,color_style:document.body.dataset.colorStyle}));retry.id='appearance-retry';card.append(retry);
 const legend=el('div','appearance-legend');legend.append(el('p','muted','狀態色固定，換風格也不會改變意思。'));statusLegend(legend);card.append(legend);
 syncAppearanceControls(data);
}
function renderSettings(root,data){const quick=el('section','card');quick.id='activation-settings';root.append(quick);document.dispatchEvent(new CustomEvent('qa-activation-settings',{detail:quick}));const advanced=el('details');advanced.append(el('summary','','部署者進階連線設定'));root.append(advanced);const conn=el('div','card');conn.style.marginTop='18px';advanced.append(conn);conn.append(el('h3','','AI 助理連線'));const protocol=el('details');protocol.append(el('summary','','進階：連線協定'));conn.append(el('p','muted','先保存共用 Endpoint，再新增 Assistant ID；可使用共用金鑰，或在助理編輯中設定個別金鑰。組織範例預設使用 Assistants 協定。'));const wire=field(protocol,'連線協定',(!data.settings?.wire_mode||data.settings.wire_mode==='unconfigured')?'assistants':data.settings.wire_mode,'text',['unconfigured','assistants','model','body_field']);protocol.append(el('p','muted','組織範例請選 assistants；切換協定會使舊助理版本及能力驗證失效。'));const endpoint=field(conn,'Endpoint',data.settings?.endpoint||''),key=field(conn,'共用 API key','','password');key.autocomplete='new-password';conn.append(el('p','muted','金鑰狀態：'+(data.settings?.key_status||'尚未設定')));const actions=el('div','card-actions');actions.append(button('保存連線',async()=>{const saved=await action('connection_save',{endpoint:endpoint.value,wire_mode:wire.value,...(key.value?{key:key.value}:{})});key.value='';notify(saved?.cleanup_pending?'新連線已生效；舊認證項目清理失敗，請聯絡維護者。':'連線設定已保存；尚未完成實測，可試用一般聊天。',!!saved?.cleanup_pending);},'button primary'),button('移除共用金鑰',()=>confirm('移除共用金鑰','使用共用金鑰的助理將無法呼叫；個別金鑰保留。','確認移除',async()=>{const saved=await action('key_remove');if(saved?.cleanup_pending)notify('共用金鑰已停用；認證管理員殘留項目清理失敗，請聯絡維護者。',true);}),'button danger'));conn.append(actions,protocol);const ids=el('section','card');ids.style.marginTop='18px';ids.append(el('h3','','Assistant ID'),el('p','muted','已設定 '+(data.profiles||[]).filter(p=>p.id!=='demo').length+' 位AI 助理。先測通一位的連續對話，再設定團隊角色。'),button('新增助理 ID',()=>editProfile()),button('管理及檢查每位助理',()=>navigate('team')));advanced.append(ids);companyReadinessEntry(advanced);renderAppearance(root,data);renderCloseBehavior(root,data);if(String(data.mode).toLowerCase().includes('groq')||data.settings?.editable===false){wire.disabled=true;endpoint.disabled=true;key.disabled=true;actions.querySelectorAll('button').forEach(b=>b.disabled=true);conn.append(el('p','notice','外部試用工作區不能修改組織連線。'));}}
function renderHelp(root){const about=el('section','card');about.append(el('h3','','關於 QA agent'),el('p','muted','作者資訊與版本'));root.append(about);call('about').then(info=>{if(about.isConnected)about.append(el('div','plain-text',info.text));}).catch(error=>{if(about.isConnected)about.append(el('p','error',error.message));});root.append(button('管理本機資料',manageRecords),button('匯出除錯包',()=>confirm('匯出除錯包','僅包含版本、錯誤代碼與程式位置，不包含對話、設定、金鑰或資料庫。存成 ZIP 後請依組織規定分享。','選擇儲存位置',async()=>{const r=await call('support_export');if(r.saved)notify('已匯出：'+r.path);closeModal();})));const grid=el('div','card-grid');root.append(grid);[['USER-GUIDE','使用手冊','依工作查找操作步驟與常見問題'],['SKILLS','Skills 使用說明','從建立做法、Plan 確認到每日工作'],['DATA-USAGE','資料使用說明','了解本機保存、傳送與功能限制'],['THIRD-PARTY-LICENSES','第三方授權','使用的開源元件與授權資訊']].forEach(([name,title,desc])=>{const c=el('div','card');c.append(el('h3','',title),el('p','',desc),button('閱讀',async()=>{const r=await call('help',{name});const body=modal(title);trustedMarkdown(body,r.html,'手冊未提供');}));grid.append(c);});}
function renderIssues(root,data){$('page-actions').append(button('回報問題',()=>{const body=modal('問題與需求回報');const type=field(body,'類型','操作故障','text',['操作故障','回答不符','新需求']),title=field(body,'標題'),desc=field(body,'問題描述','','textarea'),expected=field(body,'預期結果','','textarea');body.append(el('p','notice','目前只保存在本機，不自動附加對話、資料或附件。'));modalButtons(button('取消',closeModal),button('保存回報',async()=>{await action('issue_save',{type:({'操作故障':'app','回答不符':'answer','新需求':'feature'})[type.value],title:title.value,description:desc.value,expected:expected.value});closeModal();},'button primary'));},'button primary'));(data.issues||[]).forEach(i=>{const row=el('div','list-row');row.append(el('strong','grow',i.title||i.description),badge(i.state||'本機草稿'),button('刪除',()=>deleteRecords('issues',[i.id]),'button danger'));root.append(row);});if(!data.issues?.length)empty(root,'讓工作區逐漸更好','記下問題或需求，交給組織維護者後續處理。');}
async function manageChats(){const body=modal('管理對話');const search=field(body,'搜尋標題');const list=el('div');body.append(list);const chosen=new Set();function draw(){list.replaceChildren();(S.state.conversations||[]).filter(c=>(c.title||'').includes(search.value)).forEach(c=>{const label=el('label','check-field'),check=el('input');check.type='checkbox';check.checked=chosen.has(c.id);check.addEventListener('change',()=>check.checked?chosen.add(c.id):chosen.delete(c.id));label.append(check,document.createTextNode(c.title||'新對話'));list.append(label);});}search.addEventListener('input',()=>{chosen.clear();draw();});draw();modalButtons(button('取消',closeModal),button('刪除選取對話',async()=>{if(!chosen.size)throw Error('請先選擇對話。');const preview=await call('delete_preview',{ids:[...chosen]});confirm('永久刪除對話','不能由應用復原。另存待辦、獨立查詢與排程保留。\n'+plain(preview.counts),'確認永久刪除',async()=>{const r=await call('delete_confirm',{token:preview.token});S.cid=r?.new_cid||null;S.signatures={};S.dirty=false;await refresh();});},'button danger'));}
$('collapse').addEventListener('click',()=>action('sidebar',{collapsed:!S.state?.sidebar_collapsed}).catch(e=>notify(e.message,true)));
$('theme-toggle').addEventListener('click',()=>setAppearance({theme:document.body.dataset.theme==='dark'?'light':'dark'}).catch(e=>notify(e.message,true)));
$('logout').addEventListener('click',()=>confirm('登出','登出會關閉工作區；展示資料會清除。','登出',async()=>{await call('logout');S.closing=true;closeModal();const shell=document.querySelector('.app-shell');shell.hidden=true;shell.inert=true;document.body.append(el('p','notice','已登出。請重新啟動並登入。'));}));
$('new-chat').addEventListener('click',()=>{if(S.page!=='chat'){navigate('dialogue');document.dispatchEvent(new Event('qa-dialogue-new'));}else newChat().catch(e=>notify(e.message,true));});
$('manage-chats').addEventListener('click',()=>{if(S.page!=='chat')$('dialogue-history').click();else manageChats().catch(e=>notify(e.message,true));});
$('modal-close').addEventListener('click',closeModal);
$('message-input').addEventListener('input',()=>{S.dirty=true;S.editVersion++;resizeInput();$('draft-status').textContent='儲存中…';clearTimeout(S.saveTimer);S.saveTimer=setTimeout(()=>saveDraft().catch(()=>{}),1000);});
$('message-input').addEventListener('compositionstart',()=>S.composing=true);$('message-input').addEventListener('compositionend',()=>{setTimeout(()=>S.composing=false,0);});
$('message-input').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing&&!S.composing&&e.keyCode!==229){e.preventDefault();if(!e.repeat)send();}});
$('send').addEventListener('click',send);$('draft-status').addEventListener('click',()=>saveDraft().catch(e=>notify(e.message,true)));
$('cancel-work').addEventListener('click',()=>action('cancel_task',{task_id:$('cancel-work').dataset.task}).catch(e=>notify(e.message,true)));
function mode(value){S.mode=value;$('chat-mode').classList.toggle('active',value==='chat');$('plan-mode').classList.toggle('active',value==='workflow');S.signatures.profiles=null;if(S.state)renderProfiles(S.state);}
$('chat-mode').addEventListener('click',()=>mode('chat'));$('plan-mode').addEventListener('click',()=>mode('workflow'));
$('assistant-select').addEventListener('change',()=>{updateAssistantNote();if(S.mode==='chat')newChat().catch(e=>notify(e.message,true));});
$('assistant-info').addEventListener('click',()=>{const p=(S.state?.profiles||[]).find(p=>p.id===$('assistant-select').value),binding=S.state?.conversation?.binding;const body=modal('助理資訊');if(S.mode==='chat'&&(!binding||!p||p.revision!==binding.revision)){body.append(el('p','notice','此對話保留原本的助理綁定，不能改送目前的新連線。請另開對話或預覽轉交選定內容。'),el('p','','來源版本：'+(binding?.revision??'舊資料未記錄')));return;}body.append(el('div','plain-text',p?`${p.name}\nAssistant ID：${p.assistant_id}\n連線版本：${p.revision}\n${p.notes||'用途尚未填寫'}`:'尚無助理'));});
$('composer-options').addEventListener('click',()=>{const body=modal('更多輸入選項');const purpose=field(body,'用途',S.purpose,'text',[{value:'chat',label:'一般對話'},{value:'summarize',label:'整理重點'},{value:'rewrite',label:'改寫文字'}]);const plan=field(body,'先預覽本機計畫',S.planned?'yes':'no','text',[{value:'no',label:'直接處理文字'},{value:'yes',label:'先規劃，另行批准'}]);modalButtons(button('保存選擇',()=>{S.purpose=purpose.value;S.planned=plan.value==='yes';S.dirty=true;S.editVersion++;closeModal();return saveDraft();}));});
$('attach-file').addEventListener('click',async()=>{try{const r=await call('upload',{cid:S.cid});if(!r)return;const body=modal('附件預覽');body.append(el('p','',r.name||'附件'),el('div','plain-text',r.preview||r.text||plain(r)));modalButtons(button('取消',closeModal),button('附加此資料',async()=>{await action('attachment_accept',{cid:S.cid,token:r.token});closeModal();},'button primary'));}catch(e){notify(e.message,true);}});
document.querySelectorAll('[data-starter]').forEach(b=>b.addEventListener('click',async()=>{try{if($('message-input').value.trim())await newChat();const key=b.dataset.starter;mode(key==='plan'?'workflow':'chat');$('message-input').value=key==='query'?sampleQuery().text:key==='plan'?'請幫我規劃以下工作，先確認需求與分工：\n':'請整理以下虛構工作筆記的重點與待辦：\n今天完成測試資料檢查，下次需要確認報告格式。';S.dirty=true;S.editVersion++;resizeInput();$('message-input').focus();await saveDraft();}catch(e){notify(e.message,true);}}));
document.addEventListener('selectionchange',()=>{const selected=window.getSelection();const within=selected?.anchorNode&&$('messages').contains(selected.anchorNode)&&$('messages').contains(selected.focusNode);const text=within?selected.toString():'';if(text.trim()){S.selectedText=text;S.selectedCid=S.cid;}$('selection-tools').hidden=!text.trim();});
$('selection-todo').addEventListener('click',()=>{const text=S.selectedText||'';if(text.length>50000){notify('選取文字超過 50,000 字，請縮小範圍。',true);return;}const title=text.split('\n').find(t=>t.trim())||'';editTodo({title:title.length<=120?title:'',description:text,source_conversation_id:S.selectedCid});});
$('selection-transfer').addEventListener('click',()=>transferDialog({cid:S.selectedCid,text:S.selectedText||''}).catch(e=>notify(e.message,true)));
const briefingEntry=button('財經日報',()=>showBriefing(),'button quiet');briefingEntry.id='dialogue-briefing';$('dialogue-plan').insertAdjacentElement('afterend',briefingEntry);$('dialogue-plan').parentElement.style.flexWrap='wrap';
renderNav();navigate('dialogue');
const agentJobsEntry=button('',()=>{navigate('dialogue');document.dispatchEvent(new Event('qa-agent-history'));},'nav-item');agentJobsEntry.id='agent-jobs-nav';agentJobsEntry.dataset.page='agent-work';agentJobsEntry.title='交辦工作';agentJobsEntry.append(icon('workflow'),el('span','nav-label','交辦工作'));$('navigation').children[0]?.insertAdjacentElement('afterend',agentJobsEntry);
const closingControls=new Map();let previousInert=false;
window.qaSetClosing=value=>{if(value===true){if(S.closing)return;S.closing=true;clearTimeout(S.saveTimer);previousInert=document.body.inert;document.body.inert=true;document.querySelectorAll('button,input,textarea,select').forEach(control=>{closingControls.set(control,{disabled:control.disabled,readOnly:control.readOnly});control.disabled=true;if('readOnly'in control)control.readOnly=true;});$('status-text').textContent='正在保存並等待背景工作結束…';}else{S.closing=false;document.body.inert=previousInert;for(const[control,prior]of closingControls){if(control.isConnected){control.disabled=prior.disabled;if('readOnly'in control)control.readOnly=prior.readOnly;}}closingControls.clear();$('send').disabled=S.sending;$('status-text').textContent='關閉未完成，請檢查草稿保存狀態。';}};
window.qaDraftSnapshot=()=>{clearTimeout(S.saveTimer);window.qaSetClosing(true);if(!S.dirty||!S.cid)return null;return {cid:S.cid,text:$('message-input').value,purpose:S.purpose,planned:S.planned,seq:++S.seq};};
window.addEventListener('pywebviewready',()=>{S.ready=true;refresh();setInterval(refresh,1500);});
document.addEventListener('qa-navigate',e=>{if(['settings','team','chat','orders','dialogue','skills','memories','schedule','activity'].includes(e.detail))navigate(e.detail);});

window.qaRequestClose=(unsavedExit=false,rememberExit=false)=>{
 if(S.closing)return;
 if($('modal').open&&!unsavedExit){notify('請先完成或關閉目前視窗，再選擇關閉方式。');return;}
 if(unsavedExit){const body=modal('工作內容尚未保存');body.append(el('p','notice','尚未提交的需求、Skill 草稿、補充文字或條件修改將在退出時遺失。已保存的討論、成果與排程保留。可取消並返回保存，或明確放棄這些編輯。'));const cancel=button('返回保存',()=>{closeModal();if(window.qaAgentHasUnsaved?.()){navigate('dialogue');document.dispatchEvent(new Event('qa-agent-open'));}else navigate(window.qaSkillHasUnsaved?.()?'skills':'orders');});modalButtons(cancel,button('放棄未保存編輯並退出',async()=>{window.qaOrderExitConfirmed=true;const result=await call('host_close',{value:'exit',remember:rememberExit});if(!result.pending)closeModal();},'button danger'));cancel.focus();return;}
 const body=modal('關閉視窗後，要繼續自動工作嗎？');
 body.append(el('p','notice','留在系統匣會保持此程式及已啟用的本機排程運作。電腦關機、休眠或登出後不能執行。退出會停止本機自動工作。'));
 const row=el('label','check-field'),remember=el('input');remember.type='checkbox';row.append(remember,document.createTextNode('記住這次選擇（可在設定變更）'));body.append(row);
 const choose=async value=>{const result=await call('host_close',{value,remember:remember.checked});if(result.pending)return;closeModal();if(!result.saved)notify('本次選擇已處理，但偏好未保存；下次仍會詢問。',true);};
 const cancel=button('取消',closeModal);modalButtons(cancel,button('退出程式',()=>choose('exit')),button('留在系統匣',()=>choose('background'),'button primary'));cancel.focus();
};

function renderCloseBehavior(root,data){
 const card=el('section','card');card.style.marginTop='18px';card.append(el('h3','','關閉視窗與自動工作'),el('p','muted','留在系統匣時排程繼續；電腦必須保持運作。登入失效時須重新登入。'));
 const value=field(card,'按右上角關閉時',data.close_behavior||'ask','text',[{value:'ask',label:'每次詢問'},{value:'background',label:'留在系統匣'},{value:'exit',label:'退出程式'}]);value.id='close-behavior';value.previousElementSibling.htmlFor=value.id;
 const info=el('p','muted');card.append(button('保存關閉方式',async()=>{const result=await call('close_behavior',{value:value.value});info.textContent=result.saved?'關閉方式已保存。':'保存失敗，請重試。';info.className=result.saved?'muted':'error';}),info);root.append(card);
}
document.addEventListener('qa-plan-entry',()=>{navigate('chat');$('plan-mode').click();});
// Shared local UI primitives; model output never becomes executable markup.
window.qaSkillUI={el,field,modal,modalButtons,closeModal,notify,call,icon,badge,time,navigate,showOutcome};
})();
