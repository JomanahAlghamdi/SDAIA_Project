'use strict';
const $ = id => document.getElementById(id);
let session = null, polling = false, lastMessages = '', approvalId = null;
async function api(path, body) {
  const response = await fetch(path, body === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'The request could not be completed.');
  return data;
}
function showError(text='') { $('error').textContent=text; $('error').hidden=!text; }
function render(data) {
  session = data;
  const ready = data.state === 'ready';
  for (const id of ['send','message','detailsButton','newChat']) $(id).disabled=!ready;
  document.querySelectorAll('[data-prompt]').forEach(b=>b.disabled=!ready);
  $('busy').hidden=!['starting','running'].includes(data.state);
  $('busyText').textContent=data.state==='starting' ? 'Starting your conversation…' : 'Looking through opportunities…';
  $('connection').textContent=ready?'Ready to explore':data.state==='awaiting_approval'?'Waiting for your decision':data.state==='error'?'Connection unavailable':'Working on your request…';
  if (data.error) {showError(data.error);$('newChat').disabled=false;}
  $('welcome').hidden=data.messages.length>0;
  const signature=JSON.stringify(data.messages);
  if(signature!==lastMessages){
    lastMessages=signature; $('messages').replaceChildren();
    for(const msg of data.messages){
      const row=document.createElement('div');row.className='message '+msg.role;
      if(msg.role==='assistant'){const icon=document.createElement('span');icon.className='avatar';icon.textContent='✳';icon.setAttribute('aria-label','Assistant');row.append(icon);}
      const bubble=document.createElement('div');bubble.className='bubble';bubble.textContent=msg.text;row.append(bubble);$('messages').append(row);
    }
    $('conversation').scrollTop=$('conversation').scrollHeight;
  }
  const pending=data.approval;
  $('approval').hidden=!pending;
  if(pending && approvalId!==pending.id){
    approvalId=pending.id;$('preview').replaceChildren();
    const labels={company:'Company',title:'Opportunity',opportunity_id:'Catalog ID',training_kind:'Training type',duration_months:'Duration (months)',start_date:'Start date',status:'Status'};
    for(const [key,label] of Object.entries(labels)){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=label;dd.textContent=String(pending.preview[key]??'—');$('preview').append(dt,dd);}
    $('approve').disabled=$('decline').disabled=false;
    $('conversation').scrollTop=$('conversation').scrollHeight;
  }
  if(!pending)approvalId=null;
}
async function poll(){
  if(polling)return;polling=true;
  try{
    while(session && ['starting','running','awaiting_approval'].includes(session.state)){
      await new Promise(r=>setTimeout(r,600));
      render(await api('/api/sessions/'+session.id));
    }
  }catch(e){showError(e.message);$('newChat').disabled=false;}
  finally{polling=false;}
}
async function start(){
  try{
    showError();
    if(session && session.state==='ready')await api('/api/sessions/'+session.id+'/close',{});
    session=null;lastMessages='';
    render(await api('/api/sessions',{}));await poll();
  }catch(e){showError(e.message);$('newChat').disabled=false;}
}
$('chatForm').addEventListener('submit',async event=>{
  event.preventDefault();const message=$('message').value.trim();if(!message||session?.state!=='ready')return;
  try{showError();render(await api('/api/sessions/'+session.id+'/messages',{message}));$('message').value='';$('message').style.height='auto';await poll();$('message').focus();}catch(e){showError(e.message);}
});
$('message').addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();$('chatForm').requestSubmit();}});
$('message').addEventListener('input',()=>{$('message').style.height='auto';$('message').style.height=Math.min($('message').scrollHeight,110)+'px';});
document.querySelectorAll('[data-prompt]').forEach(button=>button.addEventListener('click',()=>{$('message').value=button.dataset.prompt;$('chatForm').requestSubmit();}));
$('newChat').addEventListener('click',start);
$('detailsButton').addEventListener('click',()=>{for(const [key,value] of Object.entries(session.academic_details))$('detailsForm').elements[key].value=value??'';$('detailsError').textContent='';$('detailsDialog').showModal();});
$('closeDetails').addEventListener('click',()=>$('detailsDialog').close());
$('detailsForm').addEventListener('submit',async event=>{
  event.preventDefault();const details={};for(const [key,value] of new FormData(event.target))details[key]=value===''?null:['year','gpa','required_months'].includes(key)?Number(value):value;
  try{render(await api('/api/sessions/'+session.id+'/details',details));$('detailsDialog').close();}catch(e){$('detailsError').textContent=e.message;}
});
async function decide(approved){
  $('approve').disabled=$('decline').disabled=true;
  try{await api('/api/sessions/'+session.id+'/approval',{approval_id:approvalId,approved});}
  catch(e){showError(e.message);}
}
$('approve').addEventListener('click',()=>decide(true));$('decline').addEventListener('click',()=>decide(false));
(async()=>{try{const info=await api('/api/status');$('catalogDate').textContent='· Catalog date: '+info.as_of;
if(!info.configured){$('connection').textContent='One-time setup needed';showError('Add your OPENROUTER_API_KEY and OPENROUTER_MODEL to the local .env file, then restart the server. Your key stays on the server and is never sent to this page.');for(const id of ['send','message','detailsButton','newChat'])$(id).disabled=true;document.querySelectorAll('[data-prompt]').forEach(b=>b.disabled=true);}else await start();}catch(e){showError(e.message);}})();
