"""Native Sleepy shell: Qt window + offline rich chat, with a proximity-aware face."""
import base64
import json
import math
import random
import re
import sys
import threading
import time
import uuid
import platform
import ctypes
import io
from pathlib import Path

from app_paths import RESOURCE_DIR, load_source_environment
from PIL import Image, ImageGrab, ImageOps, ImageSequence
from PySide6.QtCore import Qt, QTimer, QObject, Signal, Slot, QUrl, QRectF, QPointF, QEvent, QBuffer, QIODevice
from PySide6.QtGui import QPainter, QColor, QPen, QPainterPath, QPixmap, QCursor, QIcon, QDesktopServices, QAction, QKeySequence, QShortcut, QMovie
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QFileDialog, QMessageBox, QSystemTrayIcon, QMenu, QRubberBand
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtTextToSpeech import QTextToSpeech
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from agent_core import Agent, encode_image, friendly_error, history_text
from local_store import Store, DATA_DIR
import github_plugin
from api_connections import Connections, fetch_catalog, test_connection
from provider_usage import record
from focus_overlay import FocusOverlay
from windows_integration import CaptureExclusion, set_taskbar_identity, SideBySide
import platform_capture
from assistant_features import AssistantFeatures
from desktop_actions import explicit_action,open_url
from web_media import search_images

BASE = RESOURCE_DIR
load_source_environment()
DEFAULTS = {'theme': 'light', 'background': 'glow', 'accent': '#5365ed', 'display_name': '',
            'font_size': 15, 'motion': True, 'dot_size': 72, 'proximity': 180, 'dot_style': 'eyes',
            'capture_target': 'Primary display', 'screen_enabled': True, 'memories': '',
            'github_enabled': False, 'speech_rate': 0.0, 'speech_voice': '',
            'browser':'System default','voice_engine':'neural','neural_voice':'en-US-AriaNeural',
            'speech_connection':'','voice_send':True,'voice_reply':True,'music_service':'none'}


def image_data(path):
    if not path or not Path(path).is_file():
        return ''
    mime = 'gif' if Path(path).suffix.lower()=='.gif' else 'png'
    return 'data:image/'+mime+';base64,' + base64.b64encode(Path(path).read_bytes()).decode()


class Face(QWidget):
    def __init__(self, host):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.host = host
        self.setWindowTitle('Sleepy companion')
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip('Sleepy · Click to chat · Drag to move · Right-click for options')
        self.openness = 0.0
        self.gaze = QPointF(0, 0)
        self.squint_until = self.blink_until = 0
        self.next_blink = time.monotonic() + random.uniform(3, 6)
        self.dragged = False
        self.movie = None
        self.near = False
        self.apply_settings()
        area = QApplication.primaryScreen().availableGeometry()
        self.move(area.right()-self.width()-22, area.bottom()-self.height()-24)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(1000)

    def apply_settings(self):
        size = int(self.host.prefs.get('dot_size', 72))
        self.setFixedSize(size, size)
        self.logo = QPixmap(self.host.store.get('logo', ''))
        if self.movie:
            self.movie.stop()
            self.movie.deleteLater()
        self.movie = QMovie(self)
        self.movie_buffer = QBuffer(self.movie)
        logo_path = self.host.store.get('logo','')
        if logo_path and Path(logo_path).is_file():
            self.movie_buffer.setData(Path(logo_path).read_bytes())
        self.movie_buffer.open(QIODevice.ReadOnly)
        self.movie.setDevice(self.movie_buffer)
        self.movie.setCacheMode(QMovie.CacheNone)
        self.movie.frameChanged.connect(lambda _: self.update() if self.isVisible() else None)
        self.movie.jumpToFrame(0)
        self.update()

    def tick(self):
        if not self.isVisible():
            return
        delta = QCursor.pos() - self.geometry().center()
        distance = math.hypot(delta.x(), delta.y())
        near = distance < self.host.prefs['proximity']
        self.near = near
        if hasattr(self.host,'music_island'):
            if self.geometry().contains(QCursor.pos()) and self.host.music.state()['active']:
                if not self.host.music_island.isVisible():self.host.music_island.reveal()
            elif not self.host.music_island.geometry().adjusted(-15,-15,15,15).contains(QCursor.pos()):
                self.host.music_island.hide()
        now = time.monotonic()
        motion = self.host.prefs['motion']
        if self.host.prefs['dot_style']=='image' and self.movie.isValid() and self.movie.frameCount()>1:
            if near and motion:
                if self.movie.state()!=QMovie.Running:
                    self.movie.start()
            elif self.movie.state()!=QMovie.NotRunning:
                self.movie.stop()
                self.movie.jumpToFrame(0)
        if near and motion and now > self.next_blink:
            self.blink_until = now + .13
            self.next_blink = now + random.uniform(3.5, 7)
        target = 1.0 if near else 0.0
        if now < self.squint_until or (motion and now < self.blink_until):
            target = .08
        old_open, old_gaze = self.openness, QPointF(self.gaze)
        self.openness += (target-self.openness) * (.6 if near else 1)
        factor = min(distance, 140) / 140
        x = delta.x()/max(1, distance)*3.5*factor if near and motion else 0
        y = delta.y()/max(1, distance)*3.0*factor if near and motion else 0
        self.gaze += (QPointF(x, y)-self.gaze)*.3
        moving=abs(self.openness-old_open)>.005 or (self.gaze-old_gaze).manhattanLength()>.02
        interval=33 if near and motion and (moving or now<self.blink_until) else 125 if near else 1000
        if self.timer.interval()!=interval:self.timer.setInterval(interval)
        if moving:
            self.update()

    def enterEvent(self,event):
        self.tick()  # Immediate wake on hover, even with slow distant-pointer checks.
        super().enterEvent(event)

    def showEvent(self, event):
        if hasattr(self,'timer'):
            self.timer.start(100)
        super().showEvent(event)

    def hideEvent(self, event):
        self.timer.stop()
        if self.movie:
            self.movie.stop()
        super().hideEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        size = self.width()
        p.scale(size/72, size/72)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(20, 24, 38, 20))
        p.drawEllipse(QRectF(4, 6, 64, 64))
        p.setBrush(QColor('#141618'))
        p.drawEllipse(QRectF(5, 3, 62, 62))
        if self.host.prefs['dot_style'] == 'image' and not self.logo.isNull():
            clip = QPainterPath()
            clip.addEllipse(QRectF(6, 4, 60, 60))
            p.setClipPath(clip)
            frame = self.movie.currentPixmap() if self.movie.isValid() else self.logo
            scaled = frame.scaled(60,60,Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation)
            p.drawPixmap(6+(60-scaled.width())//2,4+(60-scaled.height())//2,scaled)
            if self.host.recording:
                p.setClipping(False);p.setPen(QPen(QColor('#8ac7ff'),3,Qt.SolidLine,Qt.RoundCap))
                for i in range(5):
                    height=3+self.host.mic_level*(10 if i%2==0 else 16)
                    p.drawLine(QPointF(26+i*5,51-height/2),QPointF(26+i*5,51+height/2))
            return
        p.setBrush(QColor('#ffffff'))
        for center in (26, 44):
            x, y = center+self.gaze.x(), 32+self.gaze.y()
            height = 2.8 + self.openness*13
            p.drawRoundedRect(QRectF(x-3.8, y-height/2, 7.6, height), 3.8, 3.8)
        if self.host.busy:
            p.setBrush(QColor(self.host.prefs['accent']))
            p.drawEllipse(QRectF(33, 53, 6, 3))
        if self.host.recording:
            p.setPen(QPen(QColor('#8ac7ff'),2.4,Qt.SolidLine,Qt.RoundCap))
            for i in range(5):
                height=3+self.host.mic_level*(10 if i%2==0 else 16)
                p.drawLine(QPointF(26+i*5,51-height/2),QPointF(26+i*5,51+height/2))

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            menu = QMenu(self)
            menu.addAction('Open Sleepy', self.host.show_chat)
            menu.addAction('Settings', lambda: self.host.open_settings())
            menu.addAction('Hide companion', lambda: (self.hide(), self.host.tray.showMessage('Sleepy', 'Use the tray icon to bring me back.')))
            menu.addSeparator()
            menu.addAction('Quit', self.host.quit_app)
            menu.exec(event.globalPosition().toPoint())
            return
        self.press = event.globalPosition().toPoint()
        self.origin = self.pos()
        self.dragged = False
        self.held=False
        if not hasattr(self,'hold_timer'):
            self.hold_timer=QTimer(self);self.hold_timer.setSingleShot(True);self.hold_timer.timeout.connect(self.begin_hold)
        self.hold_timer.start(400)

    def begin_hold(self):
        if self.dragged:return
        self.held=True
        try:self.host.start_mic()
        except Exception as error:self.host.emit('error',message=friendly_error(error));self.host.show_chat()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            delta = event.globalPosition().toPoint()-self.press
            if delta.manhattanLength() > 5:
                if hasattr(self,'hold_timer'):self.hold_timer.stop()
                if self.host.recording:return
                self.dragged = True
                self.move(self.origin+delta)

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        if hasattr(self,'hold_timer'):self.hold_timer.stop()
        if getattr(self,'held',False):
            self.host.microphone.stop();return
        if not self.dragged:
            self.squint_until = time.monotonic()+.2
            self.update()
            QTimer.singleShot(130, self.host.toggle_chat)
        else:
            screen = QApplication.screenAt(self.geometry().center()) or QApplication.primaryScreen()
            area = screen.availableGeometry()
            self.move(max(area.left(), min(self.x(), area.right()-self.width())),
                      max(area.top(), min(self.y(), area.bottom()-self.height())))


class LocalPage(QWebEnginePage):
    def acceptNavigationRequest(self, url, kind, main):
        return url.scheme() == 'file' and Path(url.toLocalFile()).resolve() == (BASE / 'ui' / 'index.html').resolve()


class Bridge(QObject):
    event = Signal(str)
    @Slot(str)
    def request(self, raw):
        try:
            self.parent().dispatch(json.loads(raw))
        except Exception as error:
            self.parent().emit('error', message=str(error) if isinstance(error, ValueError) else 'That action could not be completed. Please try again.')


class SleepyWindow(AssistantFeatures,QMainWindow):
    completed = Signal(str, object)
    def __init__(self, store=None):
        super().__init__()
        self.store = store or Store()
        self.connections = Connections(self.store)
        self.prefs = {key: self.store.get(key, default) for key, default in DEFAULTS.items()}
        # Keep the new personality's motion separate from Orbit's spinning-ring switch.
        self.busy = False
        self.capture = None
        self.proposal = None
        self.capturing = False
        self.closed = False
        self.jobs = set()
        self.file_dialog = None
        self.attachment = None
        self.capture_region = None
        self.capture_without_hiding = False
        self.chat_id = self.store.new_chat()
        self.layout_pair=SideBySide()
        self.setWindowTitle('Sleepy')
        self.resize(560, 760)
        self.setMinimumSize(440, 460)
        self.view = QWebEngineView(self)
        self.profile = QWebEngineProfile(self.view)
        self.page = LocalPage(self.profile, self.view)
        self.view.setPage(self.page)
        self.view.settings().setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, False)
        self.setCentralWidget(self.view)
        self.bridge = Bridge(self)
        self.channel = QWebChannel(self.page)
        self.channel.registerObject('bridge', self.bridge)
        self.page.setWebChannel(self.channel)
        self.idle_timer = QTimer(self)
        self.idle_timer.setSingleShot(True)
        self.idle_timer.timeout.connect(self.freeze_page)
        self.discard_timer = QTimer(self)
        self.discard_timer.setSingleShot(True)
        self.discard_timer.timeout.connect(self.discard_page)
        self.view.setContextMenuPolicy(Qt.NoContextMenu)
        # Companion-only startup does not start a Chromium renderer.
        self.ui_loaded=False
        self.state_dirty=True
        self.completed.connect(self.on_completed)
        self.speech = QTextToSpeech(self)
        self.default_voice = self.speech.voice()
        self.speech.stateChanged.connect(lambda state: self.emit('speech', speaking=state == QTextToSpeech.Speaking))
        self.speech.errorOccurred.connect(lambda *_: self.emit('error', message='Read aloud is unavailable. Check voices installed in your system settings.'))
        self.init_features()
        self.page.loadStarted.connect(lambda:setattr(self,'page_ready',False))
        self.face = Face(self)
        self.face.show()
        icon = QPixmap(64, 64)
        icon.fill(Qt.transparent)
        painter = QPainter(icon)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor('#141618'))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(2, 2, 60, 60)
        painter.setBrush(Qt.white)
        painter.drawRoundedRect(22, 24, 6, 14, 3, 3)
        painter.drawRoundedRect(36, 24, 6, 14, 3, 3)
        painter.end()
        self.setWindowIcon(QIcon(icon))
        self.tray = QSystemTrayIcon(QIcon(icon), self)
        menu = QMenu()
        menu.addAction('Open Sleepy', self.show_chat)
        menu.addAction('Show companion', self.face.show)
        menu.addAction('Quit', self.quit_app)
        self.tray.setContextMenu(menu)
        self.tray.setToolTip('Sleepy')
        self.tray.activated.connect(lambda reason: self.show_chat() if reason == QSystemTrayIcon.DoubleClick else None)
        self.tray.show()
        QShortcut(QKeySequence('F11'), self, activated=self.fullscreen)
        QShortcut(QKeySequence('Escape'), self, activated=lambda: self.showNormal() if self.isFullScreen() else None)

    def emit(self, kind, **data):
        self.bridge.event.emit(json.dumps({'type': kind, **data}))

    def state(self):
        prefs = dict(self.prefs)
        prefs['logo'] = image_data(self.store.get('logo', ''))
        if prefs['background'] == 'image':
            prefs['background'] = 'glow'
        return {'chats': self.store.chats(), 'chat_id': self.chat_id,
                'messages': self.store.messages(self.chat_id), 'prefs': prefs,
                'draft': self.store.get('draft:'+self.chat_id, ''), 'busy': self.busy,
                'github_login': self.store.get('github_login', ''),
                'voices': [v.name() for v in self.speech.availableVoices() if v.locale().name() in ('en_US','en_GB')],
                'speech_available': self.speech.state() != QTextToSpeech.Error,
                'speech_platform': platform.system(),
                'connections': self.connections.public(),
                'attachment': self.attachment['name'] if self.attachment else '',
                'focused': self.capture_region is not None,
                'features':self.features_state(),
                'proposal': self.proposal if self.proposal and self.proposal['chat_id'] == self.chat_id else None}

    def publish(self):
        self.state_dirty=True
        self.face.update()
        if not self.page_ready or not self.isVisible() or self.isMinimized():
            return
        self.emit('state', **self.state())
        self.state_dirty=False

    def job(self, name, function):
        if name in self.jobs:
            raise ValueError('That operation is already running.')
        self.jobs.add(name)
        def work():
            try:
                result = {'ok': True, 'value': function()}
            except Exception as error:
                result = {'ok': False, 'error': friendly_error(error)}
            self.completed.emit(name, result)
        threading.Thread(target=work, daemon=True).start()

    def dispatch(self, data):
        action = data.get('action')
        if self.feature_dispatch(data):return
        if action == 'ready':
            self.page_ready=True
            self.publish()
            if self.pending_settings:
                tab=self.pending_settings;self.pending_settings=None;self.emit('open_settings',tab=tab)
        elif action == 'api_test':
            if self.busy:
                raise ValueError('Wait for the chat request to finish.')
            screen=bool(data.get('screen'))
            config=self.connections.runtime(data.get('id'),screen=screen)
            self.emit('api_status',message='Sending a small test request to the saved model…')
            self.job('test:'+config['id'],lambda:test_connection(config,screen))
        elif action in ('api_save','api_select','api_delete','api_models'):
            if self.busy or any(j.startswith(('models:','test:')) for j in self.jobs):
                raise ValueError('Wait for the current request to finish before changing connections.')
            if action == 'api_save':
                profile=self.connections.save(data)
                self.emit('api_saved', id=profile['id'], message='Connection saved. Load models or enter model IDs, then save again.')
            elif action == 'api_select':
                self.connections.select(data.get('id'), data.get('model'), self.prefs['screen_enabled'])
            elif action == 'api_delete':
                if QMessageBox.question(self,'Remove API connection?','Remove this connection and its saved key?',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:
                    return
                self.connections.delete(data.get('id'))
            else:
                config=self.connections.runtime(data.get('id'),require_model=False)
                self.emit('api_status',message='Loading models from this provider…')
                self.job('models:'+config['id'],lambda:fetch_catalog(config))
            self.publish()
        elif action == 'rename':
            title=str(data.get('title','')).strip()[:100]
            if title:
                self.store.rename(self.chat_id,title)
                self.publish()
        elif action == 'focus_screen':
            if not self.busy:
                self.choose_focus()
        elif action == 'clear_focus':
            self.capture_region=None
            self.publish()
        elif action == 'attach_file':
            self.open_file_dialog('attachment')
        elif action == 'clear_attachment':
            self.attachment=None
            self.publish()
        elif action == 'export_chat':
            self.open_file_dialog('export')
        elif action == 'send':
            self.send(data.get('text', ''))
        elif action == 'draft':
            cid = data.get('chat_id')
            if cid==self.chat_id or cid in {c['id'] for c in self.store.chats()}:
                self.store.set('draft:'+cid, data.get('text', '')[:30000])
        elif action in ('new', 'select', 'delete'):
            if self.busy:
                raise ValueError('Wait for this response to finish first.')
            if action == 'delete':
                if QMessageBox.question(self, 'Delete chat', 'Delete this saved conversation?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                    return
                self.store.delete(self.chat_id)
                chats = self.store.chats()
                self.chat_id = chats[0]['id'] if chats else self.store.new_chat()
            elif action == 'new':
                self.chat_id = self.store.new_chat()
            else:
                cid = data.get('id')
                if cid not in {c['id'] for c in self.store.chats()}:
                    return
                self.chat_id = cid
            self.speech.stop()
            self.capture = None
            self.attachment = None
            self.publish()
        elif action == 'settings':
            self.save_settings(data.get('values', {}))
        elif action == 'pick_image':
            QTimer.singleShot(0, lambda: self.pick_image(data.get('kind')))
        elif action == 'remove_image':
            kind = 'logo' if data.get('kind') == 'logo' else 'background_image'
            self.store.set(kind, '')
            self.save_settings({'background':'glow'} if kind=='background_image' else {'dot_style':'eyes'})
            self.publish()
            self.face.apply_settings()
        elif action == 'preview':
            self.emit('preview', image=self.capture or '')
        elif action == 'speak':
            self.read_aloud(str(data.get('text',''))[:12000])
        elif action == 'stop_speech':
            self.stop_voice()
        elif action == 'copy':
            QApplication.clipboard().setText(str(data.get('text', '')))
        elif action == 'open_link':
            open_url(data.get('url',''),self.prefs['browser'])
        elif action == 'github_connect':
            credential = str(data.get('token', '')).strip()
            if not credential:
                raise ValueError('Paste a GitHub token to connect.')
            self.emit('plugin_status', message='Connecting…')
            self.job('github_connect', lambda: github_plugin.connect(credential))
        elif action == 'github_disconnect':
            self.prefs['github_enabled'] = False
            self.store.set('github_enabled', False)
            self.store.set('github_login', '')
            self.emit('plugin_status', message=github_plugin.disconnect())
            self.publish()
        elif action == 'repo_propose':
            self.prepare_repo(data)
        elif action == 'repo_cancel':
            self.proposal = None
            self.publish()
        elif action == 'repo_confirm':
            self.confirm_repo(data.get('id'))
        elif action == 'hide':
            self.hide()
            self.face.show()
        elif action == 'fullscreen':
            self.fullscreen()
        elif action == 'quit':
            self.quit_app()

    def save_settings(self, values):
        enums = {'theme': ('light','dark','system'), 'background': ('glow','plain','dusk'),
                 'voice_engine':('system','neural'),'music_service':('none','soundcloud'),
                 'capture_target': ('Primary display','All displays'), 'dot_style': ('eyes','image')}
        ranges = {'font_size': (13,20), 'dot_size': (56,100), 'proximity': (90,350), 'speech_rate': (-.8,.8)}
        for key, value in values.items():
            if key not in DEFAULTS or key == 'github_enabled':
                continue
            if key in enums and value not in enums[key]:
                continue
            if key in ranges:
                low, high = ranges[key]
                value = max(low, min(high, float(value)))
                if key != 'speech_rate':
                    value = int(value)
            if key in ('motion','screen_enabled','voice_send','voice_reply'):
                value = bool(value)
            if key == 'accent' and not re.fullmatch(r'#[0-9a-fA-F]{6}', value):
                continue
            if key in ('display_name','memories','speech_voice','browser','neural_voice','speech_connection'):
                value = str(value)[:6000 if key == 'memories' else 100]
            self.prefs[key] = value
            self.store.set(key, value)
        self.face.apply_settings()
        self.emit('preferences', prefs=self.state()['prefs'])

    def pick_image(self, kind):
        if kind != 'logo':
            return
        self.open_file_dialog(kind)

    def open_file_dialog(self, kind):
        if self.file_dialog:
            self.file_dialog.raise_()
            return
        dialog=QFileDialog(self, 'Export conversation' if kind=='export' else 'Choose a file')
        self.file_dialog=dialog
        dialog.setOption(QFileDialog.DontUseNativeDialog, True)
        dialog.setWindowModality(Qt.WindowModal)
        if kind=='export':
            dialog.setAcceptMode(QFileDialog.AcceptSave)
            dialog.setDefaultSuffix('md')
            dialog.setNameFilter('Markdown (*.md)')
            dialog.selectFile('Sleepy-chat.md')
        else:
            dialog.setFileMode(QFileDialog.ExistingFile)
            dialog.setNameFilter('Documents (*.pdf *.txt *.md *.py *.json *.csv)' if kind=='attachment' else 'Images (*.png *.jpg *.jpeg *.webp *.gif)')
        def chosen(path):
            try:
                self.import_file(kind,path)
            except Exception as error:
                self.emit('error',message=str(error) if isinstance(error,ValueError) else 'Could not read that file. Try another image or document.')
        dialog.fileSelected.connect(chosen)
        def finished(_):
            self.file_dialog=None
            dialog.deleteLater()
            self.emit('file_picker_closed',file_kind=kind)
        dialog.finished.connect(finished)
        dialog.open()
        dialog.raise_()
        dialog.activateWindow()

    def import_file(self, kind, path):
        if kind=='export':
            lines=['# Sleepy conversation','']
            for m in self.store.messages(self.chat_id):
                lines.extend(['## '+('You' if m['role']=='user' else 'Sleepy' if m['role']=='assistant' else 'Error'),'',m['content'],''])
            Path(path).write_text('\n'.join(lines),encoding='utf-8')
            self.emit('notice',message='Conversation exported.')
            return
        if Path(path).stat().st_size>25*1024*1024:
            raise ValueError('Choose a file smaller than 25 MB.')
        if kind=='attachment':
            if Path(path).suffix.lower()=='.pdf':
                from pypdf import PdfReader
                reader=PdfReader(path)
                if len(reader.pages)>40:
                    raise ValueError('Attach a PDF with 40 pages or fewer, or use a focused screenshot.')
                text='\n'.join((p.extract_text() or '') for p in reader.pages)
            else:
                text=Path(path).read_text(encoding='utf-8-sig')
            if not text.strip():
                raise ValueError('No readable text was found. For a scanned PDF, use a focused screenshot.')
            self.attachment={'name':Path(path).name,'text':text[:24000]}
            self.publish()
            if len(text)>24000:
                self.emit('notice',message='Attached the first 24,000 characters. Split long documents for complete coverage.')
            return
        target_dir=Path(self.store.path).parent
        with Image.open(path) as source:
            image = source.convert('RGBA')
            if kind=='logo' and getattr(source,'n_frames',1)>1:
                if source.n_frames>200:
                    raise ValueError('Choose an animation with 200 frames or fewer.')
                frames=[];durations=[]
                for frame in ImageSequence.Iterator(source):
                    frames.append(ImageOps.fit(frame.convert('RGBA'),(256,256)))
                    durations.append(max(50,frame.info.get('duration',100)))
                target=target_dir/'logo.gif'
                frames[0].save(target,save_all=True,append_images=frames[1:],duration=durations,loop=0,disposal=2)
            elif kind == 'logo':
                image = ImageOps.fit(image, (256,256))
                target=target_dir/'logo.png'
                image.save(target)
            else:
                image.thumbnail((1920,1920))
                target=target_dir/'background_image.png'
                image.save(target)
        self.store.set(kind, str(target))
        self.save_settings({'dot_style':'image'} if kind == 'logo' else {'background':'image'})
        self.publish()

    def send(self, text):
        text = str(text).strip()
        if self.busy or not text:
            return
        if len(text) > 30000:
            raise ValueError('Please keep a message under 30,000 characters.')
        self.stop_voice()
        direct=explicit_action(text,self.store.get('apps',[]),self.store.get('workspaces',[]))
        if direct:
            self.store.add(self.chat_id,'user',text)
            try:answer=self.execute_action(direct)
            except Exception as error:answer=friendly_error(error)
            self.store.add(self.chat_id,'assistant',answer);self.store.set('draft:'+self.chat_id,'');self.publish()
            if self.last_voice and self.prefs['voice_reply']:self.read_aloud(answer)
            self.last_voice=False
            return
        self.pending_config=self.connections.runtime(screen=self.prefs['screen_enabled'])
        self.pending_config['desktop_context']=json.dumps({'apps':[a['name'] for a in self.store.get('apps',[])],'workspaces':[p['name'] for p in self.store.get('workspaces',[])],'file_workspace_selected':bool(self.store.get('workspace_root',''))})
        self.busy = True
        self.speech.stop()
        self.pending_text = text
        self.pending_attachment=dict(self.attachment) if self.attachment else None
        self.pending_cid = self.chat_id
        self.pending_history = [{'role': m['role'], 'content': history_text(m['content']), 'screen': bool(m['screen'])}
                                for m in self.store.recent_context(self.chat_id)]
        self.pending_memories = self.prefs['memories']
        # Preparing a review card needs no credential; actual creation checks the connection.
        self.pending_github = True
        self.pending_message_id = self.store.add(self.chat_id, 'user', text)
        self.store.set('draft:'+self.chat_id, '')
        self.publish()
        if self.prefs['screen_enabled']:
            self.was_maximized = self.isMaximized()
            self.was_fullscreen = self.isFullScreen()
            self.capturing = True
            self.capture_exclusion = CaptureExclusion([self, self.face])
            self.capture_without_hiding = self.capture_exclusion.begin()
            if not self.capture_without_hiding:
                self.hide()
                self.face.hide()
            # Give the outgoing message one paint cycle, then capture. On modern
            # Windows Sleepy stays visible but is excluded from the image.
            QTimer.singleShot(60 if self.capture_without_hiding else 120, self.capture_and_start)
        else:
            self.start_chat(None)

    def choose_focus(self):
        if self.capturing or self.file_dialog:
            return
        self.was_maximized, self.was_fullscreen = self.isMaximized(), self.isFullScreen()
        self.capturing = True
        self.hide()
        self.face.hide()
        def restore(region=None):
            if region:
                self.capture_region=region
                self.save_settings({'screen_enabled':True})
            self.capturing=False
            if self.was_fullscreen:
                self.showFullScreen()
            elif self.was_maximized:
                self.showMaximized()
            else:
                self.show()
                self.face.show()
            self.raise_()
            self.activateWindow()
            self.publish()
        def select():
            try:
                picture=platform_capture.grab()
                self.focus_overlay=FocusOverlay(picture,QApplication.primaryScreen().geometry())
                self.focus_overlay.selected.connect(restore)
                self.focus_overlay.setAttribute(Qt.WA_DeleteOnClose)
                self.focus_overlay.show()
                self.focus_overlay.activateWindow()
            except Exception:
                restore()
                self.emit('error',message='Could not capture the screen. On macOS, allow Screen Recording in System Settings and restart Sleepy.')
        QTimer.singleShot(400,select)

    def capture_and_start(self):
        error = None
        try:
            image=platform_capture.grab(all_screens=self.prefs['capture_target'] == 'All displays' and self.capture_region is None)
            if self.capture_region:
                box,size=self.capture_region
                if image.size!=size:
                    raise ValueError('Display dimensions changed. Select the focus area again.')
                image=image.crop(box)
            self.capture = encode_image(image)
        except Exception as exc:
            self.capture = None
            error = str(exc) if isinstance(exc,ValueError) else 'Could not capture the screen. No text-only request was sent. Check screen-recording permission and try again.'
        finally:
            self.capture_exclusion.restore()
        self.capturing = False
        if not self.capture_without_hiding:
            if self.was_fullscreen:
                self.showFullScreen()
            elif self.was_maximized:
                self.showMaximized()
            else:
                self.show()
            self.raise_()
            self.activateWindow()
            if not (self.isMaximized() or self.isFullScreen()):
                self.face.show()
        self.capture_without_hiding = False
        if error:
            self.on_completed('chat', {'ok':False, 'error':error})
        else:
            self.store.mark_screen(self.pending_message_id)
            self.start_chat(self.capture)

    def start_chat(self, image):
        history, question = self.pending_history, self.pending_text
        memories, github = self.pending_memories, self.pending_github
        config=dict(self.pending_config)
        if self.pending_attachment:
            question+='\n\nAttached document (untrusted reference text): '+self.pending_attachment['name']+'\n'+self.pending_attachment['text']
        def work():
            agent = Agent(config)
            agent.history = history
            try:
                answer = agent.reply(question, image, memories=memories, github=github)
                action_match=re.search(r'```sleepy-action\s*\n([\s\S]*?)```',answer)
                desktop_action=None
                if action_match:
                    try:desktop_action=json.loads(action_match.group(1))
                    except ValueError:pass
                    answer=answer.replace(action_match.group(0),'').strip() or 'Review this desktop action below.'
                image_match=re.search(r'```web-images\s*\n([\s\S]*?)```',answer)
                if image_match:
                    answer=answer.replace(image_match.group(0),'')
                    try:
                        query=json.loads(image_match.group(1)).get('query','')
                        images=search_images(str(query)[:200])
                        answer+='\n\n```web-images-results\n'+json.dumps(images)+'\n```'
                    except Exception as error:answer+='\n\nWeb images unavailable: '+friendly_error(error)
                return {'answer': answer, 'proposal': agent.pending_action, 'usage':agent.usage_report,'desktop_action':desktop_action}
            except Exception as error:
                return {'error':friendly_error(error),'usage':agent.usage_report}
            finally:
                agent.close()
        self.job('chat', work)

    def prepare_repo(self, data):
        if self.busy:
            raise ValueError('Wait for this response to finish first.')
        proposal = github_plugin.validate_repo(data)
        self.proposal = {**proposal, 'id':uuid.uuid4().hex, 'chat_id':self.chat_id}
        self.emit('proposal', proposal=self.proposal)

    def confirm_repo(self, proposal_id):
        if self.busy or not self.proposal or self.proposal['id'] != proposal_id:
            return
        if not self.prefs['github_enabled']:
            raise ValueError('Connect GitHub in Settings → Plugins first.')
        data = self.proposal
        login = self.store.get('github_login', 'your account')
        visibility = 'private' if data['private'] else 'PUBLIC'
        detail = f"Create {login}/{data['name']} as a {visibility} repository with a README?\n\n{data['description']}"
        if QMessageBox.question(self, 'Create GitHub repository?', detail, QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        self.proposal = None
        self.busy = True
        self.pending_cid = self.chat_id
        self.publish()
        self.job('repo_create', lambda: github_plugin.create_repo(data))

    @Slot(str, object)
    def on_completed(self, name, result):
        if self.closed:
            return
        self.jobs.discard(name)
        if self.feature_completed(name,result):return
        if name.startswith('test:'):
            if result['ok']:
                value=result['value']
                record(self.store,name.split(':',1)[1],value['model'],value['usage'])
            self.emit('api_status',message=result['value']['message'] if result['ok'] else result['error'])
            self.publish()
        elif name.startswith('models:'):
            profile_id=name.split(':',1)[1]
            if result['ok']:
                self.connections.cache_models(profile_id,result['value'])
                self.emit('api_status',message=f"Loaded {len(result['value']['models'])} models. Capabilities are shown where the provider reports them; unknown does not mean unsupported.")
            else:
                self.emit('api_status',message=result['error'])
            self.publish()
        elif name == 'chat':
            self.busy = False
            if result['ok']:
                value=result['value']
                record(self.store,self.pending_config['id'],self.pending_config['selected_model'],value.get('usage'))
                if value.get('error'):
                    result={'ok':False,'error':value['error']}
            if result['ok']:
                value = result['value']
                self.store.add(self.pending_cid, 'assistant', value['answer'])
                if isinstance(value.get('desktop_action'),dict):
                    action=value['desktop_action']
                    if action.get('kind') in ('create_folder','rename_file','organize_pdfs'):
                        try:self.execute_action(action)
                        except Exception as error:self.store.add(self.pending_cid,'error',friendly_error(error))
                    else:
                        self.action_preview={'id':uuid.uuid4().hex,'action':action,'chat_id':self.pending_cid,'model_proposal':True,
                                             'lines':[str(action.get('kind','')).replace('_',' ')+': '+str({k:v for k,v in action.items() if k!='kind'})]}
                if self.last_voice and self.prefs['voice_reply']:
                    spoken=re.sub(r'```[\s\S]*?```','',value['answer'])
                    self.read_aloud(spoken)
                self.last_voice=False
                if value['proposal']:
                    self.proposal = {**value['proposal'], 'id':uuid.uuid4().hex, 'chat_id':self.pending_cid}
            else:
                self.store.add(self.pending_cid, 'error', result['error'])
                self.store.set('draft:'+self.pending_cid, self.pending_text)
            self.pending_history=[]
            self.pending_attachment=None
            self.pending_config={}
            self.publish()
        elif name == 'github_connect':
            if result['ok']:
                self.store.set('github_login', result['value'])
                self.store.set('github_enabled', True)
                self.prefs['github_enabled'] = True
            self.emit('plugin_status', message='Connected as '+result['value'] if result['ok'] else result['error'])
            self.publish()
        elif name == 'repo_create':
            self.busy = False
            if result['ok']:
                repo = result['value']
                text = f"Created [{repo['name']}]({repo['url']}) with a README."
                self.store.add(self.pending_cid, 'assistant', text)
            else:
                self.store.add(self.pending_cid, 'error', result['error'])
            self.publish()

    def show_chat(self):
        was_hidden=not self.isVisible() or self.isMinimized()
        if was_hidden and not self.capturing:self.layout_pair.arrange(self)
        self.idle_timer.stop()
        self.discard_timer.stop()
        self.page.setLifecycleState(QWebEnginePage.Active)
        if self.isMinimized():
            self.showNormal()
        else:
            self.show()
        self.raise_()
        self.activateWindow()
        if not (self.isMaximized() or self.isFullScreen()):
            self.face.show()
        if self.state_dirty:self.publish()

    def toggle_chat(self):
        if self.isVisible() and not self.isMinimized():
            self.hide()
        else:
            self.show_chat()

    def open_settings(self,tab='appearance'):
        self.pending_settings=tab
        self.show_chat()
        if self.page_ready:
            self.pending_settings=None
            QTimer.singleShot(0,lambda:self.emit('open_settings',tab=tab))

    def fullscreen(self):
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange and hasattr(self, 'face') and not self.capturing:
            self.face.setVisible(not (self.isMaximized() or self.isFullScreen()))
            if self.isMinimized():
                self.idle_timer.start(3000)
            else:
                self.page.setLifecycleState(QWebEnginePage.Active)
                QTimer.singleShot(0,self.publish)
        super().changeEvent(event)

    def hideEvent(self, event):
        if hasattr(self,'idle_timer') and not self.capturing:
            self.layout_pair.restore()
            self.idle_timer.start(3000)
        super().hideEvent(event)

    def showEvent(self, event):
        if hasattr(self,'idle_timer'):
            self.idle_timer.stop()
            self.discard_timer.stop()
            self.page.setLifecycleState(QWebEnginePage.Active)
            if not self.ui_loaded:
                self.ui_loaded=True
                self.view.load(QUrl.fromLocalFile(str(BASE / 'ui' / 'index.html')))
            elif self.page_ready:
                self.publish()
        set_taskbar_identity(int(self.winId()), BASE)
        super().showEvent(event)

    def freeze_page(self):
        if not self.ui_loaded:return
        if (not self.isVisible() or self.isMinimized()) and not self.busy and not self.capturing and not self.audio_busy() and self.speech.state()!=QTextToSpeech.Speaking:
            self.page.setLifecycleState(QWebEnginePage.Frozen)
            self.discard_timer.start(20000)
        elif not self.isVisible() or self.isMinimized():
            self.idle_timer.start(3000)

    def discard_page(self):
        if not self.ui_loaded:return
        if (not self.isVisible() or self.isMinimized()) and not self.busy and not self.capturing and not self.audio_busy() and not self.file_dialog and self.speech.state()!=QTextToSpeech.Speaking:
            self.page_ready=False
            self.page.setLifecycleState(QWebEnginePage.Discarded)
            self.capture=None
            self.pending_history=[]
            self.pending_attachment=None
        elif not self.isVisible() or self.isMinimized():
            self.discard_timer.start(20000)

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.face.show()

    def quit_app(self):
        if self.busy and QMessageBox.question(self, 'Quit Sleepy?', 'A request is still running. Quit anyway?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        self.closed = True
        self.microphone.stop(cancel=True);self.music.stop();self.music_island.close();self.stop_voice();self.layout_pair.restore()
        self.speech.stop()
        self.store.close()
        self.tray.hide()
        QApplication.quit()


def main():
    if sys.platform=='win32':
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('Sleepy.Desktop.1')
    app = QApplication(sys.argv)
    app.setApplicationName('Sleepy')
    app.setWindowIcon(QIcon(str(BASE/'assets'/'sleepy.ico')))
    app.setQuitOnLastWindowClosed(False)
    socket = QLocalSocket()
    socket.connectToServer('SleepyDesktop.Local.v1')
    if socket.waitForConnected(300):
        socket.write(b'show')
        socket.waitForBytesWritten(300)
        return 0
    server = QLocalServer()
    QLocalServer.removeServer('SleepyDesktop.Local.v1')
    server.listen('SleepyDesktop.Local.v1')
    window = SleepyWindow()
    def wake():
        connection = server.nextPendingConnection()
        connection.close()
        if not window.busy:window.dispatch({'action':'new'})
        window.show_chat()
    server.newConnection.connect(wake)
    if '--open' in sys.argv:
        window.show_chat()
    return app.exec()

if __name__ == '__main__':
    sys.exit(main())
