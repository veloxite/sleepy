"""Window layout adapters. Wayland deliberately uses compositor-owned tiling."""
import os
import shutil
import subprocess
import sys


def supported():
    return sys.platform == 'darwin' or (sys.platform.startswith('linux') and os.environ.get('XDG_SESSION_TYPE') != 'wayland' and bool(shutil.which('wmctrl')))


def windows():
    if not supported():
        return {}
    if sys.platform == 'darwin':
        import Quartz
        rows = Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements, Quartz.kCGNullWindowID)
        return {int(r[Quartz.kCGWindowNumber]): (r.get(Quartz.kCGWindowName, ''), r.get(Quartz.kCGWindowOwnerName, ''))
                for r in rows if r.get(Quartz.kCGWindowLayer) == 0 and r.get(Quartz.kCGWindowOwnerPID) != os.getpid()}
    rows = subprocess.run(['wmctrl', '-lp'], capture_output=True, text=True, timeout=3, check=True).stdout.splitlines()
    result = {}
    for row in rows:
        parts = row.split(None, 4)
        if len(parts) == 5 and parts[2] != str(os.getpid()):
            result[int(parts[0], 16)] = (parts[4], '')
    return result


def _mac_window(handle):
    import Quartz
    import ApplicationServices as AX
    if not AX.AXIsProcessTrusted():
        raise ValueError('Allow Sleepy in System Settings → Privacy & Security → Accessibility to arrange windows.')
    rows = Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionIncludingWindow, handle)
    if not rows:
        raise ValueError('The window is no longer available.')
    info = rows[0]
    app = AX.AXUIElementCreateApplication(info[Quartz.kCGWindowOwnerPID])
    status, items = AX.AXUIElementCopyAttributeValue(app, AX.kAXWindowsAttribute, None)
    if status or not items:
        raise ValueError('This application does not expose movable windows.')
    title = info.get(Quartz.kCGWindowName, '')
    for item in items:
        status, value = AX.AXUIElementCopyAttributeValue(item, AX.kAXTitleAttribute, None)
        if not status and value == title:
            return item
    if len(items) == 1:
        return items[0]
    raise ValueError('Could not safely identify the application window to arrange.')


def move(handle, rect):
    if sys.platform == 'darwin':
        import ApplicationServices as AX
        window = _mac_window(handle)
        x, y, w, h = rect
        for attribute, kind, value in ((AX.kAXPositionAttribute, AX.kAXValueCGPointType, (x, y)),
                                       (AX.kAXSizeAttribute, AX.kAXValueCGSizeType, (w, h))):
            if AX.AXUIElementSetAttributeValue(window, attribute, AX.AXValueCreate(kind, value)):
                raise ValueError('The application refused window resizing. Exit its full-screen mode and try again.')
    else:
        subprocess.run(['wmctrl', '-ir', hex(handle), '-b', 'remove,maximized_vert,maximized_horz'], timeout=3, check=True)
        subprocess.run(['wmctrl', '-ir', hex(handle), '-e', '0,' + ','.join(str(round(v)) for v in rect)], timeout=3, check=True)


def bounds(handle):
    if sys.platform == 'darwin':
        import Quartz
        rows = Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionIncludingWindow, handle)
        if not rows:raise ValueError('Window closed.')
        r = rows[0][Quartz.kCGWindowBounds]
        return tuple(round(r[k]) for k in ('X', 'Y', 'Width', 'Height'))
    rows = subprocess.run(['wmctrl', '-lG'], capture_output=True, text=True, timeout=3, check=True).stdout.splitlines()
    for row in rows:
        parts = row.split(None, 7)
        if len(parts) >= 6 and int(parts[0], 16) == handle:
            return tuple(int(v) for v in parts[2:6])
    raise ValueError('Window closed.')


def active():
    if sys.platform == 'darwin':
        import AppKit
        import Quartz
        pid = AppKit.NSWorkspace.sharedWorkspace().frontmostApplication().processIdentifier()
        if pid == os.getpid():return None
        rows = Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionOnScreenOnly, 0)
        return next((int(r[Quartz.kCGWindowNumber]) for r in rows if r.get(Quartz.kCGWindowOwnerPID) == pid and r.get(Quartz.kCGWindowLayer) == 0), None)
    if not shutil.which('xprop'):return None
    text = subprocess.run(['xprop', '-root', '_NET_ACTIVE_WINDOW'], capture_output=True, text=True, timeout=3, check=True).stdout
    import re
    match = re.search(r'0x[0-9a-fA-F]+', text)
    return int(match.group(), 16) if match else None
