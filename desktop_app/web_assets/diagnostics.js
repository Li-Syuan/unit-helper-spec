(() => {
'use strict';
const U=window.qaSkillUI,e=U.el;
const labels={not_tested:'未測試',running:'檢查中',passed:'通過',failed:'失敗',cancelled:'已取消',incomplete:'未完成',stale:'設定已變更'};
const checkLabels={chat:'聊天與上下文',routing:'需求辨識',work:'工作格式',autonomous:'自主決策',search:'核准搜尋'};
const mounted=new Set();
function button(label,run,action,cls='button'){
 const node=e('button',cls,label);node.type='button';if(action)node.dataset.diagnosticAction=action;
 node.onclick=async()=>{if(node.disabled)return;node.disabled=true;try{await run();}finally{if(node.isConnected)node.disabled=false;}};
 return node;
}
function time(value){
 if(!value)return '沒有可用紀錄';const date=new Date(value);
 if(!Number.isFinite(date.getTime()))return '沒有可用紀錄';
 return new Intl.DateTimeFormat('zh-TW',{timeZone:'Asia/Taipei',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}).format(date)+'（台北）';
}
function message(node,text,bad=false){node.textContent=text;node.hidden=!text;node.className=bad?'error diagnostic-message':'muted diagnostic-message';node.setAttribute('role',bad?'alert':'status');}
function requestNote(root,request){
 if(!request)return;
 let text='原對話仍保留。請返回原對話，使用服務允許的恢復入口；這裡不會重新送出。';
 if(request.busy)text='原請求仍在執行或取消收尾中。請等它結束，再返回原對話檢查；不要重複送出。';
 else if(request.read_only)text='這份對話的連線版本已變更，保留閱讀。請返回原對話選取內容並建立接續對話。';
 else if(request.retry_unsent)text='已確認原請求尚未送出。修正設定後，返回原對話使用「重試未送出」；此處不會重送。';
 else if(request.recoverable)text='已有可恢復的原請求。請返回原對話使用「取回原回覆」，沿用原請求識別。';
 else if(['unknown','run_outcome_unknown','message_outcome_unknown','thread_outcome_unknown'].includes(request.remote_state))text='目前無法確認原請求是否送出。請返回原對話檢查原請求，不要盲目重送。';
 const note=e('section','notice diagnostic-request');note.dataset.diagnosticRequest=request.remote_state||request.state||'unknown';
 note.append(e('strong','','原對話請求'),e('p','',text));
 if(request.summary)note.append(e('p','muted',request.summary));
 const evidence=e('div','diagnostic-evidence');
 for(const [label,value]of [['錯誤代碼',request.code],['階段',request.stage],['HTTP 狀態',request.http_status],['錯誤編號',request.incident]])if(value)evidence.append(e('p','',label+'：'+String(value)));
 note.append(evidence);root.append(note);
}
function mount(root,target,options={}){
 for(const item of mounted)if(!item.root.isConnected)mounted.delete(item);
 root.classList.add('connection-diagnostics');root.dataset.diagnosticTarget=target.thread_id?'thread':'profile';
 if(target.profile_id)root.dataset.profileId=target.profile_id;
 const header=e('div','diagnostic-heading'),heading=e('div');
 heading.append(e('h4','','連線診斷'),e('p','muted','查看、重新整理及匯出只讀取本機紀錄，不呼叫助理。'));
 const alert=e('p','diagnostic-message');alert.hidden=true;
 const content=e('div','diagnostic-content'),report=e('section','diagnostic-report');report.hidden=true;
 const state={root,target,data:null,pending:false,refreshing:false,sequence:0,reportSequence:0};
 const refreshButton=button('重新整理',()=>refresh(),'refresh');
 const reportButton=button('預覽修復工作單',()=>showReport(),'report');
 header.append(heading,refreshButton);root.append(header,alert,content,reportButton,report);
 mounted.add(state);
 function connected(){return root.isConnected;}
 async function refresh(){
  if(state.pending)return;const sequence=++state.sequence;state.refreshing=true;refreshButton.disabled=true;
  try{const data=await U.call('diagnostics_status',target);if(!connected()||sequence!==state.sequence)return;state.data=data;message(alert,'');render();}
  catch(error){if(connected()&&sequence===state.sequence)message(alert,'無法讀取診斷：'+error.message,true);}
  finally{if(sequence===state.sequence){state.refreshing=false;if(connected())refreshButton.disabled=false;}}
 }
 function render(){
  const data=state.data;if(!data)return;content.replaceChildren();options.onStatus?.(data);
  const title=e('p','diagnostic-profile');title.append(e('strong','',data.name||'目前助理'),e('span','muted',' · 連線修訂 '+String(data.revision??'—')));content.append(title);
  if(target.thread_id&&data.source_revision!=null&&data.source_revision!==data.revision)content.append(e('p','notice','來源對話使用修訂 '+data.source_revision+'；下方能力紀錄屬於目前修訂 '+data.revision+'，不代表原對話已恢復。'));
  if(data.busy)content.append(e('p','notice','此助理仍有請求尚未結束，暫時不能重測。查看診斷不會取消或重送請求。'));
  requestNote(content,data.request);
  for(const warning of data.warnings||[])content.append(e('p','notice',String(warning)));
  const cards=e('div','diagnostic-grid');content.append(cards);
  for(const row of data.rows||[]){
   const status=Object.hasOwn(labels,row.status)?row.status:'incomplete',card=e('section','diagnostic-card');
   card.dataset.diagnosticCheck=row.check;card.dataset.diagnosticStatus=status;
   const top=e('div','diagnostic-card-title'),badge=e('span','diagnostic-badge',(status==='failed'?'! ':'')+labels[status]);badge.dataset.status=status;
   top.append(e('strong','',row.label||checkLabels[row.check]||'檢查項目'),badge);card.append(top,e('p','diagnostic-time',time(row.time)));
   if(row.check==='search')card.append(e('p','muted',data.search_approved?'工具已人工核准；測試通過仍須核對來源品質。':'工具尚未核准；請先在搜尋設定讀取宣告並人工核准。'));
   card.append(e('p','diagnostic-summary',row.summary||'沒有可用紀錄，無法推定服務已通過。'));
   if(row.next_step)card.append(e('p','diagnostic-next','下一步：'+row.next_step));
   if(row.code||row.stage||row.http_status||row.incident){
    const evidence=e('details','diagnostic-evidence');evidence.append(e('summary','','查看安全錯誤資訊'));
    for(const [label,value]of [['證據修訂',row.evidence_revision],['錯誤代碼',row.code],['階段',row.stage],['HTTP 狀態',row.http_status],['錯誤編號',row.incident]])if(value)evidence.append(e('p','',label+'：'+String(value)));
    card.append(evidence);
   }
   const consent=e('div','diagnostic-consent');consent.hidden=true;
   const test=button('重測此項',()=>confirmRetest(row,consent),'retest');test.dataset.diagnosticCheck=row.check;test.disabled=state.pending||!!data.busy||!row.can_retest;
   card.append(test,consent);cards.append(card);
  }
  if(!data.rows?.length)content.append(e('p','notice','沒有可用診斷紀錄。請保留原對話，先核對目前設定。'));
  if(options.allowChat!==false&&data.rows?.some(row=>row.check==='chat'&&row.status==='passed')){
   const start=button('開始聊天',async()=>{
    try{const info=await U.call('activation_status'),profile=info.chat_profiles.find(p=>p.id===data.profile_id);if(!profile)throw Error('目前助理設定已不存在，請重新整理。');U.closeModal();U.navigate('dialogue');document.dispatchEvent(new CustomEvent('qa-dialogue-activate',{detail:{assistant_id:profile.assistant_id}}));}
    catch(error){message(alert,error.message,true);}
   },'chat','button primary');start.disabled=!!data.busy;content.append(start,e('p','muted','聊天通過即可開始；其他項目未通過不代表聊天不可用。'));
  }
  reportButton.disabled=!data.report_available;
 }
 function confirmRetest(row,area){
  if(state.pending||!state.data||state.data.busy||!row.can_retest)return;
  const limit=Number(row.request_limit);if(!Number.isInteger(limit)||limit<1){message(alert,'沒有可用的請求上限，無法啟動重測。請重新整理診斷。',true);return;}
  root.querySelectorAll('.diagnostic-consent').forEach(node=>{node.hidden=true;node.replaceChildren();});
  area.hidden=false;area.append(e('p','notice','只重測「'+(row.label||checkLabels[row.check])+'」，最多 '+limit+' 次非敏感合成模型請求，可能產生 API 費用。'+(row.check==='search'?'只使用已核准搜尋；來源品質另由人核對。':'停用工具，不執行工作或排程。')+'失敗不會自動重試。'));
  const error=e('p','diagnostic-message');error.hidden=true;
  const checked=e('label','check-field'),checkbox=e('input');checkbox.type='checkbox';checkbox.dataset.diagnosticConsent=row.check;
  checked.append(checkbox,document.createTextNode('我同意這次指定項目的合成測試。'));area.append(checked,error);
  const cancel=button('取消',()=>{area.hidden=true;area.replaceChildren();},'cancel-retest');
  const confirm=button('同意並重測',async()=>{
   if(!checkbox.checked){message(error,'請先勾選同意這次測試。',true);return;}
   const revision=state.data.revision,profileId=state.data.profile_id;state.pending=true;cancel.disabled=true;checkbox.disabled=true;refreshButton.disabled=true;
   const tests=[...content.querySelectorAll('[data-diagnostic-action="retest"],[data-diagnostic-action="chat"]')];tests.forEach(node=>node.disabled=true);
   message(error,'檢查中；不會重新送出原對話。請等待目前請求完成。');
   try{const data=await U.call('diagnostics_retest',{profile_id:profileId,revision,check:row.check,consent:true});if(!connected())return;state.data=data;message(alert,'此項檢查已結束，結果與下一步如下。');}
   catch(failure){
    try{state.data=await U.call('diagnostics_status',target);}
    catch{state.data={...state.data,busy:true};}
    if(connected())message(alert,'重測未完成：'+failure.message+'。請重新整理查看紀錄；不會自動重送。',true);
   }
   finally{state.pending=false;if(connected()){refreshButton.disabled=false;render();}document.dispatchEvent(new CustomEvent('qa-diagnostics-changed',{detail:{profile_id:profileId}}));document.dispatchEvent(new Event('qa-dialogue-catalog-refresh'));}
  },'confirm-retest','button primary');confirm.dataset.diagnosticCheck=row.check;area.append(cancel,confirm);cancel.focus();
 }
 async function showReport(){
  const sequence=++state.reportSequence;report.hidden=false;
  const reportMessage=e('p','diagnostic-message');reportMessage.setAttribute('role','status');
  // Keep the last preview intact if generating a fresh report fails.
  report.append(reportMessage);message(reportMessage,'正在整理本機修復工作單…');
  try{
   const result=await U.call('diagnostics_report',target);if(!connected()||sequence!==state.reportSequence)return;
   if(typeof result.markdown!=='string'||!result.markdown.trim())throw Error('沒有可用的修復工作單。');
   const preview=e('textarea','diagnostic-report-preview');preview.readOnly=true;preview.value=result.markdown;preview.setAttribute('aria-label','修復工作單 Markdown 預覽');preview.dataset.diagnosticReport='preview';
   report.replaceChildren(e('h4','','修復工作單預覽'),e('p','muted','只包含白名單診斷資訊，不自動上傳。可先檢閱，再交給維護者。'),preview,reportMessage);message(reportMessage,'');
   const tools=e('div','card-actions');
   tools.append(button('複製修復工作單',async()=>{try{if(!navigator.clipboard?.writeText)throw Error('clipboard unavailable');await navigator.clipboard.writeText(preview.value);message(reportMessage,'修復工作單已複製。');}catch{message(reportMessage,'剪貼簿無法使用；預覽仍保留，請改用「另存 Markdown」。',true);}},'copy-report'),button('另存 Markdown',async()=>{try{const result=await U.call('diagnostics_export',target);message(reportMessage,result.saved?'修復工作單已保存。':'已取消另存，預覽仍保留。');}catch(failure){message(reportMessage,'保存失敗：'+failure.message+'。預覽仍保留，可再次另存。',true);}},'save-report'),button('收合工作單',()=>{report.hidden=true;},'hide-report'));report.append(tools);
  }catch(error){if(connected()&&sequence===state.reportSequence)message(reportMessage,'無法產生工作單：'+error.message,true);}
 }
 state.refresh=refresh;state.showReport=showReport;
 state.retest=check=>{const row=state.data?.rows?.find(item=>item.check===check),card=[...content.querySelectorAll('.diagnostic-card')].find(node=>node.dataset.diagnosticCheck===check);if(row&&card)confirmRetest(row,card.querySelector('.diagnostic-consent'));};
 state.ready=refresh();return state;
}
async function open(target){
 const body=U.modal('連線診斷與修復工作單'),root=e('section');body.append(root);const panel=mount(root,target,{allowChat:false});
 U.modalButtons(button('返回原處',U.closeModal,'close'));return panel;
}
document.addEventListener('qa-diagnostics-refresh',event=>{
 for(const state of mounted){if(!state.root.isConnected){mounted.delete(state);continue;}if(!event.detail?.profile_id||state.data?.profile_id===event.detail.profile_id||state.target.profile_id===event.detail.profile_id)state.refresh();}
});
window.qaDiagnosticsUI={mount,open};
})();
