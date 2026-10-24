(() => {
'use strict';
const U=window.qaSkillUI,$=id=>document.getElementById(id),e=U.el;
let selectedJob=null,epoch=0,skillSignature='';
function context(){return window.qaDialogueContext?.()||{};}
window.qaWorkspaceHasAnswers=()=>!!(selectedJob&&selectedJob.source_thread===context().id&&!selectedJob.task&&Object.keys(window.qaAgentUI.answers()).length);
function button(text,run,cls='button'){const b=e('button',cls,text);b.type='button';b.onclick=async()=>{if(b.disabled)return;b.disabled=true;try{await run();}catch(error){U.notify(error.message,true);}finally{b.disabled=false;}};return b;}
async function skills(){const rows=await U.call('skill_list'),signature=JSON.stringify(rows.map(r=>[r.id,r.name,r.enabled,r.revision]));if(signature===skillSignature)return;skillSignature=signature;const node=$('workspace-skill'),before=node.value;node.replaceChildren();for(const [value,label]of [['','不使用 Skill'],...rows.filter(r=>r.enabled).map(r=>[r.id,r.name]),['__manage__','管理 Skills…']]){const option=e('option','',label);option.value=value;node.append(option);}node.value=[...node.options].some(o=>o.value===before)?before:'';}
function composing(w){selectedJob=w;const target=$('workspace-composing'),active=w&&!w.task&&['draft','ready','planning'].includes(w.state);target.hidden=!active;target.replaceChildren();if(active){target.append(e('span','','補充目前工作 · '+w.goal),button('另開對話',()=>window.qaDialogueNew(),'button quiet'));$('dialogue-input').placeholder=w.busy?'正在整理計畫…':'補充這件工作的條件，或回答上方選項…';}else $('dialogue-input').placeholder='說說你想做什麼…';$('workspace-skill').disabled=!!active;if(w?.busy&&!w.task)$('dialogue-send').disabled=true;else $('dialogue-send').disabled=!!context().busy||!!context().blocked;}
window.qaWorkspaceSend=async(id,text,requestId)=>{
 const w=selectedJob;
 if(w&&w.source_thread===id&&!w.task&&['draft','ready','planning'].includes(w.state)){const r=await U.call('workspace_reply',{id,job_id:w.id,revision:w.revision,text,answers:window.qaAgentUI.answers()});window.qaAgentUI.acceptEdits();return {...r,focus_work:true};}
 const r=await U.call('workspace_send',{id,text,request_id:requestId,skill_id:$('workspace-skill').value||null});return {...r,focus_work:!!r.work};
};
window.qaWorkspacePaint=async thread=>{
 const turn=++epoch;try{
  const state=thread.work!==undefined?thread:await U.call('workspace_state',{id:thread.id});if(turn!==epoch||context().id!==thread.id)return;
  await skills();if(turn!==epoch||context().id!==thread.id)return;
  const picker=$('workspace-skill');if(state.skill_id&&[...picker.options].some(o=>o.value===state.skill_id))picker.value=state.skill_id;else picker.value='';
  document.querySelectorAll('.workspace-route').forEach(n=>n.remove());
  for(const route of state.routes||[]){const r=route.proposal;if(!r)continue;const card=e('div','notice workspace-route');
   if(route.job_id){card.append(button('查看這次工作',()=>window.qaWorkspaceOpenJob(route.job_id,thread.id),'button quiet'));}
   else if(r.kind==='clarify'&&!route.decision){card.append(e('p','','你想如何處理這件事？'),button('直接回答',async()=>{const next=await U.call('workspace_choose',{id:thread.id,request_id:route.request_id,choice:'chat'});window.qaDialoguePaint(next);$('dialogue-input').value=next.suggested_draft;$('dialogue-input').dispatchEvent(new Event('input'));$('dialogue-input').focus();}),button('建立工作計畫',async()=>window.qaDialoguePaint(await U.call('workspace_choose',{id:thread.id,request_id:route.request_id,choice:'work'}))));}
   else if(r.kind==='work'&&!route.job_id){card.append(e('p','','工作建議已保留；尚未執行。'),button('繼續準備計畫',async()=>window.qaDialoguePaint(await U.call('workspace_choose',{id:thread.id,request_id:route.request_id,choice:'work'}))),button('檢查助理設定',()=>document.dispatchEvent(new Event('qa-activation-open'))));}
   if(card.children.length)$('dialogue-result').append(card);
  }
  if(thread.work_notice)$('dialogue-result').append(e('p','error workspace-route',thread.work_notice));
  if(turn!==epoch||context().id!==thread.id)return;composing(state.work);await window.qaAgentUI.inline(state.work);if(thread.focus_work&&state.work)$('agent-job-panel').scrollIntoView({block:'start'});
 }catch(error){if(turn===epoch)U.notify(error.message,true);}
};
window.qaWorkspaceOpenJob=async(id,source)=>{
 if(source){try{await U.call('dialogue_state',{id:source});}catch{source=null;}}
 if(!source){await window.qaAgentUI.openJob(id);return;}
 if(context().id!==source)await window.qaDialogueOpen(source);U.navigate('dialogue');
 const next=await U.call('workspace_select',{id:source,job_id:id,skill_id:$('workspace-skill').value||null});window.qaDialoguePaint({...next,focus_work:true});
};
document.addEventListener('qa-work-updated',event=>{const w=event.detail;if(w.source_thread===context().id&&!document.getElementById('dialogue-page').classList.contains('agent-mode'))composing(w);});
$('workspace-more').onclick=()=>U.moreTools();$('workspace-notifications').onclick=()=>U.navigate('notice');
$('workspace-skill').onchange=async()=>{const node=$('workspace-skill');if(node.value==='__manage__'){node.value='';U.navigate('skills');return;}if(!context().id)return;try{await U.call('workspace_select',{id:context().id,skill_id:node.value||null,job_id:selectedJob?.id||null});}catch(error){U.notify(error.message,true);}};
document.addEventListener('qa-dialogue-enter',()=>skills().catch(error=>U.notify(error.message,true)));
})();
