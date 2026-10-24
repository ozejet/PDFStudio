import ctypes
import io
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import fitz
import pytest

from pdfstudio.app import create_app
from pdfstudio.processes import ConversionCancelled, run_converter


def test_cancellation_stops_only_its_converter_and_child_process(tmp_path):
    child_file = tmp_path / "child.pid"
    script = "import subprocess,sys,time;from pathlib import Path;p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)']);Path(sys.argv[1]).write_text(str(p.pid));time.sleep(30)"
    cancel = threading.Event()
    unrelated = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(30)"], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        with ThreadPoolExecutor() as pool:
            result = pool.submit(run_converter, [sys.executable, "-c", script, str(child_file)], timeout=20, cancel=cancel)
            deadline = time.monotonic() + 8
            while not child_file.exists() and time.monotonic() < deadline:
                time.sleep(.02)
            assert child_file.exists()
            child = int(child_file.read_text())
            cancel.set()
            with pytest.raises(ConversionCancelled):
                result.result(timeout=10)
            assert unrelated.poll() is None
            if os.name == "nt":
                from ctypes import wintypes
                kernel = ctypes.WinDLL("kernel32", use_last_error=True)
                kernel.OpenProcess.restype = wintypes.HANDLE
                kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
                kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
                kernel.CloseHandle.argtypes = [wintypes.HANDLE]
                handle = kernel.OpenProcess(0x1000, False, child)
                if handle:
                    code = wintypes.DWORD()
                    assert kernel.GetExitCodeProcess(handle, ctypes.byref(code))
                    kernel.CloseHandle(handle)
                    assert code.value != 259
    finally:
        cancel.set()
        unrelated.terminate()
        unrelated.wait(timeout=5)


def test_cancel_batch_keeps_ready_files_releases_slots_and_allows_next_import(tmp_path, monkeypatch):
    app = create_app(tmp_path / "data", testing=True)
    client = app.test_client()
    headers = {"X-Studio-Token": app.config["STUDIO_TOKEN"]}
    entered = threading.Event()
    def convert(_source, _destination, *, cancel):
        entered.set()
        assert cancel.wait(5)
        raise ConversionCancelled()
    monkeypatch.setattr("pdfstudio.imports.utilities.office_to_pdf", convert)
    with fitz.open() as pdf:
        pdf.new_page()
        raw = pdf.tobytes()
    try:
        response = client.post("/api/import-jobs", headers=headers, data={"files": [(io.BytesIO(raw), "ready.pdf"), (io.BytesIO(b"office"), "slow.docx"), (io.BytesIO(raw), "queued.pdf")]})
        key = response.json["id"]
        assert entered.wait(3)
        assert client.post("/api/import-jobs/" + key + "/cancel", headers=headers, json={}).status_code == 200
        app.extensions["imports"].worker.join(5)
        state = client.get("/api/import-jobs/" + key, headers=headers).json
        assert state["done"] and state["cancelled"] and not state["errors"]
        assert state["completed"] == 1 and [row["phase"] for row in state["files"]] == ["ready", "cancelled", "cancelled"]
        assert len(state["documents"]) == 1 and "_cancel" not in state
        assert app.extensions["workspace"].reserved_imports == 0
        assert not list(app.extensions["workspace"].root.glob("import-*"))
        response = client.post("/api/import-jobs", headers=headers, data={"files": [(io.BytesIO(raw), "again.pdf")]})
        assert response.status_code == 200
        app.extensions["imports"].worker.join(5)
        assert len(app.extensions["workspace"].documents) == 2
    finally:
        app.extensions["imports"].close()
        app.extensions["workspace"].close()


def test_cancel_preparation_preserves_previous_preview_and_source(tmp_path, monkeypatch):
    app = create_app(tmp_path / "data", testing=True)
    workspace = app.extensions["workspace"]
    doc = workspace.import_bytes(b"Previous preview", "notes.txt")
    previous = doc.path.read_bytes()
    entered = threading.Event()
    def render(_content, _options, *, cancel):
        entered.set()
        assert cancel.wait(5)
        raise ConversionCancelled()
    monkeypatch.setattr("pdfstudio.source_jobs.render_pdf", render)
    try:
        jobs = app.extensions["sources"]
        key = jobs.start(doc.id, "Uncommitted draft")
        assert entered.wait(3)
        jobs.cancel(key)
        jobs.worker.join(5)
        assert jobs.status(key)["cancelled"] and jobs.status(key)["done"]
        assert doc.path.read_bytes() == previous and doc.source.text == "Previous preview"
        with pytest.raises(ValueError):
            jobs.commit(key)
    finally:
        app.extensions["sources"].close()
        workspace.close()
