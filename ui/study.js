'use strict';
const studyCommands=[['mermaid','Create flowcharts and concept diagrams'],['flashcards','Generate and review study cards'],['eli5','Explain simply, with examples and detail']];
function openCommands(){ $('settings-dialog').close();$('command-search').value='';listCommands();$('command-dialog').showModal();$('command-search').focus(); }
function listCommands(){
 const list=$('command-list');list.replaceChildren();
 for(const [name,description] of studyCommands.filter(c=>c.join(' ').includes($('command-search').value.toLowerCase()))){
  const b=document.createElement('button');b.className='command-row';
  const title=document.createElement('strong');title.textContent='/'+name;
  const help=document.createElement('small');help.textContent=description;b.append(title,help);
  b.onclick=()=>{const p=$('prompt');p.value='/'+name+' '+p.value.replace(/^\/(mermaid|flashcards|eli5)\b[,\s]*|^\/$/i,'');$('command-dialog').close();p.focus();sizePrompt();saveDraft();};list.append(b);
 }
}
$('command-open').onclick=openCommands;$('plugin-commands').onclick=openCommands;
$('command-close').onclick=()=>$('command-dialog').close();$('command-search').oninput=listCommands;
document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();openCommands();}});
$('prompt').addEventListener('input',()=>{if($('prompt').value==='/')openCommands();});
$('api-test').onclick=()=>send('api_test',{id:$('api-profile').value});
$('api-test-screen').onclick=()=>send('api_test',{id:$('api-profile').value,screen:true});
function showProviderDetails(p){
 const details=$('api-capabilities');details.replaceChildren();
 const status=v=>v===true?'Yes':v===false?'No':'Not reported';
 for(const [label,model] of [['Chat',p?.model],['Screen',p?.vision_model]]){
  if(!model)continue;const m=p.capabilities?.[model]||{};
  const line=document.createElement('p');line.textContent=`${label}: ${model}\nText: ${status(m.text)} · Images: ${status(m.vision)} · Tools: ${status(m.tools)} · Structured output: ${status(m.structured)}\nContext: ${m.context??'Not reported'} · Output limit: ${m.max_output??'Not reported'}`;details.append(line);
 }
 const box=$('api-usage');box.replaceChildren();const title=document.createElement('strong');title.textContent='Your usage';box.append(title);
 const balance=state?.connections.credits?.[p?.id];const usage=state?.connections.usage?.[p?.id];
 let total,remaining,unit,at;
 if(balance){total=balance.total;remaining=balance.remaining;unit=balance.unit;at=balance.at;}
 else{const reports=Object.values(usage?.models||{}).sort((a,b)=>b.at.localeCompare(a.at));const last=reports.find(r=>r.limits?.['x-ratelimit-limit-requests']||r.limits?.['anthropic-ratelimit-requests-limit']);if(last){const anthropic=last.limits['anthropic-ratelimit-requests-limit']!==undefined;total=Number(last.limits[anthropic?'anthropic-ratelimit-requests-limit':'x-ratelimit-limit-requests']);remaining=Number(last.limits[anthropic?'anthropic-ratelimit-requests-remaining':'x-ratelimit-remaining-requests']);unit=p.base_url.includes('groq.com')?'daily requests':'requests in provider window';at=last.at;}}
 if(Number.isFinite(total)&&total>0&&Number.isFinite(remaining)){
  remaining=Math.min(total,Math.max(0,remaining));const used=total-remaining,percent=100*used/total;
  const row=document.createElement('div');row.className='usage-summary';const chart=document.createElement('div');chart.className='usage-chart';chart.style.setProperty('--used',percent+'%');chart.setAttribute('role','img');chart.setAttribute('aria-label',`${used} used, ${remaining} remaining ${unit}`);const number=document.createElement('strong');number.textContent=Math.round(percent)+'%';chart.append(number);
  const legend=document.createElement('div');legend.className='usage-legend';for(const text of [`${used.toLocaleString(undefined,{maximumFractionDigits:2})} used`,`${remaining.toLocaleString(undefined,{maximumFractionDigits:2})} remaining`,unit]){const line=document.createElement('p');line.textContent=text;legend.append(line);}row.append(chart,legend);box.append(row);
  const time=document.createElement('p');time.className='note';time.textContent='Last reported '+new Date(at).toLocaleString()+'. Limits can reset or change after this snapshot.';box.append(time);
 }else{const note=document.createElement('p');note.textContent='Remaining balance not reported by this provider yet.';box.append(note);}
 if(p?.base_url==='https://openrouter.ai/api/v1'){const refresh=document.createElement('button');refresh.className='secondary';refresh.textContent='Refresh credits';refresh.onclick=()=>send('credits_refresh',{id:p.id});box.append(refresh);}
 const note=document.createElement('p');note.className='note';note.textContent=balance?'Account credits reported by OpenRouter.':'This provider does not report money credits here. The chart uses its actual request allowance when available.';box.append(note);
 if(usage){const details=document.createElement('details');const summary=document.createElement('summary');summary.textContent='Token details';const text=document.createElement('p');text.textContent=usage.total_tokens.toLocaleString()+' reported tokens used through Sleepy since tracking began. '+usage.unreported+' requests had no token count.';details.append(summary,text);box.append(details);}

}
window.showProviderDetails=showProviderDetails;
let mermaidLoad;
function loadMermaid(){
 if(!mermaidLoad)mermaidLoad=new Promise((resolve,reject)=>{const script=document.createElement('script');script.src='vendor/mermaid.js';script.onload=()=>{mermaid.initialize({startOnLoad:false,securityLevel:'strict',theme:'neutral',htmlLabels:false,maxTextSize:20000,maxEdges:120,flowchart:{htmlLabels:false},suppressErrorRendering:true});resolve(mermaid);};script.onerror=()=>{mermaidLoad=null;reject(Error('Diagram renderer could not load.'));};document.head.append(script);});return mermaidLoad;
}
function studyButton(label,fn){const b=document.createElement('button');b.className='secondary';b.textContent=label;b.onclick=fn;return b;}
window.renderStudy=function(code,kind,raw){
 if(!['mermaid','flashcards'].includes(kind))return false;
 const card=document.createElement('section');card.className='study-card';
 const heading=document.createElement('strong');heading.textContent=kind==='mermaid'?'Flowchart':kind==='flashcards'?'Flashcards':kind==='desmos'?'Graph expressions':'Editable drawing';card.append(heading);
 const content=document.createElement('div');content.className='study-content';card.append(content);
 const source=document.createElement('details'),summary=document.createElement('summary'),pre=document.createElement('pre');summary.textContent='View source';pre.textContent=raw;source.append(summary,pre);
 const fail=error=>{content.textContent='Could not display this artifact: '+error.message+'. The source is available below; ask Sleepy to correct it.';};
 try{
  if(raw.length>60000)throw Error('Content is too large');
  if(kind==='mermaid'){
   if(raw.length>20000||!/^\s*(flowchart|graph)\s+(TD|TB|LR|RL|BT)\b/.test(raw)||/%%\{|^---|\bclick\s|<\s*\/?[a-z]/im.test(raw))throw Error('Use a plain flowchart without links, HTML or configuration');
   const render=studyButton('Render flowchart',async()=>{render.disabled=true;try{const engine=await loadMermaid();const result=await engine.render('sleepyDiagram'+crypto.randomUUID().replaceAll('-',''),raw);if(!card.isConnected)return;content.innerHTML=DOMPurify.sanitize(result.svg,{USE_PROFILES:{svg:true,svgFilters:true},FORBID_TAGS:['foreignObject','a','script','image'],FORBID_ATTR:['href','xlink:href','onload','onclick']});const svg=content.querySelector('svg');if(svg){svg.style.width=Math.max(320,svg.viewBox.baseVal.width)+'px';svg.style.height='auto';svg.style.maxWidth='100%';}}catch(e){fail(e);} });content.append(render);const observer=new IntersectionObserver(entries=>{if(entries.some(e=>e.isIntersecting)){observer.disconnect();card.sleepyObserver=null;render.click();}});card.sleepyObserver=observer;observer.observe(card);
  }else{
   const data=JSON.parse(raw);heading.textContent=String(data.title||heading.textContent).slice(0,120);
   if(kind==='flashcards'){
    if(!Array.isArray(data.cards)||!data.cards.length||data.cards.length>50||data.cards.some(c=>!c||typeof c.front!=='string'||typeof c.back!=='string'||c.front.length>3000||c.back.length>3000))throw Error('Invalid card format');
    let index=0,back=false;const face=document.createElement('button');face.className='flash-face';const counter=document.createElement('p');counter.className='note';
    const paint=()=>{face.replaceChildren();const text=document.createElement('div');renderAnswer(text,data.cards[index][back?'back':'front']);face.append(text);counter.textContent=`${index+1} / ${data.cards.length} · ${back?'Answer':'Question'} · Click to flip`;};
    face.onclick=()=>{back=!back;paint();};const controls=document.createElement('div');controls.className='inline';controls.append(studyButton('Previous',()=>{index=(index+data.cards.length-1)%data.cards.length;back=false;paint();}),studyButton('Next',()=>{index=(index+1)%data.cards.length;back=false;paint();}));content.append(counter,face,controls);paint();
   }
  }
 }catch(error){fail(error);}
 card.append(source);code.parentElement.replaceWith(card);return true;
};

window.disposeStudy=root=>root.querySelectorAll(".study-card").forEach(card=>{card.sleepyObserver?.disconnect();card.sleepyObserver=null;});
