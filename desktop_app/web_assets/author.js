/* Read-only publisher popover. No model, profile mutation, or navigation. */
(() => {
  'use strict';
  const trigger=document.getElementById('author-toggle');
  const panel=document.getElementById('author-popover');
  const content=document.getElementById('author-content');
  const closeButton=document.getElementById('author-close');
  let generation=0;
  function position(){
    if(panel.hidden)return;
    const rect=trigger.getBoundingClientRect();
    panel.style.left=Math.max(12,Math.min(rect.right-panel.offsetWidth,innerWidth-panel.offsetWidth-12))+'px';
    panel.style.top=Math.max(12,Math.min(rect.bottom+10,innerHeight-panel.offsetHeight-12))+'px';
  }
  function close(restoreFocus=false){
    generation++;panel.hidden=true;trigger.setAttribute('aria-expanded','false');
    if(restoreFocus)trigger.focus();
  }
  async function open(){
    if(!panel.hidden){close();return;}
    const request=++generation;
    panel.hidden=false;trigger.setAttribute('aria-expanded','true');
    content.textContent='正在讀取作者資訊…';position();
    try{
      const api=window.pywebview?.api;
      if(!api)throw Error('bridge_not_ready');
      const response=await api.call('about',{});
      if(request!==generation||panel.hidden)return;
      if(!response?.ok)throw Error('about_unavailable');
      const info=response.data?.author||{};
      const list=document.createElement('dl');
      for(const [label,key] of [['姓名','name'],['工號','employee_id'],['電話／分機','phone']]){
        const term=document.createElement('dt'),value=document.createElement('dd');
        term.textContent=label;value.textContent=typeof info[key]==='string'?info[key]:'尚未設定';
        list.append(term,value);
      }
      content.replaceChildren(list);position();
    }catch(error){
      if(request===generation&&!panel.hidden){content.textContent='作者資訊暫時無法讀取，請關閉後重試。';position();}
    }
  }
  trigger.addEventListener('click',open);
  closeButton.addEventListener('click',()=>close(true));
  document.addEventListener('pointerdown',event=>{
    if(!panel.hidden&&!panel.contains(event.target)&&!trigger.contains(event.target))close();
  });
  document.addEventListener('keydown',event=>{
    if(event.key==='Escape'&&!panel.hidden){event.preventDefault();event.stopPropagation();close(true);}
  },true);
  window.addEventListener('resize',position);
})();
