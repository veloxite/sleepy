"""Local synthetic capture regression: no desktop image is saved or uploaded."""
import ctypes as C
import time
from pathlib import Path
from PIL import ImageGrab
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget
from windows_integration import CaptureExclusion, set_taskbar_identity, GUID, PropertyKey, PropVariant

app = QApplication([])
def pump():
    for _ in range(20):
        app.processEvents()
        time.sleep(.01)

background = QWidget(None, Qt.FramelessWindowHint)
background.setStyleSheet('background: rgb(32,64,96)')
background.showFullScreen()
foreground = QWidget(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
foreground.setStyleSheet('background: rgb(240,80,80)')
foreground.setGeometry(100,100,300,300)
foreground.show()
foreground.raise_()
pump()
try:
    assert set_taskbar_identity(int(foreground.winId()), Path(__file__).resolve().parent.parent)
    # Read the actual window property store back, including the relaunch icon.
    store = C.c_void_p()
    iid = GUID.parse('886d8eeb-8cf2-4446-8d02-cdba1dbdcf99')
    assert C.windll.shell32.SHGetPropertyStoreForWindow(int(foreground.winId()), C.byref(iid), C.byref(store)) == 0
    table = C.cast(store, C.POINTER(C.POINTER(C.c_void_p))).contents
    get = C.WINFUNCTYPE(C.c_long, C.c_void_p, C.POINTER(PropertyKey), C.POINTER(PropVariant))(table[5])
    try:
        for pid, expected in [(3, 'sleepy.ico,0'), (4,'Sleepy'), (5,'Sleepy.Desktop.1'), (2,'--open')]:
            key = PropertyKey(GUID.parse('9f4c2855-9f79-4b39-a8d0-e1d42de1d5f3'),pid)
            value = PropVariant()
            assert get(store,C.byref(key),C.byref(value)) == 0
            assert expected in value.value.text
            C.windll.ole32.PropVariantClear(C.byref(value))
    finally:
        C.WINFUNCTYPE(C.c_ulong,C.c_void_p)(table[2])(store)
    # Convert the test window center to physical screenshot pixels for DPI scaling.
    ratio = foreground.devicePixelRatioF()
    center = foreground.geometry().center()
    point = (round(center.x()*ratio),round(center.y()*ratio))
    def color():
        return ImageGrab.grab().convert('RGB').getpixel(point)
    assert color() == (240,80,80), color()
    exclusion = CaptureExclusion([foreground])
    assert exclusion.begin(), 'Windows capture exclusion failed'
    try:
        pump()
        assert foreground.isVisible()
        assert color() == (32,64,96), 'Capture did not reveal the test background'
    finally:
        exclusion.restore()
    pump()
    assert foreground.isVisible() and color() == (240,80,80)
    print('PASS: taskbar icon/name/relaunch readback; real capture excludes visible window; recording restored')
finally:
    foreground.close()
    background.close()
