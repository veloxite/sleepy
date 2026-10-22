"""On-demand public SoundCloud streams and local audio; no background polling."""
from pathlib import Path
import re
from functools import lru_cache
from PySide6.QtCore import QObject,Signal,QUrl,Qt,QByteArray,QSize
from PySide6.QtGui import QIcon,QPixmap,QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtMultimedia import QMediaPlayer,QAudioOutput
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QSlider

@lru_cache(maxsize=4)
def transport_icon(kind):
    paths={'previous':'<path d="M5 5h3v14H5zM19 5v14l-10-7z"/>',
           'next':'<path d="M16 5h3v14h-3zM5 5l10 7-10 7z"/>',
           'pause':'<path d="M5 4h5v16H5zM14 4h5v16h-5z"/>',
           'play':'<path d="M6 3l15 9-15 9z"/>'}
    svg=('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#f5f4f7">'+paths[kind]+'</svg>').encode()
    pixmap=QPixmap(48,48);pixmap.fill(Qt.transparent);painter=QPainter(pixmap)
    QSvgRenderer(QByteArray(svg)).render(painter);painter.end();return QIcon(pixmap)

def music_query(query):
    """Recognize broad listening intents; preserve specific song/artist searches."""
    moods={'party':'dance pop upbeat party DJ mix','study':'instrumental lofi focus study mix',
           'focus':'ambient instrumental focus mix','relaxing':'chill ambient relaxing mix',
           'workout':'energetic workout dance mix','sleep':'calm ambient sleep mix',
           'chill':'chill downtempo mix','party music':'dance pop upbeat party DJ mix'}
    clean=re.sub(r'^(?:some|a little)\s+','',query.strip().lower())
    clean=re.sub(r'\s+(?:music|songs|playlist|mix)$','',clean)
    return moods.get(clean,query)

def search_tracks(query):
    import yt_dlp
    class Quiet:
        def debug(self,*args):pass
        def warning(self,*args):pass
        def error(self,*args):pass
    options={'quiet':True,'no_warnings':True,'logger':Quiet(),'extract_flat':True,'socket_timeout':15,'retries':0,'playlistend':5,'skip_download':True}
    with yt_dlp.YoutubeDL(options) as ydl:
        result=ydl.extract_info('scsearch5:'+music_query(query)[:200],download=False)
    tracks=[]
    for item in (result or {}).get('entries',[]):
        url=item.get('webpage_url') or item.get('url','')
        if url.startswith('https://soundcloud.com/'):
            tracks.append({'title':item.get('title','SoundCloud track'),'artist':item.get('uploader',''),'url':url})
    if not tracks:raise ValueError('No public SoundCloud tracks found. Try the song title plus artist, or open SoundCloud in your browser.')
    return tracks

def stream_track(track):
    if track.get('local'):return track['url']
    import yt_dlp
    class Quiet:
        def debug(self,*args):pass
        def warning(self,*args):pass
        def error(self,*args):pass
    try:
        with yt_dlp.YoutubeDL({'quiet':True,'logger':Quiet(),'no_warnings':True,'format':'bestaudio/best','socket_timeout':15,'retries':0,'skip_download':True,'noplaylist':True}) as ydl:
            item=ydl.extract_info(track['url'],download=False)
        if item.get('is_drm') or item.get('availability') in ('premium_only','subscriber_only','needs_auth'):
            raise ValueError('This track requires a subscription or login. Open it on SoundCloud instead.')
        url=item.get('url','')
        if not url.startswith('https://'):raise ValueError('No playable public stream is available for this track.')
        return url
    except ValueError:raise
    except Exception:raise ValueError('SoundCloud could not provide this public stream. It may be unavailable, restricted, or the service may have changed. Open the track in your browser instead.') from None

class MusicPlayer(QObject):
    changed=Signal()
    advance=Signal(int)
    failed=Signal(str)
    def __init__(self,parent=None):
        super().__init__(parent);self.queue=[];self.index=0
        self.output=QAudioOutput(self);self.output.setVolume(.5)
        self.player=QMediaPlayer(self);self.player.setAudioOutput(self.output)
        self.player.playbackStateChanged.connect(lambda _:self.changed.emit())
        self.player.errorOccurred.connect(lambda _,message:self.failed.emit('Music playback: '+message))
        self.player.mediaStatusChanged.connect(lambda status:self.advance.emit(1) if status==QMediaPlayer.EndOfMedia else None)

    def state(self):
        track=self.queue[self.index] if self.queue else {}
        return {'playing':self.player.playbackState()==QMediaPlayer.PlayingState,'active':not self.player.source().isEmpty(),'title':track.get('title',''),'artist':track.get('artist',''),'url':track.get('url',''),'queue':self.queue,'index':self.index}

    def play_url(self,url):
        self.player.setSource(QUrl.fromLocalFile(url) if Path(url).is_absolute() else QUrl(url));self.player.play();self.changed.emit()

    def stop(self):
        self.player.stop();self.player.setSource(QUrl());self.changed.emit()

class MusicIsland(QWidget):
    def __init__(self,host):
        super().__init__(None,Qt.Tool|Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint)
        self.host=host;self.setFixedWidth(330)
        self.setAttribute(Qt.WA_TranslucentBackground)
        outer=QVBoxLayout(self);outer.setContentsMargins(0,0,0,0)
        card=QWidget();card.setObjectName('island');outer.addWidget(card)
        self.setStyleSheet('QWidget#island{background:#101114;border:1px solid #39333f;border-radius:26px} QLabel{color:#f5f4f7;background:transparent;border:0} QPushButton{color:#f5f4f7;background:transparent;border:0;border-radius:14px;padding:9px;font-size:18px} QPushButton:hover{background:#303039} QLabel#cover{background:#413652;border-radius:14px;color:#dcc8ff;font-size:28px} QLabel#artist{color:#9d9aa7;font-size:11px} QSlider::groove:horizontal{height:4px;background:#35343b;border-radius:2px} QSlider::sub-page:horizontal{background:#c9b0f5;border-radius:2px} QSlider::handle:horizontal{background:#f4ebff;width:10px;margin:-3px 0;border-radius:5px}')
        layout=QVBoxLayout(card);layout.setContentsMargins(20,17,20,14);layout.setSpacing(10)
        top=QHBoxLayout();cover=QLabel('♫');cover.setObjectName('cover');cover.setAlignment(Qt.AlignCenter);cover.setFixedSize(48,48);top.addWidget(cover)
        text=QVBoxLayout();self.title=QLabel();self.title.setMaximumWidth(200);self.title.setStyleSheet('font-weight:600;font-size:13px');self.artist=QLabel();self.artist.setObjectName('artist');text.addWidget(self.title);text.addWidget(self.artist);top.addLayout(text,1)
        close=QPushButton('×');close.setToolTip('Close music');close.setAccessibleName('Close music');close.clicked.connect(lambda:host.execute_action({'kind':'music_close'}));top.addWidget(close);layout.addLayout(top)
        self.progress=QSlider(Qt.Horizontal);self.progress.setAccessibleName('Track position');self.progress.sliderReleased.connect(lambda:host.music.player.setPosition(self.progress.value()));layout.addWidget(self.progress)
        self.time=QLabel();self.time.setObjectName('artist');layout.addWidget(self.time)
        row=QHBoxLayout();row.addStretch()
        for label,tip,action in [('⏮','Previous','music_previous'),('Ⅱ','Pause','music_pause'),('⏭','Next','music_next')]:
            b=QPushButton();b.setIcon(transport_icon({'music_previous':'previous','music_pause':'pause','music_next':'next'}[action]));b.setIconSize(QSize(22,22));b.setToolTip(tip);b.setAccessibleName(tip);b.setFixedSize(54,38)
            if action=='music_pause':self.pause=b;b.clicked.connect(self.toggle)
            else:b.clicked.connect(lambda _,a=action:host.execute_action({'kind':a}))
            row.addWidget(b)
        row.addStretch();layout.addLayout(row)
        host.music.player.positionChanged.connect(self.refresh_progress)
        host.music.player.durationChanged.connect(self.refresh_progress)

    def toggle(self):
        self.host.execute_action({'kind':'music_pause' if self.host.music.state()['playing'] else 'music_resume'})

    def refresh_progress(self,*_):
        if not self.isVisible():return
        player=self.host.music.player;duration=player.duration();position=player.position()
        if not self.progress.isSliderDown():self.progress.setRange(0,max(1,duration));self.progress.setValue(position)
        self.progress.setEnabled(player.isSeekable())
        def stamp(ms):return f'{ms//60000}:{ms//1000%60:02d}'
        self.time.setText(stamp(position)+'  /  '+(stamp(duration) if duration else 'Live stream'))

    def refresh(self):
        state=self.host.music.state()
        self.title.setText(self.title.fontMetrics().elidedText(state['title'],Qt.ElideRight,190))
        self.title.setToolTip(state['title']);self.artist.setText(self.artist.fontMetrics().elidedText(state['artist'] or 'Local audio',Qt.ElideRight,190))
        self.pause.setIcon(transport_icon('pause' if state['playing'] else 'play'));self.pause.setToolTip('Pause' if state['playing'] else 'Resume');self.pause.setAccessibleName(self.pause.toolTip());self.refresh_progress()
    def reveal(self):
        state=self.host.music.state()
        if not state['active']:self.hide();return
        self.refresh()
        ball=self.host.face;screen=ball.screen().availableGeometry()
        self.move(max(screen.left(),min(ball.x()+ball.width()-self.width(),screen.right()-self.width())),max(screen.top(),ball.y()-self.sizeHint().height()-8))
        self.show()
