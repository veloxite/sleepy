"""Desktop feature checks; no real microphone capture or personal file edits."""
import json
import tempfile
import wave
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import Qt,QPoint
from PySide6.QtTest import QTest
from PySide6.QtMultimedia import QMediaPlayer
from tests.check_sleepy import app,js,pump
from sleepy_app import SleepyWindow
from local_store import Store

def run():
    with tempfile.TemporaryDirectory() as folder,patch('windows_integration.SideBySide.arrange'):
        root=Path(folder);store=Store(root/'test.db');store.set('api_profiles',[])
        store.set('screen_enabled',False);store.set('voice_engine','system');store.set('workspace_root',str(root))
        store.set('apps',[{'name':'Calculator','path':'test-app'}]);store.set('workspaces',[{'name':'Physics','apps':['Calculator'],'urls':['https://example.com']}])
        w=SleepyWindow(store);errors=[];w.page.javaScriptConsoleMessage=lambda l,m,n,s:errors.append(m)
        w.show();pump(2)
        try:
            assert store.chats()==[]
            for _ in range(3):w.dispatch({'action':'new'})
            assert store.chats()==[]
            w.resize(460,740);pump()
            for tab in ('appearance','voice','models','workspaces','music'):
                js(w,'(openSettings('+json.dumps(tab)+'),true)');pump()
                bounds=js(w,"(()=>{const d=$('settings-dialog').getBoundingClientRect();return {left:d.left,right:d.right,w:innerWidth,overflow:$('settings-dialog').scrollWidth>$('settings-dialog').clientWidth}})()")
                assert bounds['left']>=0 and bounds['right']<=bounds['w'] and not bounds['overflow'],(tab,bounds)
            assert js(w,"document.querySelectorAll('#feature-apps .feature-row').length")==1
            with patch.object(w.workspace_layout,'start') as arrange,patch('assistant_features.launch_app') as launch,patch('assistant_features.open_workspace_urls') as opened:
                w.send('Sleepy open my Physics preset');jobs=arrange.call_args.args[0]
                for _,callback in jobs:callback()
                launch.assert_called_once_with('test-app');opened.assert_called_once_with(['https://example.com'],'System default')
            assert js(w,"$('app-rail').querySelectorAll('button').length")==6
            assert js(w,"[...$('feature-neural').options].every(o=>/^en-(US|GB)-/.test(o.value))")
            assert js(w,"document.querySelector('.settings-tabs').clientWidth > $('settings-dialog').clientWidth * .9")
            w.feature_dispatch({'action':'music_service','service':'soundcloud'});pump()
            js(w,"(openSettings('music'),$('save-settings').click(),true)");pump()
            assert js(w,"$('connect-soundcloud').getAttribute('aria-pressed')==='true' && $('settings-dialog').open")
            w.grab().save(str(Path(tempfile.gettempdir())/'sleepy-settings-update.png'))
            # Renaming is staged, then happens only after the matching review.
            (root/'a.pdf').write_bytes(b'fixture')
            w.execute_action({'kind':'rename_file','source':'a.pdf','target':'b.pdf'})
            assert (root/'a.pdf').exists() and not (root/'b.pdf').exists()
            w.confirm_desktop(w.action_preview['id']);assert (root/'b.pdf').exists()
            # A discarded renderer must reopen directly to Settings.
            js(w,"($('settings-dialog').close(),true)");w.hide();pump();w.freeze_page();w.discard_page();pump()
            assert not w.page_ready
            w.open_settings('voice');pump(2)
            assert js(w,"$('settings-dialog').open && !document.querySelector('[data-section=voice]').hidden")
            js(w,"($('settings-dialog').close(),true)")
            with patch.object(w,'start_mic') as start,patch.object(w.microphone,'stop') as stop:
                QTest.mousePress(w.face,Qt.LeftButton,Qt.NoModifier,QPoint(30,30));pump(.5)
                start.assert_called_once();QTest.mouseRelease(w.face,Qt.LeftButton,Qt.NoModifier,QPoint(30,30));stop.assert_called_once()
            # Real local music state drives the island. Silent fixture, output muted.
            track=root/'silence.wav'
            with wave.open(str(track),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(b'\0\0'*16000*5)
            w.music.output.setVolume(0);w.music.queue=[{'title':'Test track','artist':'Fixture','url':str(track),'local':True}]
            w.music.play_url(str(track));pump(.8)
            assert w.music.state()['playing']
            w.music_island.reveal();assert w.music_island.isVisible()
            w.execute_action({'kind':'music_pause'});pump();position=w.music.player.position()
            pump(.4);assert w.music.player.position()==position and w.music.player.playbackState()==QMediaPlayer.PausedState
            w.music_island.reveal();assert w.music_island.isVisible() and w.music_island.pause.toolTip()=='Resume'
            w.music_island.grab().save(str(Path(tempfile.gettempdir())/'sleepy-island-update.png'))
            w.execute_action({'kind':'music_resume'});pump(.3);assert w.music.player.position()>position
            w.execute_action({'kind':'music_close'});pump();assert not w.music_island.isVisible() and not w.music.state()['active']
            assert not [e for e in errors if 'Uncaught' in e],errors
            print('PASS: empty chat lifecycle, compact settings, settings after discard, workspace launch, reviewed rename, ball hold/release, real music state/island')
        finally:
            w.closed=True;w.microphone.stop(cancel=True);w.music.stop();w.music_island.close();w.stop_voice();w.face.close();w.tray.hide();w.hide();w.view.setPage(None);w.deleteLater();pump(.5);store.close()

if __name__=='__main__':run()
