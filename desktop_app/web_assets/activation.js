(() => {
'use strict';
const U=window.qaSkillUI,e=U.el;
function button(label,fn,cls='button'){const b=e('button',cls,label);b.type='button';b.onclick=async()=>{if(b.disabled)return;b.disabled=true;try{await fn();}catch(error){U.notify(error.message,true);}finally{b.disabled=false;}};return b;}
async function form(root,info){
 root.replaceChildren();if(root.id!=='modal-body')root.append(e('span','eyebrow','START WITH ONE ASSISTANT'),e('h2','','啟用你的助理'));
 root.append(e('p','muted','填入助理端點、Assistant ID 與 API key 即可開始設定。連線預設使用系統信任的憑證。'));
 if(!info.available){if(root.id==='modal-body')U.modalButtons(button('稍後設定',U.closeModal));root.append(e('p','notice',info.message||'此工作區不能修改助理連線。'));return;}
 const endpoint=U.field(root,'Endpoint',info.endpoint||'','url'),id=U.field(root,'Assistant ID','','text'),key=U.field(root,'API key','','password');
 for(const [input,name]of [[endpoint,'endpoint'],[id,'assistant-id'],[key,'api-key']]){input.id='activation-'+name;input.previousElementSibling.htmlFor=input.id;}
 endpoint.placeholder='https://…/api/assts/v1';endpoint.autocomplete='url';key.autocomplete='new-password';
 const notice=e('p','notice','金鑰只存 Windows 認證管理員。測試會傳送兩輪非敏感合成訊息，可能產生 API 費用；不測搜尋。'),result=e('div','activation-result');root.append(notice);
 const show=e('label','check-field'),toggle=e('input');toggle.type='checkbox';toggle.onchange=()=>key.type=toggle.checked?'text':'password';show.append(toggle,document.createTextNode('顯示金鑰'));root.append(show);
 const consent=e('label','check-field'),yes=e('input');yes.type='checkbox';yes.id='activation-consent';consent.append(yes,document.createTextNode('我同意傳送兩輪合成訊息，測試連續對話。'));root.append(consent);
 const controls=e('div','card-actions');root.append(controls,result);let busy=false;
 function endpointApproval(value){
  result.replaceChildren(e('h3','','更換連線前，請先確認'),e('p','notice','此變更會撤銷舊目的地的憑證與能力核准，原對話保留為唯讀。這次輸入的 API key 將只用於新的連線；不會自動重送任何工作。'),e('p','plain-text','原端點：'+(info.endpoint||'未設定')+'\n新端點：'+value+'\n協定：Assistants'));
  return new Promise(resolve=>{const row=e('div','card-actions'),cancel=button('取消更換',()=>{result.replaceChildren(e('p','muted','已取消，設定與金鑰未變更。'));resolve(false);}),approve=button('確認更換連線',()=>{row.querySelectorAll('button').forEach(b=>b.disabled=true);resolve(true);},'button danger');row.append(cancel,approve);result.append(row);cancel.focus();result.scrollIntoView({block:'nearest'});});
 }
 async function submit(testing){
  if(busy)return;if(!endpoint.value.trim()||!id.value.trim()||!key.value.trim())throw Error('請填寫 Endpoint、Assistant ID 與 API key。');if(testing&&!yes.checked)throw Error('請先勾選同意兩輪合成測試。');
  busy=true;const payload={endpoint:endpoint.value.trim(),assistant_id:id.value.trim(),api_key:key.value,confirm_endpoint_change:false};
  const fields=[endpoint,id,key,toggle,yes];fields.forEach(input=>input.disabled=true);
  try{
   if((info.endpoint&&info.endpoint!==payload.endpoint)||!['unconfigured','assistants'].includes(info.wire_mode||'unconfigured')){if(!await endpointApproval(payload.endpoint))return;payload.confirm_endpoint_change=true;}
   const saved=await U.call('activation_save',payload);key.value='';info.endpoint=payload.endpoint;info.wire_mode='assistants';
   if(testing)await test(saved.profile_id,saved.assistant_id);else result.replaceChildren(e('p','notice','已保存。聊天尚未實測，沒有呼叫模型。'));
   document.dispatchEvent(new Event('qa-dialogue-catalog-refresh'));
  }finally{busy=false;fields.forEach(input=>input.disabled=false);}
 }
 controls.append(button('只保存，不測試',()=>submit(false)),button('測試並開始使用',()=>submit(true),'button primary'));
 if(root.id==='modal-body')U.modalButtons(button('稍後設定',U.closeModal),...controls.children);
 async function test(profileId,assistantId){
  result.replaceChildren(e('span','busy-spinner'),e('p','muted','正在測試兩輪對話，請稍候；不會自動重試。'));
  try{const r=await U.call('activation_test',{profile_id:profileId,consent:true});result.replaceChildren(e('p',r.passed?'notice':'error',r.message||(r.passed?'聊天可用；Skill 格式與搜尋需另行驗證。':'測試未通過，設定已保留。')));
   for(const check of r.checks||[])result.append(e('p','muted',typeof check==='string'?check:[check.name||check.code||check.stage||(check.round?'第 '+check.round+' 輪':''),check.status||'',check.message||'',check.incident?.id?'錯誤編號 '+check.incident.id:''].filter(Boolean).join(' · ')));
   if(r.passed)result.append(button('開始聊天',()=>{U.closeModal();U.navigate('dialogue');document.dispatchEvent(new CustomEvent('qa-dialogue-activate',{detail:{assistant_id:r.assistant_id||assistantId}}));},'button primary'));
  }catch(error){result.replaceChildren(e('p','error',error.message),e('p','muted','已保存的設定仍在；請依錯誤編號檢查。沒有切換示範或自動重送。'));}
 }
 for(const profile of info.chat_profiles||[]){const line=e('section','activation-profile');line.append(e('h3','',profile.name),e('p','muted','聊天：'+(profile.chat_status||'尚未測試')+' · Skill：'+((profile.skill_roles||[]).join('、')||'尚未測試')+' · 搜尋：'+(profile.search_approved?'已核准（來源仍須核對）':'未核准')));line.append(button('測試此助理兩輪對話',async()=>{if(busy)return;if(!yes.checked)throw Error('請先勾選同意兩輪合成測試。');busy=true;try{await test(profile.id,profile.assistant_id);}finally{busy=false;}}));root.append(line);}
}
async function open(){const info=await U.call('activation_status'),body=U.modal('設定助理 · 三個欄位開始');await form(body,info);}
document.addEventListener('qa-activation-open',()=>open().catch(error=>U.notify(error.message,true)));
document.addEventListener('qa-activation-settings',event=>U.call('activation_status').then(info=>form(event.detail,info)).catch(error=>event.detail.append(e('p','error',error.message))));
window.addEventListener('pywebviewready',()=>setTimeout(async()=>{try{const info=await U.call('activation_status');if(info.needed&&!document.getElementById('modal').open)await open();}catch(error){U.notify(error.message,true);}},200));
})();
