'use strict';
function featureSection(name,title,html){
 const tab=document.createElement('button');tab.dataset.tab=name;tab.textContent=title;tab.onclick=()=>selectTab(name);document.querySelector('.settings-tabs').append(tab);
 const section=document.createElement('section');section.dataset.section=name;section.hidden=true;section.innerHTML=html;document.querySelector('.settings-content').append(section);
}
featureSection('workspaces','Workspaces',`<h3>Settle into your workspace.</h3><p>Save the apps and websites you use together. Say “Open my Physics preset”.</p>
<label>Open websites with<select id="feature-browser"></select></label>
<div class="plugin-card"><strong>Your apps</strong><p>Choose apps once, then open them by name.</p><div id="feature-apps"></div><label>Installed app<select id="installed-app"></select></label><button class="secondary" id="app-register">Add selected app</button><button class="text-button" id="app-add">Browse for another app</button></div>
<div class="plugin-card"><strong>File workspace</strong><p>Folder creation, renaming and PDF organization stay inside this folder. You review changes before applying them.</p><p id="workspace-path" class="note"></p><button class="secondary" id="workspace-choose">Choose folder</button></div>
<div class="plugin-card"><strong>Workspace presets</strong><div id="preset-list"></div><label>Name<input id="preset-name" placeholder="Physics"></label><label>Apps</label><div id="preset-apps"></div><label>Websites · one per line<textarea id="preset-urls" rows="3" placeholder="https://www.khanacademy.org"></textarea></label><button class="primary" id="preset-save">Save workspace</button></div>`);
featureSection('music','Music',`<h3>A soundtrack for your work.</h3><p>Choose a source. No developer credentials or API forms.</p><div class="music-services"><button class="service-tile" id="connect-soundcloud"><strong>☁ SoundCloud</strong><small>Play publicly available tracks</small></button><button class="service-tile" id="connect-local"><strong>♫ Your music</strong><small>Choose audio files on this device</small></button></div><p id="music-service-status" class="note"></p><p class="note">SoundCloud access is for public tracks, not an account login. Availability and previews vary; subscription tracks may need the website.</p><div class="inline"><input id="music-query" placeholder="Song, artist, or mood — try party music" aria-label="Find a song"><button class="primary" id="music-find">Play</button></div><div id="music-now" class="plugin-card"></div><button class="text-button" id="music-disconnect">Disconnect SoundCloud</button>`);
const voice=document.querySelector('[data-section=voice]');
const extra=document.createElement('div');extra.innerHTML=`<label>Read-aloud voice<select id="feature-voice-engine"><option value="system">System voice · offline</option><option value="neural">Natural voice · online, no API key</option></select></label><label>Natural voice<select id="feature-neural"><option value="en-US-AriaNeural">Aria · English (US)</option><option value="en-US-GuyNeural">Guy · English (US)</option><option value="en-GB-SoniaNeural">Sonia · English (UK)</option><option value="en-GB-RyanNeural">Ryan · English (UK)</option></select></label><p class="note">Natural voice sends the text to Microsoft's online speech service. It works without Windows or Edge, but requires internet and service availability. System voice stays on your device.</p><h3>Hold to talk.</h3><p>Hold the companion for a moment, speak, and release. The microphone switches off on release, or after 30 seconds. Drag immediately to move the companion.</p><label>Speech recognition connection<select id="feature-speech"></select></label><p class="note">Audio is sent to your selected Groq or OpenAI speech service after release, then discarded. Speech uses that provider's quota. No always-on listening.</p><label class="check"><input type="checkbox" id="feature-voice-send">Send automatically after speaking</label><label class="check"><input type="checkbox" id="feature-voice-reply">Read replies to voice messages aloud</label>`;voice.append(extra);
const mic=document.createElement('button');mic.id='talk-button';mic.className='icon';mic.title='Hold to talk';mic.setAttribute('aria-label','Hold to talk');mic.innerHTML='<svg viewBox="0 0 24 24"><rect x="9" y="2" width="6" height="13" rx="3"/><path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3m-4 0h8"/></svg>';$('preview-button').after(mic);
mic.onpointerdown=e=>{e.preventDefault();mic.setPointerCapture(e.pointerId);send('mic_start');};mic.onpointerup=()=>send('mic_stop');mic.onpointercancel=()=>send('mic_stop');mic.onlostpointercapture=()=>send('mic_stop');
mic.onkeydown=e=>{if(e.code==='Space'&&!e.repeat){e.preventDefault();send('mic_start');}};mic.onkeyup=e=>{if(e.code==='Space'){e.preventDefault();send('mic_stop');}};
window.addEventListener('blur',()=>send('mic_stop'));
$('app-add').onclick=()=>send('app_add');$('app-register').onclick=()=>send('app_register',{name:$('installed-app').value});$('workspace-choose').onclick=()=>send('workspace_root');
$('preset-save').onclick=()=>send('preset_save',{name:$('preset-name').value,apps:[...document.querySelectorAll('#preset-apps input:checked')].map(x=>x.value),urls:$('preset-urls').value});
$('connect-soundcloud').onclick=()=>send('music_service',{service:'soundcloud'});$('connect-local').onclick=()=>send('music_local');$('music-disconnect').onclick=()=>send('music_service',{service:'none'});$('music-find').onclick=()=>send('music_search',{query:$('music-query').value});
function featurePrefs(){return {browser:$('feature-browser').value,voice_engine:$('feature-voice-engine').value,neural_voice:$('feature-neural').value,speech_connection:$('feature-speech').value,voice_send:$('feature-voice-send').checked,voice_reply:$('feature-voice-reply').checked};}
window.featurePrefs=featurePrefs;
window.fillFeatureSettings=function(){
 if(!state)return;options($('feature-browser'),(state.features?.browsers||['System default']).map(x=>[x,x]),state.prefs.browser);
 $('feature-voice-engine').value=state.prefs.voice_engine;$('feature-neural').value=['en-US-AriaNeural','en-US-GuyNeural','en-GB-SoniaNeural','en-GB-RyanNeural'].includes(state.prefs.neural_voice)?state.prefs.neural_voice:'en-US-AriaNeural';
 options($('feature-speech'),[['','Automatically choose Groq or OpenAI'],...state.connections.profiles.filter(p=>p.base_url==='https://api.groq.com/openai/v1'||p.base_url==='https://api.openai.com/v1').map(p=>[p.id,p.name])],state.prefs.speech_connection);
 $('feature-voice-send').checked=state.prefs.voice_send;$('feature-voice-reply').checked=state.prefs.voice_reply;
};
function actionButton(label,fn){const b=document.createElement('button');b.className='secondary';b.textContent=label;b.onclick=fn;return b;}
function renderMusic(music){
 const box=$('music-now');box.replaceChildren();const title=document.createElement('strong');title.textContent=music.title||'Nothing playing';const artist=document.createElement('p');artist.textContent=music.artist||'';box.append(title,artist);
 if(music.active){const controls=document.createElement('div');controls.className='inline';for(const [label,action]of [['Previous','music_previous'],[music.playing?'Pause':'Resume',music.playing?'music_pause':'music_resume'],['Next','music_next'],['Close','music_close']])controls.append(actionButton(label,()=>send(action)));box.append(controls);if(music.url.startsWith('https://'))box.append(actionButton('Open on SoundCloud ↗',()=>send('music_open')));}
}
window.renderFeatures=function(){
 if(!state?.features)return;const f=state.features;
 if($('settings-dialog').open||$('feature-dialog')?.open){
 $('workspace-path').textContent=f.workspace_root||'No folder selected';$('feature-apps').replaceChildren();
 for(const app of f.apps){const row=document.createElement('div');row.className='feature-row';const label=document.createElement('span');label.textContent=app.name;row.append(label,actionButton('Remove',()=>send('app_remove',{name:app.name})));$('feature-apps').append(row);}
 options($('installed-app'),f.installed_apps.map(a=>[a.name,a.name]),$('installed-app').value||f.installed_apps[0]?.name);
 const selected=new Set([...document.querySelectorAll('#preset-apps input:checked')].map(x=>x.value));$('preset-apps').replaceChildren();
 for(const app of f.apps){const label=document.createElement('label');label.className='check';const input=document.createElement('input');input.type='checkbox';input.value=app.name;input.checked=selected.has(app.name);label.append(input,document.createTextNode(app.name));$('preset-apps').append(label);}
 $('preset-list').replaceChildren();for(const preset of f.presets){const row=document.createElement('div');row.className='feature-row';const label=document.createElement('strong');label.textContent=preset.name;row.append(label,actionButton('Open',()=>send('preset_open',{name:preset.name})),actionButton('Edit',()=>{$('preset-name').value=preset.name;$('preset-urls').value=preset.urls.join('\n');document.querySelectorAll('#preset-apps input').forEach(x=>x.checked=preset.apps.includes(x.value));}),actionButton('Remove',()=>send('preset_remove',{name:preset.name})));$('preset-list').append(row);}
 $('connect-soundcloud').classList.toggle('selected',state.prefs.music_service==='soundcloud');$('connect-soundcloud').setAttribute('aria-pressed',String(state.prefs.music_service==='soundcloud'));$('connect-soundcloud').querySelector('small').textContent=state.prefs.music_service==='soundcloud'?'✓ Selected · saved automatically':'Play publicly available tracks';
 $('music-service-status').textContent=state.prefs.music_service==='soundcloud'?'SoundCloud selected · say “Play song title by artist”':'Choose SoundCloud or local audio to start.';renderMusic(f.music);
 }
 const box=$('desktop-action');box.replaceChildren();const preview=f.action_preview;
 if(preview){const card=document.createElement('div');card.className='repo-card';const title=document.createElement('strong');title.textContent='Review action';const details=document.createElement('pre');details.textContent=preview.lines.join('\n');card.append(title,details,actionButton('Continue',()=>send('desktop_confirm',{id:preview.id})),actionButton('Cancel',()=>send('desktop_cancel')));box.append(card);}
};
window.handleFeatureEvent=function(event){
 if(event.type==='error')$('api-load').disabled=false;
 if(event.type==='welcome_guide'){showWelcomeGuide();return true;}
 if(event.type==='api_catalog'){
  if(event.request_id!==catalogRequest)return true;
  $('api-load').disabled=false;
  if(event.error){$('api-status').textContent=event.error;return true;}
  modelOptions('api-models',event.catalog);refreshModelPickers();
  $('api-status').textContent='Models loaded. Choose chat and screen models, then save everything together.';return true;
 }
 if(event.type==='mic'){mic.classList.toggle('listening',event.recording);mic.title=event.recording?'Listening · release to send':'Hold to talk';return true;}
 if(event.type==='transcript'){$('prompt').value=event.autosent?'':event.text;sizePrompt();if(!event.autosent)saveDraft();return true;}
 if(event.type==='music'){if(state?.features)state.features.music=event.music;if($('feature-dialog')?.open)renderMusic(event.music);return true;}
 return false;
};
window.renderMedia=function(code,kind,raw){
 if(!['web-images-results','videos'].includes(kind))return false;
 const box=document.createElement('div');box.className='web-results';
 try{const items=JSON.parse(raw);if(!Array.isArray(items)||items.length>8)throw Error('Invalid results');
 for(const item of items){const source=kind==='videos'?item.url:item.source;const parsed=new URL(source);if(parsed.protocol!=='https:'||!(kind==='videos'?parsed.hostname==='www.youtube.com':parsed.hostname==='commons.wikimedia.org'))continue;
 const card=document.createElement('div');card.className='web-result';
 if(kind==='web-images-results'&&/^data:image\/jpeg;base64,[A-Za-z0-9+/=]+$/.test(item.image)&&item.image.length<500000){const img=document.createElement('img');img.src=item.image;img.alt=item.title;img.loading='lazy';card.append(img);}
 const link=document.createElement('a');link.href=source;link.textContent=item.title;const credit=document.createElement('small');credit.textContent=kind==='videos'?item.author:[item.credit,item.license].filter(Boolean).join(' · ');card.append(link,credit);box.append(card);
 }}catch{box.textContent='These search results could not be displayed. Ask Sleepy to search again.';}
 code.parentElement.replaceWith(box);return true;
};
if(state){fillFeatureSettings();renderFeatures();}

const rail=document.createElement('nav');rail.id='app-rail';rail.setAttribute('aria-label','Sleepy navigation');
icons.music='<path d="M9 18V5l12-2v13M9 9l12-2"/><ellipse cx="6" cy="18" rx="3" ry="3"/><ellipse cx="18" cy="16" rx="3" ry="3"/>';
for(const [tab,label,icon] of [['chat','Chats','panel'],['models','Models & APIs','spark'],['workspaces','Workspaces','models'],['plugins','Plugins','plug'],['music','Music','music'],['appearance','Settings','settings']]){
 const b=document.createElement('button');b.className='rail-button';b.title=label;b.setAttribute('aria-label',label);b.innerHTML='<svg viewBox="0 0 24 24">'+icons[icon]+'</svg>';b.onclick=()=>tab==='chat'?document.querySelector('[data-command=sidebar]').click():openSettings(tab);rail.append(b);
}
$('app').prepend(rail);
$('feature-browser').onchange=()=>send('settings',{values:{browser:$('feature-browser').value}});

// Feature destinations have their own dialog; Settings only holds preferences.
const destinations={models:'Models & APIs',workspaces:'Workspaces',plugins:'Plugins',music:'Music'};
const featureDialog=document.createElement('dialog');featureDialog.id='feature-dialog';
featureDialog.innerHTML='<div class="dialog-heading"><h2 tabindex="-1"></h2><button class="icon" aria-label="Close">×</button></div><div class="feature-content"></div>';
featureDialog.querySelector('button').onclick=()=>featureDialog.close();document.body.append(featureDialog);
const originalOpenSettings=openSettings;
openSettings=function(tab='appearance'){
 if(!destinations[tab]){originalOpenSettings(tab);return;}
 if(!state)return;
 saveDraft();document.querySelectorAll('dialog[open]').forEach(d=>d.close());
 fillSettings();
 for(const name of Object.keys(destinations)){
  const section=document.querySelector(`[data-section="${name}"]`);
  featureDialog.querySelector('.feature-content').append(section);section.hidden=name!==tab;
 }
 featureDialog.querySelector('h2').textContent=destinations[tab];featureDialog.showModal();
 renderFeatures();featureDialog.querySelector('h2').focus({preventScroll:true});featureDialog.querySelector('.feature-content').scrollTop=0;
};
for(const name of Object.keys(destinations))document.querySelector(`[data-tab="${name}"]`)?.remove();
document.querySelector('.side-bottom [data-command="plugins"]')?.remove();
for(const button of rail.querySelectorAll('button'))button.dataset.tooltip=button.getAttribute('aria-label');

let catalogRequest='';
const apiSection=document.querySelector('[data-section="models"]');
const apiSaveRow=$('api-save').parentElement;
apiSection.insertBefore($('api-model').closest('label'),apiSaveRow);
apiSection.insertBefore($('api-vision').closest('label'),apiSaveRow);
$('api-save').textContent='Save connection and models';
for(const note of apiSection.querySelectorAll('p'))if(note.textContent.startsWith('Save again'))note.textContent='Choose models from your provider, or enter a custom model ID. Screen context needs an image-capable model.';
function refreshModelPickers(){
 for(const [inputId,listId] of [['api-model','api-models'],['api-vision','api-screen-models']]){
  let picker=$(inputId+'-picker');
  if(!picker){picker=document.createElement('select');picker.id=inputId+'-picker';picker.setAttribute('aria-label',inputId==='api-model'?'Available chat models':'Available screen models');$(inputId).before(picker);picker.onchange=()=>{if(picker.value)$(inputId).value=picker.value;};}
  options(picker,[['','Choose an available model'],...[...$(listId).options].map(o=>[o.value,o.value])],$(inputId).value);
 }
}
const originalLoadProfile=loadProfile;
loadProfile=function(id){originalLoadProfile(id);$('api-load').disabled=false;refreshModelPickers();};
$('api-load').textContent='Find available models';
$('api-load').onclick=()=>{
 catalogRequest=String(Date.now());$('api-load').disabled=true;$('api-status').textContent='Fetching available models…';
 send('api_catalog_preview',{request_id:catalogRequest,id:$('api-profile').value,base_url:$('api-url').value,key:$('api-key').value,provider_type:providerPreset($('api-preset').value).provider_type});
};
$('api-key').addEventListener('change',()=>{if($('api-key').value.trim())$('api-load').click();});
const originalPresetChange=$('api-preset').onchange;
$('api-preset').onchange=()=>{catalogRequest='';originalPresetChange();$('api-model').value='';$('api-vision').value='';modelOptions('api-models',null);refreshModelPickers();$('api-load').disabled=false;};

function showWelcomeGuide(){
 const dialog=document.createElement('dialog');dialog.className='welcome-guide';
 dialog.innerHTML='<div class="dialog-heading"><h2>Welcome to Sleepy</h2></div><div class="picker-body"><p>Want a quick guide to your new desktop companion?</p><button class="primary" id="guide-start">Show me around</button> <button class="secondary" id="guide-skip">Skip</button><div id="guide-content" hidden><h3>Connect your AI</h3><p>Open Models & APIs in the left rail. Choose a provider, paste your own API key, and find available models. Choose a chat model and an image-capable screen model, then save. Your key is kept in the system credential vault. Provider charges and limits apply.</p><h3>Your screen</h3><p>Enable Screen on to include a fresh screenshot when you send a message. Select a screen area for small text. Turn it off for ordinary chat. Screenshots go to your selected AI provider.</p><h3>Apps, browser and workspaces</h3><p>Open Workspaces. Select your default browser under Open websites with. Add installed apps. Create a named preset with apps and website addresses, then say “Open my Physics preset”. Window arrangement depends on your desktop; Wayland may restrict it.</p><h3>Files and plugins</h3><p>Choose a file workspace folder before asking to create folders, rename files or organize PDFs. Review proposed changes. Plugins includes GitHub connection and repository creation, document attachments, and chat export.</p><h3>Voice and music</h3><p>Hold the ball or microphone button to speak; release to finish. A working microphone is required. Configure voices in Settings. Use Music to select SoundCloud or local files; pause, resume or close playback there.</p><h3>Study and chat</h3><p>Ask for a flowchart, use /flashcards to study or /eli5 for a simple explanation. Rename or delete conversations from chat history. Settings holds appearance, companion, voice, memories and privacy preferences.</p><h3>Permissions and help</h3><p>On macOS allow Screen Recording for screenshots, Microphone for voice and Accessibility for window controls in System Settings → Privacy & Security. Restart Sleepy after permission changes. On Linux choose a screen when prompted by your desktop and check Sound → Input if recording fails. If an API request fails, check the displayed error, selected model, key and provider quota.</p><button class="primary" id="guide-done">Start using Sleepy</button></div></div>';
 document.body.append(dialog);dialog.showModal();
 const finish=()=>{dialog.close();dialog.remove();};dialog.querySelector('#guide-skip').onclick=finish;dialog.querySelector('#guide-done').onclick=finish;
 dialog.querySelector('#guide-start').onclick=()=>{dialog.querySelector('#guide-content').hidden=false;dialog.querySelector('#guide-start').hidden=true;dialog.querySelector('#guide-skip').hidden=true;};
 dialog.addEventListener('cancel',()=>dialog.remove());
}
