"""Offline packaged-app check: isolated data, real Qt renderer, no user keys."""
import json
import os
import sys
import tempfile
import time
from pathlib import Path


def main():
    report = Path(sys.argv[sys.argv.index('--self-test') + 1]).resolve()
    result = {'ok': False, 'checks': []}
    try:
        # Do not instantiate an API client, capture the screen, or read the vault.
        from app_paths import RESOURCE_DIR
        from local_store import Store
        from api_connections import Connections
        from provider_adapters import AnthropicAdapter, OpenAICompatibleAdapter
        import edge_tts
        import yt_dlp
        import keyring
        import platform_capture
        import unix_windows
        from PySide6.QtCore import QUrl
        from PySide6.QtWidgets import QApplication
        from PySide6.QtWebEngineWidgets import QWebEngineView
        from PySide6.QtWebChannel import QWebChannel
        from PySide6.QtMultimedia import QMediaPlayer
        from PySide6.QtTextToSpeech import QTextToSpeech
        from PySide6.QtGui import QIcon
        from sleepy_app import SleepyWindow
        result['checks'].append('runtime imports')
        app = QApplication.instance() or QApplication([])
        app.setApplicationName('Sleepy package check')
        temporary = tempfile.TemporaryDirectory(prefix='sleepy-check-')
        with temporary as directory:
            store = Store(Path(directory) / 'check.sqlite3')
            store.set('api_profiles', [])
            assert Connections(store).profiles() == []
            cid = store.new_chat()
            assert store.chats() == []
            store.add(cid, 'user', 'Packaging check')
            assert store.messages(cid)[0]['content'] == 'Packaging check'
            result['checks'].append('fresh database')
            assert not QIcon(str(RESOURCE_DIR / 'assets' / 'sleepy.ico')).isNull()
            window = SleepyWindow(store)
            loaded = []
            window.view.loadFinished.connect(loaded.append)
            window.resize(600, 700)
            window.show()
            deadline = time.monotonic() + 45
            while (not loaded or not window.page_ready) and time.monotonic() < deadline:
                app.processEvents()
                time.sleep(.02)
            assert loaded and loaded[0] and window.page_ready, f'Bundled UI/bridge failed to load (load results={loaded}, bridge={window.page_ready})'
            answer = []
            window.page.runJavaScript("typeof marked !== 'undefined' && typeof katex !== 'undefined' && !!document.getElementById('prompt') && state.connections.profiles.length === 0", answer.append)
            while not answer and time.monotonic() < deadline:
                app.processEvents()
                time.sleep(.02)
            assert answer == [True], 'Offline frontend assets did not initialize'
            result['checks'].append('Qt WebEngine, UI bridge, fresh provider settings')
            def js(code):
                values=[]
                window.page.runJavaScript(code, values.append)
                end=time.monotonic()+10
                while not values and time.monotonic()<end:
                    app.processEvents();time.sleep(.02)
                assert values, 'Settings JavaScript timed out'
                return values[0]
            def settle():
                end=time.monotonic()+1
                while time.monotonic()<end:
                    app.processEvents();time.sleep(.02)
            # A localhost fixture avoids credential access and network requests.
            js("openSettings('models');$('api-name').value='Offline fixture';$('api-url').value='http://localhost:11434/v1';$('api-model').value='chat-before';$('api-vision').value='screen-before';$('api-save').click();")
            assert js("$('feature-dialog').open && !$('settings-dialog').open && !document.querySelector('[data-tab=models]')"), 'Models must open independently of Settings'
            settle()
            js("$('api-model').value='chat-after';$('api-vision').value='screen-after';$('save-settings').click();")
            settle()
            assert window.connections.active()['model']=='chat-after'
            assert window.connections.active()['vision_model']=='screen-after'
            js("$('settings-dialog').close();openSettings('models');")
            assert js("$('api-model').value")=='chat-after'
            assert js("$('api-vision').value")=='screen-after'
            reopened=Store(store.path)
            try:
                assert Connections(reopened).active()['model']=='chat-after'
                assert Connections(reopened).active()['vision_model']=='screen-after'
            finally:reopened.close()
            js("selectTab('workspaces');document.querySelector('.settings-content').scrollTop=500;$('settings-dialog').close();openSettings();")
            assert js("document.querySelector('.settings-content').scrollTop") == 0
            assert js("document.querySelector('[data-section=workspaces]').hidden") is True
            result['checks'].append('model edit/save/reopen/database persistence and settings scroll reset')
            window.quit_app()
            window.face.hide()
            result['ok'] = True
    except Exception as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2), encoding='utf-8')
    if sys.stdout is not None:
        print(json.dumps(result, indent=2), flush=True)
    return 0 if result['ok'] else 1
