"""Qt + real web renderer regression check. --live sends only a full-screen test card."""
import json
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tempfile
import time
from pathlib import Path
from unittest.mock import patch
from PIL import Image, ImageGrab
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QMessageBox
from PySide6.QtTextToSpeech import QTextToSpeech
from sleepy_app import SleepyWindow
from local_store import Store

app=QApplication.instance() or QApplication([])
app.setQuitOnLastWindowClosed(False)

def pump(seconds=.2):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        app.processEvents()
        time.sleep(.01)

def js(window, code):
    output=[]
    window.page.runJavaScript('JSON.stringify('+code+')',lambda value:output.append(value))
    deadline=time.monotonic()+10
    while not output and time.monotonic()<deadline:
        pump(.02)
    assert output, 'JavaScript did not respond'
    return json.loads(output[0]) if output[0] else None

def wait_idle(window):
    deadline=time.monotonic()+90
    while window.busy and time.monotonic()<deadline:
        pump(.05)
    assert not window.busy,'Request timed out'
    pump(.3)

def run():
    with tempfile.TemporaryDirectory() as directory:
        store=Store(Path(directory)/'test.sqlite3')
        store.set('screen_enabled',False)
        if '--live' not in sys.argv:
            store.set('api_profiles',[{'id':'offline','name':'Offline fixture','base_url':'http://localhost:11434/v1',
                'model':'test-chat','vision_model':'test-vision','tools':True,'token_parameter':'max_tokens','models':[]}])
            store.set('api_active','offline')
        w=SleepyWindow(store)
        errors=[]
        w.page.javaScriptConsoleMessage=lambda level,message,line,source:errors.append(message)
        w.show()
        try:
            deadline=time.monotonic()+20
            while time.monotonic()<deadline:
                if js(w,'!!window.qt && typeof state !== "undefined" && state !== null'):
                    break
                pump(.2)
            assert js(w,'state !== null'),'UI bridge never initialized'
            for width,height in [(1000,760),(560,460)]:
                w.resize(width,height);pump(.25)
                bounds=js(w,"(()=>{const p=document.querySelector('.composer').getBoundingClientRect();return {bottom:p.bottom,width:p.width,view:innerHeight,overflow:document.body.scrollWidth>innerWidth}})()")
                assert bounds['bottom']<=bounds['view'] and not bounds['overflow'],bounds
            w.resize(1000,760)
            store.add(w.chat_id,'user','Show a formula and Python code.')
            store.add(w.chat_id,'assistant','Use **energy**:\n\n$$E = \\frac{1}{2}mv^2$$\n\n```python\ndef energy(m, v):\n    return 0.5 * m * v**2\n```\n\n<img src=x onerror="alert(1)">')
            w.publish();pump(.4)
            result=js(w,"({math:document.querySelectorAll('.katex').length,code:document.querySelectorAll('.code-box').length,bubbles:document.querySelectorAll('.user-bubble').length,unsafe:document.querySelectorAll('.answer img,.answer script').length})")
            assert result=={'math':1,'code':1,'bubbles':1,'unsafe':0},result
            js(w,"(document.querySelector('.code-head button').click(),true)");pump()
            assert 'def energy' in QApplication.clipboard().text()
            w.save_settings({'theme':'dark','background':'dusk','font_size':17,'memories':'Start with intuition'})
            pump()
            assert js(w,'document.body.dataset.theme')=='dark'
            w.showMaximized();pump();assert w.isMaximized() and not w.face.isVisible()
            w.fullscreen();pump();assert not w.isMaximized() and not w.isFullScreen()
            w.fullscreen();pump();assert w.isFullScreen() and not w.face.isVisible()
            w.hide();pump();w.show_chat();pump(.5)
            assert not w.isFullScreen() and not w.isMaximized()
            assert w.view.width()==w.centralWidget().width()
            w.showNormal();pump();assert w.face.isVisible()
            center=w.face.geometry().center()
            w.face.next_blink=time.monotonic()+100
            with patch('sleepy_app.QCursor.pos',return_value=center+QPoint(50,20)):
                for _ in range(10):w.face.tick()
                assert w.face.openness>.9 and w.face.gaze.x()>0
            with patch('sleepy_app.QCursor.pos',return_value=center+QPoint(700,700)):
                for _ in range(10):w.face.tick()
                assert w.face.openness<.05
            logo=Path(directory)/'logo.png';Image.new('RGBA',(128,128),'purple').save(logo)
            store.set('logo',str(logo));w.save_settings({'dot_style':'image'});assert not w.face.logo.isNull()
            w.save_settings({'dot_style':'eyes'})
            w.prepare_repo({'name':'sleepy-test','private':True,'description':'Test only'})
            proposal=w.proposal['id']
            w.prefs['github_enabled']=True
            with patch('sleepy_app.QMessageBox.question',return_value=QMessageBox.No),patch('github_plugin.create_repo') as create:
                w.confirm_repo(proposal);create.assert_not_called();assert w.proposal is not None
            with patch('sleepy_app.QMessageBox.question',return_value=QMessageBox.Yes),patch('github_plugin.create_repo',return_value={'name':'me/sleepy-test','url':'https://github.com/me/sleepy-test'}) as create:
                w.confirm_repo(proposal);w.confirm_repo(proposal);wait_idle(w);create.assert_called_once()
            w.prefs['github_enabled']=False
            from agent_core import Agent
            def fake_reply(agent,*args,**kwargs):
                agent.pending_action=None
                return 'A test response'
            w.save_settings({'screen_enabled':True})
            def capture(**kwargs):
                # Modern Windows excludes Sleepy from capture without hiding it;
                # other platforms use the short hide-and-restore fallback.
                if w.capture_without_hiding:
                    assert w.isVisible()
                else:
                    assert not w.isVisible() and not w.face.isVisible()
                return Image.new('RGB',(80,80),'red')
            with patch('api_connections.keyring.get_password',return_value='fixture-only'),patch('agent_core.Agent.reply',fake_reply),patch('sleepy_app.ImageGrab.grab',side_effect=capture) as grabbed:
                js(w,"($('prompt').value='Read the screen', $('prompt').dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true})),true)")
                pump();wait_idle(w);assert grabbed.call_count==1
            with patch('api_connections.keyring.get_password',return_value='fixture-only'),patch('sleepy_app.ImageGrab.grab',side_effect=OSError('No screen')),patch('agent_core.Agent.reply') as replied:
                w.send('Screen failure test');wait_idle(w);replied.assert_not_called()
            assert store.messages(w.chat_id)[-1]['role']=='error'
            print('PASS: rich math/code, safe rendering, clipboard, compact layout, themes, full screen, eyes, logo, repo approval, Enter capture, capture failure')
            print('Speech engine:',w.speech.engine(),'voices:',len(w.speech.availableVoices()))
            assert w.speech.state()!=QTextToSpeech.Error,'No speech engine'
            w.speech.say('Sleepy is ready.');pump(.5);w.speech.stop()
            if '--live' in sys.argv:
                w.dispatch({'action':'new'})
                fixture=QWidget(None,Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint)
                fixture.setStyleSheet('background:#204060;color:white;')
                layout=QVBoxLayout(fixture)
                label=QLabel('SCREEN CAPTURE TEST\n\nCode: MOON-731\n\nProblem 3.14: 8 x 9 = ?')
                label.setAlignment(Qt.AlignCenter);label.setStyleSheet('font:40px "Segoe UI";')
                layout.addWidget(label);fixture.showFullScreen();fixture.raise_();pump(.5)
                real_grab=ImageGrab.grab
                def safe_capture(**kwargs):
                    fixture.raise_();pump(.2)
                    image=real_grab(**kwargs);width,height=image.size
                    for point in [(2,2),(width-3,2),(2,height-3),(width-3,height-3)]:
                        assert all(abs(a-b)<5 for a,b in zip(image.convert('RGB').getpixel(point),(32,64,96))),'Test card did not cover the display'
                    return image
                with patch('sleepy_app.ImageGrab.grab',side_effect=safe_capture):
                    w.send('Read the code on this screen and solve problem 3.14. Include both code and answer.');wait_idle(w)
                fixture.close()
                answer=store.messages(w.chat_id)[-1]
                print('Live answer:',answer['content'])
                assert answer['role']=='assistant' and 'MOON-731' in answer['content'] and '72' in answer['content']
                print('PASS: actual display capture and live Groq vision')
            print('Renderer errors:',errors)
            assert not [e for e in errors if 'Uncaught' in e],errors
        finally:
            w.closed=True;w.speech.stop();w.face.close();w.tray.hide();w.hide();w.view.setPage(None);w.deleteLater();pump(.1);store.close()

if __name__=='__main__':run()
