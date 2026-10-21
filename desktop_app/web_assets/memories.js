(() => {
'use strict';
const U=window.qaSkillUI,$=id=>document.getElementById(id),e=U.el;
let rows=[],catalog=[],scope='';
function fail(error){$('memory-error').textContent=error.message;U.notify(error.message,true);}
function button(label,fn,cls='button'){const b=e('button',cls,label);b.type='button';b.onclick=async()=>{if(b.disabled)return;b.disabled=true;try{await fn();}catch(error){fail(error);}finally{b.disabled=false;}};return b;}
function close(){U.closeModal();}
function field(parent,label,value,type='text',options){return U.field(parent,label,value,type,options);}
async function editor(row=null,selection=null){
 catalog=(await U.call('dialogue_catalog')).assistants;
 const body=U.modal(row?'編輯記憶':'記住這件事');
 body.append(e('p','notice','只保存你確認的筆記。啟用後，同一位助理的新對話會顯示將使用的記憶；不會自動分析聊天。'));
 const owner=field(body,'所屬助理',row?.assistant_id||selection?.assistant_id||scope||catalog[0]?.id||'','text',catalog.map(a=>({value:a.id,label:a.name})));
 owner.disabled=!!row;
 const category=field(body,'類型',row?.category||'background','text',[{value:'preference',label:'偏好'},{value:'background',label:'背景'},{value:'rule',label:'工作規則'}]);
 const title=field(body,'標題',row?.title||'','text'),text=field(body,'記憶內容',row?.text||selection?.text||'','textarea');title.maxLength=120;text.maxLength=2000;text.rows=8;
 if(selection?.text?.length>2000)body.append(e('p','error','選取內容超過 2,000 字，請自行精簡後預覽；不會默默截斷。'));
 const preview=button('預覽保存',async()=>{
  const p=await U.call('memory_preview',{...(row?{id:row.id,revision:row.revision}:{}),data:{title:title.value,text:text.value,category:category.value,assistant_id:owner.value,...((row?.source_thread_id||selection?.source_thread_id)?{source_thread_id:row?.source_thread_id||selection.source_thread_id}:{})}});
  const view=U.modal('確認保存這份記憶');view.append(e('h3','',p.data.title),e('p','plain-text',p.data.text),e('p','notice','更新影響未來新對話；既有對話的記憶快照不變。此步驟不呼叫模型。'));
  const cancel=button('取消',close);U.modalButtons(cancel,button('返回修改',()=>editor({...p.data,...(row?{id:row.id,revision:row.revision}:{})})),button('確認保存',async()=>{await U.call('memory_confirm',{token:p.token});close();await load();U.notify('記憶已保存，既有對話不變。');},'button primary'));cancel.focus();
 });U.modalButtons(button('取消',close),preview);
}
async function manage(row,action){
 const p=await U.call('memory_manage_preview',{id:row.id,revision:row.revision,action}),body=U.modal(action==='delete'?'刪除記憶':'變更記憶狀態');
 body.append(e('h3','',row.title),e('p','notice',action==='delete'?'刪除後不再加入未來的新對話；已送出內容、既有對話快照與備份不會撤回。':'此變更影響未來新對話，不會修改既有對話的固定快照。'));
 const cancel=button('取消',close);U.modalButtons(cancel,button(action==='delete'?'確認刪除':action==='disable'?'確認停用':'確認啟用',async()=>{await U.call('memory_manage_confirm',{token:p.token});close();await load();},action==='delete'?'button danger':'button primary'));cancel.focus();
}
async function load(){
 $('memory-error').textContent='';catalog=(await U.call('dialogue_catalog')).assistants;rows=await U.call('memory_list');
 const root=$('memory-content');root.replaceChildren();$('memory-actions').replaceChildren(button('新增記憶',()=>editor(),'button primary'));
 const controls=e('div','toolbar'),owner=field(controls,'所屬助理',scope,'text',[{value:'',label:'全部助理'},...catalog.map(a=>({value:a.id,label:a.name}))]),search=field(controls,'搜尋記憶','','search'),list=e('div','card-grid');root.append(controls,e('p','notice','每段對話使用建立當下的固定快照。刪除來源對話不會刪除另存記憶；來源可能顯示已刪除。'),list);
 function draw(){scope=owner.value;list.replaceChildren();const term=search.value.trim().toLocaleLowerCase();for(const row of rows.filter(r=>(!scope||r.assistant_id===scope)&&(r.title+' '+r.text).toLocaleLowerCase().includes(term))){const card=e('article','card memory-card');card.dataset.memoryId=row.id;card.append(e('span','pill',row.enabled?'啟用中':'已停用'),e('h3','',row.title),e('div','plain-text',row.text),e('p','muted',(catalog.find(a=>a.id===row.assistant_id)?.name||'原助理')+' · '+U.time(row.updated_at)));if(row.source_thread_id)card.append(row.source_deleted?e('p','muted','來源對話已刪除'):button('查看來源',()=>{U.navigate('dialogue');document.dispatchEvent(new CustomEvent('qa-dialogue-open',{detail:{id:row.source_thread_id}}));}));const actions=e('div','card-actions');actions.append(button('編輯',()=>editor(row)),button(row.enabled?'停用':'啟用',()=>manage(row,row.enabled?'disable':'enable')),button('刪除',()=>manage(row,'delete'),'button danger'));card.append(actions);list.append(card);}if(!list.children.length)list.append(e('div','empty-state','尚無符合的記憶。可手動新增，或從對話選取內容後按「記住這件事」。'));}
 owner.onchange=draw;search.oninput=draw;draw();
}
document.addEventListener('qa-memories-enter',()=>load().catch(fail));
document.addEventListener('qa-memory-create',event=>editor(null,event.detail).catch(fail));
})();
