"""PDF Studio's per-user Windows identity, icons, Open With registration and links."""
from __future__ import annotations

import ctypes
import json
from pathlib import Path
import sys

APP_ID = "PDFStudio.Desktop"
PROG_ID = "PDFStudio.PDF"


def set_app_identity():
    if sys.platform == "win32":
        from ctypes import wintypes
        shell = ctypes.WinDLL("shell32")
        shell.SetCurrentProcessExplicitAppUserModelID.argtypes = [wintypes.LPCWSTR]
        shell.SetCurrentProcessExplicitAppUserModelID.restype = ctypes.c_long
        shell.SetCurrentProcessExplicitAppUserModelID(APP_ID)


def registration_entries(executable: Path, icon: Path):
    """Only app-owned keys and the named OpenWithProgids value; no default takeover."""
    resource = f'"{icon}",0'
    command = f'"{executable}" "%1"'
    application = r"Software\Classes\Applications\PDFStudio.exe"
    prog = "Software\\Classes\\" + PROG_ID
    capabilities = r"Software\PDFStudio\Capabilities"
    return [
        (prog, "", "PDF Studio PDF document", "string"),
        (prog, "FriendlyTypeName", "PDF Studio PDF document", "string"),
        (prog + r"\DefaultIcon", "", resource, "string"),
        (prog + r"\shell\open\command", "", command, "string"),
        (application, "FriendlyAppName", "PDF Studio", "string"),
        (application + r"\DefaultIcon", "", resource, "expand"),
        (application + r"\SupportedTypes", ".pdf", "", "string"),
        (application + r"\shell\open\command", "", command, "string"),
        (r"Software\Classes\.pdf\OpenWithProgids", PROG_ID, b"", "none"),
        (capabilities, "ApplicationName", "PDF Studio", "string"),
        (capabilities, "ApplicationDescription", "Read, organize and edit PDFs on this device.", "string"),
        (capabilities, "ApplicationIcon", resource, "string"),
        (capabilities + r"\FileAssociations", ".pdf", PROG_ID, "string"),
        (r"Software\RegisteredApplications", "PDF Studio", capabilities, "string"),
        (r"Software\Microsoft\Windows\CurrentVersion\App Paths\PDFStudio.exe", "", str(executable), "string"),
        (r"Software\Microsoft\Windows\CurrentVersion\App Paths\PDFStudio.exe", "Path", str(executable.parent), "string"),
    ]


def write_registration(entries, registry):
    kinds = {"string": registry.REG_SZ, "expand": registry.REG_EXPAND_SZ, "none": registry.REG_NONE}
    for path, name, value, kind in entries:
        with registry.CreateKeyEx(registry.HKEY_CURRENT_USER, path, 0, registry.KEY_SET_VALUE) as key:
            registry.SetValueEx(key, name, 0, kinds[kind], value)


def create_shortcuts(executable: Path, icon: Path, *, folders=None):
    """Use Unicode IShellLinkW directly; no script host or extra COM dependency."""
    import uuid
    from ctypes import wintypes as w
    c = ctypes
    ole, shell = c.WinDLL("ole32"), c.WinDLL("shell32")
    ole.CoInitializeEx.argtypes = [c.c_void_p, w.DWORD]
    ole.CoInitializeEx.restype = c.c_long
    ole.CoCreateInstance.argtypes = [c.c_void_p, c.c_void_p, w.DWORD, c.c_void_p, c.POINTER(c.c_void_p)]
    ole.CoCreateInstance.restype = c.c_long
    ole.CoTaskMemFree.argtypes = [c.c_void_p]
    ole.CoUninitialize.argtypes = []
    shell.SHGetKnownFolderPath.argtypes = [c.c_void_p, w.DWORD, w.HANDLE, c.POINTER(c.c_void_p)]
    shell.SHGetKnownFolderPath.restype = c.c_long
    def guid(value): return c.create_string_buffer(uuid.UUID(value).bytes_le, 16)
    def check(result):
        if result < 0: raise OSError(f"Windows shortcut error: 0x{result & 0xffffffff:08X}")
    def call(pointer, index, types, *args):
        table = c.cast(pointer, c.POINTER(c.POINTER(c.c_void_p))).contents
        return c.WINFUNCTYPE(c.c_long, c.c_void_p, *types)(table[index])(pointer, *args)
    check(ole.CoInitializeEx(None, 2))
    results = []
    try:
        for name, folder_id in (("Desktop", "B4BFCC3A-DB2C-424C-B029-7FE99A87C641"), ("Programs", "A77F5D77-2E2B-44C3-A6A2-ABA601054A51")):
            if folders:
                folder = Path(folders[name])
            else:
                location = c.c_void_p()
                check(shell.SHGetKnownFolderPath(guid(folder_id), 0, None, c.byref(location)))
                try: folder = Path(c.wstring_at(location))
                finally: ole.CoTaskMemFree(location)
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / "PDF Studio.lnk"
            link, persist = c.c_void_p(), c.c_void_p()
            check(ole.CoCreateInstance(guid("00021401-0000-0000-C000-000000000046"), None, 1, guid("000214F9-0000-0000-C000-000000000046"), c.byref(link)))
            try:
                check(call(link, 0, [c.c_void_p, c.POINTER(c.c_void_p)], guid("0000010B-0000-0000-C000-000000000046"), c.byref(persist)))
                if path.exists():
                    loaded = call(persist, 5, [w.LPCWSTR, w.DWORD], str(path), 0)
                    target, description = c.create_unicode_buffer(32768), c.create_unicode_buffer(1024)
                    if loaded >= 0:
                        check(call(link, 3, [w.LPWSTR, c.c_int, c.c_void_p, w.DWORD], target, len(target), None, 4))
                        check(call(link, 6, [w.LPWSTR, c.c_int], description, len(description)))
                    if loaded < 0 or (target.value.casefold() != str(executable).casefold() and description.value != "PDF Studio - local document workspace"):
                        results.append(dict(path=str(path), status="preserved existing unrelated shortcut"))
                        continue
                check(call(link, 20, [w.LPCWSTR], str(executable)))
                check(call(link, 9, [w.LPCWSTR], str(executable.parent)))
                check(call(link, 7, [w.LPCWSTR], "PDF Studio - local document workspace"))
                check(call(link, 17, [w.LPCWSTR, c.c_int], str(icon), 0))
                check(call(persist, 6, [w.LPCWSTR, w.BOOL], str(path), True))
                results.append(dict(path=str(path), status="ready"))
            finally:
                if persist: call(persist, 2, [])
                call(link, 2, [])
    finally:
        ole.CoUninitialize()
    return results


def register_windows(executable: Path, *, shortcuts=True):
    import winreg
    executable = executable.resolve(strict=True)
    icon = executable.parent / "_internal/web/dist/branding/pdfstudio.ico"
    if executable.name.lower() != "pdfstudio.exe" or not icon.is_file():
        raise ValueError("Run Windows integration from the complete PDF Studio application folder.")
    entries = registration_entries(executable, icon)
    write_registration(entries, winreg)
    links = create_shortcuts(executable, icon) if shortcuts else []
    shell = ctypes.WinDLL("shell32")
    shell.SHChangeNotify.argtypes = [ctypes.c_long, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
    shell.SHChangeNotify.restype = None
    shell.SHChangeNotify(0x08000000, 0, None, None)  # SHCNE_ASSOCCHANGED | SHCNF_IDLIST
    return dict(registered=True, default_changed=False, icon=str(icon), shortcuts=links)


def window_icons(user, owner, icon: Path):
    """Set both native window sizes from prepared ICO frames; caller owns handles."""
    from ctypes import wintypes as w
    if not icon.is_file():
        return []
    user.LoadImageW.argtypes = [w.HINSTANCE, w.LPCWSTR, w.UINT, ctypes.c_int, ctypes.c_int, w.UINT]
    user.LoadImageW.restype = w.HANDLE
    user.SendMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
    user.SendMessageW.restype = ctypes.c_ssize_t
    user.DestroyIcon.argtypes = [w.HANDLE]
    user.DestroyIcon.restype = w.BOOL
    handles = []
    for kind, size in ((0, 16), (1, 32)):
        handle = user.LoadImageW(None, str(icon), 1, size, size, 0x10)  # IMAGE_ICON | LR_LOADFROMFILE
        if handle:
            handles.append(handle)
            user.SendMessageW(owner, 0x80, kind, handle)  # WM_SETICON
    return handles
