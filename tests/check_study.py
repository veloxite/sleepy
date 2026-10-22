"""Offline real-renderer checks for study tools, settings and usage."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from tests.check_sleepy import app, js, pump, wait_idle
from local_store import Store
from sleepy_app import SleepyWindow
from provider_usage import record, metrics
from types import SimpleNamespace

def run():
    with tempfile.TemporaryDirectory() as folder:
        store=Store(Path(folder)/'test.db')
        store.set('api_profiles',[{'id':'test','name':'Test','base_url':'http://localhost:11434/v1','model':'chat','vision_model':'vision','models':['chat','vision','audio'],'tools':False,'token_parameter':'max_tokens',
                                  'capabilities':{'chat':{'text':True,'vision':False},'vision':{'text':True,'vision':True},'audio':{'text':False}}}])
        store.set('api_active','test');store.set('screen_enabled',False)
        w=SleepyWindow(store);errors=[];w.page.javaScriptConsoleMessage=lambda l,m,n,s:errors.append(m)
        w.show();pump(2)
        try:
            assert js(w,'typeof window.renderStudy')=='function'
            assert js(w,"document.querySelector('[data-command=pick_background]')===null")
            js(w,"(openSettings('models'),true)");pump()
            assert js(w,"Array.from($('api-screen-models').options).map(o=>o.value)")==['vision']
            assert 'Not reported' in js(w,"$('api-capabilities').textContent")
            report=metrics(SimpleNamespace(usage=SimpleNamespace(prompt_tokens=10,completion_tokens=20,total_tokens=30)),{'x-ratelimit-remaining-tokens':'1000'})
            record(store,'test','chat',report);w.publish();pump()
            assert '30 reported tokens' in js(w,"$('api-usage').textContent")
            with patch('sleepy_app.test_connection',return_value={'message':'Chat model responded successfully: hello','usage':report,'model':'chat'}) as test:
                js(w,"($('api-test').click(),true)");pump(.5);test.assert_called_once()
            assert 'successfully' in js(w,"$('api-status').textContent")
            js(w,"($('settings-dialog').close(),openCommands(),$('command-search').value='flash',listCommands(),$('command-list').querySelector('button').click(),true)")
            assert js(w,"$('prompt').value").startswith('/flashcards ')
            artifacts=[('mermaid','flowchart TD\n A["Energy"] --> B["Kinetic"]'),('flashcards',json.dumps({'title':'Physics','cards':[{'front':'Energy?','back':'Ability to do work.'},{'front':'Unit?','back':'Joule'}]}))]
            for kind,raw in artifacts:store.add(w.chat_id,'assistant','```'+kind+'\n'+raw+'\n```')
            w.publish();pump(4)
            js(w,"(document.querySelector('.study-card').scrollIntoView(),true)");pump(3)
            assert js(w,"document.querySelectorAll('.study-card').length")==2
            assert js(w,"document.querySelectorAll('.study-content svg').length")>0,js(w,"document.querySelector('.study-content').textContent")
            bounds=js(w,"(()=>{const r=document.querySelector('.study-content svg').getBoundingClientRect();return {width:r.width,height:r.height}})()")
            assert bounds['width']>250 and bounds['height']>100,bounds
            assert js(w,"document.querySelector('.study-content svg').textContent.includes('Energy')"),'Diagram labels missing'
            assert js(w,"document.querySelector('.study-content svg').textContent.includes('Kinetic')"),'Diagram labels missing'
            w.view.grab().save(str(Path(tempfile.gettempdir())/'sleepy-study-qa.png'))
            js(w,"(document.querySelector('.flash-face').click(),true)")
            assert 'Ability' in js(w,"document.querySelector('.flash-face').textContent")
            # An unrelated state update should not destroy the rendered diagram.
            w.publish();pump();assert js(w,"document.querySelectorAll('.study-content svg').length")>0
            # Malformed generated artifacts keep source and do not break other replies.
            js(w,"(window.savedDiagram=document.querySelector('.study-content svg'),true)")
            store.add(w.chat_id,'assistant','```flashcards\n{"cards": []}\n```');w.publish();pump()
            assert js(w,"window.savedDiagram===document.querySelector('.study-content svg')"),'New reply rebuilt old diagram'
            assert 'Ability' in js(w,"document.querySelector('.flash-face').textContent"),'New reply reset the flashcard'
            assert 'Could not display' in js(w,"$('messages').lastElementChild.textContent")
            assert not [e for e in errors if 'Uncaught' in e],errors
            print('PASS: palette, full-size automatic Mermaid rendering, flashcards, capability filtering, usage/test UI, removed tools/background, malformed artifacts')
        finally:
            w.closed=True;w.face.close();w.tray.hide();w.hide();w.view.setPage(None);w.deleteLater();pump();store.close()

if __name__=='__main__':run()
