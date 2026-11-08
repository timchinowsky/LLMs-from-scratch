'use strict';
const $ = id => document.getElementById(id);
let csrf = '', role = '', status = {}, instance = '', cursor = 0, next = null;
let rows = new Map(), busy = false, signedIn = false, query = '', failures = 0;
const sessionId = crypto.randomUUID();
async function api(path, options = {}) {
  const response = await fetch(path, {...options, headers: {'Content-Type':'application/json', 'X-CSRF-Token':csrf, ...options.headers}, signal: AbortSignal.timeout(7000)});
  const data = await response.json();
  if (!response.ok) {const error = new Error(data.detail || 'Please refresh your history.'); error.code = response.status; throw error;}
  return data;
}
function error(e) { $('error').textContent = typeof e.message === 'string' ? e.message : 'Request could not be completed.'; }
function connection(ok) {
  $('connection').textContent = ok ? '● Connected to laptop' : '○ Disconnected — history may be out of date';
  $('mute').disabled = !ok;
  $('sample-form').querySelector('button').disabled = !ok || status.muted;
  document.querySelectorAll('.entry select').forEach(select => {select.disabled = !ok;});
}
function render() {
  const container = $('history'); container.replaceChildren();
  const ordered = [...rows.values()].sort((a,b) => b.capture_start.localeCompare(a.capture_start) || b.id.localeCompare(a.id));
  if (!ordered.length) {const p = document.createElement('p'); p.className='empty'; p.textContent=query ? 'No matching transcripts.' : 'A quiet moment. Saved speech will appear here.'; container.append(p);}
  for (const row of ordered) {
    const article=document.createElement('article'); article.className='entry'; article.dataset.id=row.id;
    const time=document.createElement('time'); time.dateTime=row.capture_start;
    time.textContent=new Intl.DateTimeFormat('en-US',{dateStyle:'medium',timeStyle:'short',timeZone:status.timezone || 'America/Los_Angeles'}).format(new Date(row.capture_start));
    const text=document.createElement('p'); text.textContent=row.text;
    const meta=document.createElement('div'); meta.className='meta';
    const label=document.createElement('span'); label.textContent='FINAL · SYNTHETIC FIXTURE';
    const select=document.createElement('select'); select.setAttribute('aria-label','Caregiver status for transcript at '+time.textContent);
    for (const value of ['unread','acknowledged','handled']) {const option=document.createElement('option'); option.value=value; option.textContent=value[0].toUpperCase()+value.slice(1); select.append(option);}
    select.value=row.caregiver_status;
    select.addEventListener('change',async()=>{try{await api('/api/transcripts/'+row.id,{method:'PATCH',body:JSON.stringify({status:select.value})}); row.caregiver_status=select.value;}catch(e){select.value=row.caregiver_status;error(e);}});
    meta.append(label,select); article.append(time,text,meta);container.append(article);
  }
  $('more').hidden=!next;
}
async function snapshot() {
  const result=await api('/api/transcripts?q='+encodeURIComponent(query));
  rows=new Map(result.items.map(row=>[row.id,row])); instance=result.instance; cursor=result.cursor;next=result.next;render();
}
async function refreshStatus() {
  status=await api('/api/status');
  $('provisional').hidden=!status.partial;
  $('partial-text').textContent=status.partial ? status.partial.text : '';
  $('listening').textContent=status.muted ? 'Locally muted' : 'Synthetic input enabled';
  $('mic').textContent=status.microphone;
  $('storage').textContent=status.storage==='ok' ? 'History is being saved' : 'Storage fault — saving stopped';
  $('disk').textContent=status.disk_free_mb+' MB free on laptop';
  $('mute').textContent=status.muted?'Resume synthetic listening':'Mute listening';
}
async function tick() {
  if (!signedIn || busy) return;
  busy=true;
  try {
    await refreshStatus();
    let more=true;
    while(more) {
      let result;
      try {result=await api('/api/events?instance='+encodeURIComponent(instance)+'&after='+cursor);}
      catch(e){if(e.code===409){await snapshot();break;}throw e;}
      if(result.events.length){
        // Reload a consistent snapshot for filtered/paginated views. Stable IDs prevent duplicates.
        await snapshot(); break;
      }
      cursor=result.cursor;more=result.more;
    }
    failures=0; connection(true);
  }catch(e){failures++;connection(false);if(e.code===401){signedIn=false;$('dashboard').hidden=true;$('login-panel').hidden=false;}error(e);}
  finally {busy=false;}
}
async function enter(session) {
  csrf=session.csrf; role=session.role; signedIn=true;
  $('login-panel').hidden=true;$('dashboard').hidden=false;$('role').textContent=role==='local'?'Local parent session':'Caregiver session';
  $('local-controls').hidden=role!=='local';
  await refreshStatus();await snapshot();connection(true);
}
$('login-form').addEventListener('submit',async event=>{event.preventDefault();try{const result=await api('/api/session',{method:'POST',body:JSON.stringify({token:$('token').value})});$('token').value='';$('error').textContent='';await enter(result);}catch(e){error(e);}});
$('logout').addEventListener('click',async()=>{try{await api('/api/session',{method:'DELETE'});signedIn=false;rows.clear();$('history').replaceChildren();$('dashboard').hidden=true;$('login-panel').hidden=false;}catch(e){error(e);}});
$('search-form').addEventListener('submit',async event=>{event.preventDefault();if(busy)return;busy=true;query=$('search').value;try{await snapshot();}catch(e){error(e);}finally{busy=false;}});
$('more').addEventListener('click',async()=>{if(!next||busy)return;busy=true;try{const result=await api('/api/transcripts?q='+encodeURIComponent(query)+'&before='+encodeURIComponent(JSON.stringify(next)));for(const row of result.items)rows.set(row.id,row);next=result.next;render();}catch(e){error(e);}finally{busy=false;}});
$('mute').addEventListener('click',async()=>{try{await api('/api/local/listening',{method:'POST',body:JSON.stringify({muted:!status.muted})});await tick();}catch(e){error(e);}});
$('sample-form').addEventListener('submit',async event=>{event.preventDefault();try{const capture=new Date().toISOString();const result=await api('/api/synthetic/segments',{method:'POST',body:JSON.stringify({id:crypto.randomUUID(),capture_start:capture,capture_end:capture,text:$('sample').value,session_id:sessionId,generation:status.generation})});if(!result.saved)throw new Error('Sample canceled by local mute or a changed capture generation.');await tick();}catch(e){error(e);}});
async function poll(){await tick();setTimeout(poll,Math.min(10000,2000 * 2 ** Math.min(failures,2)));}
api('/api/session').then(enter).catch(()=>{}).finally(poll);
