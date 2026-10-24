import ctypes
from pathlib import Path
import shutil
import sys

import pytest

from pdfstudio.windows_integration import PROG_ID, create_shortcuts, registration_entries, window_icons, write_registration

ROOT = Path(__file__).resolve().parents[1]


def test_registration_is_per_user_and_preserves_default_choice():
    executable = Path("C:/Apps/Folder with spaces/PDFStudio.exe")
    icon = executable.parent / "_internal/web/dist/branding/pdfstudio.ico"
    entries = registration_entries(executable, icon)
    stored = {(r"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.pdf\UserChoice", "ProgId"): "Original.PDF"}
    class Key:
        def __init__(self, path): self.path = path
        def __enter__(self): return self
        def __exit__(self, *_): pass
    class Registry:
        HKEY_CURRENT_USER = "current user"
        KEY_SET_VALUE = 2
        REG_SZ, REG_EXPAND_SZ, REG_NONE = 1, 2, 0
        @staticmethod
        def CreateKeyEx(root, path, reserved, access):
            assert root == "current user" and access == 2
            assert "UserChoice" not in path
            assert path.lower() != r"software\classes\.pdf"
            return Key(path)
        @staticmethod
        def SetValueEx(key, name, _reserved, _kind, value): stored[key.path, name] = value
    write_registration(entries, Registry)
    assert stored[r"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.pdf\UserChoice", "ProgId"] == "Original.PDF"
    assert stored[r"Software\Classes\.pdf\OpenWithProgids", PROG_ID] == b""
    assert stored[r"Software\Classes\PDFStudio.PDF\shell\open\command", ""] == f'"{executable}" "%1"'
    assert stored[r"Software\Classes\PDFStudio.PDF\DefaultIcon", ""] == f'"{icon}",0'
    assert stored[r"Software\Classes\Applications\PDFStudio.exe\DefaultIcon", ""] == f'"{icon}",0'


@pytest.mark.skipif(sys.platform != "win32", reason="Windows shortcut COM format")
def test_real_shortcut_creation_uses_safe_unicode_paths_and_preserves_unrelated_links(tmp_path):
    folder = tmp_path / "Owner's & local \u0e44\u0e17\u0e22"
    folder.mkdir()
    executable = folder / "PDFStudio.exe"
    executable.write_bytes(b"synthetic shortcut target")
    icon = folder / "logo.ico"
    shutil.copy2(ROOT / "web/public/branding/pdfstudio.ico", icon)
    locations = {name: str(tmp_path / name) for name in ("Desktop", "Programs")}
    for location in locations.values(): Path(location).mkdir()
    results = create_shortcuts(executable, icon, folders=locations)
    assert [item["status"] for item in results] == ["ready", "ready"]
    for location in locations.values():
        path = Path(location) / "PDF Studio.lnk"
        raw = path.read_bytes()
        assert raw[:4] == b"\x4c\x00\x00\x00"  # Shell Link header.
        assert str(executable).encode("utf-16le") in raw
        assert str(icon).encode("utf-16le") in raw
    existing = Path(locations["Desktop"]) / "PDF Studio.lnk"
    existing.write_bytes(b"existing unrelated shortcut data")
    results = create_shortcuts(executable, icon, folders=locations)
    assert results[0]["status"] == "preserved existing unrelated shortcut"
    assert existing.read_bytes() == b"existing unrelated shortcut data"



@pytest.mark.skipif(sys.platform != "win32", reason="Windows icon decoder")
def test_windows_loads_both_native_icon_sizes_from_the_prepared_ico():
    user = ctypes.WinDLL("user32")
    # A null owner does not show or change a user window; LoadImage still validates ICO data.
    handles = window_icons(user, None, ROOT / "web/public/branding/pdfstudio.ico")
    assert len(handles) == 2 and all(handles)
    for handle in handles:
        assert user.DestroyIcon(handle)
