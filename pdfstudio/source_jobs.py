"""Prepare a source's PDF while existing PDF workers and HTTP requests stay usable."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import threading
import uuid

import fitz

from .source_formats import MAX_TEXT_BYTES, formatted_html, layout_options
from .source_worker import render_pdf
from .processes import ConversionCancelled, check_cancelled


class SourceJobs:
    def __init__(self, workspace):
        self.workspace = workspace
        self.lock = threading.Lock()
        self.jobs = {}
        self.worker = None

    def start(self, key, content=None, options=None):
        with self.lock, self.workspace.lock:
            if self.worker and self.worker.is_alive():
                raise ValueError("A PDF preview is already preparing. You can continue reading while it finishes.")
            document = self.workspace.document(key, pdf=False)
            if not document.source:
                raise ValueError("This document already has a fixed PDF layout.")
            if content is not None and (not isinstance(content, str) or len(content.encode("utf-8")) > MAX_TEXT_BYTES):
                raise ValueError("Use a text draft below 8 MB.")
            source = document.source
            layout = layout_options(options or source.layout)
            key_id = uuid.uuid4().hex
            state = dict(id=key_id, phase="preparing", done=False, document=None, error="", cancelled=False, _cancel=threading.Event())
            self.jobs = {key_id: state}
            self.worker = threading.Thread(target=self._run, args=(state, document.id, document.revision, source, content, layout), name="pdfstudio-source")
            self.worker.start()
            return key_id

    def status(self, key):
        with self.lock:
            if key not in self.jobs:
                raise ValueError("This PDF preparation is no longer available.")
            return {name: value for name, value in self.jobs[key].items() if not name.startswith("_")}

    def cancel(self, key):
        with self.lock:
            state = self.jobs.get(key)
            if not state:
                raise ValueError("This PDF preparation is no longer available.")
            state["_cancel"].set()
            if state.get("_result"):
                state["_result"][2].unlink(missing_ok=True)
                state["_result"] = None
                state.update(cancelled=True, phase="cancelled")
            elif not state["done"]:
                state["phase"] = "cancelling"

    def commit(self, key):
        with self.lock, self.workspace.lock:
            state = self.jobs.get(key)
            if not state or not state.get("_result"):
                raise ValueError("The prepared preview is not available. Prepare it again.")
            document_id, revision, path, pages, source, fingerprint = state["_result"]
            document = self.workspace.document(document_id, pdf=False)
            if document.revision != revision:
                raise ValueError("The document changed. Review it before refreshing its preview.")
            document.path, document.pages, document.source = path, pages, source
            document.revision, document.fingerprint = revision + 1, fingerprint
            state["_result"] = None
            return document.public()

    def _run(self, state, key, revision, source, content, options):
        try:
            value = source.text if content is None else content
            formatted, notes = (source.html, [note for note in source.warnings if "The text is available to read" not in note and "This larger text file" not in note]) if content is None else formatted_html(value, source.kind, source.assets)
            pdf_bytes = render_pdf(formatted, options, cancel=state["_cancel"])
            with self.workspace.lock:
                check_cancelled(state["_cancel"])
                document = self.workspace.document(key, pdf=False)
                if document.revision != revision:
                    raise ValueError("The document changed during preparation. Review it and try again.")
                with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf:
                    pages = [{"number": i + 1, "width": page.rect.width, "height": page.rect.height, "rotation": page.rotation} for i, page in enumerate(pdf)]
                path = self.workspace.root / (key + "-preview-" + state["id"] + ".pdf")
                path.write_bytes(pdf_bytes)
                prepared_source = replace(source, text=value, html=formatted, layout=options, warnings=notes)
            with self.lock:
                if state["_cancel"].is_set():
                    path.unlink(missing_ok=True)
                    raise ConversionCancelled()
                state.update(phase="complete", done=True, _result=(key, revision, path, pages, prepared_source, hashlib.sha256(pdf_bytes).hexdigest()))
        except ConversionCancelled:
            with self.lock:
                state.update(phase="cancelled", cancelled=True, done=True)
        except Exception as error:
            message = str(error) if isinstance(error, (ValueError, RuntimeError)) else "PDF preparation could not finish. Your previous preview and source are preserved."
            with self.lock:
                state.update(phase="error", error=message, done=True)

    def close(self):
        if self.worker:
            with self.lock:
                for state in self.jobs.values():
                    state["_cancel"].set()
            self.worker.join()
