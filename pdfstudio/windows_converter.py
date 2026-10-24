"""Start a suspended converter in a private Windows job before it can spawn children.

https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects
"""
import ctypes
from ctypes import wintypes
import subprocess
import time
import _winapi


class BasicLimits(ctypes.Structure):
    _fields_ = [("processTime", ctypes.c_longlong), ("jobTime", ctypes.c_longlong),
                ("flags", wintypes.DWORD), ("minWorkingSet", ctypes.c_size_t),
                ("maxWorkingSet", ctypes.c_size_t), ("activeProcesses", wintypes.DWORD),
                ("affinity", ctypes.c_size_t), ("priority", wintypes.DWORD), ("scheduling", wintypes.DWORD)]


class ExtendedLimits(ctypes.Structure):
    _fields_ = [("basic", BasicLimits), ("io", ctypes.c_ulonglong * 6),
                ("processMemory", ctypes.c_size_t), ("jobMemory", ctypes.c_size_t),
                ("peakProcessMemory", ctypes.c_size_t), ("peakJobMemory", ctypes.c_size_t)]


def run_windows_converter(args, timeout, cancel):
    from .processes import check_cancelled
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel.SetInformationJobObject.restype = wintypes.BOOL
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel.TerminateJobObject.restype = wintypes.BOOL
    kernel.ResumeThread.argtypes = [wintypes.HANDLE]
    kernel.ResumeThread.restype = wintypes.DWORD
    job = kernel.CreateJobObjectW(None, None)
    if not job:
        raise ctypes.WinError(ctypes.get_last_error())
    process = thread = None
    assigned = False
    try:
        limits = ExtendedLimits()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            raise ctypes.WinError(ctypes.get_last_error())
        check_cancelled(cancel)
        startup = subprocess.STARTUPINFO()
        startup.dwFlags = subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = subprocess.SW_HIDE
        # Keep the primary thread handle, which subprocess.Popen closes. This
        # lets us assign the job before any converter/venv child code executes.
        process, thread, _pid, _tid = _winapi.CreateProcess(str(args[0]), subprocess.list2cmdline(list(map(str, args))),
                                                         None, None, False, 0x4 | subprocess.CREATE_NO_WINDOW,
                                                         None, None, startup)
        if not kernel.AssignProcessToJobObject(job, process):
            raise ctypes.WinError(ctypes.get_last_error())
        assigned = True
        check_cancelled(cancel)
        if kernel.ResumeThread(thread) == 0xFFFFFFFF:
            raise ctypes.WinError(ctypes.get_last_error())
        deadline = time.monotonic() + timeout
        while _winapi.WaitForSingleObject(process, 100) == _winapi.WAIT_TIMEOUT:
            check_cancelled(cancel)
            if time.monotonic() >= deadline:
                raise subprocess.TimeoutExpired(args, timeout)
        check_cancelled(cancel)
        return subprocess.CompletedProcess(args, _winapi.GetExitCodeProcess(process), b"", b"")
    finally:
        if assigned:
            kernel.TerminateJobObject(job, 1)
        elif process:
            _winapi.TerminateProcess(process, 1)
        if process:
            _winapi.WaitForSingleObject(process, 5000)
            _winapi.CloseHandle(process)
        if thread:
            _winapi.CloseHandle(thread)
        _winapi.CloseHandle(job)
