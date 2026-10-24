import io
import time

import fitz
from PIL import Image
import pytest

from pdfstudio.app import create_app
from pdfstudio.source_formats import decode_text, read_source, TextConfirmationRequired
from pdfstudio.storage import Workspace


@pytest.fixture
def session(tmp_path):
    app = create_app(tmp_path / "data", testing=True)
    client = app.test_client()
    headers = {"X-Studio-Token": app.config["STUDIO_TOKEN"]}
    yield app, client, headers
    app.extensions["imports"].close()
    app.extensions["sources"].close()
    app.extensions["workspace"].close()


def wait_job(client, headers, url):
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        response = client.get(url, headers=headers)
        assert response.status_code == 200
        if response.json["done"]:
            return response.json
        time.sleep(.02)
    pytest.fail("Source job did not finish")


def upload(client, headers, name, data):
    result = client.post("/api/import-jobs", headers=headers, data={"files": [(io.BytesIO(data), name)]})
    assert result.status_code == 200
    return wait_job(client, headers, "/api/import-jobs/" + result.json["id"])


@pytest.mark.parametrize("name", ["sample.txt", "sample.text", "sample.log", "sample.vtt", "sample.json", "sample.unknown", "README"])
def test_known_and_confident_unfamiliar_text_formats_open_without_confirmation(name):
    source = read_source(b"WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nCaption text\n", name)
    assert source.kind == "text"
    assert "00:00:01.000 --> 00:00:02.000" in source.text
    assert "Caption text" in source.html
    assert source.fallback == (name in {"sample.unknown", "README"})


def test_encoding_detection_preserves_unicode_and_requires_a_choice_for_ambiguous_text():
    text = "English and Thai \u0e44\u0e17\u0e22\nSecond line"
    for raw in [text.encode("utf-8-sig"), text.encode("utf-16"), "Plain text".encode("utf-16-le")]:
        assert decode_text(raw)[0] in {text, "Plain text"}
    with pytest.raises(TextConfirmationRequired):
        read_source(b"caf\xe9\n", "notes.custom")
    assert read_source(b"caf\xe9\n", "notes.custom", force=True, encoding="cp1252").text == "caf\u00e9\n"
    thai = "\u0e20\u0e32\u0e29\u0e32\u0e44\u0e17\u0e22"
    assert read_source(thai.encode("cp874"), "thai.log", force=True, encoding="cp874").text == thai
    with pytest.raises(TextConfirmationRequired):
        decode_text(b"caf\xe9", force=True, encoding="utf-8")
    assert read_source(b"<h1>caf\xe9</h1>", "notes.html", force=True, encoding="cp1252").kind == "text"
    assert read_source(b"**caf\xe9**", "notes.md", force=True, encoding="cp1252").kind == "text"


@pytest.mark.parametrize("name,data", [("binary.bin", bytes(range(32))*4), ("program.exe", b"MZ readable words"), ("archive.custom", b"PK\x03\x04file data")])
def test_binary_files_are_not_automatically_or_forcibly_opened_as_text(name, data):
    for force in [False, True]:
        with pytest.raises(ValueError):
            read_source(data, name, force=force)


def test_html_reading_is_static_local_and_does_not_prepare_a_pdf(session):
    app, client, headers = session
    original = b'<h1>Local report</h1><script>alert("run")</script><iframe src="https://example.com"></iframe><img src="file:///private.png"><style>p{background:url(https://example.com/a.png)}</style><a href="https://example.com">external</a>'
    result = upload(client, headers, "report.html", original)
    assert not result["errors"]
    public = result["documents"][0]
    assert public["sourceKind"] == "html" and not public["pdfReady"] and not public["pages"]
    doc = app.extensions["workspace"].document(public["id"], pdf=False)
    assert doc.source_path.read_bytes() == original
    assert not list(app.extensions["workspace"].root.glob("*.pdf"))
    source = client.get(f'/api/documents/{doc.id}/source', headers=headers).json
    assert "Local report" in source["html"] and "Content-Security-Policy" in source["html"]
    assert "alert(" not in source["html"] and "file:///" not in source["html"] and "https://example.com" not in source["html"]
    assert client.get(f'/api/documents/{doc.id}/file', headers=headers).status_code == 400
    assert client.post("/api/export/original", headers=headers, json={"id": doc.id}).status_code == 400


def test_prepare_and_commit_html_pdf_is_explicit_and_preserves_the_source(session):
    app, client, headers = session
    original = b"<h1>Report title</h1><p>Selectable content</p>"
    doc = upload(client, headers, "report.htm", original)["documents"][0]
    job = client.post(f'/api/documents/{doc["id"]}/prepare', headers=headers, json={"options": {"paper": "Letter", "orientation": "landscape"}}).json["id"]
    state = wait_job(client, headers, "/api/source-jobs/" + job)
    assert not state["error"]
    # A completed background render does not replace a user's current preview until committed.
    assert not app.extensions["workspace"].document(doc["id"], pdf=False).pages
    assert "_result" not in state
    prepared = client.post("/api/source-jobs/" + job + "/commit", headers=headers, json={}).json
    assert prepared["id"] == doc["id"] and prepared["revision"] == 1 and prepared["pdfReady"]
    assert prepared["pages"][0]["width"] > prepared["pages"][0]["height"]
    internal = app.extensions["workspace"].document(doc["id"])
    with fitz.open(internal.path) as pdf:
        assert "Selectable content" in pdf[0].get_text()
    assert internal.source_path.read_bytes() == original
    assert len(app.extensions["workspace"].documents) == 1


def test_markdown_and_text_edits_generate_real_pages_without_modifying_originals(session):
    app, client, headers = session
    original = b"# Heading\n\n**Bold text**\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n```\ncode line\n```"
    document = upload(client, headers, "notes.md", original)["documents"][0]
    internal = app.extensions["workspace"].document(document["id"])
    with fitz.open(internal.path) as pdf:
        text = pdf[0].get_text()
        assert "Heading" in text and "Bold text" in text and "code line" in text
        assert "**" not in text
    job = client.post(f'/api/documents/{internal.id}/prepare', headers=headers, json={"content": "# Updated\n\nNew working copy", "options": {"fontSize": 14}}).json["id"]
    assert not wait_job(client, headers, "/api/source-jobs/" + job)["error"]
    client.post("/api/source-jobs/" + job + "/commit", headers=headers, json={})
    with fitz.open(internal.path) as pdf:
        assert "New working copy" in pdf[0].get_text()
    assert internal.source_path.read_bytes() == original
    assert "New working copy" in internal.source.text


def test_mixed_batch_keeps_valid_files_and_offers_text_fallback_by_index(session):
    app, client, headers = session
    with fitz.open() as pdf:
        pdf.new_page().insert_text((40, 50), "PDF page")
        raw = pdf.tobytes()
    image = io.BytesIO()
    Image.new("RGB", (80, 50), "blue").save(image, format="PNG")
    files = [(io.BytesIO(raw), "first.pdf"), (io.BytesIO(image.getvalue()), "chart.png"), (io.BytesIO(b'<h1>Chart</h1><img src="chart.png">'), "chart.html"), (io.BytesIO(b"plain text"), "notes.blob"), (io.BytesIO(b"caf\xe9"), "legacy.blob"), (io.BytesIO(b"MZ\0\0binary"), "binary.exe")]
    response = client.post("/api/import-jobs", headers=headers, data={"files": files})
    result = wait_job(client, headers, "/api/import-jobs/" + response.json["id"])
    assert len(result["documents"]) == 4 and [error["index"] for error in result["errors"]] == [4, 5]
    assert result["errors"][0]["code"] == "open-as-text" and result["errors"][1]["code"] == ""
    html_doc = next(doc for doc in app.extensions["workspace"].documents.values() if doc.kind == "html")
    assert "data:image/png;base64," in html_doc.source.html
    assert html_doc.source.assets
    # Companion images survive cleanup of the import batch and remain usable for PDF preparation.
    job = client.post(f'/api/documents/{html_doc.id}/prepare', headers=headers, json={}).json["id"]
    assert not wait_job(client, headers, "/api/source-jobs/" + job)["error"]
    client.post("/api/source-jobs/" + job + "/commit", headers=headers, json={})
    with fitz.open(html_doc.path) as pdf:
        assert pdf[0].get_images()


def test_remembered_encoding_still_validates_content_and_separate_pdf_exports_are_unique(session):
    app, client, headers = session
    result = client.post("/api/import-jobs", headers=headers, data={"files": [(io.BytesIO(b"caf\xe9"), "same.blob"), (io.BytesIO(b"another file"), "same.txt")], "textDefaults": '{".blob":"cp1252"}'})
    state = wait_job(client, headers, "/api/import-jobs/" + result.json["id"])
    assert not state["errors"] and len(state["documents"]) == 2
    export = client.post("/api/export/separate", headers=headers, json={"ids": [doc["id"] for doc in state["documents"]]})
    assert export.status_code == 200
    import zipfile
    archive = client.get(export.json["url"], headers=headers).data
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        assert z.namelist() == ["same.pdf", "same_2.pdf"]
        assert all(z.read(name).startswith(b"%PDF-") for name in z.namelist())


def test_failed_preparation_keeps_previous_pdf_and_source(session, monkeypatch):
    app, client, headers = session
    document = upload(client, headers, "notes.txt", b"Keep this content")["documents"][0]
    internal = app.extensions["workspace"].document(document["id"])
    previous = internal.path.read_bytes()
    def fail(*_args, **_options):
        raise ValueError("Synthetic conversion failure")
    monkeypatch.setattr("pdfstudio.source_jobs.render_pdf", fail)
    job = client.post(f'/api/documents/{internal.id}/prepare', headers=headers, json={"content": "Changed draft"}).json["id"]
    assert wait_job(client, headers, "/api/source-jobs/" + job)["error"]
    assert internal.path.read_bytes() == previous and internal.source.text == "Keep this content"
    assert client.post("/api/source-jobs/" + job + "/commit", headers=headers, json={}).status_code == 400


def test_long_lines_wrap_without_losing_text_and_unwrapped_overflow_keeps_previous_pdf(session):
    app, client, headers = session
    original = "Long line: " + "A" * 1000 + "\nThai \u0e44\u0e17\u0e22"
    public = upload(client, headers, "wide.log", original.encode())["documents"][0]
    doc = app.extensions["workspace"].document(public["id"])
    with fitz.open(doc.path) as pdf:
        text = "".join(page.get_text() for page in pdf)
        assert text.count("A") == 1000 and "\u0e44\u0e17\u0e22" in text
    previous = doc.path.read_bytes()
    job = client.post(f'/api/documents/{doc.id}/prepare', headers=headers, json={"options": {"wrap": False}}).json["id"]
    state = wait_job(client, headers, "/api/source-jobs/" + job)
    assert "unwrapped lines" in state["error"]
    assert doc.path.read_bytes() == previous


def test_larger_logs_open_for_reading_without_waiting_for_pagination(session):
    app, client, headers = session
    original = b"Log line\n" * 70000
    public = upload(client, headers, "large.log", original)["documents"][0]
    assert not public["pdfReady"] and public["sourceKind"] == "text"
    source = client.get(f'/api/documents/{public["id"]}/source', headers=headers).json
    assert source["text"].encode() == original and source["html"] == ""


def test_static_svg_survives_html_reading_and_renders_in_the_pdf(session):
    app, client, headers = session
    raw = b'<h1>SVG chart</h1><svg viewBox="0 0 100 50"><rect width="90" height="40" fill="red" onclick="alert(1)"/></svg>'
    public = upload(client, headers, "chart.html", raw)["documents"][0]
    doc = app.extensions["workspace"].document(public["id"], pdf=False)
    assert '<svg viewBox="0 0 100 50">' in doc.source.html and "onclick" not in doc.source.html
    job = client.post(f'/api/documents/{doc.id}/prepare', headers=headers, json={}).json["id"]
    assert not wait_job(client, headers, "/api/source-jobs/" + job)["error"]
    client.post("/api/source-jobs/" + job + "/commit", headers=headers, json={})
    with fitz.open(doc.path) as pdf:
        assert "SVG chart" in pdf[0].get_text() and pdf[0].get_images()


def test_rtf_uses_the_office_converter(session, monkeypatch, tmp_path):
    app, client, headers = session
    called = []
    def office(source, destination, **_options):
        called.append(source.suffix)
        destination.mkdir()
        output = destination / "rtf.pdf"
        with fitz.open() as pdf:
            pdf.new_page().insert_text((40, 60), "RTF converted")
            pdf.save(output)
        return output
    monkeypatch.setattr("pdfstudio.imports.utilities.office_to_pdf", office)
    result = upload(client, headers, "document.rtf", b"{\\rtf1 sample}")
    assert not result["errors"] and called == [".rtf"] and result["documents"][0]["kind"] == "office"
