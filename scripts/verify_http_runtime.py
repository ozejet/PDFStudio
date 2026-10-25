"""Check a running development or frozen app with synthetic files only."""
from __future__ import annotations

import argparse
import http.cookiejar
import io
import json
import re
import time
import uuid
import zipfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

import fitz


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--office", action="store_true")
    parser.add_argument("--sources", action="store_true")
    parser.add_argument("--encoding-recovery", action="store_true")
    parser.add_argument("--controls", action="store_true")
    parser.add_argument("--quit", action="store_true")
    args = parser.parse_args()
    base = args.url.rstrip("/")
    client = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
    token = ""

    def request(path, payload=None, *, raw=None, content_type=None):
        headers = {"X-Studio-Token": token} if token else {}
        if payload is not None:
            raw = json.dumps(payload).encode()
            content_type = "application/json"
        if content_type:
            headers["Content-Type"] = content_type
        with client.open(Request(base + path, data=raw, headers=headers), timeout=250) as response:
            body, mime = response.read(), response.headers.get_content_type()
            return (json.loads(body) if mime == "application/json" else body), mime

    def upload(name, content, *, job=False, fields=None, error_code=None, wait=True):
        boundary = uuid.uuid4().hex
        raw = (f'--{boundary}\r\nContent-Disposition: form-data; name="files"; filename="{name}"\r\n'
               'Content-Type: application/octet-stream\r\n\r\n').encode() + content + b'\r\n'
        for key, value in (fields or {}).items():
            raw += f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()
        raw += f'--{boundary}--\r\n'.encode()
        result, _ = request("/api/import-jobs" if job else "/api/documents", raw=raw, content_type="multipart/form-data; boundary=" + boundary)
        if job and not wait:
            return result
        if job:
            key = result["id"]
            deadline = time.monotonic() + 250
            while True:
                result, _ = request("/api/import-jobs/" + key)
                if result["done"]:
                    break
                assert time.monotonic() < deadline, "Import timed out"
                time.sleep(.2)
            assert result["completed"] == result["total"] == 1
        if error_code:
            assert not result["documents"] and result["errors"][0]["code"] == error_code, result
            return result["errors"][0]
        assert not result["errors"], result["errors"]
        return result["documents"][0]

    html, _ = request("/")
    assert b"<title>PDF Studio</title>" in html and b'rel="icon"' in html
    config, _ = request("/api/config")
    token = config["token"]
    assert config["local"] and config["ocr"]
    if args.office:
        assert config["office"]
    assert config["maxOpenDocuments"] == 100
    resources = [(p, "text/javascript") for p in re.findall(r'src="([^"]+\.js)"', html.decode())]
    resources += [("/vendor/pdfjs/pdf.worker.min.mjs", "text/javascript"),
                  ("/vendor/pdfjs/wasm/openjpeg.wasm", "application/wasm"),
                  ("/vendor/ocr/worker.min.js", "text/javascript"),
                  ("/vendor/ocr/lang/tha.traineddata.gz", "application/gzip"),
                  ("/fonts/sarabun-01.woff2", "font/woff2")]
    resources += [(f"/branding/pdfstudio-{size}.png", "image/png") for size in (16, 32, 40, 48, 72, 80, 144, 180, 192, 512)]
    resources += [("/branding/pdfstudio.ico", "image/vnd.microsoft.icon"), ("/favicon.ico", "image/vnd.microsoft.icon")]
    for path, expected in resources:
        body, mime = request(path)
        allowed = {expected, "application/octet-stream"} if path.endswith(".gz") else {expected, "image/x-icon"} if path.endswith(".ico") else {expected}
        assert body and mime in allowed, (path, mime, expected)
    manifest, _ = request("/site.webmanifest")
    if isinstance(manifest, bytes):
        manifest = json.loads(manifest)
    assert manifest["name"] == "PDF Studio" and [i["sizes"] for i in manifest["icons"]] == ["192x192", "512x512"]
    header_logo, _ = request("/branding/pdfstudio-40.png")
    assert len(header_logo) < 5000
    print("PASS: branded title, favicons, optimized logo sizes, Windows ICO and future browser-app manifest")
    try:
        client.open(Request(base + "/api/config", headers={"Origin": "https://example.invalid"}))
        raise AssertionError("Foreign origin was accepted")
    except HTTPError as exc:
        assert exc.code == 403
    with fitz.open() as pdf:
        for number in range(1, 4):
            page = pdf.new_page(width=400, height=500)
            page.insert_text((50, 50), "PAGE " + str(number))
            page.insert_text((80, 100), "PRIVATE")
        source = pdf.tobytes()
    doc = upload("synthetic-runtime.pdf", source, job=True)
    artifact, _ = request("/api/export/combine", {"items": [{"id": doc["id"], "label": "A"}], "pattern": "A3-1,A1"})
    merged, _ = request(artifact["url"])
    with fitz.open(stream=merged, filetype="pdf") as pdf:
        assert len(pdf) == 4
        assert [p.get_text().splitlines()[0] for p in pdf] == ["PAGE 3", "PAGE 2", "PAGE 1", "PAGE 1"]
    box = {"type": "redact", "page": 1, "scope": "range", "range": "2-3", "x": .15, "y": .14, "w": .5, "h": .09, "color": "#ffffff"}
    artifact, _ = request("/api/export/edit", {"id": doc["id"], "objects": [box]})
    redacted, _ = request(artifact["url"])
    with fitz.open(stream=redacted, filetype="pdf") as pdf:
        assert "PRIVATE" in pdf[0].get_text()
        assert all("PRIVATE" not in pdf[n].get_text() for n in (1, 2))
    png, mime = request(f'/api/documents/{doc["id"]}/render/1')
    assert mime == "image/png" and png.startswith(b"\x89PNG")
    print("PASS: built UI, local worker/font/WASM/OCR assets, origin isolation, real upload, ordered merge, range redaction and page rendering")
    field = {"type": "text", "id": "name", "page": 1, "scope": "current", "x": .1, "y": .3, "w": .7, "h": .15,
             "font": "Sarabun", "fontSize": 18, "color": "#20365b", "sourceType": "excel", "column": "Name", "value": ""}
    artifact, _ = request("/api/templates/generate", {"id": doc["id"], "objects": [field], "rows": [{"Name": "ทดสอบ ภาษาไทย"}], "preview": True})
    sample, _ = request(artifact["url"])
    with fitz.open(stream=sample, filetype="pdf") as pdf:
        assert "ทดสอบ ภาษาไทย" in pdf[0].get_text()
    with fitz.open() as pdf:
        page = pdf.new_page(width=400, height=500)
        for x in (50, 150, 250):
            page.draw_line((x, 50), (x, 130))
        for y in (50, 90, 130):
            page.draw_line((50, y), (250, y))
        for x, y, value in ((60, 75, "Name"), (160, 75, "Amount"), (60, 115, "Sample"), (160, 115, "12.00")):
            page.insert_text((x, y), value)
        table_doc = upload("synthetic-table.pdf", pdf.tobytes())
    result, _ = request("/api/tools/tables", {"id": table_doc["id"], "preview": True})
    assert result["tables"][0]["cells"] == [["Name", "Amount"], ["Sample", "12.00"]]
    artifact, _ = request("/api/tools/tables", {"id": table_doc["id"], "preview": False})
    workbook, _ = request(artifact["url"])
    assert workbook.startswith(b"PK")
    print("PASS: bundled Thai font/template preview, ruled-table detection and Excel export")
    if args.sources:
        prepared = []
        if args.encoding_recovery:
            upload("legacy.custom", b"caf\xe9", job=True, error_code="open-as-text")
            upload("legacy.custom", b"caf\xe9", job=True, fields={"forceText": "1", "encoding": "utf-8"}, error_code="open-as-text")
            legacy = upload("legacy.custom", b"caf\xe9", job=True, fields={"forceText": "1", "encoding": "cp1252"})
            assert legacy["sourceKind"] == "text" and legacy["pdfReady"]
        for name in ("captions.vtt", "notes.text", "readable.custom"):
            opened = upload(name, b"WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nReadable caption\n", job=True)
            assert opened["sourceKind"] == "text" and opened["pdfReady"] and opened["pages"]
            prepared.append(opened)
        markdown = upload("notes.md", b"# Runtime heading\n\n**Formatted Markdown**\n\n| A | B |\n|---|---|\n| 1 | 2 |", job=True)
        data, _ = request(markdown["url"])
        with fitz.open(stream=data, filetype="pdf") as pdf:
            assert "Formatted Markdown" in "".join(page.get_text() for page in pdf)
        original = b'<h1>Static HTML report</h1><p>Local HTML content</p><svg width="90" height="40" viewBox="0 0 90 40"><rect width="90" height="40" fill="blue"/></svg><script>alert(1)</script><img src="https://example.invalid/private.png">'
        native = upload("report.html", original, job=True)
        assert native["sourceKind"] == "html" and not native["pdfReady"] and not native["pages"]
        source, _ = request(f'/api/documents/{native["id"]}/source')
        assert "Local HTML content" in source["html"] and "sandbox" not in source["html"]
        assert "alert(1)" not in source["html"] and "https://example.invalid" not in source["html"]
        job, _ = request(f'/api/documents/{native["id"]}/prepare', {"options": {"paper": "Letter", "orientation": "landscape"}})
        deadline = time.monotonic() + 120
        while True:
            state, _ = request("/api/source-jobs/" + job["id"])
            if state["done"]:
                break
            assert time.monotonic() < deadline, "Source preparation timed out"
            time.sleep(.2)
        assert not state["error"], state["error"]
        converted, _ = request("/api/source-jobs/" + job["id"] + "/commit", {})
        assert converted["id"] == native["id"] and converted["revision"] == 1
        data, _ = request(converted["url"])
        with fitz.open(stream=data, filetype="pdf") as pdf:
            assert "Local HTML content" in pdf[0].get_text()
            assert pdf[0].rect.width > pdf[0].rect.height and pdf[0].get_images()
        artifact, _ = request("/api/export/separate", {"ids": [prepared[0]["id"], converted["id"]]})
        data, _ = request(artifact["url"])
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            assert len(archive.namelist()) == 2 and all(name.endswith(".pdf") for name in archive.namelist())
        print("PASS: text/VTT/unfamiliar readable formats, bundled Markdown extensions, static HTML without automatic conversion, explicit PDF preparation, SVG and separate PDF ZIP")
    if args.office:
        fixtures = Path(__file__).resolve().parents[1] / "vendor/smoke-check"
        for name in ("word-test.docx", "slides-test.pptx"):
            converted = upload(name, (fixtures / name).read_bytes(), job=True)
            assert converted["kind"] == "office" and converted["pages"]
            print("PASS: frozen/local Office conversion -", name)
        converted = upload("notes.rtf", b"{\\rtf1\\ansi RTF runtime document.}", job=True)
        assert converted["kind"] == "office" and converted["pages"]
        print("PASS: frozen/local Office conversion - notes.rtf")
    if args.controls:
        original_preferences = config["preferences"]
        try:
            changed, _ = request("/api/preferences", {"confirmQuit": False})
            assert changed == {**original_preferences, "confirmQuit": False}
            fresh, _ = request("/api/config")
            assert fresh["preferences"] == changed
        finally:
            request("/api/preferences", original_preferences)
        fixture = Path(__file__).resolve().parents[1] / "vendor/smoke-check/word-test.docx"
        if config["office"] and fixture.is_file():
            pending = upload("cancel-office.docx", fixture.read_bytes(), job=True, wait=False)
            time.sleep(.5)
            request("/api/import-jobs/" + pending["id"] + "/cancel", {})
            deadline = time.monotonic() + 25
            while True:
                state, _ = request("/api/import-jobs/" + pending["id"])
                if state["done"]:
                    break
                assert time.monotonic() < deadline, "Office cancellation did not finish"
                time.sleep(.1)
            assert state["cancelled"] and not state["documents"] and not state["errors"], state
            fresh, _ = request("/api/config")
            assert any(item["id"] == doc["id"] for item in fresh["documents"])
        original = upload("cancel-prepare.html", b"<p>Cancel this generated page.</p>" * 20000, job=True)
        pending, _ = request(f'/api/documents/{original["id"]}/prepare', {})
        request("/api/source-jobs/" + pending["id"] + "/cancel", {})
        deadline = time.monotonic() + 25
        while True:
            state, _ = request("/api/source-jobs/" + pending["id"])
            if state["done"]:
                break
            assert time.monotonic() < deadline, "PDF preparation cancellation did not finish"
            time.sleep(.1)
        assert state["cancelled"] and not state["error"]
        fresh, _ = request("/api/config")
        assert not next(item for item in fresh["documents"] if item["id"] == original["id"])["pdfReady"]
        print("PASS: persisted reminder preferences, preserved ready files and cancelled PDF preparation without committing"
              + (", including real Office cancellation" if config["office"] and fixture.is_file() else ""))
    if args.quit:
        request("/api/quit", {})


if __name__ == "__main__":
    main()
