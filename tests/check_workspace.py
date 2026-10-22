"""Arrange only disposable synthetic windows owned by child test processes."""
import subprocess
import sys
import time
import ctypes as C
from ctypes import wintypes as W
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject
from windows_integration import WorkspaceLayout,workspace_windows

app=QApplication.instance() or QApplication([])
class Host(QObject):
    def __init__(self):
        super().__init__();self.layout_pair=type('Pair',(),{'saved':None})();self.notices=[]
    def emit(self,*args,**kwargs):self.notices.append(kwargs)
    def screen(self):return app.primaryScreen()

def run():
    if sys.platform!='win32':print('SKIP: Windows window arrangement');return
    host=Host();layout=WorkspaceLayout(host);children=[]
    def launch(name):
        code="from PySide6.QtWidgets import QApplication,QWidget; a=QApplication([]); w=QWidget(); w.setWindowTitle("+repr(name)+"); w.resize(320,240); w.show(); a.exec()"
        children.append(subprocess.Popen([sys.executable,'-c',code]))
    try:
        layout.start([(name,lambda n=name:launch(n)) for name in ('SleepyQAOne','SleepyQATwo','SleepyQAThree')])
        deadline=time.monotonic()+35
        while not host.notices and time.monotonic()<deadline:
            app.processEvents();time.sleep(.02)
        assert host.notices and len(layout.windows)==3,(host.notices,layout.windows)
        user=C.windll.user32;user.GetWindowRect.argtypes=[W.HWND,C.POINTER(W.RECT)]
        rects=[]
        for hwnd in layout.windows:
            r=W.RECT();assert user.GetWindowRect(hwnd,C.byref(r));rects.append((r.left,r.top,r.right,r.bottom))
        assert len(set(rects))==3,rects
        for i,r in enumerate(rects):
            for other in rects[i+1:]:assert r[2]<=other[0] or other[2]<=r[0] or r[3]<=other[1] or other[3]<=r[1],rects
        print('PASS: three actual external windows discovered and tiled on the same monitor')
    finally:
        layout.timer.stop()
        for child in children:
            child.terminate();child.wait(timeout=5)

if __name__=='__main__':run()
