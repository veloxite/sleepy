"""Windows process-tree benchmark with synthetic chats, no keys or network requests.

Run with python -m tests.benchmark_idle. Qt waits use its event loop, not polling.
CPU is percent of one logical core; working set includes shared pages across processes.
"""
import ctypes as C
from ctypes import wintypes as W
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import QEventLoop,QTimer
from PySide6.QtWidgets import QApplication
from sleepy_app import SleepyWindow
from local_store import Store

class Entry(C.Structure):
    _fields_=[('size',W.DWORD),('usage',W.DWORD),('pid',W.DWORD),('heap',C.c_size_t),('module',W.DWORD),('threads',W.DWORD),('parent',W.DWORD),('priority',W.LONG),('flags',W.DWORD),('name',W.WCHAR*260)]
class Memory(C.Structure):
    _fields_=[('cb',W.DWORD),('faults',W.DWORD)]+[(n,C.c_size_t) for n in ('peak_working','working','peak_paged','paged','peak_nonpaged','nonpaged','pagefile','peak_pagefile','private')]

def snapshot():
    kernel=C.windll.kernel32;psapi=C.windll.psapi
    kernel.CreateToolhelp32Snapshot.argtypes=[W.DWORD,W.DWORD];kernel.CreateToolhelp32Snapshot.restype=W.HANDLE
    kernel.Process32FirstW.argtypes=[W.HANDLE,C.POINTER(Entry)];kernel.Process32NextW.argtypes=[W.HANDLE,C.POINTER(Entry)]
    kernel.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];kernel.OpenProcess.restype=W.HANDLE
    kernel.CloseHandle.argtypes=[W.HANDLE]
    kernel.GetProcessTimes.argtypes=[W.HANDLE,*([C.POINTER(W.FILETIME)]*4)]
    psapi.GetProcessMemoryInfo.argtypes=[W.HANDLE,C.POINTER(Memory),W.DWORD]
    handle=kernel.CreateToolhelp32Snapshot(2,0);entry=Entry();entry.size=C.sizeof(entry);parents={}
    try:
        ok=kernel.Process32FirstW(handle,C.byref(entry))
        while ok:parents[entry.pid]=entry.parent;ok=kernel.Process32NextW(handle,C.byref(entry))
    finally:kernel.CloseHandle(handle)
    ids={os.getpid()}
    while True:
        expanded=ids|{pid for pid,parent in parents.items() if parent in ids}
        if expanded==ids:break
        ids=expanded
    result={}
    for pid in ids:
        process=kernel.OpenProcess(0x410,False,pid)
        if not process:continue
        try:
            memory=Memory();memory.cb=C.sizeof(memory)
            if not psapi.GetProcessMemoryInfo(process,C.byref(memory),memory.cb):continue
            times=[W.FILETIME() for _ in range(4)]
            kernel.GetProcessTimes(process,*[C.byref(t) for t in times])
            cpu=sum((t.dwHighDateTime<<32)+t.dwLowDateTime for t in times[2:])/10_000_000
            result[pid]=(cpu,memory.working,memory.private)
        finally:kernel.CloseHandle(process)
    return result

def wait(seconds):
    loop=QEventLoop();QTimer.singleShot(round(seconds*1000),loop.quit);loop.exec()

def measure(label,seconds=10):
    before=snapshot();start=time.monotonic();wait(seconds);after=snapshot();elapsed=time.monotonic()-start
    cpu=sum(max(0,values[0]-before.get(pid,values)[0]) for pid,values in after.items())
    result={'phase':label,'seconds':round(elapsed,1),'processes':len(after),'cpu_one_core_percent':round(cpu/elapsed*100,2),
            'working_set_mb':round(sum(v[1] for v in after.values())/2**20,1),'private_mb':round(sum(v[2] for v in after.values())/2**20,1)}
    print(json.dumps(result),flush=True);return result

def run():
    if sys.platform!='win32':raise SystemExit('This benchmark uses Windows process counters.')
    app=QApplication.instance() or QApplication([]);app.setQuitOnLastWindowClosed(False)
    with tempfile.TemporaryDirectory() as folder,patch('windows_integration.SideBySide.arrange'):
        store=Store(Path(folder)/'bench.db');store.set('api_profiles',[]);store.set('screen_enabled',False)
        window=SleepyWindow(store)
        try:
            wait(2);measure('cold_ball');window.show_chat();wait(4)
            measure('visible_empty')
            for i in range(40):
                store.add(window.chat_id,'user',f'Explain concept {i}.')
                store.add(window.chat_id,'assistant','A short explanation with **formatting**.\n\n```python\nprint("hello")\n```')
            window.publish();wait(3);measure('visible_80_messages')
            window.hide();wait(5);measure('ball_frozen')
            window.discard_page();wait(3);measure('ball_discarded')
            # Import the SDK without an API request to model memory after first use.
            from openai import OpenAI
            wait(2);measure('ball_discarded_sdk_loaded')
            window.publish();wait(1)
            print(json.dumps({'hidden_publish_lifecycle':window.page.lifecycleState().name}),flush=True)
        finally:
            window.closed=True;window.face.close();window.tray.hide();window.music.stop();window.stop_voice();window.view.setPage(None);window.deleteLater();wait(.5);store.close()

if __name__=='__main__':run()
