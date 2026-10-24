import io
import threading
import time

import fitz
import pytest

from pdfstudio.app import create_app


def pdf_bytes(pages=1):
    with fitz.open() as pdf:
        for index in range(pages):
            page = pdf.new_page()
            page.insert_text((50, 60), f"Synthetic import page {index + 1}")
        return pdf.tobytes()


@pytest.fixture
def session(tmp_path):
    app = create_app(tmp_path / "data", testing=True)
    client = app.test_client()
    headers = {"X-Studio-Token": app.config["STUDIO_TOKEN"]}
    yield app, client, headers
    app.extensions["imports"].close()
    app.extensions["workspace"].close()


def status_until_done(client, headers, key):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        result = client.get("/api/import-jobs/" + key, headers=headers)
        assert result.status_code == 200
        if result.json["done"]:
            return result.json
        time.sleep(.005)
    pytest.fail("Import did not complete")


def test_100_documents_admitted_and_oversized_batch_rejected_whole(session):
    app, client, headers = session
    raw = pdf_bytes(10)
    result = client.post("/api/import-jobs", headers=headers, data={"files": [(io.BytesIO(raw), f"sample-{i}.pdf") for i in range(100)]})
    assert result.status_code == 200
    state = status_until_done(client, headers, result.json["id"])
    assert state["completed"] == 100 and len(state["documents"]) == 100 and not state["errors"]
    workspace = app.extensions["workspace"]
    assert workspace.reserved_imports == 0
    for endpoint in ("/api/documents", "/api/import-jobs"):
        rejected = client.post(endpoint, headers=headers, data={"files": [(io.BytesIO(raw), "101.pdf")]})
        assert rejected.status_code == 400 and "100" in rejected.json["error"]
        assert len(workspace.documents) == 100
    # A batch of two must also be rejected when there is only one free slot.
    key = state["documents"][0]["id"]
    client.delete("/api/documents/" + key, headers=headers)
    rejected = client.post("/api/documents", headers=headers, data={"files": [(io.BytesIO(raw), "a.pdf"), (io.BytesIO(raw), "b.pdf")]})
    assert rejected.status_code == 400 and len(workspace.documents) == 99
    admitted = client.post("/api/documents", headers=headers, data={"files": [(io.BytesIO(raw), "100-again.pdf")]})
    assert admitted.status_code == 200 and len(workspace.documents) == 100


def test_conversion_progress_is_pollable_and_slots_reserved(session, monkeypatch):
    app, client, headers = session
    workspace = app.extensions["workspace"]
    entered, release = threading.Event(), threading.Event()
    def convert(_source, destination, **_options):
        entered.set()
        assert release.wait(5)
        destination.mkdir()
        result = destination / "converted.pdf"
        result.write_bytes(pdf_bytes())
        return result
    monkeypatch.setattr("pdfstudio.imports.utilities.office_to_pdf", convert)
    try:
        result = client.post("/api/import-jobs", headers=headers, data={"files": [(io.BytesIO(b"office"), "slides.pptx"), (io.BytesIO(b"bad"), "broken.pdf")]})
        assert entered.wait(2)
        state = client.get("/api/import-jobs/" + result.json["id"], headers=headers).json
        assert state["phase"] == "converting" and state["current"] == "slides.pptx" and state["completed"] == 0
        assert workspace.reserved_imports == 2
        # MuPDF/config requests remain usable while LibreOffice is working.
        assert client.get("/api/config", headers=headers).status_code == 200
        other = client.post("/api/import-jobs", headers=headers, data={"files": [(io.BytesIO(pdf_bytes()), "other.pdf")]})
        assert other.status_code == 400 and "already running" in other.json["error"]
    finally:
        release.set()
    state = status_until_done(client, headers, result.json["id"])
    assert len(state["documents"]) == 1 and state["documents"][0]["kind"] == "office"
    assert state["errors"][0]["index"] == 1 and workspace.reserved_imports == 0


def test_password_failures_keep_original_batch_indices(session):
    app, client, headers = session
    with fitz.open(stream=pdf_bytes(), filetype="pdf") as pdf:
        encrypted = pdf.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="test", owner_pw="owner")
    result = client.post("/api/import-jobs", headers=headers, data={"files": [(io.BytesIO(encrypted), "same.pdf"), (io.BytesIO(pdf_bytes()), "ok.pdf"), (io.BytesIO(encrypted), "same.pdf")]})
    state = status_until_done(client, headers, result.json["id"])
    assert [error["index"] for error in state["errors"]] == [0, 2]
    assert len(state["documents"]) == 1 and app.extensions["workspace"].reserved_imports == 0


def test_finished_documents_are_available_before_batch_ends_without_repeating_pages(session, monkeypatch):
    app, client, headers = session
    entered, release = threading.Event(), threading.Event()

    def convert(_source, destination, **_options):
        entered.set()
        assert release.wait(5)
        destination.mkdir()
        result = destination / "converted.pdf"
        result.write_bytes(pdf_bytes())
        return result

    monkeypatch.setattr("pdfstudio.imports.utilities.office_to_pdf", convert)
    result = client.post("/api/import-jobs", headers=headers, data={"files": [
        (io.BytesIO(pdf_bytes(3)), "ready.pdf"), (io.BytesIO(b"office"), "slow.docx"),
        (io.BytesIO(b"broken"), "broken.pdf")]})
    url = "/api/import-jobs/" + result.json["id"]
    try:
        assert entered.wait(2)
        state = client.get(url, headers=headers).json
        assert not state["done"] and state["ready"] == 1
        assert state["files"][0]["phase"] == "ready"
        assert state["files"][1]["phase"] == "converting"
        assert state["files"][2]["phase"] == "queued"
        ready = state["documents"][0]
        assert len(ready["pages"]) == 3
        assert client.get(f'/api/documents/{ready["id"]}/file', headers=headers).status_code == 200
        # The next poll omits the document metadata already consumed by the UI.
        assert client.get(url + "?after=1", headers=headers).json["documents"] == []
    finally:
        release.set()
    final = status_until_done(client, headers, result.json["id"])
    assert [row["phase"] for row in final["files"]] == ["ready", "ready", "error"]
    delta = client.get(url + "?after=1", headers=headers).json
    assert delta["ready"] == 2 and len(delta["documents"]) == 1
    assert delta["documents"][0]["kind"] == "office"
    assert delta["errors"][0]["index"] == 2
    assert app.extensions["workspace"].reserved_imports == 0
