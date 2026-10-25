from pathlib import Path
from types import SimpleNamespace

import pytest

import pdfstudio.app as app_module
from pdfstudio import dialogs, storage


def test_macos_uses_application_support(monkeypatch, tmp_path):
    monkeypatch.setattr("sys.platform", "darwin")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    assert storage.user_data() == tmp_path / "Library/Application Support/PDFStudio"


def test_macos_save_uses_system_dialog_without_shell(monkeypatch):
    calls = []

    def run(command, **options):
        calls.append((command, options))
        return SimpleNamespace(returncode=0, stdout="/tmp/Folder with spaces/result.pdf\n")

    monkeypatch.setattr(dialogs.subprocess, "run", run)
    assert dialogs.macos_save("result.pdf", "/tmp/Folder with spaces") == "/tmp/Folder with spaces/result.pdf"
    command, options = calls[0]
    assert command[0] == "/usr/bin/osascript"
    assert 'tell application "Safari" to activate' in command[2]
    assert command[-2:] == ["result.pdf", "/tmp/Folder with spaces"]
    assert "shell" not in options


def test_macos_save_cancel_and_failure(monkeypatch):
    monkeypatch.setattr(dialogs.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="\n"))
    assert dialogs.macos_save("result.pdf", "") is None
    monkeypatch.setattr(dialogs.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout=""))
    with pytest.raises(ValueError, match="macOS Save As"):
        dialogs.macos_save("result.pdf", "")


def test_frozen_macos_save_uses_bundled_appkit_helper(monkeypatch):
    calls = []

    def run(command, **options):
        calls.append((command, options))
        return SimpleNamespace(returncode=0, stdout="/tmp/Folder with spaces/result.pdf\n")

    monkeypatch.setattr(dialogs.sys, "platform", "darwin")
    monkeypatch.setattr(dialogs.sys, "frozen", True, raising=False)
    monkeypatch.setattr(dialogs.sys, "executable", "/Applications/PDFStudio.app/Contents/Resources/runtime/PDFStudioBackend/PDFStudioBackend")
    monkeypatch.setattr(dialogs.subprocess, "run", run)
    assert dialogs.choose_save("result.pdf", "/tmp/Folder with spaces") == "/tmp/Folder with spaces/result.pdf"
    assert calls == [(["/Applications/PDFStudio.app/Contents/Resources/runtime/PDFStudioBackend/PDFStudioSavePanel.app/Contents/MacOS/PDFStudioSavePanel", "result.pdf", "/tmp/Folder with spaces"], {"capture_output": True, "text": True})]


def test_macos_external_url_uses_safari(monkeypatch):
    calls = []
    monkeypatch.setattr(app_module.sys, "platform", "darwin")
    monkeypatch.setattr(app_module.subprocess, "run", lambda args, **kwargs: calls.append((args, kwargs)) or SimpleNamespace(returncode=0))
    assert app_module.open_external_url("https://forms.office.com/r/synthetic")
    assert calls == [(["/usr/bin/open", "-a", "Safari", "https://forms.office.com/r/synthetic"], {"capture_output": True})]
