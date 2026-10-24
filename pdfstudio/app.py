from __future__ import annotations

import io
import json
import secrets
import shutil
import traceback
import zipfile
from pathlib import Path
from urllib.parse import urlsplit

import fitz
from flask import Flask, abort, g, jsonify, request, send_file, send_from_directory
from werkzeug.exceptions import HTTPException

from . import __version__
from . import engine, templates, utilities
from .storage import MAX_OPEN_DOCUMENTS, Workspace, app_root, safe_name
from .imports import ImportJobs
from .source_jobs import SourceJobs
from .source_formats import reader_html, ENCODINGS
from .preferences import Preferences
from .feedback import Feedback


def create_app(data_dir: Path | None = None, *, testing=False):
    app = Flask(__name__, static_folder=None)
    app.config.update(MAX_CONTENT_LENGTH=512 * 1024 * 1024, TESTING=testing)
    workspace = Workspace(data_dir)
    preferences = app.extensions["preferences"] = Preferences(workspace.data_dir)
    feedback = app.extensions["feedback"] = Feedback(workspace.data_dir, app_root() / "web/dist/feedback-form.json")
    token = secrets.token_urlsafe(32)
    cookie = "pdfstudio_" + secrets.token_hex(6)
    app.extensions["workspace"] = workspace
    imports = app.extensions["imports"] = ImportJobs(workspace)
    sources = app.extensions["sources"] = SourceJobs(workspace)
    app.config["STUDIO_TOKEN"] = token
    app.config["STUDIO_COOKIE"] = cookie
    dist = app_root() / "web" / "dist"
    documents_folder = Path.home() / "Documents"
    save_folder = documents_folder if documents_folder.is_dir() else Path.home()

    @app.before_request
    def local_only():
        if request.host.split(":")[0] not in {"localhost", "127.0.0.1"}:
            abort(403, "PDF Studio only accepts connections from this device.")
        origin = request.headers.get("Origin")
        if origin and urlsplit(origin).netloc != request.host:
            abort(403, "Cross-origin requests are not allowed.")
        if request.path.startswith("/api/") and request.path != "/api/health":
            supplied = request.headers.get("X-Studio-Token", "")
            authenticated = secrets.compare_digest(request.cookies.get(cookie, ""), token) or secrets.compare_digest(supplied, token)
            if not authenticated or (request.method not in {"GET", "HEAD"} and not secrets.compare_digest(supplied, token)):
                abort(403, "Open PDF Studio in its browser window, then try again.")
            # MuPDF operations are serialized; independent HTTP file transfers
            # still use their own streams. MuPDF itself is not thread-safe.
            source_preparation = request.path.startswith("/api/documents/") and request.path.endswith("/prepare")
            if not request.path.startswith(("/api/import-jobs", "/api/source-jobs", "/api/feedback")) and request.path not in {"/api/quit", "/api/save", "/api/preferences"} and not source_preparation:
                workspace.lock.acquire()
                g.studio_locked = True

    @app.teardown_request
    def release_job_lock(_error):
        if getattr(g, "studio_locked", False):
            g.studio_locked = False
            workspace.lock.release()

    @app.after_request
    def private_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store" if request.path.startswith("/api/") else "no-cache"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; worker-src 'self' blob:; connect-src 'self'; frame-src 'self' https://forms.office.com https://forms.cloud.microsoft https://forms.microsoft.com; object-src 'none'; frame-ancestors 'none'; base-uri 'self'"
        return response

    @app.errorhandler(Exception)
    def error(exc):
        if isinstance(exc, HTTPException):
            return jsonify(error=exc.description), exc.code
        if isinstance(exc, (ValueError, KeyError, FileNotFoundError, fitz.FileDataError, zipfile.BadZipFile)):
            return jsonify(error=str(exc)), 400
        if testing:
            raise exc
        # Do not log document text, names, payloads, or user paths.
        app.logger.error("Document operation failed: %s", type(exc).__name__)
        return jsonify(error="The operation could not finish. Check the document and try a smaller job."), 500

    @app.get("/api/health")
    def health():
        return jsonify(ok=True, version=__version__)

    @app.get("/api/config")
    def config():
        return jsonify(token=token, version=__version__, preferences=preferences.read(), feedback=feedback.read(), maxOpenDocuments=MAX_OPEN_DOCUMENTS, local=True, office=bool(utilities.office_binary()), ocr=(dist / "vendor/ocr/lang/eng.traineddata.gz").exists(), profiles=workspace.profile_list(), documents=[doc.public() for doc in workspace.documents.values()], launchedWithFiles=app.extensions.get("launched_with_files", False), launchErrors=app.extensions.get("launch_errors", []))

    @app.post("/api/preferences")
    def save_preferences():
        return jsonify(preferences.update(request.get_json()))

    @app.route("/api/feedback/settings", methods=["GET", "POST"])
    def feedback_settings():
        return jsonify(feedback.update(request.get_json()) if request.method == "POST" else feedback.read())

    @app.post("/api/feedback/open")
    def open_feedback():
        import webbrowser
        url = feedback.read()["url"]
        if not url:
            raise ValueError("Connect your Microsoft Form in Settings first.")
        if not webbrowser.open(url, new=2):
            raise ValueError("The browser could not open. Copy the form link from Settings and open it in your browser.")
        return jsonify(opened=True)

    @app.post("/api/quit")
    def quit_app():
        import threading
        shutdown = app.extensions.get("shutdown")
        if shutdown:
            threading.Timer(.25, shutdown).start()
        return jsonify(ok=True)

    @app.get("/")
    def index():
        if not (dist / "index.html").exists():
            return "PDF Studio's interface has not been built. Run the development setup in README.md.", 503
        response = send_from_directory(dist, "index.html")
        response.set_cookie(cookie, token, httponly=True, samesite="Strict")
        return response

    @app.get("/<path:path>")
    def static(path):
        return send_from_directory(dist, path)

    @app.post("/api/documents")
    def upload():
        files = request.files.getlist("files")
        if not files:
            raise ValueError("Choose at least one file.")
        workspace.check_capacity(len(files))
        documents, errors = [], []
        for file in files:
            try:
                documents.append(workspace.import_bytes(file.read(), file.filename or "document.pdf", request.form.get("password", "")).public())
            except (ValueError, fitz.FileDataError, RuntimeError) as exc:
                errors.append({"name": file.filename, "error": str(exc)})
        return jsonify(documents=documents, errors=errors)

    @app.post("/api/import-jobs")
    def start_import():
        defaults = json.loads(request.form.get("textDefaults", "{}"))
        if not isinstance(defaults, dict) or len(defaults) > 100 or any(not isinstance(key, str) or len(key) > 24 or not isinstance(value, str) or value not in ENCODINGS for key, value in defaults.items()):
            raise ValueError("Text format preferences are invalid.")
        return jsonify(id=imports.start(request.files.getlist("files"), request.form.get("password", ""), request.form.get("forceText") == "1", request.form.get("encoding", ""), defaults))

    @app.get("/api/import-jobs/<key>")
    def import_status(key):
        return jsonify(imports.status(key, request.args.get("after", 0, type=int)))

    @app.post("/api/import-jobs/<key>/cancel")
    def cancel_import(key):
        imports.cancel(key)
        return jsonify(ok=True)

    @app.get("/api/documents/<key>/file")
    def document_file(key):
        return send_file(workspace.document(key).path, mimetype="application/pdf", conditional=True)

    @app.delete("/api/documents/<key>")
    def document_close(key):
        doc = workspace.document(key, pdf=False)
        doc.path.unlink(missing_ok=True)
        if doc.source_path:
            doc.source_path.unlink(missing_ok=True)
        del workspace.documents[key]
        return jsonify(ok=True)

    @app.get("/api/documents/<key>/source")
    def source_content(key):
        doc = workspace.document(key, pdf=False)
        if not doc.source:
            raise ValueError("This document has no text or HTML source view.")
        source = doc.source
        return jsonify(text=source.text, html=reader_html(source.html) if source.kind != "text" else "", encoding=source.encoding, kind=source.kind, layout=source.layout, warnings=source.warnings)

    @app.post("/api/documents/<key>/prepare")
    def prepare_source(key):
        data = request.get_json() or {}
        return jsonify(id=sources.start(key, data.get("content"), data.get("options")))

    @app.get("/api/source-jobs/<key>")
    def source_status(key):
        return jsonify(sources.status(key))

    @app.post("/api/source-jobs/<key>/cancel")
    def cancel_source(key):
        sources.cancel(key)
        return jsonify(ok=True)

    @app.post("/api/source-jobs/<key>/commit")
    def commit_source(key):
        return jsonify(sources.commit(key))

    @app.post("/api/export/separate")
    def export_separate():
        data = request.get_json()
        documents = [workspace.document(key) for key in data.get("ids", [])]
        if not documents:
            raise ValueError("Choose at least one prepared PDF.")
        output = io.BytesIO()
        names = set()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for doc in documents:
                stem, count = Path(doc.name).stem, 1
                name = safe_name(stem) + ".pdf"
                while name.casefold() in names:
                    count += 1
                    name = safe_name(stem) + f"_{count}.pdf"
                names.add(name.casefold())
                archive.writestr(name, doc.path.read_bytes())
        return jsonify(workspace.artifact(output.getvalue(), engine.timestamp("converted", "zip")))

    @app.get("/api/documents/<key>/render/<int:number>")
    def render_page(key, number):
        doc = workspace.document(key)
        if not 1 <= number <= len(doc.pages):
            abort(404)
        scale = min(3, max(.1, float(request.args.get("scale", "1"))))
        with fitz.open(doc.path) as pdf:
            page = pdf[number - 1]
            if page.rect.width * page.rect.height * scale ** 2 > 32_000_000:
                scale = (32_000_000 / (page.rect.width * page.rect.height)) ** .5
            image = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            return send_file(io.BytesIO(image.tobytes("png")), mimetype="image/png")

    @app.get("/api/documents/<key>/text")
    def document_text(key):
        with fitz.open(workspace.document(key).path) as pdf:
            selected = engine.page_range(request.args.get("pages", "all"), len(pdf))
            return jsonify(pages=[{"page": i + 1, "text": pdf[i].get_text(sort=True)} for i in selected])

    @app.post("/api/assets")
    def asset_upload():
        file = request.files["file"]
        return jsonify(workspace.add_asset(file.read(), file.filename or "image.png"))

    @app.get("/api/assets/<key>")
    def asset_file(key):
        if key not in workspace.assets:
            abort(404)
        return send_file(workspace.assets[key])

    @app.post("/api/export/combine")
    def export_combine():
        data = request.get_json()
        result = engine.combine(workspace, data.get("items", []), data.get("pattern", ""))
        return jsonify(workspace.artifact(result, engine.timestamp()))

    @app.post("/api/export/split")
    def export_split():
        data = request.get_json()
        return jsonify(workspace.artifact(engine.split(workspace, data["id"], data["groups"]), engine.timestamp("split", "zip")))

    @app.post("/api/export/edit")
    def export_edit():
        data = request.get_json()
        result = engine.edit(workspace, data["id"], data.get("objects", []))
        prefix = "redact" if any(o.get("type") == "redact" for o in data.get("objects", [])) else "edited"
        return jsonify(workspace.artifact(result, engine.timestamp(prefix)))

    @app.post("/api/export/original")
    def export_original():
        doc = workspace.document(request.get_json()["id"])
        return jsonify(workspace.artifact(doc.path.read_bytes(), Path(doc.name).stem + ".pdf"))

    @app.get("/api/artifacts/<key>")
    def artifact_download(key):
        path, name = workspace.artifacts[key]
        return send_file(path, as_attachment=True, download_name=name, conditional=True)

    @app.post("/api/save")
    def save():
        nonlocal save_folder
        from .dialogs import choose_save
        data = request.get_json()
        source, name = workspace.artifacts[data["id"]]
        path = choose_save(safe_name(data.get("name", name)), str(save_folder))
        if not path:
            return jsonify(cancelled=True)
        destination = Path(path)
        stem, extension, index = destination.stem, destination.suffix, 1
        while True:
            try:
                with destination.open("xb") as stream, source.open("rb") as input_:
                    shutil.copyfileobj(input_, stream)
                break
            except FileExistsError:
                index += 1
                destination = destination.with_name(f"{stem}_{index}{extension}")
        save_folder = destination.parent
        return jsonify(cancelled=False, name=destination.name, path=str(destination))

    @app.post("/api/spreadsheet")
    def spreadsheet():
        file = request.files["file"]
        return jsonify(templates.spreadsheet(file.read(), file.filename or "data.xlsx", request.form.get("sheet")))

    @app.get("/api/profiles")
    def profiles():
        return jsonify(profiles=workspace.profile_list())

    @app.post("/api/profiles")
    def profile_save():
        data = request.get_json()
        return jsonify(workspace.save_profile(data["profile"], workspace.document(data["documentId"])))

    @app.get("/api/profiles/<key>")
    def profile_load(key):
        profile, doc = workspace.load_profile(key)
        return jsonify(profile=profile, document=doc.public())

    @app.post("/api/profiles/<key>/export")
    def profile_export(key):
        if key not in {p["id"] for p in workspace.profile_list()}:
            raise ValueError("This profile was not found.")
        folder = workspace.profile_dir / key
        profile = json.loads((folder / "profile.json").read_text(encoding="utf-8"))
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for file in folder.iterdir():
                if file.is_file() and file.name != "profile.tmp":
                    archive.write(file, file.name)
        return jsonify(workspace.artifact(buffer.getvalue(), safe_name(profile["name"]) + ".pdfstudio.zip"))

    @app.post("/api/profiles/import")
    def profile_import():
        file = request.files["file"]
        with zipfile.ZipFile(io.BytesIO(file.read())) as archive:
            if sum(f.file_size for f in archive.infolist()) > 100_000_000:
                raise ValueError("The profile package exceeds 100 MB.")
            record = json.loads(archive.read("profile.json").decode("utf-8"))
            if record.get("schema") != "pdfstudio.profile/v1":
                raise ValueError("This is not a PDF Studio profile package.")
            doc = workspace.import_bytes(archive.read("template.pdf"), safe_name(record.get("name", "Template")) + ".pdf")
            import re
            for name in archive.namelist():
                if re.fullmatch(r"asset-[a-f0-9]{32}\.(png|jpg|jpeg)", name):
                    data = archive.read(name)
                    target = workspace.root / name
                    target.write_bytes(data)
                    workspace.assets[Path(name).stem.removeprefix("asset-")] = target
            record.pop("id", None)
            record = workspace.save_profile(record, doc)
            return jsonify(profile=record, document=doc.public())

    @app.post("/api/templates/migrate")
    def migrate():
        data = request.get_json()
        return jsonify(templates.migrate_legacy(workspace, data["id"], data["mapping"], data.get("coordinateMode", "")))

    @app.post("/api/templates/generate")
    def generate():
        data = request.get_json()
        result, name = templates.generate(workspace, data["id"], data["objects"], data["rows"], combined=data.get("combined", False), filename_pattern=data.get("filenamePattern", "row_{row}"), preview=data.get("preview", False))
        return jsonify(workspace.artifact(result, name))

    @app.post("/api/tools/tables")
    def tables():
        data = request.get_json()
        result = utilities.extract_tables(workspace, data["id"], data.get("pages", "all"), data.get("strategy", "lines"))
        if data.get("preview", True):
            return jsonify(tables=result)
        format_ = data.get("format", "xlsx")
        return jsonify(workspace.artifact(utilities.tables_export(result, format_), engine.timestamp("tables", "xlsx" if format_ == "xlsx" else "zip")))

    @app.post("/api/tools/markdown")
    def markdown():
        data = request.get_json()
        text = utilities.markdown(workspace, data["id"], data.get("pages", "all"))
        return jsonify(text=text, artifact=workspace.artifact(text.encode("utf-8"), Path(workspace.document(data["id"]).name).stem + ".md"))

    @app.post("/api/tools/rename")
    def rename():
        data = request.get_json()
        result = utilities.rename_preview(workspace, data["ids"], data.get("pattern", "{Date}_{ReferenceID}_{OriginalName}"))
        if data.get("preview", True):
            return jsonify(files=result)
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for item in result:
                archive.write(workspace.document(item["id"]).path, item["name"])
        return jsonify(workspace.artifact(output.getvalue(), engine.timestamp("payments", "zip")))

    @app.post("/api/tools/ocr")
    def ocr():
        data = request.get_json()
        original = workspace.document(data["id"])
        pdf = engine.searchable(workspace, original.id, data["pages"])
        document = workspace.import_bytes(pdf, Path(original.name).stem + "_searchable.pdf")
        return jsonify(document=document.public(), artifact=workspace.artifact(pdf, engine.timestamp("searchable")))

    return app
