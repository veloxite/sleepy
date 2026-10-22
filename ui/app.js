'use strict';
const $ = id => document.getElementById(id);
const icons = {
 focus:'<path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5M8 8h8v8H8z"/>',
 attach:'<path d="m8 12 6-6a3 3 0 0 1 4 4l-8 8a5 5 0 0 1-7-7l8-8m-6 11 8-8"/>',
 models:'<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/>',
 edit:'<path d="m4 16-1 5 5-1L21 7l-4-4zM14 6l4 4"/>',
 trash:'<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7"/>',
 panel:'<rect x="3" y="4" width="18" height="16" rx="3"/><path d="M9 4v16"/>',
 new:'<path d="M12 5H6a3 3 0 0 0-3 3v10a3 3 0 0 0 3 3h10a3 3 0 0 0 3-3v-6M15 3l6 6M10 14l1-5 7-7 4 4-7 7z"/>',
 history:'<circle cx="12" cy="12" r="8"/><path d="M12 7v5l3 2"/>',
 close:'<path d="m6 6 12 12M18 6 6 18"/>',
 expand:'<path d="M9 3H3v6m12-6h6v6M3 15v6h6m12-6v6h-6"/>',
 search:'<circle cx="10" cy="10" r="6"/><path d="m15 15 5 5"/>',
 screen:'<rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8m-4-4v4"/>',
 eye:'<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
 arrow:'<path d="M12 20V4m-6 6 6-6 6 6"/>',
 stop:'<rect x="6" y="6" width="12" height="12" rx="2"/>',
 copy:'<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M15 4H6a2 2 0 0 0-2 2v9"/>',
 volume:'<path d="m11 4-6 5H2v6h3l6 5zM15 8a6 6 0 0 1 0 8m3-11a10 10 0 0 1 0 14"/>',
 plug:'<path d="M9 3v5m6-5v5M6 8h12v3a6 6 0 0 1-12 0zm6 9v5"/>',
 spark:'<path d="m12 3 2.6 6.4L21 12l-6.4 2.6L12 21l-2.6-6.4L3 12l6.4-2.6z"/>',
 memory:'<path d="M9 4a3 3 0 0 0-5 3 4 4 0 0 0-1 7 4 4 0 0 0 6 5m6-15a3 3 0 0 1 5 3 4 4 0 0 1 1 7 4 4 0 0 1-6 5M9 4v16m6-16v16M5 9h4m6 5h4"/>',
 lock:'<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3m-4 4v3"/>',
 settings:'<path d="m10 3-1 3-3 1-3 3 2 2-1 3 3 3 3-1 2 2 3-1 1-3 3-1 1-3-2-2 1-3-3-3-3 1-2-2z"/><circle cx="12" cy="12" r="3"/>',
 github:'<path d="M9 20c-4 1-4-2-6-2m13 4v-4a3 3 0 0 0-1-2c3 0 6-2 6-6a5 5 0 0 0-1-3 5 5 0 0 0 0-4s-2 0-4 2a14 14 0 0 0-8 0C6 3 4 3 4 3a5 5 0 0 0 0 4 5 5 0 0 0-1 3c0 4 3 6 6 6a3 3 0 0 0-1 2v4"/>'
};
const icon = name => `<svg viewBox="0 0 24 24" aria-hidden="true">${icons[name] || icons.spark}</svg>`;
document.querySelectorAll('[data-icon]').forEach(el => el.innerHTML = icon(el.dataset.icon));
let bridge = null, state = null, draftTimer, toastTimer, proposal = null, speaking = false, pickerReturn = null, pendingConnection = null;
const send = (action, values={}) => {
 if(bridge) bridge.request(JSON.stringify({action,...values}));
 else if(action !== 'draft') toast('Starting Sleepy…');
};
const escapeHtml = text => String(text).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function toast(message) { const t=$('toast');const modal=document.querySelector('dialog[open]');(modal||document.body).append(t);t.textContent=message;t.hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>t.hidden=true,6000); }

function mathHtml(text, display) {
 try { return katex.renderToString(text,{displayMode:display,throwOnError:false,trust:false,strict:'ignore',output:'html',maxExpand:200,maxSize:20}); }
 catch { return escapeHtml(text); }
}
marked.use({renderer:{html(token){return escapeHtml(token.text);}},extensions:[
 {name:'mathBlock',level:'block',start(src){return src.search(/\$\$|\\\[/);},tokenizer(src){const m=/^(?:\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\])(?:\n|$)?/.exec(src);if(m)return {type:'mathBlock',raw:m[0],text:m[1]||m[2]};},renderer(t){return mathHtml(t.text,true);}},
 {name:'mathInline',level:'inline',start(src){return src.search(/\$|\\\(/);},tokenizer(src){const m=/^(?:\$(?!\$)([^\n$]+?)\$|\\\(([^\n]+?)\\\))/.exec(src);if(m)return {type:'mathInline',raw:m[0],text:m[1]||m[2]};},renderer(t){return mathHtml(t.text,false);}}
]});
function renderAnswer(el, text) {
 const html = marked.parse(text,{gfm:true,breaks:false});
 el.innerHTML=DOMPurify.sanitize(html,{USE_PROFILES:{html:true},FORBID_TAGS:['img','input','button','form','iframe','style','script','svg'],FORBID_ATTR:['id','name']});
 el.querySelectorAll('pre > code').forEach(code=>{
  const raw=code.textContent;
  const language=(code.className.match(/language-([\w+-]+)/)||[])[1]||'code';
  if(window.renderMedia && window.renderMedia(code,language,raw))return;
  if(window.renderStudy && window.renderStudy(code,language,raw))return;
  if(hljs.getLanguage(language)) hljs.highlightElement(code);
  const wrapper=document.createElement('div'); wrapper.className='code-box';
  const head=document.createElement('div'); head.className='code-head';
  const lang=document.createElement('span'); lang.textContent=language;
  const copy=document.createElement('button'); copy.innerHTML=icon('copy')+'Copy code'; copy.title='Copy code';
  copy.onclick=()=>{send('copy',{text:raw});copy.textContent='Copied';setTimeout(()=>copy.innerHTML=icon('copy')+'Copy code',1400);};
  head.append(lang,copy); code.parentElement.replaceWith(wrapper); wrapper.append(head); const pre=document.createElement('pre');pre.append(code);wrapper.append(pre);
 });
}
let renderedMessages=[],renderedChat='';
function renderMessages() {
 const box=$('messages');let unchanged=0;
 if(renderedChat===state.chat_id){while(unchanged<renderedMessages.length&&unchanged<state.messages.length){
  const old=renderedMessages[unchanged],next=state.messages[unchanged];
  if(old.role!==next.role||old.content!==next.content||old.screen!==next.screen)break;
  unchanged++;
 }}
 if(unchanged===renderedMessages.length&&unchanged===state.messages.length&&renderedChat===state.chat_id){$('thinking').hidden=!state.busy;renderProposal(state.proposal);return;}
 renderedChat=state.chat_id;renderedMessages=state.messages;
 while(box.children.length>unchanged){if(window.disposeStudy)window.disposeStudy(box.lastElementChild);box.lastElementChild.remove();}
 $('welcome').hidden=state.messages.length>0;
 for(const m of state.messages.slice(unchanged)){
  const article=document.createElement('article');article.className='message '+m.role;
  if(m.role==='user'){
   const bubble=document.createElement('div');bubble.className='user-bubble';bubble.textContent=m.content;
   if(m.screen){const mark=document.createElement('span');mark.className='screen-mark';mark.innerHTML=icon('screen')+'Screen';bubble.append(mark);}
   article.append(bubble);
  }else if(m.role==='assistant'){
   const answer=document.createElement('div');answer.className='answer';renderAnswer(answer,m.content);article.append(answer);
   const tools=document.createElement('div');tools.className='message-actions';
   const copy=document.createElement('button');copy.className='icon';copy.title='Copy reply';copy.setAttribute('aria-label','Copy reply');copy.innerHTML=icon('copy');copy.onclick=()=>{send('copy',{text:m.content});toast('Copied');};
   const read=document.createElement('button');read.className='icon';read.title='Read aloud';read.setAttribute('aria-label','Read reply aloud');read.innerHTML=icon('volume');read.onclick=()=>{
    const readable=answer.cloneNode(true);readable.querySelectorAll('.code-box').forEach(b=>b.replaceWith(document.createTextNode('Code block.')));
    send('speak',{text:readable.textContent});
   };tools.append(copy,read);article.append(tools);
  }else article.textContent=m.content;
  box.append(article);
 }
 $('thinking').hidden=!state.busy;
 renderProposal(state.proposal);
 requestAnimationFrame(()=>$('scroll').scrollTop=$('scroll').scrollHeight);
}
function renderHistory(){
 const term=$('search').value.toLowerCase();$('history').replaceChildren();
 for(const chat of state.chats.filter(c=>c.title.toLowerCase().includes(term))){
  const b=document.createElement('button');b.className='history-row'+(chat.id===state.chat_id?' active':'');b.textContent=chat.title==='New conversation'?'New chat':chat.title;b.title=chat.title;b.disabled=state.busy;
  b.onclick=()=>{saveDraft();send('select',{id:chat.id});if(innerWidth<680)document.body.classList.add('sidebar-closed');};
  const row=document.createElement('div');row.className='history-item';row.append(b);
  if(chat.id===state.chat_id){
   const actions=document.createElement('div');actions.className='chat-actions';
   for(const [name,label,fn] of [['edit','Rename chat',()=>{$('rename-title').value=chat.title;$('rename-dialog').showModal();$('rename-title').select();}],['trash','Delete chat',()=>send('delete')]]){
    const action=document.createElement('button');action.className='icon';action.title=label;action.setAttribute('aria-label',label);action.innerHTML=icon(name);action.disabled=state.busy;action.onclick=fn;actions.append(action);
   }row.append(actions);
  }$('history').append(row);
 }
}
function applyPrefs(p){
 let theme=p.theme==='system'?(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'):p.theme;
 document.body.dataset.theme=theme;document.body.dataset.background=p.background;
 document.body.style.setProperty('--accent',p.accent);document.body.style.setProperty('--chat-font',p.font_size+'px');

 document.body.classList.toggle('reduce-motion',!p.motion);
 $('greeting').textContent=p.display_name?`Hi, ${p.display_name}.`:'What’s on your mind?';
 $('screen-toggle').classList.toggle('on',p.screen_enabled);$('screen-toggle').setAttribute('aria-pressed',String(p.screen_enabled));$('screen-label').textContent=p.screen_enabled?'Screen on':'Screen off';
 $('screen-toggle').disabled=!!state?.busy;
}
function acceptState(data){
 const same=state?.chat_id===data.chat_id; const typed=$('prompt').value;
 state=data;proposal=data.proposal;
 applyPrefs(data.prefs);renderHistory();renderMessages();if(window.renderFeatures)window.renderFeatures();
 renderConnections();renderContext();if($('settings-dialog').open&&window.showProviderDetails)window.showProviderDetails(data.connections.profiles.find(p=>p.id===$('api-profile').value));
 $('prompt').value=same&&typed?typed:(data.draft||'');sizePrompt();
 $('side-new').disabled=data.busy;
 updatePlugin();
 if(pendingConnection){fillConnections(pendingConnection);pendingConnection=null;}
 if($('settings-dialog').open && $('api-profile').value && !data.connections.profiles.some(p=>p.id===$('api-profile').value))fillConnections();
}
function sizePrompt(){const p=$('prompt');p.style.height='auto';p.style.height=Math.min(160,p.scrollHeight)+'px';$('send').disabled=!p.value.trim()||!!state?.busy;}
function saveDraft(){clearTimeout(draftTimer);if(state)send('draft',{chat_id:state.chat_id,text:$('prompt').value});}
function submit(){
 if(!state||state.busy||!$('prompt').value.trim())return;
 const connection=state.connections.profiles.find(p=>p.id===state.connections.active);
 if(!/^(?:(?:hey\s+)?sleepy[,!\s]+)?(?:open|launch|start|play|pause|resume|next|previous|stop|put on|create|rename|organize|organise)\b/i.test($('prompt').value.trim())&&(!connection||!(state.prefs.screen_enabled?connection.vision_model:connection.model))){openSettings('models');toast('Add a connection and choose a model first.');return;}
 const text=$('prompt').value;clearTimeout(draftTimer);$('prompt').value='';sizePrompt();send('send',{text});
}
$('prompt').addEventListener('input',()=>{sizePrompt();clearTimeout(draftTimer);draftTimer=setTimeout(saveDraft,600);});
$('prompt').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();submit();}});
$('send').onclick=submit;
$('screen-toggle').onclick=()=>{if(!state)return;state.prefs.screen_enabled=!state.prefs.screen_enabled;applyPrefs(state.prefs);send('settings',{values:{screen_enabled:state.prefs.screen_enabled}});};
$('search').oninput=renderHistory;
function openSettings(tab='appearance'){if(!state)return;saveDraft();document.querySelectorAll('dialog[open]').forEach(d=>d.close());fillSettings();selectTab(tab);$('settings-dialog').showModal();if(window.renderFeatures)window.renderFeatures();}
function selectTab(tab){document.querySelectorAll('[data-section]').forEach(e=>e.hidden=e.dataset.section!==tab);document.querySelectorAll('[data-tab]').forEach(e=>e.classList.toggle('active',e.dataset.tab===tab));}
document.querySelectorAll('[data-tab]').forEach(e=>e.onclick=()=>selectTab(e.dataset.tab));
document.querySelectorAll('.close-dialog').forEach(e=>e.onclick=()=>e.closest('dialog').close());
document.querySelectorAll('dialog').forEach(d=>d.addEventListener('click',e=>{if(e.target===d){const r=d.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)d.close();}}));
function fillSettings(){
 if(!state)return;const p=state.prefs;
 const fields={name:'display_name',theme:'theme',background:'background',accent:'accent',font:'font_size','dot-style':'dot_style',proximity:'proximity','dot-size':'dot_size',memories:'memories',rate:'speech_rate',capture:'capture_target'};
 for(const [id,key]of Object.entries(fields))$('pref-'+id).value=p[key];
 $('pref-motion').checked=p.motion;$('font-output').value=p.font_size+' px';
 $('pref-voice').replaceChildren();const def=document.createElement('option');def.value='';def.textContent='System default';$('pref-voice').append(def);
 for(const name of state.voices){const o=document.createElement('option');o.value=name;o.textContent=name;$('pref-voice').append(o);}$('pref-voice').value=p.speech_voice;
 $('logo-preview').hidden=!p.logo;if(p.logo)$('logo-preview').src=p.logo;

 const system=state.speech_platform==='Darwin'?'macOS':state.speech_platform;
 $('voice-note').textContent=state.speech_available?`Uses installed ${system} voices. No paid voice service is needed.`:'No speech engine available. Install a voice in your system settings.';
 fillConnections();
 if(window.fillFeatureSettings)window.fillFeatureSettings();
 updatePlugin();
}
$('pref-font').oninput=()=>$('font-output').value=$('pref-font').value+' px';
$('save-settings').onclick=()=>{
 const values={display_name:$('pref-name').value,theme:$('pref-theme').value,background:$('pref-background').value,accent:$('pref-accent').value,font_size:Number($('pref-font').value),dot_style:$('pref-dot-style').value,motion:$('pref-motion').checked,proximity:Number($('pref-proximity').value),dot_size:Number($('pref-dot-size').value),memories:$('pref-memories').value,speech_voice:$('pref-voice').value,speech_rate:Number($('pref-rate').value),capture_target:$('pref-capture').value};
 Object.assign(values,window.featurePrefs?.()||{});send('settings',{values});toast('Settings saved');
};
function updatePlugin(){if(!state)return;const connected=state.prefs.github_enabled;$('github-badge').textContent=connected?(state.github_login||'Connected'):'Not connected';$('github-connect').hidden=connected;$('github-connected').hidden=!connected;}
$('connect-github').onclick=()=>{const token=$('github-token').value;$('github-token').value='';send('github_connect',{token});};
$('disconnect-github').onclick=()=>send('github_disconnect');
$('token-help').onclick=()=>send('open_link',{url:'https://github.com/settings/personal-access-tokens/new'});
$('prepare-repo').onclick=()=>{
 if(!$('repo-name').value.trim()){toast('Give your repository a name.');return;}
 send('repo_propose',{name:$('repo-name').value,description:$('repo-description').value,private:$('repo-private').checked});$('settings-dialog').close();
};
function renderProposal(p){
 proposal=p;$('proposal').replaceChildren();if(!p)return;
 const card=document.createElement('div');card.className='repo-card';
 const title=document.createElement('h3');title.textContent='Create '+p.name;
 const privacy=document.createElement('span');privacy.className='badge';privacy.textContent=p.private?'Private':'Public';
 const desc=document.createElement('p');desc.textContent=p.description||'A new repository with a README.';
 const controls=document.createElement('div');controls.className='inline';
 const confirm=document.createElement('button');confirm.className='primary';confirm.textContent=state.prefs.github_enabled?'Create repository':'Connect GitHub';confirm.onclick=()=>state.prefs.github_enabled?send('repo_confirm',{id:p.id}):openSettings('plugins');
 const cancel=document.createElement('button');cancel.className='text-button';cancel.textContent='Cancel';cancel.onclick=()=>send('repo_cancel');
 controls.append(confirm,cancel);card.append(title,privacy,desc,controls);$('proposal').append(card);
}
document.addEventListener('click',e=>{
 const a=e.target.closest('a');if(a){e.preventDefault();if(/^https?:\/\//i.test(a.href))send('open_link',{url:a.href});return;}
 const button=e.target.closest('[data-command]');if(!button)return;
 const cmd=button.dataset.command;
 if(cmd==='sidebar')document.body.classList.toggle('sidebar-closed');
 else if(cmd==='history'){document.body.classList.remove('sidebar-closed');$('search').focus();}
 else if(cmd==='settings'||cmd==='plugins')openSettings(cmd==='plugins'?'plugins':'appearance');
 else if(cmd==='new'){saveDraft();send('new');}
 else if(cmd==='pick_logo'||cmd==='pick_background'){
  pickerReturn=cmd==='pick_logo'?'companion':'appearance';$('settings-dialog').close();send('pick_image',{kind:cmd==='pick_logo'?'logo':'background_image'});
 }
 else if(cmd==='remove_logo'||cmd==='remove_background')send('remove_image',{kind:cmd==='remove_logo'?'logo':'background_image'});
 else {saveDraft();if(['delete','attach_file','export_chat','focus_screen'].includes(cmd))$('settings-dialog').close();send(cmd);}
});
let faceNear=false,blinkTimer=0,blinkEnd=0;
const welcomeFace=document.querySelector('.welcome-face');
function cancelBlink(){clearTimeout(blinkTimer);clearTimeout(blinkEnd);blinkTimer=0;welcomeFace.classList.remove('blink');}
function scheduleBlink(){
 if(blinkTimer||!faceNear||!state?.prefs.motion||document.hidden||$('welcome').hidden)return;
 blinkTimer=setTimeout(()=>{blinkTimer=0;if(!faceNear||document.hidden||$('welcome').hidden)return;
  welcomeFace.classList.add('blink');blinkEnd=setTimeout(()=>{welcomeFace.classList.remove('blink');scheduleBlink();},120);
 },3500+Math.random()*4000);
}
document.addEventListener('pointermove',e=>{
 if($('welcome').hidden||document.hidden){faceNear=false;cancelBlink();return;}
 const r=welcomeFace.getBoundingClientRect(),dx=e.clientX-(r.x+r.width/2),dy=e.clientY-(r.y+r.height/2);
 faceNear=Math.hypot(dx,dy)<150;welcomeFace.classList.toggle('awake',faceNear);
 welcomeFace.querySelectorAll('i').forEach(eye=>eye.style.transform=faceNear&&state?.prefs.motion?`translate(${Math.max(-2.5,Math.min(2.5,dx/30))}px,${Math.max(-2,Math.min(2,dy/30))}px)`:'none');
 if(faceNear)scheduleBlink();else cancelBlink();
});
document.addEventListener('visibilitychange',()=>{if(document.hidden){saveDraft();faceNear=false;cancelBlink();}});
if(innerWidth<850)document.body.classList.add('sidebar-closed');
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{if(state)applyPrefs(state.prefs);});
new QWebChannel(qt.webChannelTransport,channel=>{
 bridge=channel.objects.bridge;
 bridge.event.connect(raw=>{
  const event=JSON.parse(raw);
  if(window.handleFeatureEvent && window.handleFeatureEvent(event))return;
  if(event.type==='state')acceptState(event);
  else if(event.type==='preferences'){state.prefs=event.prefs;applyPrefs(event.prefs);renderConnections();renderContext();if($('settings-dialog').open){$('pref-background').value=event.prefs.background;$('pref-dot-style').value=event.prefs.dot_style;$('logo-preview').hidden=!event.prefs.logo;if(event.prefs.logo)$('logo-preview').src=event.prefs.logo;}}
  else if(event.type==='error'||event.type==='notice')toast(event.message);
  else if(event.type==='api_saved'){$('api-status').textContent=event.message;pendingConnection=event.id;}
  else if(event.type==='api_status'){$('api-status').textContent=event.message;}
  else if(event.type==='file_picker_closed'){if(pickerReturn){openSettings(pickerReturn);pickerReturn=null;}}
  else if(event.type==='plugin_status'){$('plugin-status').textContent=event.message;}
  else if(event.type==='speech'){speaking=event.speaking;$('stop-speech').hidden=!speaking;}
  else if(event.type==='proposal'){state.proposal=event.proposal;renderProposal(event.proposal);$('scroll').scrollTop=$('scroll').scrollHeight;}
  else if(event.type==='open_settings')openSettings(event.tab||'appearance');
  else if(event.type==='preview'){$('screen-preview').hidden=!event.image;$('preview-empty').hidden=!!event.image;if(event.image)$('screen-preview').src=event.image;$('preview-dialog').showModal();}
 });send('ready');
});
sizePrompt();

function options(select,items,value){select.replaceChildren();for(const [id,label] of items){const o=document.createElement('option');o.value=id;o.textContent=label;select.append(o);}select.value=value;}
function modelOptions(id,profile){
 const screen=id==='api-screen-models'||(id==='quick-models'&&state.prefs.screen_enabled);
 options($(id),[...new Set([...(profile?.models||[]),profile?.model,profile?.vision_model].filter(Boolean))].filter(m=>{const c=profile?.capabilities?.[m]||{};return c.text!==false&&(!screen||c.vision!==false);}).map(m=>[m,m]),'');
 if(id==='api-models')modelOptions('api-screen-models',profile);
}
function renderConnections(){
 const c=state.connections, p=c.profiles.find(p=>p.id===c.active);
 const model=state.prefs.screen_enabled?p?.vision_model:p?.model;
 $('model-menu').textContent=(model||'Choose AI')+' ⌄';$('model-menu').title=p?`${p.name} · ${state.prefs.screen_enabled?'Screen model':'Chat model'}`:'Set up your API';$('model-menu').disabled=state.busy;
 if($('settings-dialog').open)modelOptions('api-models',c.profiles.find(p=>p.id===$('api-profile').value));
}
function fillConnections(id){
 const c=state.connections;const selected=id===undefined?(c.active||''):id;
 options($('api-profile'),[['','New connection'],...c.profiles.map(p=>[p.id,p.name])],selected);
 options($('api-preset'),Object.keys(c.provider_presets||c.presets).map(n=>[n,n]),'Groq');
 loadProfile(selected);
}
function providerPreset(name){const item=(state.connections.provider_presets||{})[name];return typeof item==='string'?{base_url:item,provider_type:'openai_compatible'}:(item||{base_url:state.connections.presets[name]||'',provider_type:'openai_compatible'});}
function applyProviderUI(name){const meta=providerPreset(name);const native=meta.provider_type==='anthropic';$('api-url').readOnly=native;$('api-tokens').disabled=native;$('api-reasoning').disabled=native;$('api-provider-note').textContent=native?'Native Anthropic Messages API · use a key from Anthropic Console. System instructions, images, tools, usage, and provider errors are handled directly.':'Uses this provider’s OpenAI-compatible API.';}
function loadProfile(id){
 const p=state.connections.profiles.find(p=>p.id===id);
 $('api-profile').value=id||'';$('api-name').value=p?.name||'';$('api-url').value=p?.base_url||state.connections.presets.Groq;
 $('api-key').value='';$('api-model').value=p?.model||'';$('api-vision').value=p?.vision_model||'';$('api-tools').checked=p?.tools||false;$('api-tokens').value=p?.token_parameter||'max_completion_tokens';
 $('api-preset').value=p?.provider_type==='anthropic'?'Anthropic':Object.entries(state.connections.presets).find(([n,url])=>url===$('api-url').value)?.[0]||'Custom';applyProviderUI($('api-preset').value);
 $('api-output').value=p?.output_limit||4096;$('api-reasoning').value=p?.reasoning||'';
 if(window.showProviderDetails)window.showProviderDetails(p);
 for(const name of ['api-load','api-delete','api-use','api-test','api-test-screen'])$(name).disabled=!p;
 modelOptions('api-models',p);
}
$('api-profile').onchange=()=>loadProfile($('api-profile').value);
$('api-new').onclick=()=>loadProfile('');
$('api-preset').onchange=()=>{const name=$('api-preset').value,meta=providerPreset(name);$('api-url').value=meta.base_url;$('api-name').value=name==='Custom'?'My API':name;$('api-key').value='';$('api-tokens').value=meta.provider_type==='anthropic'?'max_tokens':(name==='Groq'||name==='OpenAI'?'max_completion_tokens':'max_tokens');applyProviderUI(name);};
$('api-save').onclick=()=>{
 const key=$('api-key').value;$('api-key').value='';
 send('api_save',{id:$('api-profile').value,name:$('api-name').value,base_url:$('api-url').value,key,provider_type:providerPreset($('api-preset').value).provider_type,model:$('api-model').value,vision_model:$('api-vision').value,tools:$('api-tools').checked,token_parameter:$('api-tokens').value,output_limit:Number($('api-output').value),reasoning:$('api-reasoning').value});
};
$('api-load').onclick=()=>send('api_models',{id:$('api-profile').value});
$('api-use').onclick=()=>{send('api_select',{id:$('api-profile').value});toast('Connection selected.');};
$('api-delete').onclick=()=>send('api_delete',{id:$('api-profile').value});
function quickModel(){const p=state.connections.profiles.find(p=>p.id===$('quick-profile').value);$('quick-model').value=(state.prefs.screen_enabled?p?.vision_model:p?.model)||'';modelOptions('quick-models',p);$('quick-mode').textContent=state.prefs.screen_enabled?'Screen is on. Choose a model that accepts images.':'Screen is off. Choose a chat model.';}
$('model-menu').onclick=()=>{
 if(!state.connections.profiles.length){openSettings('models');return;}
 options($('quick-profile'),state.connections.profiles.map(p=>[p.id,p.name]),state.connections.active);quickModel();$('models-dialog').showModal();
};
$('quick-profile').onchange=quickModel;
$('quick-apply').onclick=()=>{if(!$('quick-model').value.trim()){toast('Choose a model first.');return;}send('api_select',{id:$('quick-profile').value,model:$('quick-model').value});$('models-dialog').close();};
$('manage-api').onclick=()=>{$('models-dialog').close();openSettings('models');};
$('rename-form').onsubmit=e=>{e.preventDefault();send('rename',{title:$('rename-title').value});$('rename-dialog').close();};
function renderContext(){
 const box=$('context-chips');box.replaceChildren();
 for(const [label,action] of [[state.attachment,'clear_attachment'],[state.focused?'Focused area'+(state.prefs.screen_enabled?'':' · paused'):'','clear_focus']]){
  if(!label)continue;const b=document.createElement('button');b.className='context-chip';b.textContent=label+' ×';b.title='Remove '+label;b.onclick=()=>send(action);box.append(b);
 }box.hidden=!box.children.length;
}
