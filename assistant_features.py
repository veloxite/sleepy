"""Voice, desktop actions, workspaces and music UI integration."""
import json
import re
import threading
from pathlib import Path
from PySide6.QtCore import Qt,QTimer,QBuffer,QIODevice,QUrl
from PySide6.QtWidgets import QFileDialog,QInputDialog,QMessageBox
from PySide6.QtMultimedia import QMediaPlayer,QAudioOutput
from desktop_actions import browsers,open_url,launch_app,safe_url,file_plan,execute_plan,explicit_action,installed_apps,open_workspace_urls
from windows_integration import WorkspaceLayout
from voice_input import Microphone,transcribe,neural_speech
from music_player import MusicPlayer,MusicIsland,search_tracks,stream_track
from web_media import youtube_results
from agent_core import friendly_error

class AssistantFeatures:
    def init_features(self):
        self.recording=False;self.mic_level=0;self.last_voice=False;self.voice_generation=0;self.pending_settings=None;self.page_ready=False
        self.microphone=Microphone(self)
        self.microphone.level.connect(self.mic_meter)
        self.microphone.finished.connect(self.transcribe_audio)
        self.microphone.failed.connect(self.mic_failed)
        self.voice_output=QAudioOutput(self);self.voice_player=QMediaPlayer(self);self.voice_player.setAudioOutput(self.voice_output)
        self.voice_player.playbackStateChanged.connect(lambda s:self.emit('speech',speaking=s==QMediaPlayer.PlayingState))
        self.voice_player.errorOccurred.connect(lambda _,m:self.emit('error',message='Voice playback: '+m))
        self.music=MusicPlayer(self);self.music.changed.connect(self.music_changed)
        self.music.failed.connect(lambda m:self.emit('error',message=m));self.music.advance.connect(self.music_step)
        self.music_island=MusicIsland(self)
        self.undo_plan=[];self.action_preview=None
        self.music_cancelled=False
        self.workspace_layout=WorkspaceLayout(self)

    def features_state(self):
        return {'apps':self.store.get('apps',[]),'presets':self.store.get('workspaces',[]),
                'installed_apps':[{'name':a['name']} for a in installed_apps()],
                'browsers':list(browsers()),'workspace_root':self.store.get('workspace_root',''),
                'music':self.music.state(),'action_preview':self.action_preview,'recording':self.recording}

    def feature_dispatch(self,data):
        action=data.get('action')
        if action=='credits_refresh':
            from provider_usage import credits
            config=self.connections.runtime(data.get('id'),require_model=False)
            self.job('credits:'+config['id'],lambda:credits(config))
        elif action=='mic_start':self.start_mic()
        elif action=='mic_stop':self.microphone.stop()
        elif action=='mic_cancel':self.microphone.stop(cancel=True);self.recording=False;self.face.update()
        elif action=='app_register':
            app=next((a for a in installed_apps() if a['name']==data.get('name')),None)
            if not app:raise ValueError('Choose an installed app from the list.')
            apps=[a for a in self.store.get('apps',[]) if a['name'].casefold()!=app['name'].casefold()]
            apps.append(dict(app));self.store.set('apps',apps);self.publish()
        elif action=='app_add':self.choose_feature_file('app')
        elif action=='app_remove':
            self.store.set('apps',[a for a in self.store.get('apps',[]) if a['name']!=data.get('name')]);self.publish()
        elif action=='workspace_root':self.choose_feature_file('folder')
        elif action=='preset_save':
            name=str(data.get('name','')).strip()[:60]
            if not name:raise ValueError('Give this workspace a name, such as Physics.')
            registered={a['name'] for a in self.store.get('apps',[])}
            apps=[str(a) for a in data.get('apps',[]) if a in registered][:15]
            urls=[safe_url(u) for u in str(data.get('urls','')).splitlines() if u.strip()][:10]
            if not apps and not urls:raise ValueError('Choose at least one app or website for this workspace.')
            presets=[p for p in self.store.get('workspaces',[]) if p['name'].casefold()!=name.casefold()]
            presets.append({'name':name,'apps':apps,'urls':urls});self.store.set('workspaces',presets);self.publish()
            self.emit('notice',message='Workspace saved. Say “Open my '+name+' preset”.')
        elif action=='preset_remove':
            self.store.set('workspaces',[p for p in self.store.get('workspaces',[]) if p['name']!=data.get('name')]);self.publish()
        elif action=='preset_open':self.execute_action({'kind':'open_preset','name':data.get('name')})
        elif action=='desktop_confirm':self.confirm_desktop(data.get('id'))
        elif action=='desktop_cancel':self.action_preview=None;self.publish()
        elif action=='music_local':self.choose_feature_file('music')
        elif action=='music_service':
            self.save_settings({'music_service':str(data.get('service','none'))})
            if data.get('service')=='none':self.music_cancelled=True;self.music.stop();self.music.queue=[];self.music_changed()
            self.publish()
        elif action=='music_search':self.execute_action({'kind':'play_music','query':str(data.get('query',''))})
        elif action in ('music_pause','music_resume','music_next','music_previous','music_close'):self.execute_action({'kind':action})
        elif action=='music_open':
            url=self.music.state().get('url')
            if url and url.startswith('https://'):open_url(url,self.prefs['browser'])
        elif action=='open_youtube':open_url(str(data.get('url','')),self.prefs['browser'])
        else:return False
        return True

    def choose_feature_file(self,kind):
        if self.file_dialog:return
        dialog=QFileDialog(self,{'app':'Choose an app','folder':'Choose your file workspace','music':'Choose audio files'}[kind]);self.file_dialog=dialog
        dialog.setOption(QFileDialog.DontUseNativeDialog,True)
        dialog.setFileMode(QFileDialog.Directory if kind=='folder' else QFileDialog.ExistingFiles if kind=='music' else QFileDialog.ExistingFile)
        if kind=='app':dialog.setNameFilter('Applications (*.exe *.lnk *.app *.desktop);;All files (*)')
        if kind=='music':dialog.setNameFilter('Audio (*.mp3 *.wav *.flac *.ogg *.m4a *.aac)')
        def selected(paths):
            if not paths:return
            if kind=='folder':self.store.set('workspace_root',str(Path(paths[0]).resolve()))
            elif kind=='app':
                path=str(Path(paths[0]).resolve());name,ok=QInputDialog.getText(self,'Name this app','What should Sleepy call it?',text=Path(path).stem)
                if ok and name.strip():
                    apps=[a for a in self.store.get('apps',[]) if a['name'].casefold()!=name.strip().casefold()]
                    apps.append({'name':name.strip()[:60],'path':path});self.store.set('apps',apps)
            else:
                self.music_cancelled=False
                self.music.queue=[{'title':Path(p).stem,'artist':'Local audio','url':str(Path(p).resolve()),'local':True} for p in paths][:200]
                self.music.index=0;self.music.play_url(self.music.queue[0]['url'])
            self.publish()
        dialog.filesSelected.connect(selected)
        def closed(_):self.file_dialog=None;dialog.deleteLater()
        dialog.finished.connect(closed);dialog.open()

    def execute_action(self,action):
        kind=action.get('kind')
        if kind=='open_website':open_url(action.get('url',''),self.prefs['browser']);return 'Opened the website in '+self.prefs['browser']+'.'
        if kind=='open_app':
            app=next((a for a in self.store.get('apps',[]) if a['name'].casefold()==str(action.get('name','')).casefold()),None)
            if not app:raise ValueError('Add that app in Settings → Workspaces first, so Sleepy knows exactly what to open.')
            launch_app(app['path']);return 'Opened '+app['name']+'.'
        if kind=='open_preset':
            preset=next((p for p in self.store.get('workspaces',[]) if p['name'].casefold()==str(action.get('name','')).casefold()),None)
            if not preset:raise ValueError('That workspace was not found. Create it in Settings → Workspaces.')
            jobs=[]
            for name in preset['apps']:
                jobs.append((name,lambda n=name:self.execute_action({'kind':'open_app','name':n})))
            if preset['urls']:
                urls=list(preset['urls']);browser=self.prefs['browser']
                jobs.append(('Browser',lambda:open_workspace_urls(urls,browser)))
            self.workspace_layout.start(jobs)
            return 'Opening '+preset['name']+' and arranging its windows together…'
        if kind in ('create_folder','rename_file','organize_pdfs'):
            root=self.store.get('workspace_root','')
            if not root:raise ValueError('Choose a file workspace in Settings → Workspaces first.')
            plan=file_plan(root,action)
            import uuid
            self.action_preview={'id':uuid.uuid4().hex,'action':action,'root':root,'chat_id':self.chat_id,
                                 'lines':[(str(source.relative_to(Path(root)))+' → ' if source else 'Create folder: ')+str(target.relative_to(Path(root))) for _,source,target in plan]}
            self.publish();return 'Review the file changes below before applying them.'
        if kind in ('youtube','youtube_play'):
            query=str(action.get('query','')).strip()[:200]
            if not query:raise ValueError('Tell Sleepy what video to find.')
            self.media_chat=self.chat_id;self.job(kind,lambda:youtube_results(query));return 'Searching YouTube for '+query+'…'
        if kind=='play_music':
            query=str(action.get('query','')).strip()[:200]
            if not query:raise ValueError('Tell Sleepy the song title and artist.')
            if self.prefs['music_service']!='soundcloud':
                raise ValueError('Choose SoundCloud in Settings → Music, or add local audio files there.')
            self.music_cancelled=False;self.job('music_search',lambda:search_tracks(query));return 'Looking for a public SoundCloud track matching '+query+'…'
        if kind=='music_close':
            self.music_cancelled=True;self.music.queue=[];self.music.stop();return 'Music closed.'
        if kind=='music_pause':self.music_cancelled=True;self.music.player.pause();return 'Music paused.'
        if kind=='music_resume':self.music_cancelled=False;self.music.player.play();return 'Resuming the selected track.'
        if kind in ('music_next','music_previous'):self.music_step(1 if kind=='music_next' else -1);return 'Changing track.'
        raise ValueError('That desktop action is not supported yet.')

    def confirm_desktop(self,identifier):
        preview=self.action_preview
        if not preview or identifier!=preview['id']:return
        if preview.get('model_proposal'):
            self.action_preview=None
            answer=self.execute_action(preview['action'])
            self.store.add(preview['chat_id'],'assistant',answer);self.publish();return
        plan=file_plan(preview['root'],preview['action'])
        lines=[(str(s.relative_to(Path(preview['root'])))+' → ' if s else 'Create folder: ')+str(t.relative_to(Path(preview['root']))) for _,s,t in plan]
        if lines!=preview['lines']:raise ValueError('The files changed since this review. Ask Sleepy to prepare a fresh plan.')
        execute_plan(plan);self.action_preview=None
        self.store.add(preview['chat_id'],'assistant',f'Completed {len(plan)} file change(s).');self.publish()

    def start_mic(self):
        if self.busy or 'transcribe' in self.jobs:return
        profiles=self.connections.profiles()
        profile=next((p for p in profiles if p['id']==self.prefs.get('speech_connection')),None)
        if profile is None:profile=next((p for p in profiles if p['base_url'] in ('https://api.groq.com/openai/v1','https://api.openai.com/v1')),None)
        if profile is None:
            self.open_settings('voice');raise ValueError('Choose a Groq or OpenAI connection for voice input in Settings → Voice.')
        self.speech_config=self.connections.runtime(profile['id'],require_model=False)
        self.stop_voice();self.microphone.start();self.recording=True;self.face.update();self.emit('mic',recording=True)

    def mic_meter(self,level):
        self.mic_level=level
        if hasattr(self,'face'):self.face.update()

    def mic_failed(self,message):
        self.recording=False;self.emit('mic',recording=False);self.emit('error',message=message);self.face.update()

    def transcribe_audio(self,audio):
        self.recording=False;self.emit('mic',recording=False);self.face.update()
        config=self.speech_config;self.speech_config=None
        self.job('transcribe',lambda:transcribe(config,audio))
        self.emit('notice',message='Transcribing… microphone is off.')

    def stop_voice(self):
        self.voice_generation+=1
        if hasattr(self,'voice_cancel'):self.voice_cancel.set()
        self.speech.stop();self.voice_player.stop();self.voice_player.setSource(QUrl())
        if hasattr(self,'voice_buffer'):self.voice_buffer.close();self.voice_buffer.deleteLater();del self.voice_buffer

    def read_aloud(self,text):
        self.stop_voice()
        if self.prefs.get('voice_engine')=='neural':
            cancel=threading.Event();self.voice_cancel=cancel
            self.job('tts:'+str(self.voice_generation),lambda:neural_speech(text,self.prefs['neural_voice'] if self.prefs['neural_voice'] in ('en-US-AriaNeural','en-US-GuyNeural','en-GB-SoniaNeural','en-GB-RyanNeural') else 'en-US-AriaNeural',self.prefs['speech_rate'],cancel))
        else:
            self.speech.setRate(float(self.prefs['speech_rate']))
            voice=next((v for v in self.speech.availableVoices() if v.name()==self.prefs['speech_voice'] and v.locale().name() in ('en_US','en_GB')),None)
            voice=voice or next((v for v in self.speech.availableVoices() if v.locale().name() in ('en_US','en_GB')),None)
            if voice is None:raise ValueError('Install an English US or UK system voice, or choose a Natural voice.')
            self.speech.setVoice(voice);self.speech.say(text)

    def audio_busy(self):
        return self.recording or self.voice_player.playbackState()==QMediaPlayer.PlayingState

    def music_step(self,step):
        if not self.music.queue:raise ValueError('Choose a track first.')
        if 'music_stream' in self.jobs:return
        self.music_cancelled=False
        self.music.index=(self.music.index+step)%len(self.music.queue)
        track=dict(self.music.queue[self.music.index]);self.music.player.stop()
        self.job('music_stream',lambda:stream_track(track))

    def music_changed(self):
        if not self.music.state()['active']:self.music_island.hide()
        else:self.music_island.refresh()
        self.emit('music',music=self.music.state())
        if hasattr(self,'face'):self.face.update()

    def feature_completed(self,name,result):
        if name.startswith('credits:'):
            if result['ok']:
                balances=self.store.get('api_credits',{});balances[name.split(':',1)[1]]=result['value'];self.store.set('api_credits',balances);self.publish()
            else:self.emit('error',message=result['error'])
        elif name=='transcribe':
            if result['ok']:
                self.last_voice=True;self.show_chat();self.emit('transcript',text=result['value'],autosent=self.prefs.get('voice_send',True))
                if self.prefs.get('voice_send',True):
                    try:self.send(result['value'])
                    except Exception as e:self.emit('error',message=friendly_error(e))
            else:self.emit('error',message=result['error'])
        elif name.startswith('tts:'):
            if int(name.split(':')[1])!=self.voice_generation:return True
            if result['ok']:
                self.voice_buffer=QBuffer(self);self.voice_buffer.setData(result['value']);self.voice_buffer.open(QIODevice.ReadOnly)
                self.voice_player.setSourceDevice(self.voice_buffer,QUrl('voice.mp3'));self.voice_player.play()
            else:self.emit('error',message='Natural voice unavailable: '+result['error']+' You can select System voice in Settings.')
        elif name=='music_search':
            if self.music_cancelled:return True
            if result['ok']:
                self.music.queue=result['value'];self.music.index=0;self.music_step(0)
            else:self.emit('error',message=result['error'])
        elif name=='music_stream':
            if self.music_cancelled:return True
            if result['ok']:self.music.play_url(result['value'])
            else:self.emit('error',message=result['error'])
        elif name in ('youtube','youtube_play'):
            if result['ok']:
                if name=='youtube_play':
                    first=result['value'][0];open_url(first['url']+'&autoplay=1',self.prefs['browser'])
                    self.store.add(self.media_chat,'assistant','Opened the top YouTube match: '+first['title']+'. Your browser may require a click to start playback.')
                self.store.add(self.media_chat,'assistant','```videos\n'+json.dumps(result['value'])+'\n```');self.publish()
            else:self.emit('error',message=result['error'])
        else:return False
        return True
