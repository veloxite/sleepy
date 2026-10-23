"""Native Qt capture on macOS/Wayland; retain Pillow on Windows and X11."""
import io
import os
import sys
from PIL import Image, ImageGrab


def grab(*, all_screens=False):
    if sys.platform != 'darwin' and not (sys.platform.startswith('linux') and os.environ.get('XDG_SESSION_TYPE') == 'wayland'):
        return ImageGrab.grab(all_screens=all_screens)
    from PySide6.QtCore import QEventLoop, QTimer, QBuffer, QIODevice
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtMultimedia import QScreenCapture, QMediaCaptureSession, QVideoSink
    loop = QEventLoop()
    capture = QScreenCapture()
    session = QMediaCaptureSession()
    sink = QVideoSink()
    session.setScreenCapture(capture)
    session.setVideoSink(sink)
    capture.setScreen(QGuiApplication.primaryScreen())
    result = []
    errors = []

    def frame_ready(frame):
        image = frame.toImage()
        if not image.isNull() and not result:
            buffer = QBuffer()
            buffer.open(QIODevice.WriteOnly)
            image.save(buffer, 'PNG')
            result.append(Image.open(io.BytesIO(bytes(buffer.data()))).convert('RGB'))
            loop.quit()

    def failed(*args):
        errors.append(capture.errorString())
        loop.quit()

    sink.videoFrameChanged.connect(frame_ready)
    capture.errorOccurred.connect(failed)
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    timer.start(45000)
    try:
        capture.start()
        if not result and not errors:
            loop.exec()
    finally:
        timer.stop()
        capture.stop()
        session.setScreenCapture(None)
        session.setVideoSink(None)
    if not result:
        detail = '; '.join(errors) or 'Capture timed out or sharing was cancelled.'
        raise ValueError(detail + ' On macOS allow Sleepy in Privacy & Security → Screen Recording. On Wayland approve the system sharing picker and check that PipeWire and your desktop portal are installed. No AI request was sent.')
    return result[0]
