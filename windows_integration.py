"""Small Windows integrations; no packaging or user-data migration required."""
import ctypes as C
from ctypes import wintypes as W
import subprocess
import sys
import uuid
import math
import os
import re
from app_paths import relaunch_command

def tile_rects(area,count):
    """Balanced rows, with no empty cells in the final row."""
    if count<1:return []
    columns=math.ceil(math.sqrt(count*area.width()/area.height()))
    columns=min(count,columns);rows=math.ceil(count/columns);result=[]
    for row in range(rows):
        cells=min(columns,count-row*columns)
        for col in range(cells):
            x=area.x()+col*area.width()//cells;y=area.y()+row*area.height()//rows
            result.append((x,y,(col+1)*area.width()//cells-col*area.width()//cells,(row+1)*area.height()//rows-row*area.height()//rows))
    return result

def workspace_windows():
    """Visible user windows with title/process identity; never infer shell commands."""
    if sys.platform!='win32':
        import unix_windows
        return unix_windows.windows()
    user=C.windll.user32;kernel=C.windll.kernel32;result={}
    user.GetWindowTextW.argtypes=[W.HWND,W.LPWSTR,C.c_int]
    user.IsWindowVisible.argtypes=[W.HWND]
    user.GetWindowThreadProcessId.argtypes=[W.HWND,C.POINTER(W.DWORD)]
    kernel.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];kernel.OpenProcess.restype=W.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,C.POINTER(W.DWORD)]
    kernel.CloseHandle.argtypes=[W.HANDLE]
    @C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
    def visit(hwnd,_):
        if not user.IsWindowVisible(hwnd):return True
        title=C.create_unicode_buffer(1024);user.GetWindowTextW(hwnd,title,1024)
        if not title.value:return True
        pid=W.DWORD();user.GetWindowThreadProcessId(hwnd,C.byref(pid))
        if pid.value==os.getpid():return True
        image='';handle=kernel.OpenProcess(0x1000,False,pid.value)
        if handle:
            try:
                path=C.create_unicode_buffer(32768);length=W.DWORD(32768)
                if kernel.QueryFullProcessImageNameW(handle,0,path,C.byref(length)):image=path.value.rsplit('\\',1)[-1]
            finally:kernel.CloseHandle(handle)
        result[int(hwnd)]=(title.value,image)
        return True
    user.EnumWindows(visit,0)
    return result

class WorkspaceLayout:
    """Bounded window discovery while a preset opens. No idle polling."""
    def __init__(self,host):
        from PySide6.QtCore import QTimer
        self.host=host;self.timer=QTimer(host);self.timer.setInterval(350);self.timer.timeout.connect(self.poll)
        self.targets=[];self.windows=[];self.jobs=[]

    def start(self,jobs):
        from PySide6.QtGui import QCursor
        from PySide6.QtWidgets import QApplication
        if self.timer.isActive():raise ValueError('A workspace is still opening. Please wait a moment.')
        self.screen=QApplication.screenAt(QCursor.pos()) or self.host.screen()
        self.jobs=list(jobs);self.windows=[];self.failed=[];self.next()

    def next(self):
        if not self.jobs:self.finish();return
        name,launch=self.jobs.pop(0);self.name=name;self.before=workspace_windows();self.ticks=0
        try:launch()
        except Exception as e:
            self.failed.append(name+': '+str(e));self.next();return
        if sys.platform!='win32':
            import unix_windows
            if not unix_windows.supported():self.next();return
        self.timer.start()

    def poll(self):
        self.ticks+=1;current=workspace_windows()
        def normalized(s):return re.sub(r'[^a-z0-9]','',s.lower())
        names=['chrome','msedge','firefox','brave','opera'] if self.name=='Browser' else [normalized(self.name)]
        matches=[h for h,(title,exe) in current.items() if any(n and (n in normalized(title) or n in normalized(exe)) for n in names)]
        # Prefer the newly created window; existing single-instance apps can reuse theirs.
        fresh=[h for h in matches if h not in self.before]
        if fresh or (matches and self.ticks>=5) or self.ticks>=20:
            foreground=None
            if sys.platform=='win32':
                user=C.windll.user32;user.GetForegroundWindow.restype=W.HWND
                foreground=user.GetForegroundWindow()
            chosen=(fresh or ([foreground] if foreground in matches else matches))[:1]
            for hwnd in chosen:
                if hwnd not in self.windows:self.windows.append(hwnd)
            if not chosen:self.failed.append(self.name+' opened, but its window could not be arranged.')
            self.timer.stop();self.next()

    def finish(self):
        if sys.platform!='win32' and self.windows:
            import unix_windows
            for hwnd,rect in zip(self.windows,tile_rects(self.screen.availableGeometry(),len(self.windows))):
                try:unix_windows.move(hwnd,rect)
                except Exception as error:self.failed.append(str(error))
        if sys.platform=='win32' and self.windows:
            user=C.windll.user32
            user.SetWindowPos.argtypes=[W.HWND,W.HWND,C.c_int,C.c_int,C.c_int,C.c_int,W.UINT]
            user.ShowWindow.argtypes=[W.HWND,C.c_int]
            ratio=self.screen.devicePixelRatio()
            for hwnd,rect in zip(self.windows,tile_rects(self.screen.availableGeometry(),len(self.windows))):
                user.ShowWindow(hwnd,9)
                user.SetWindowPos(hwnd,None,*(round(v*ratio) for v in rect),0x0014)
            # A preset has intentionally replaced the previous two-window arrangement.
            self.host.layout_pair.saved=None
        message='Workspace ready.' if not self.failed else 'Workspace opened. '+ ' '.join(self.failed)
        if sys.platform!='win32':
            import unix_windows
            if not unix_windows.supported():message+=' Use your desktop’s native tiling; on X11 install wmctrl for automatic arrangement.'
        self.host.emit('notice',message=message)

class SideBySide:
    """Restore the previous window only if it still has the bounds we set."""
    def __init__(self):
        self.saved=None

    def arrange(self,widget):
        from PySide6.QtGui import QCursor
        from PySide6.QtWidgets import QApplication
        screen=QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        area=screen.availableGeometry()
        width=min(620,max(440,area.width()//3))
        widget.setGeometry(area.right()-width+1,area.top(),width,area.height())
        if sys.platform!='win32':return
        user=C.windll.user32
        user.GetForegroundWindow.restype=W.HWND
        hwnd=user.GetForegroundWindow()
        own=int(widget.winId())
        if not hwnd or hwnd==own:return
        pid=W.DWORD();user.GetWindowThreadProcessId.argtypes=[W.HWND,C.POINTER(W.DWORD)];user.GetWindowThreadProcessId(hwnd,C.byref(pid))
        import os
        if pid.value==os.getpid():return
        user.GetWindowRect.argtypes=[W.HWND,C.POINTER(W.RECT)]
        user.SetWindowPos.argtypes=[W.HWND,W.HWND,C.c_int,C.c_int,C.c_int,C.c_int,W.UINT]
        user.ShowWindow.argtypes=[W.HWND,C.c_int]
        user.IsZoomed.argtypes=[W.HWND];user.IsZoomed.restype=W.BOOL
        original=W.RECT()
        if not user.GetWindowRect(hwnd,C.byref(original)):return
        maximized=bool(user.IsZoomed(hwnd))
        ratio=screen.devicePixelRatio()
        rect=(round(area.x()*ratio),round(area.y()*ratio),round((area.width()-width)*ratio),round(area.height()*ratio))
        if maximized:user.ShowWindow(hwnd,9)
        if user.SetWindowPos(hwnd,None,*rect,0x0014):
            actual=W.RECT();user.GetWindowRect(hwnd,C.byref(actual))
            self.saved=(hwnd,original,maximized,tuple(getattr(actual,k) for k in ('left','top','right','bottom')))

    def restore(self):
        if not self.saved or sys.platform!='win32':return
        hwnd,rect,maximized,expected=self.saved;self.saved=None
        user=C.windll.user32;current=W.RECT()
        if user.GetWindowRect(hwnd,C.byref(current)) and tuple(getattr(current,k) for k in ('left','top','right','bottom'))==expected:
            user.SetWindowPos(hwnd,None,rect.left,rect.top,rect.right-rect.left,rect.bottom-rect.top,0x0014)
            if maximized:user.ShowWindow(hwnd,3)


class CaptureExclusion:
    """Exclude only during our snapshot, then restore previous recording behavior."""
    def __init__(self, widgets):
        self.widgets = widgets
        self.saved = []

    def begin(self):
        if sys.platform != 'win32' or sys.getwindowsversion().build < 19041:
            return False
        user = C.WinDLL('user32', use_last_error=True)
        self.set = user.SetWindowDisplayAffinity
        self.set.argtypes = [W.HWND, W.DWORD]
        self.set.restype = W.BOOL
        get = user.GetWindowDisplayAffinity
        get.argtypes = [W.HWND, C.POINTER(W.DWORD)]
        get.restype = W.BOOL
        for widget in self.widgets:
            if not widget.isVisible():
                continue
            hwnd, previous = int(widget.winId()), W.DWORD()
            if not get(hwnd, C.byref(previous)):
                self.restore()
                return False
            self.saved.append((hwnd, previous.value))
            if not self.set(hwnd, 0x11):
                self.restore()
                return False
        C.windll.dwmapi.DwmFlush()
        return True

    def restore(self):
        for hwnd, previous in reversed(self.saved):
            self.set(hwnd, previous)
        self.saved.clear()


class GUID(C.Structure):
    _fields_ = [('data1', W.DWORD), ('data2', W.WORD), ('data3', W.WORD), ('data4', C.c_ubyte * 8)]

    @classmethod
    def parse(cls, value):
        return cls.from_buffer_copy(uuid.UUID(value).bytes_le)


class PropertyKey(C.Structure):
    _fields_ = [('fmtid', GUID), ('pid', W.DWORD)]


class Value(C.Union):
    _fields_ = [('text', C.c_wchar_p), ('storage', C.c_ubyte * (16 if C.sizeof(C.c_void_p) == 8 else 8))]


class PropVariant(C.Structure):
    _fields_ = [('vt', W.WORD), ('reserved', W.WORD * 3), ('value', Value)]


def set_taskbar_identity(hwnd, root):
    """Supply relaunch properties so a pinned Python-hosted window is Sleepy."""
    if sys.platform != 'win32':
        return False
    store = C.c_void_p()
    get = C.windll.shell32.SHGetPropertyStoreForWindow
    get.argtypes = [W.HWND, C.POINTER(GUID), C.POINTER(C.c_void_p)]
    get.restype = C.c_long
    iid = GUID.parse('886d8eeb-8cf2-4446-8d02-cdba1dbdcf99')
    if get(hwnd, C.byref(iid), C.byref(store)) < 0:
        return False
    table = C.cast(store, C.POINTER(C.POINTER(C.c_void_p))).contents
    release = C.WINFUNCTYPE(W.ULONG, C.c_void_p)(table[2])
    set_value = C.WINFUNCTYPE(C.c_long, C.c_void_p, C.POINTER(PropertyKey), C.POINTER(PropVariant))(table[6])
    try:
        properties = {
            2: subprocess.list2cmdline(relaunch_command(root)),
            3: str(root / 'assets' / 'sleepy.ico') + ',0',
            4: 'Sleepy',
            5: 'Sleepy.Desktop.1',
        }
        for pid, text in properties.items():
            key = PropertyKey(GUID.parse('9f4c2855-9f79-4b39-a8d0-e1d42de1d5f3'), pid)
            value = PropVariant()
            value.vt = 31  # VT_LPWSTR; SetValue copies the string.
            value.value.text = text
            if set_value(store, C.byref(key), C.byref(value)) < 0:
                return False
        return True
    finally:
        release(store)
