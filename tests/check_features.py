"""Offline desktop integration checks for connection settings and personalization."""
import json
import base64
import io
import tempfile
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QMovie, QPdfWriter, QPainter
from PySide6.QtWidgets import QMessageBox, QFileDialog, QLineEdit
from PySide6.QtWebEngineCore import QWebEnginePage
from tests.check_sleepy import app, js, pump
from sleepy_app import SleepyWindow, image_data
from focus_overlay import FocusOverlay
from local_store import Store


def run():
 with tempfile.TemporaryDirectory() as folder, patch('api_connections.keyring.get_password',return_value='fixture-only'),patch('api_connections.keyring.set_password'),patch('api_connections.keyring.delete_password'):
  store=Store(Path(folder)/'checks.sqlite3');store.set('api_profiles',[]);store.set('screen_enabled',False)
  w=SleepyWindow(store);errors=[];w.page.javaScriptConsoleMessage=lambda l,m,n,s:errors.append(m)
  w.show();pump(2)
  try:
   assert js(w,'state.connections.profiles.length')==0
   js(w,"($('model-menu').click(),true)");pump();assert js(w,"$('settings-dialog').open")
   js(w,"($('api-name').value='Local test', $('api-url').value='http://localhost:11434/v1', $('api-model').value='chat-one', $('api-vision').value='vision-one', $('api-save').click(),true)");pump(.5)
   assert len(w.connections.profiles())==1
   pid=w.connections.active()['id'];assert js(w,"$('api-profile').value")==pid
   w.connections.cache_models(pid,['chat-one','chat-two','vision-one']);w.publish();pump()
   assert js(w,"$('api-models').options.length")==3
   js(w,"($('settings-dialog').close(), $('model-menu').click(), $('quick-model').value='chat-two', $('quick-apply').click(),true)");pump()
   assert w.connections.runtime()['selected_model']=='chat-two'
   w.save_settings({'screen_enabled':True});pump()
   assert js(w,"$('model-menu').textContent").startswith('vision-one')
   w.save_settings({'screen_enabled':False})
   # Exercise actual model-list bridge completion, without calling a provider.
   with patch('sleepy_app.fetch_catalog',return_value={'models':['chat-two','vision-one','fresh-model'],'capabilities':{}}):
    w.dispatch({'action':'api_models','id':pid});pump(.5)
   assert 'fresh-model' in w.connections.active()['models']
   assert js(w,"document.querySelector('[data-command=pick_background]')===null")
   # Animated logo runs only near the companion.
   gif=Path(folder)/'animated.gif';Image.new('RGB',(80,80),'red').save(gif,save_all=True,append_images=[Image.new('RGB',(80,80),'blue')],duration=100,loop=0)
   w.import_file('logo',str(gif));pump()
   assert image_data(store.get('logo')).startswith('data:image/gif;')
   center=w.face.geometry().center()
   with patch('sleepy_app.QCursor.pos',return_value=center):
    w.face.tick();assert w.face.movie.state()==QMovie.Running
   with patch('sleepy_app.QCursor.pos',return_value=center+QPoint(900,900)):
    w.face.tick();assert w.face.movie.state()==QMovie.NotRunning and w.face.movie.currentFrameNumber()==0
   assert w.face.timer.interval()==1000
   # Selection coordinates map logical screen points to physical pixels.
   focus=FocusOverlay(Image.new('RGB',(2000,1000)),QRect(0,0,1000,500));focus.selection=QRect(100,50,300,200)
   assert focus.pixel_box()==(200,100,800,500);focus.close()
   w.capture_region=((10,10,70,70),(80,80));w.publish();pump()
   assert js(w,"$('context-chips').textContent.includes('Focused area')")
   note=Path(folder)/'reference.txt';note.write_text('The base is 2.',encoding='utf-8');w.import_file('attachment',str(note));pump()
   assert w.attachment['text']=='The base is 2.'
   pdf=Path(folder)/'reference.pdf';writer=QPdfWriter(str(pdf));painter=QPainter(writer)
   painter.drawText(100,200,'The base is 2.');painter.end();del writer
   w.import_file('attachment',str(pdf));pump()
   assert 'The base is 2.' in w.attachment['text']
   # Include reference text in model request without putting the file in history.
   with patch('sleepy_app.Agent') as agent:
    agent.return_value.usage_report=None;agent.return_value.reply.return_value='Noted';agent.return_value.pending_action=None
    w.send('Use the document');pump(.6)
    assert 'The base is 2.' in agent.return_value.reply.call_args.args[0]
   assert 'The base is 2.' not in json.dumps(store.messages(w.chat_id))
   w.save_settings({'screen_enabled':True})
   with patch('sleepy_app.Agent') as agent,patch('sleepy_app.ImageGrab.grab',return_value=Image.new('RGB',(80,80),'white')):
    agent.return_value.usage_report=None;agent.return_value.reply.return_value='Crop read';agent.return_value.pending_action=None
    w.send('Read only the focus area');pump(1)
    payload=agent.return_value.reply.call_args.args[1]
    assert Image.open(io.BytesIO(base64.b64decode(payload.split(',')[1]))).size==(60,60)
   w.save_settings({'screen_enabled':False})
   js(w,"($('settings-dialog').close(),document.querySelector('[aria-label=\"Rename chat\"]').click(),$('rename-title').value='Physics notes',$('rename-form').requestSubmit(),true)");pump()
   assert store.chats()[0]['title']=='Physics notes'
   exported=Path(folder)/'conversation.md';w.import_file('export',str(exported));assert 'Use the document' in exported.read_text(encoding='utf-8')
   old=w.chat_id
   with patch('sleepy_app.QMessageBox.question',return_value=QMessageBox.Yes):w.dispatch({'action':'delete'})
   assert not store.messages(old) and w.chat_id!=old
   # Idle suspension and renderer discard must preserve a saved draft.
   js(w,"($('prompt').value='Keep my draft',saveDraft(),true)");pump();w.hide();pump();w.freeze_page();pump()
   assert w.page.lifecycleState()==QWebEnginePage.Frozen
   w.discard_page();pump();assert w.page.lifecycleState()==QWebEnginePage.Discarded
   with patch.object(w,'state',wraps=w.state) as build_state:
    w.publish();pump();build_state.assert_not_called()
   assert w.page.lifecycleState()==QWebEnginePage.Discarded,'Background publish woke the renderer'
   w.show_chat();pump(2)
   assert js(w,"$('prompt').value")=='Keep my draft'
   assert not [e for e in errors if 'Uncaught' in e],errors
   print('PASS: first-run setup, connection/model UI, model discovery, background removal, animated logo, focus scaling, document attachment, rename/delete/export, idle freeze/discard and draft restore')
  finally:
   w.closed=True;w.speech.stop();w.face.close();w.tray.hide();w.hide();w.view.setPage(None);w.deleteLater();pump();store.close()

if __name__=='__main__':run()
