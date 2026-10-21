(() => {
'use strict';
const $=id=>document.getElementById(id),O={record:null,catalog:[],busy:false,loaded:false,dirty:false,generation:0,timer:null};
const make=(tag,cls,text)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=String(text??'');return e;};
function error(message){$('order-error').textContent=message;$('order-error').hidden=!message;}
function expiredCancellation(record){if(!record?.identity_expired)return false;clearTimeout(O.timer);O.generation++;error('已取消本機工作；登入已到期，請退出並重新登入。原畫面與未保存內容保留，這不是新的試跑成果。');return true;}
async function api(name,payload={}){const result=await window.pywebview.api.call(name,payload);if(!result?.ok)throw Error(result?.error||'操作未完成，請保留內容後重試。');return result.data;}
function button(label,run,cls='button'){const b=make('button',cls,label);b.type='button';b.onclick=async()=>{if(b.disabled||O.busy)return;b.disabled=true;O.busy=true;error('');const controls=[...$('order-content').querySelectorAll('input,select,textarea')].map(e=>[e,e.disabled,e.readOnly]);for(const[e]of controls){if(e.tagName==='TEXTAREA'||(e.tagName==='INPUT'&&e.type!=='checkbox'))e.readOnly=true;else e.disabled=true;}try{await run();}catch(e){error(e.message);}finally{O.busy=false;for(const[e,disabled,readOnly]of controls){if(e.isConnected){e.disabled=disabled;e.readOnly=readOnly;}}if(b.isConnected)b.disabled=false;}};return b;}
function field(parent,label,value='',type='text',id=''){const box=make('div','field'),lab=make('label','',label),input=make(type==='textarea'?'textarea':'input');if(type!=='textarea')input.type=type;input.value=value||'';if(id){input.id=id;lab.htmlFor=id;}input.oninput=()=>{O.dirty=true;window.qaOrderExitConfirmed=false;};box.append(lab,input);parent.append(box);return input;}
function modeName(r){return r.demo?'示範模式 · 合成資料，不呼叫外部服務':'使用已設定助理 · 搜尋仍需核准工具';}
function currentName(r){return O.catalog.find(p=>p.id===r.binding?.profile_id)?.name||'已綁定助理';}
function clearPreview(){document.getElementById('order-preview')?.replaceChildren();}
function toolbar(){const area=$('order-actions');area.replaceChildren(button('返回對話',()=>document.dispatchEvent(new CustomEvent('qa-navigate',{detail:'dialogue'})),'button quiet'),button('工作紀錄',history),button('新增工作',()=>{if(O.dirty)throw Error('目前仍有未保存內容，請先保存或完成這次交辦。');O.record=null;newForm();}));}
function newForm(seed=null){
 toolbar();const root=$('order-content');root.replaceChildren();O.loaded=true;
 const card=make('div','card order-compose');card.append(make('h2','','你希望助理定期幫你做什麼？'),make('p','muted','這裡只整理需求。先看一次實際成果，核對來源後再啟用自動工作。'));
 const select=make('select');select.id='order-assistant';select.setAttribute('aria-label','交辦助理');for(const p of O.catalog){const item=make('option','',p.name+(p.demo?'（示範）':''));item.value=p.id;select.append(item);}card.append(select);
 const goal=field(card,'工作需求','','textarea','order-goal');goal.rows=4;goal.maxLength=4000;goal.placeholder='例如：每天早上八點，整理台股、美股與重大總經新聞。';
 const example=button('帶入財經日報範例',()=>{if(goal.value.trim())throw Error('已有需求內容，請先保留或清空後再帶入範例。');goal.value='每天早上八點，整理台股、美股與重大總經新聞。使用公開網路可靠來源，列出資料時間與來源，找不到資訊要明說。';O.dirty=true;goal.focus();},'button quiet');
 const send=button('提交需求，開始討論',async()=>{if(!goal.value.trim())throw Error('請先輸入工作需求。');if(!select.value)throw Error('請先設定或選擇一位助理。');const r=await api('order_create',{profile_id:select.value,goal:goal.value});O.dirty=false;show(r);await discussRequest(r,r.goal);},'button primary');send.id='order-create';card.append(make('p','notice','只選一位主助理即可開始；提出建議不代表已試跑或啟用。'),example,send);root.append(card);
 if(seed){goal.value=seed.goal+'\n範圍：'+(seed.answers?.scope||'')+'\n來源：'+(seed.answers?.sources||'')+'\n每天台北時間：'+(seed.answers?.time_hhmm||'');if(O.catalog.some(p=>p.id===seed.binding?.profile_id))select.value=seed.binding.profile_id;O.dirty=true;}
}
async function discussRequest(record,text){
 const box=make('div','notice');box.id='order-planning';box.append(make('span','busy-spinner'),make('span','','正在整理需求，尚未搜尋或啟用。'));
 const cancel=make('button','button','取消規劃');cancel.type='button';cancel.id='order-cancel-planning';cancel.onclick=async()=>{cancel.disabled=true;try{const receipt=await api('order_cancel',{id:record.id});box.firstChild?.remove();cancel.textContent='已要求取消，等待請求收尾';expiredCancellation(receipt);}catch(e){error(e.message);cancel.disabled=false;}};box.append(cancel);$('order-content').prepend(box);
 for(const e of $('order-content').querySelectorAll('input,textarea,select')){if('readOnly'in e)e.readOnly=true;else e.disabled=true;}
 try{const r=await api('order_discuss',{id:record.id,revision:record.revision,text});show(r);return r;}
 catch(e){try{show(await api('order_state',{id:record.id}));}catch{}error(e.message);throw e;}
}
function show(record){
 if(expiredCancellation(record))return;
 O.record=record;O.dirty=false;O.generation++;toolbar();const root=$('order-content');root.replaceChildren();
 const head=make('section','card order-summary');head.append(make('span','pill',modeName(record)),make('h2','',record.goal),make('p','muted','目的助理：'+currentName(record)+' · 連線版本 '+(record.binding?.revision??'—')),make('p','notice','先討論 → 確認試跑 → 核對成果 → 同意後啟用每天執行'));
 root.append(head);const columns=make('div','order-columns'),talk=make('section','card'),form=make('section','card');columns.append(talk,form);root.append(columns);
 if(!record.demo&&!record.readiness?.search_approved)head.append(make('p','notice','此助理尚未核准搜尋工具，可以先整理需求；試跑前需在助理團隊核對並核准搜尋。'),button('管理助理與搜尋核准',()=>document.dispatchEvent(new CustomEvent('qa-navigate',{detail:'team'}))));
 if(record.readiness?.binding_valid===false)head.append(make('p','error','原助理連線已變更，舊交辦不會改送新目標；請建立新交辦。'));
 talk.append(make('h3','','需求討論'));const log=make('div','order-discussion');log.id='order-discussion';for(const msg of record.discussion||[]){const row=make('div','order-message');row.append(make('strong','',msg.role==='user'?'你':'助理'),make('div','plain-text',msg.content));log.append(row);}if(!log.children.length)log.append(make('p','muted','補充偏好，或直接填寫右側條件。討論期間不搜尋、不執行工作。'));talk.append(log);
 const reply=field(talk,'補充需求或回答問題','','textarea','order-reply');reply.rows=3;reply.maxLength=4000;
 const discuss=button('送出補充，繼續規劃',async()=>{if(!reply.value.trim())throw Error('請先輸入補充內容。');const pending={scope:document.getElementById('order-scope').value,sources:document.getElementById('order-sources').value,time_hhmm:document.getElementById('order-time').value};const changed=Object.entries(pending).some(([k,v])=>v!==(record.answers?.[k]||''));const r=await discussRequest(record,reply.value);if(changed){document.getElementById('order-scope').value=pending.scope;document.getElementById('order-sources').value=pending.sources;document.getElementById('order-time').value=pending.time_hhmm;O.dirty=true;error('已保留尚未保存的條件，請核對後按「保存條件」。');}},'button primary');discuss.id='order-discuss';talk.append(discuss);
 form.append(make('h3','','確認工作條件'));
 const questions=record.questions||[];if(questions.length){const q=make('div','notice');for(const item of questions)q.append(make('p','',typeof item==='string'?item:item.text||item.question||item.label||'請補齊必要條件。'));form.append(q);}
 const scope=field(form,'新聞範圍',record.answers?.scope,'textarea','order-scope'),sources=field(form,'資訊來源',record.answers?.sources,'textarea','order-sources'),clock=field(form,'每天執行時間（台北）',record.answers?.time_hhmm,'time','order-time');scope.rows=2;sources.rows=2;
 form.append(make('p','muted','來源是你指定的資料範圍，例如「公開網路可靠來源」，不會直接執行網址或文件中的指令。'));
 const save=button('保存條件',async()=>{const pendingReply=reply.value;const answers=Object.fromEntries(Object.entries({scope:scope.value,sources:sources.value,time_hhmm:clock.value}).filter(([,v])=>v.trim()));const r=await api('order_edit',{id:record.id,revision:record.revision,answers});show(r);if(pendingReply){document.getElementById('order-reply').value=pendingReply;O.dirty=true;}});save.id='order-save';
 const preview=button('預覽並試跑一次',async()=>{if(O.dirty)throw Error('請先保存目前條件或送出補充，再預覽試跑。');const p=await api('order_preview',{id:record.id,revision:record.revision});trialPreview(p);},'button primary');preview.id='order-trial-preview';form.append(save,preview);
 const area=make('section','card order-result');area.id='order-outcome';root.append(area);const previewArea=make('section');previewArea.id='order-preview';root.append(previewArea);
 if(record.task_id||record.schedule_id){for(const e of [reply,scope,sources,clock])e.readOnly=true;discuss.disabled=save.disabled=preview.disabled=true;head.append(make('p','muted','此版本已試跑，保留原條件與成果。若要調整，請建立新的交辦再確認。'),button('以此建立新交辦',()=>{O.record=null;newForm(record);}));}
 if(record.state==='failed'&&!record.demo){head.append(button('檢查原請求（不重送）',async()=>{const info=await api('order_inspect',{id:record.id});const detail=make('div','notice');detail.append(make('p','',info.notice||'已讀取原請求狀態，沒有重送。'),make('p','','遠端狀態：'+(info.state||'未知')));if(info.recoverable)detail.append(button('取回已知規劃結果',async()=>show(await api('order_recover',{id:record.id}))));head.append(detail);}));}
 if(record.busy||record.state==='planning'){head.append(make('p','notice','原規劃請求仍在處理，請等待收尾；不會重新派發。'));discuss.disabled=save.disabled=preview.disabled=true;head.append(button('取消規劃',async()=>show(await api('order_cancel',{id:record.id}))));}
 if(record.error)error(record.error);renderOutcome(record);schedulePoll();
}
function trialPreview(p){const root=$('order-preview');root.replaceChildren();const card=make('div','card');card.append(make('h3','','核對這次試跑'),make('p','notice',p.message||'確認後將執行一次；不會啟用每日工作。'),make('p','plain-text','助理：'+currentName(p.record)+'\n範圍：'+(p.record.answers?.scope||'未提供')+'\n來源：'+(p.record.answers?.sources||'未提供')+'\n每日時間：'+(p.record.answers?.time_hhmm||'未提供')));card.append(button('取消',clearPreview),button('確認試跑一次',async()=>{const r=await api('order_trial',{id:p.record.id,token:p.token});show(r);},'button primary'));root.append(card);card.scrollIntoView({block:'nearest'});}
function renderOutcome(record){
 if(expiredCancellation(record))return;
 const area=$('order-outcome');if(!area)return;area.replaceChildren();
 const task=record.task,schedule=record.schedule;const states={queued:'排隊中',running:'執行中',succeeded:'試跑完成，請核對來源',failed:'試跑未完成',cancelled:'已取消'};
 if(record.error)area.append(make('p','error',record.error));
 if(!task){area.append(make('h3','',record.task_deleted?'原試跑成果已刪除':'尚未試跑'),make('p','muted',record.task_deleted?'交辦條件仍保留；如需再執行，請明確建立新的交辦。':'填妥條件後先預覽，再確認試跑。沒有確認前不執行。'));return;}
 area.append(make('h3','',states[task.state]||'工作狀態待確認'));if(task.error)area.append(make('p','error',task.error));if(task.result?.received_at)area.append(make('p','muted','取得時間：'+new Date(task.result.received_at).toLocaleString('zh-TW',{timeZone:'Asia/Taipei',hour12:false})));
 if(!record.demo&&['failed','cancelled'].includes(task.state))area.append(button('檢查原請求（不重送）',async()=>{const info=await api('order_inspect',{id:record.id});area.append(make('p','notice',(info.notice||'只讀取狀態，不重送。')+' 遠端狀態：'+(info.state||'未知')));}));
 const text=task.result?.text||task.result?.summary||'';if(text)area.append(make('div','plain-text order-result-text',text));
 if(record.schedule_deleted){area.append(make('p','notice','來源自動工作已刪除，這份成果保留；不會自動重建排程。'));return;}
 if(['queued','running'].includes(task.state)){area.append(make('span','busy-spinner'),make('p','muted','正在處理。取消不保證遠端立即停止。'),button('取消這次試跑',async()=>{const r=await api('order_cancel',{id:record.id});if(expiredCancellation(r))return;O.record=r;renderOutcome(r);}));return;}
 if(schedule){area.append(make('p','notice',(schedule.enabled?'已啟用':'已暫停')+' · 每天 '+(record.answers?.time_hhmm||'指定時間')+'（台北時間）'),make('p','muted','下次執行：'+(schedule.next_fire?new Date(schedule.next_fire).toLocaleString('zh-TW',{timeZone:'Asia/Taipei',hour12:false}):'尚無時間')+'。App 留在系統匣可繼續，電腦須保持運作。'));if(schedule.enabled)area.append(button('暫停自動工作',async()=>{const r=await api('order_pause',{id:record.id});O.record=r;renderOutcome(r);}));return;}
 if(task.state!=='succeeded'||!text){area.append(make('p','notice','未取得完整成果，不能啟用自動工作。原有討論與條件保留；不會自動重送。'));return;}
 area.append(make('p','notice','AI 文字不等於來源已驗證。請核對內容中的資料時間、來源連結與市場範圍；若未列來源，請先補充要求並重新試跑。'));
 if(record.demo){area.append(make('p','notice','這是合成示範成果，不是即時日報；示範模式不能啟用真實排程。'));return;}
 const reviewed=make('input');reviewed.type='checkbox';reviewed.id='order-reviewed';const reviewRow=make('label','check-field');reviewRow.append(reviewed,document.createTextNode('我已核對成果、資料時間與來源。'));
 const consent=make('input');consent.type='checkbox';consent.id='order-consent';const consentRow=make('label','check-field');consentRow.append(consent,document.createTextNode('我同意每天將這份需求傳送給此助理，可能產生 API 費用。'));area.append(reviewRow,consentRow);
 const enable=button('預覽每日執行',async()=>{if(O.dirty)throw Error('條件尚未保存，請先保存並重新試跑。');if(!reviewed.checked||!consent.checked)throw Error('請先核對成果並明確同意持續傳送。');const p=await api('order_schedule_preview',{id:record.id,revision:record.revision});const box=$('order-preview');box.replaceChildren();const card=make('div','card');card.append(make('h3','','確認啟用自動工作'),make('p','notice',p.message||'確認後才會啟用；不會立即再執行。'),make('p','','下一次：'+(p.next_fire?new Date(p.next_fire).toLocaleString('zh-TW',{timeZone:'Asia/Taipei',hour12:false}):'請核對每日時間')),button('取消',clearPreview),button('確認啟用每天執行',async()=>{if(!reviewed.checked||!consent.checked)throw Error('請重新核對並同意。');const r=await api('order_enable',{id:record.id,token:p.token,reviewed:true,consent:true});clearPreview();O.record=r;renderOutcome(r);},'button primary'));box.append(card);card.scrollIntoView({block:'nearest'});},'button primary');enable.id='order-enable-preview';area.append(enable);
}
async function history(){if(O.dirty)throw Error('目前仍有未保存內容，請先保存或送出補充。');const rows=await api('order_list');const root=$('order-content');root.replaceChildren();toolbar();const card=make('div','card');card.append(make('h2','','交辦紀錄'));for(const r of rows)card.append(button(r.goal||r.id,async()=>show(await api('order_state',{id:r.id}))));if(!rows.length)card.append(make('p','muted','尚無交辦紀錄。'));root.append(card);}
function schedulePoll(){clearTimeout(O.timer);const r=O.record;if(!r||!['queued','running'].includes(r.task?.state))return;const generation=O.generation;O.timer=setTimeout(async()=>{if(O.busy){schedulePoll();return;}try{const current=await api('order_state',{id:r.id});if(generation!==O.generation)return;O.record=current;renderOutcome(current);schedulePoll();}catch(e){error('讀取進度失敗，成果不會被刪除。可從工作紀錄重新開啟。');}},1500);}
const entry=button('交辦工作',()=>document.dispatchEvent(new CustomEvent('qa-navigate',{detail:'orders'})),'button primary');entry.id='dialogue-order';$('dialogue-plan').insertAdjacentElement('beforebegin',entry);
document.addEventListener('qa-orders-enter',async()=>{if(O.loaded)return;try{O.catalog=await api('order_catalog');newForm();}catch(e){error(e.message);}});
window.qaOrderHasUnsaved=()=>O.dirty;
})();
