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
