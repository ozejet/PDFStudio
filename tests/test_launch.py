import hashlib
from pathlib import Path

import fitz

from pdfstudio.app import create_app
from pdfstudio.launch import open_launch_files


def test_open_with_imports_unicode_spaced_paths_and_file_urls(tmp_path):
    first = tmp_path / "ทดสอบ browser download.pdf"
    second = tmp_path / "another download.pdf"
    with fitz.open() as pdf:
        pdf.new_page().insert_text((40, 40), "OPEN WITH PDF STUDIO")
        first.write_bytes(pdf.tobytes())
        second.write_bytes(pdf.tobytes())
    original = hashlib.sha256(first.read_bytes()).hexdigest()
    app = create_app(tmp_path / "settings", testing=True)
    try:
        documents, errors = open_launch_files(app, [str(first), second.as_uri()])
        assert not errors and len(documents) == 2
        assert [d["name"] for d in documents] == [first.name, second.name]
        assert hashlib.sha256(first.read_bytes()).hexdigest() == original
        client = app.test_client()
        config = client.get("/api/config", headers={"X-Studio-Token": app.config["STUDIO_TOKEN"]}).json
        assert config["launchedWithFiles"] and len(config["documents"]) == 2
        assert not config["launchErrors"]
    finally:
        app.extensions["workspace"].close()


def test_bad_shell_files_are_reported_without_losing_other_files(tmp_path):
    broken = tmp_path / "damaged.pdf"
    broken.write_bytes(b"not a pdf")
    app = create_app(tmp_path / "settings", testing=True)
    try:
        docs, errors = open_launch_files(app, [str(broken), str(tmp_path / "missing.pdf"), "https://example.invalid/private.pdf"])
        assert docs == [] and len(errors) == 3
        assert "damaged" in errors[0]["error"]
        assert "could not be found" in errors[1]["error"]
        assert "Download" in errors[2]["error"]
        assert app.extensions["launch_errors"] == errors
    finally:
        app.extensions["workspace"].close()


def test_oversized_shell_batch_is_rejected_before_reading_any_file(tmp_path):
    app = create_app(tmp_path / "settings", testing=True)
    try:
        docs, errors = open_launch_files(app, [str(tmp_path / f"file-{index}.pdf") for index in range(101)])
        assert not docs and len(errors) == 1 and "100" in errors[0]["error"]
        assert not app.extensions["workspace"].documents
    finally:
        app.extensions["workspace"].close()
