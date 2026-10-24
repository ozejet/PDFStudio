"""Modern Common Item Dialog ABI and lifecycle, without showing interactive UI."""
import ctypes
import sys

import pytest
from pdfstudio import dialogs

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows COM ABI")


def test_real_com_dialog_can_be_created_configured_and_released(tmp_path):
    # Calls the actual Windows COM vtable, including Unicode filenames and folders.
    with dialogs.WindowsSaveDialog() as dialog:
        assert dialog.pointer
        dialog.configure("\u0e17\u0e14\u0e2a\u0e2d\u0e1a_signature.pdf", str(tmp_path), ".pdf")
    assert not dialog.pointer and not dialog.initialized


def test_result_unicode_cancel_error_and_release(monkeypatch):
    dialog = dialogs.WindowsSaveDialog()
    dialog.pointer = ctypes.c_void_p(100)
    selected = ctypes.create_unicode_buffer("C:\\Documents\\\u0e17\u0e14\u0e2a\u0e2d\u0e1a.pdf")
    calls, freed = [], []
    monkeypatch.setattr(dialog.ole, 'CoTaskMemFree', lambda value: freed.append(value.value))
    def call(pointer, index, types, *args):
        calls.append((pointer.value, index))
        if index == 20: args[0]._obj.value = 200
        if index == 5:
            assert args[0] == 0x80058000
            args[1]._obj.value = ctypes.addressof(selected)
        return 0
    monkeypatch.setattr(dialog, 'call', call)
    assert dialog.show(123) == selected.value
    assert calls == [(100, 3), (100, 20), (200, 5), (200, 2)]
    assert freed == [ctypes.addressof(selected)]
    monkeypatch.setattr(dialog, 'call', lambda *_: ctypes.c_long(0x800704C7).value)
    assert dialog.show(123) is None
    monkeypatch.setattr(dialog, 'call', lambda *_: ctypes.c_long(0x80004005).value)
    with pytest.raises(OSError, match='80004005'): dialog.show(123)


def test_com_initialization_failure_balances_cleanup(monkeypatch):
    dialog = dialogs.WindowsSaveDialog()
    cleaned = []
    monkeypatch.setattr(dialog.ole, 'CoInitializeEx', lambda *_: 0)
    monkeypatch.setattr(dialog.ole, 'CoCreateInstance', lambda *_: -2147467259)
    monkeypatch.setattr(dialog.ole, 'CoUninitialize', lambda: cleaned.append(True))
    with pytest.raises(OSError): dialog.__enter__()
    assert cleaned == [True] and not dialog.initialized


def test_save_window_is_owned_topmost_and_cleanup_runs_on_cancel(monkeypatch, tmp_path):
    from pathlib import Path
    import shutil
    icon = tmp_path / "web/dist/branding/pdfstudio.ico"
    icon.parent.mkdir(parents=True)
    shutil.copy2(Path(__file__).resolve().parents[1] / "web/public/branding/pdfstudio.ico", icon)
    monkeypatch.setattr(dialogs, "app_root", lambda: tmp_path)
    raised, destroyed, unhooked, shown, icons, messages = [], [], [], [], [], []
    callback = None
    def create_owner(styles, *_):
        assert styles & 0x8
        return 123
    def install_hook(first, last, _module, hook, pid, thread, flags):
        import os
        nonlocal callback
        assert first == last == 0x10 and pid == os.getpid() and thread == flags == 0
        callback = hook
        return 789
    class User:
        CreateWindowExW = staticmethod(create_owner)
        LoadImageW = staticmethod(lambda _instance, _path, _type, size, _height, _flags: 1000 + size)
        SendMessageW = staticmethod(lambda hwnd, message, kind, icon: messages.append((hwnd, message, kind, icon)) or 0)
        DestroyIcon = staticmethod(lambda icon: icons.append(icon) or 1)
        DestroyWindow = staticmethod(lambda hwnd: destroyed.append(hwnd) or 1)
        GetForegroundWindow = staticmethod(lambda: 0)
        GetWindowRect = staticmethod(lambda *_: 0)
        SetWindowPos = staticmethod(lambda hwnd, after, *_: raised.append((hwnd, after)) or 1)
        SetForegroundWindow = staticmethod(lambda hwnd: 1)
        SetWinEventHook = staticmethod(install_hook)
        UnhookWinEvent = staticmethod(lambda hook: unhooked.append(hook) or 1)
    class Dialog:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def configure(self, *_): pass
        def show(self, owner):
            shown.append(owner)
            callback(789, 0x10, 456, 0, 0, 0, 0)
            return None
    monkeypatch.setattr(ctypes, "WinDLL", lambda *_args, **_kwargs: User())
    monkeypatch.setattr(dialogs, "WindowsSaveDialog", Dialog)
    assert dialogs.windows_save("result.pdf", "", ".pdf") is None
    assert shown == [123] and raised == [(456, -1)]
    assert unhooked == [789] and destroyed == [123]
    assert icons == [1016, 1032]
    assert messages == [(123, 0x80, 0, 1016), (123, 0x80, 1, 1032)]
