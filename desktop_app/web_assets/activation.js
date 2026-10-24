(() => {
'use strict';
const U=window.qaSkillUI,e=U.el;
function button(label,fn,cls='button'){const b=e('button',cls,label);b.type='button';b.onclick=async()=>{if(b.disabled)return;b.disabled=true;try{await fn();}catch(error){U.notify(error.message,true);}finally{if(b.isConnected)b.disabled=false;}};return b;}
function check(root,label,id){const row=e('label','check-field'),input=e('input');input.type='checkbox';if(id)input.id=id;row.append(input,document.createTextNode(label));root.append(row);return input;}
async function profilePanel(root,pid){
 const info=await U.call('activation_status'),p=info.chat_profiles.find(p=>p.id===pid);if(!p)return;
 root.replaceChildren(e('h3','',p.name));root.dataset.profileId=pid;
 const summary=e('p','capability-summary');const showCapabilities=q=>{const rs=q.skill_roles||[],ok=['planner','compose','assess','autonomous'].every(r=>rs.includes(r))&&q.routing_status==='passed';summary.textContent='聊天：'+(q.chat_status==='passed'?'可用':'待檢查')+' · 自動交辦：'+(ok?'可用':'待檢查')+' · 搜尋：'+(q.search_approved?(rs.includes('rag')?'已核准且測試通過':'已核准，待測試'):'尚未核准');};showCapabilities(p);root.append(summary);
 const search=e('details','activation-search');search.append(e('summary','','① 搜尋設定（選用，請先完成再測試）'),e('p','muted','需要助理上網時，先讀取工具宣告並人工核准。這只讀設定，不呼叫模型。變更工具會撤銷原版本能力，需要重新測試。'));root.append(search);
 const tools=e('div');search.append(button('讀取這位助理的工具宣告',async()=>{
  const result=await U.call('company_probe',{profile_id:pid});tools.replaceChildren();const rows=[];
  for(const t of result.search_candidates||[]){const c=check(tools,t.name+' · '+(t.description||'未提供說明'));rows.push([t.name,c]);const detail=e('details');detail.append(e('summary','','查看參數限制'),e('pre','plain-text',JSON.stringify(t.parameters||{},null,2)));tools.append(detail);}
  if(!rows.length){tools.append(e('p','notice','沒有可核准的搜尋工具；仍可先測試聊天及文字工作。'));return;}
  const consent=check(tools,'我已核對選取項目，只允許唯讀搜尋，不包含寫入或其他副作用。');
  tools.append(button('保存選取的搜尋核准',async()=>{if(!consent.checked)throw Error('請先核對工具並明確同意。');await U.call('search_policy_save',{token:result.policy_token,names:rows.filter(([,c])=>c.checked).map(([n])=>n),consent:true,chat_enabled:false});await profilePanel(root,pid);document.dispatchEvent(new Event('qa-dialogue-catalog-refresh'));},'button primary'));
 }),tools);
 const test=e('section','activation-tests');test.append(e('h4','','② 一次完成基本檢查'),e('p','muted','最多八次非敏感合成模型請求：兩輪聊天與辨識、三次工作格式、三次自主決策。停用所有工具；可能產生 API 費用，失敗不自動重試。'));
 const consent=check(test,'我同意發送上述合成測試。','activation-consent-'+pid),progress=e('div','activation-progress');progress.setAttribute('role','status');let timer=null;
 function stages(r){progress.replaceChildren();for(const s of r.stages||[]){progress.append(e('p',s.passed?'notice':'error',({chat:'聊天與上下文',work:'工作格式',autonomous:'自主決策'})[s.stage]+' · '+(s.passed?'通過':'未通過')));if(s.stage==='chat')progress.append(e('p','muted','自動辨識格式：'+(s.routing_passed?'通過':'未通過；可保留一般聊天')));for(const c of s.checks||[])if(c.status==='failed')progress.append(e('p','error',c.message||c.code||'請檢查設定或服務回覆。'));}if(r.running)progress.append(e('p','muted','檢查中…請等待目前請求結束。'));if(r.cancelled)progress.append(e('p','notice','已要求停止後續檢查；遠端請求可能仍在結束中。'));}
 const stop=button('停止後續檢查',()=>U.call('activation_cancel',{profile_id:pid}));stop.hidden=true;
 test.append(button('測試並開始使用',async()=>{
  if(!consent.checked)throw Error('請先同意合成測試。');const controls=[...root.querySelectorAll('button,input')];controls.forEach(n=>n.disabled=true);stop.disabled=false;stop.hidden=false;
  progress.replaceChildren(e('p','muted','開始檢查，沒有啟用搜尋或排程。'));
  timer=setInterval(()=>U.call('activation_progress',{profile_id:pid}).then(stages).catch(()=>{}),900);
  try{const r=await U.call('activation_run',{profile_id:pid,consent:true});stages(r);document.dispatchEvent(new Event('qa-dialogue-catalog-refresh'));const current=r.capabilities?.chat_profiles.find(p=>p.id===pid);if(current)showCapabilities(current);if(current?.chat_status==='passed')progress.append(button('開始使用',()=>{U.closeModal();U.navigate('dialogue');document.dispatchEvent(new CustomEvent('qa-dialogue-activate',{detail:{assistant_id:current.assistant_id}}));},'button primary'));if(current?.search_approved)progress.append(button('接著測試核准搜尋',()=>searchTest(pid,progress),'button'));
  }finally{clearInterval(timer);stop.hidden=true;controls.forEach(n=>{if(n.isConnected)n.disabled=false;});document.dispatchEvent(new CustomEvent('qa-diagnostics-refresh',{detail:{profile_id:pid}}));}
 },'button primary'),stop,progress);root.append(test);
 const diagnostics=e('section');root.append(diagnostics);window.qaDiagnosticsUI.mount(diagnostics,{profile_id:pid},{onStatus:data=>{const passed=check=>data.rows?.some(r=>r.check===check&&r.status==='passed');summary.textContent='聊天：'+(passed('chat')?'可用':'待檢查')+' · 自動交辦：'+(['routing','work','autonomous'].every(passed)?'可用':'待檢查')+' · 搜尋：'+(data.search_approved?(passed('search')?'已核准且測試通過':'已核准，待測試'):'尚未核准');}});
 const searchButton=button('③ 另行測試核准搜尋',()=>searchTest(pid,progress));searchButton.disabled=!p.search_approved;root.append(searchButton,e('p','muted','搜尋測試含工具結果續答，用量會在同意前顯示；來源品質仍須核對，工作仍須由你確認才執行。'));
 if(p.chat_status==='passed')root.append(button('使用這位助理',()=>{U.closeModal();U.navigate('dialogue');document.dispatchEvent(new CustomEvent('qa-dialogue-activate',{detail:{assistant_id:p.assistant_id}}));},'button primary'));
}
async function searchTest(pid,result){const panel=await window.qaDiagnosticsUI.open({profile_id:pid});await panel.ready;panel.retest('search');}
async function form(root,info){
 root.replaceChildren(e('h2','','啟用你的助理'),e('p','muted','填一次設定，在這裡完成檢查，之後直接從對話交辦工作。'));
 if(!info.available){root.append(e('p','notice',info.message));return;}
 const details=e('details');details.open=!info.chat_profiles.length;details.append(e('summary','','設定 endpoint、Assistant ID 與 API key'));root.append(details);
 const endpoint=U.field(details,'Endpoint',info.endpoint||'','url'),id=U.field(details,'Assistant ID','','text'),key=U.field(details,'API key','','password');
 for(const [input,name]of [[endpoint,'endpoint'],[id,'assistant-id'],[key,'api-key']]){input.id='activation-'+name;input.previousElementSibling.htmlFor=input.id;}key.autocomplete='new-password';
 const show=check(details,'顯示金鑰');show.onchange=()=>key.type=show.checked?'text':'password';details.append(e('p','muted','金鑰存於 Windows 認證管理員；保存不呼叫模型。CA 預設系統信任。'));
 const destination=check(details,'若變更既有端點／協定，我確認撤銷原憑證與能力；舊對話保留。');destination.parentElement.hidden=!info.endpoint;const saved=e('div');details.append(saved);
 details.append(button('保存並繼續',async()=>{if(!endpoint.value.trim()||!id.value.trim()||!key.value.trim())throw Error('請填三個欄位。');const changed=!!info.endpoint&&info.endpoint!==endpoint.value.trim()||!['unconfigured','assistants'].includes(info.wire_mode);if(changed&&!destination.checked)throw Error('更換既有端點或協定前，請明確確認。');const r=await U.call('activation_save',{endpoint:endpoint.value.trim(),assistant_id:id.value.trim(),api_key:key.value,confirm_endpoint_change:changed&&destination.checked});key.value='';details.open=false;await form(root,await U.call('activation_status'));document.dispatchEvent(new Event('qa-dialogue-catalog-refresh'));},'button primary'));
 for(const p of info.chat_profiles){const box=e('section','card activation-profile');root.append(box);await profilePanel(box,p.id);}
}
async function open(){const info=await U.call('activation_status'),body=U.modal('設定助理');await form(body,info);U.modalButtons(button('返回工作區',U.closeModal));}
document.addEventListener('qa-activation-open',()=>open().catch(error=>U.notify(error.message,true)));
document.addEventListener('qa-activation-settings',event=>U.call('activation_status').then(info=>form(event.detail,info)).catch(error=>event.detail.append(e('p','error',error.message))));
window.addEventListener('pywebviewready',()=>setTimeout(async()=>{try{const info=await U.call('activation_status');if(info.needed&&!document.getElementById('modal').open)await open();}catch(error){U.notify(error.message,true);}},200));
})();
