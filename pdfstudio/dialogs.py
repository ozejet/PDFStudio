"""Native dialogs run in their own main-thread process, including frozen builds."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from .storage import app_root


def choose_save(name: str, folder=""):
    command = [sys.executable, "--dialog"] if getattr(sys, "frozen", False) else [sys.executable, str(app_root() / "run.py"), "--dialog"]
    # File-based IPC also works in a windowed EXE, where stdin/stdout are None.
    with tempfile.TemporaryDirectory(prefix="pdfstudio-dialog-") as temporary:
        request_file, result_file = Path(temporary) / "request.json", Path(temporary) / "result.json"
        request_file.write_text(json.dumps({"name": name, "folder": folder}), encoding="utf-8")
        result = subprocess.run(command + [str(request_file), str(result_file)], capture_output=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if result.returncode or not result_file.is_file():
            raise ValueError("The native Save As dialog could not open. Use Download instead.")
        return json.loads(result_file.read_text(encoding="utf-8")).get("path")


def dialog_main():
    payload = json.loads(Path(sys.argv[-2]).read_text(encoding="utf-8"))
    extension = Path(payload["name"]).suffix or ".pdf"
    if sys.platform == "win32":
        value = windows_save(payload["name"], payload.get("folder", ""), extension)
    else:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        value = filedialog.asksaveasfilename(title="PDF Studio - Save a copy", initialfile=payload["name"], initialdir=payload.get("folder") or None, defaultextension=extension, filetypes=[(extension.upper().lstrip(".") + " files", "*" + extension), ("All files", "*.*")], parent=root)
        root.destroy()
    Path(sys.argv[-1]).write_text(json.dumps({"path": value or None}, ensure_ascii=False), encoding="utf-8")


class WindowsSaveDialog:
    """IFileSaveDialog (modern Common Item Dialog), owned by the helper's STA.

    ABI: Microsoft win32metadata ShObjIdl_core.h, IFileSaveDialogVtbl.
    No legacy GetSaveFileName fallback, and no additional GUI runtime.
    """
    def __init__(self):
        import ctypes as c
        from ctypes import wintypes as w
        self.c, self.w = c, w
        self.ole = c.WinDLL("ole32")
        self.shell = c.WinDLL("shell32")
        self.ole.CoInitializeEx.argtypes = [c.c_void_p, w.DWORD]
        self.ole.CoInitializeEx.restype = c.c_long
        self.ole.CoCreateInstance.argtypes = [c.c_void_p, c.c_void_p, w.DWORD, c.c_void_p, c.POINTER(c.c_void_p)]
        self.ole.CoCreateInstance.restype = c.c_long
        self.ole.CoTaskMemFree.argtypes = [c.c_void_p]
        self.ole.CoTaskMemFree.restype = None
        self.ole.CoUninitialize.argtypes = []
        self.ole.CoUninitialize.restype = None
        self.shell.SHCreateItemFromParsingName.argtypes = [w.LPCWSTR, c.c_void_p, c.c_void_p, c.POINTER(c.c_void_p)]
        self.shell.SHCreateItemFromParsingName.restype = c.c_long
        self.pointer = c.c_void_p()
        self.initialized = False

    @staticmethod
    def check(result):
        if result < 0:
            raise OSError(f"Windows Save As error: 0x{result & 0xffffffff:08X}")

    def guid(self, value):
        import uuid
        return self.c.create_string_buffer(uuid.UUID(value).bytes_le, 16)

    def call(self, pointer, index, types, *args):
        c = self.c
        table = c.cast(pointer, c.POINTER(c.POINTER(c.c_void_p))).contents
        return c.WINFUNCTYPE(c.c_long, c.c_void_p, *types)(table[index])(pointer, *args)

    def __enter__(self):
        c = self.c
        self.check(self.ole.CoInitializeEx(None, 2))  # COINIT_APARTMENTTHREADED
        self.initialized = True
        try:
            clsid = self.guid("C0B4E2F3-BA21-4773-8DBA-335EC946EB8B")
            iid = self.guid("84BCCD23-5FDE-4CDB-AEA4-AF64B83D78AB")
            self.check(self.ole.CoCreateInstance(clsid, None, 1, iid, c.byref(self.pointer)))
            return self
        except Exception:
            self.__exit__(None, None, None)
            raise

    def configure(self, name, folder, extension):
        c, w = self.c, self.w
        class Filter(c.Structure):
            _fields_ = [("label", w.LPCWSTR), ("pattern", w.LPCWSTR)]
        filters = (Filter * 2)(Filter(extension.lstrip(".").upper() + " files", "*" + extension), Filter("All files", "*.*"))
        self.check(self.call(self.pointer, 4, [w.UINT, c.POINTER(Filter)], 2, filters))
        # FORCEFILESYSTEM | PATHMUSTEXIST | NOCHANGEDIR | DONTADDTORECENT.
        # The writer uses exclusive creation and a suffix, never overwrites.
        self.check(self.call(self.pointer, 9, [w.DWORD], 0x40 | 0x800 | 0x8 | 0x2000000))
        self.check(self.call(self.pointer, 15, [w.LPCWSTR], name))
        self.check(self.call(self.pointer, 17, [w.LPCWSTR], "PDF Studio - Save As"))
        self.check(self.call(self.pointer, 22, [w.LPCWSTR], extension.lstrip(".")))
        if folder:
            item = c.c_void_p()
            iid = self.guid("43826D1E-E718-42EE-BC55-A1E261C37BFE")
            result = self.shell.SHCreateItemFromParsingName(str(folder), None, iid, c.byref(item))
            if result >= 0:
                try:
                    self.check(self.call(self.pointer, 12, [c.c_void_p], item))
                finally:
                    self.call(item, 2, [])

    def show(self, owner):
        c, w = self.c, self.w
        result = self.call(self.pointer, 3, [w.HWND], owner)
        if result & 0xffffffff == 0x800704C7:  # User canceled.
            return None
        self.check(result)
        item, path = c.c_void_p(), c.c_void_p()
        self.check(self.call(self.pointer, 20, [c.POINTER(c.c_void_p)], c.byref(item)))
        try:
            self.check(self.call(item, 5, [w.DWORD, c.POINTER(c.c_void_p)], 0x80058000, c.byref(path)))  # SIGDN_FILESYSPATH
            return c.wstring_at(path)
        finally:
            if path:
                self.ole.CoTaskMemFree(path)
            self.call(item, 2, [])

    def __exit__(self, *_args):
        if self.pointer:
            self.call(self.pointer, 2, [])
            self.pointer = self.c.c_void_p()
        if self.initialized:
            self.ole.CoUninitialize()
            self.initialized = False


def windows_save(name: str, folder: str, extension: str):
    import ctypes as c
    import os
    from ctypes import wintypes as w

    user = c.WinDLL("user32", use_last_error=True)
    user.CreateWindowExW.argtypes = [w.DWORD, w.LPCWSTR, w.LPCWSTR, w.DWORD, c.c_int, c.c_int, c.c_int, c.c_int, w.HWND, w.HMENU, w.HINSTANCE, w.LPVOID]
    user.CreateWindowExW.restype = w.HWND
    user.DestroyWindow.argtypes = [w.HWND]
    user.DestroyWindow.restype = w.BOOL
    user.SetWindowPos.argtypes = [w.HWND, w.HWND, c.c_int, c.c_int, c.c_int, c.c_int, w.UINT]
    user.SetWindowPos.restype = w.BOOL
    user.SetForegroundWindow.argtypes = [w.HWND]
    user.SetForegroundWindow.restype = w.BOOL
    user.GetForegroundWindow.restype = w.HWND
    user.GetWindowRect.argtypes = [w.HWND, c.POINTER(w.RECT)]
    user.GetWindowRect.restype = w.BOOL
    bounds = w.RECT()
    foreground = user.GetForegroundWindow()
    x = y = 0
    if foreground and user.GetWindowRect(foreground, c.byref(bounds)):
        x, y = (bounds.left + bounds.right) // 2, (bounds.top + bounds.bottom) // 2
    owner = user.CreateWindowExW(0x8 | 0x80, "STATIC", "PDF Studio", 0x80000000, x, y, 1, 1, None, None, None, None)
    if not owner:
        raise OSError("Windows could not create the Save As window.")
    hook_type = c.WINFUNCTYPE(None, w.HANDLE, w.DWORD, w.HWND, c.c_long, c.c_long, w.DWORD, w.DWORD)
    @hook_type
    def foreground_dialog(_hook, _event, window, object_id, _child, _thread, _time):
        if window and object_id == 0:
            user.SetWindowPos(window, -1, 0, 0, 0, 0, 0x1 | 0x2 | 0x40)
            user.SetForegroundWindow(window)
    user.SetWinEventHook.argtypes = [w.DWORD, w.DWORD, w.HMODULE, hook_type, w.DWORD, w.DWORD, w.DWORD]
    user.SetWinEventHook.restype = w.HANDLE
    user.UnhookWinEvent.argtypes = [w.HANDLE]
    user.UnhookWinEvent.restype = w.BOOL
    # Only dialogs from this short-lived helper process can trigger the hook.
    hook = user.SetWinEventHook(0x10, 0x10, None, foreground_dialog, os.getpid(), 0, 0)
    icons = []
    try:
        from .windows_integration import window_icons
        icons = window_icons(user, owner, app_root() / "web/dist/branding/pdfstudio.ico")
        with WindowsSaveDialog() as dialog:
            dialog.configure(name, folder, extension)
            return dialog.show(owner)
    finally:
        if hook:
            user.UnhookWinEvent(hook)
        user.DestroyWindow(owner)
        for icon in icons:
            user.DestroyIcon(icon)
