"""Local import jobs. Status polling never waits on conversion or MuPDF."""
from __future__ import annotations

import shutil
import threading
import uuid
from pathlib import Path

from . import utilities
from .storage import safe_name
from .source_formats import OFFICE_EXTENSIONS, BINARY_EXTENSIONS, MAX_TEXT_BYTES, AUTO_PDF_BYTES, read_source, TextConfirmationRequired
from .processes import ConversionCancelled, check_cancelled

class ImportJobs:
    def __init__(self, workspace):
        self.workspace = workspace
        self.lock = threading.Lock()
        self.jobs = {}
        self.worker = None

    def start(self, files, password="", force_text=False, encoding="", text_defaults=None):
        if not files:
            raise ValueError("Choose at least one file.")
        with self.lock, self.workspace.lock:
            if self.worker and self.worker.is_alive():
                raise ValueError("An import is already running. Wait for it to finish before adding another batch.")
            self.workspace.check_capacity(len(files))
            key = uuid.uuid4().hex
            folder = self.workspace.root / ("import-" + key)
            folder.mkdir()
            try:
                queued = []
                for index, file in enumerate(files):
                    name = safe_name(file.filename or "document.pdf")
                    path = folder / (str(index) + Path(name).suffix.lower())
                    file.save(path)
                    queued.append((path, name))
            except Exception:
                shutil.rmtree(folder)
                raise
            self.workspace.reserved_imports += len(queued)
            state = dict(id=key, phase="queued", current="", index=0, total=len(files), completed=0, documents=[], errors=[], done=False,
                         cancelled=False, _cancel=threading.Event(), files=[dict(index=i, name=name, phase="queued") for i, (_, name) in enumerate(queued)])
            # Completed jobs are no longer needed by later uploads.
            self.jobs = {key: state}
            self.worker = threading.Thread(target=self._run, args=(state, queued, password, folder, force_text, encoding, text_defaults or {}), name="pdfstudio-import")
            self.worker.start()
            return key

    def status(self, key, after=0):
        with self.lock:
            if key not in self.jobs:
                raise ValueError("This import is no longer available.")
            state = self.jobs[key]
            # Send new documents once. Finished files can be used while later files convert.
            return {**{name: value for name, value in state.items() if not name.startswith("_")}, "ready": len(state["documents"]), "documents": list(state["documents"][max(0, after):]),
                    "errors": list(state["errors"]), "files": [dict(file) for file in state["files"]]}

    def cancel(self, key):
        with self.lock:
            state = self.jobs.get(key)
            if not state:
                raise ValueError("This import is no longer available.")
            if not state["done"]:
                state["_cancel"].set()
                state["phase"] = "cancelling"

    def _update(self, state, **changes):
        with self.lock:
            state.update(changes)

    def _file_update(self, state, index, **changes):
        with self.lock:
            state["files"][index].update(changes)

    def _run(self, state, queued, password, folder, force_text, encoding, text_defaults):
        pending = len(queued)
        cancel = state["_cancel"]
        # Only files explicitly included in this batch can become HTML companions.
        assets, duplicates = {}, set()
        for path, name in queued:
            key = name.casefold()
            if key in assets:
                duplicates.add(key)
            assets[key] = path
        for key in duplicates:
            assets.pop(key, None)
        try:
            for index, (path, name) in enumerate(queued):
                reserved = True
                try:
                    check_cancelled(cancel)
                    office = path.suffix.lower() in OFFICE_EXTENSIONS
                    self._update(state, phase="converting" if office else "opening", current=name, index=index + 1)
                    self._file_update(state, index, phase="converting" if office else "opening")
                    # LibreOffice is a separate process; do not hold the MuPDF lock.
                    output = utilities.office_to_pdf(path, folder / ("converted-" + str(index)), cancel=cancel) if office else None
                    source, pdf_bytes = None, None
                    if not office and path.suffix.lower() not in {".pdf", ".png", ".jpg", ".jpeg"}:
                        if path.suffix.lower() in BINARY_EXTENSIONS:
                            raise ValueError("This file type is not supported. Other files in the batch can still open.")
                        with path.open("rb") as stream:
                            header = stream.read(8)
                        if not header.startswith(b"%PDF-") and path.stat().st_size > MAX_TEXT_BYTES:
                            raise ValueError("Use a text file below 8 MB. Split larger logs into smaller files first.")
                        raw = path.read_bytes()
                        if not raw.startswith(b"%PDF-"):
                            preferred = text_defaults.get(path.suffix.lower(), "")
                            source = read_source(raw, name, force=force_text or bool(preferred), encoding=encoding or preferred, assets=assets)
                            if source.kind != "html" and len(raw) <= AUTO_PDF_BYTES:
                                from .source_worker import render_pdf
                                self._update(state, phase="converting")
                                self._file_update(state, index, phase="converting")
                                try:
                                    pdf_bytes = render_pdf(source.html, source.layout, cancel=cancel)
                                except ValueError as error:
                                    source.warnings.append(str(error) + " The text is available to read.")
                            elif source.kind != "html":
                                source.warnings.append("This larger text file is ready to read. Choose Prepare PDF when you need page previews or PDF export.")
                    if office:
                        self._update(state, phase="opening")
                        self._file_update(state, index, phase="opening")
                    with self.workspace.lock:
                        check_cancelled(cancel)
                        self.workspace.reserved_imports -= 1
                        pending -= 1
                        reserved = False
                        doc = self.workspace.import_source(raw, name, source, pdf_bytes) if source else self.workspace.import_pdf(output, Path(name).stem + ".pdf", "office") if office else self.workspace.import_bytes(path.read_bytes(), name, password)
                        public = doc.public()
                    with self.lock:
                        state["documents"].append(public)
                        state["files"][index].update(phase="ready", documentId=doc.id)
                except ConversionCancelled:
                    with self.lock:
                        state["cancelled"] = True
                        for row in state["files"][index:]:
                            if row["phase"] not in {"ready", "error"}:
                                row["phase"] = "cancelled"
                    break
                except Exception as exc:
                    # Return useful validation errors, never tracebacks or document data.
                    message = str(exc) if isinstance(exc, (ValueError, RuntimeError)) else "This file could not be opened. Check the file and try again."
                    with self.lock:
                        code = "open-as-text" if isinstance(exc, TextConfirmationRequired) else ""
                        state["errors"].append(dict(index=index, name=name, error=message, code=code))
                        state["files"][index].update(phase="error", error=message, code=code)
                finally:
                    if reserved:
                        with self.workspace.lock:
                            self.workspace.reserved_imports -= 1
                            pending -= 1
                    with self.lock:
                        state["completed"] = sum(row["phase"] in {"ready", "error"} for row in state["files"])
        finally:
            with self.workspace.lock:
                self.workspace.reserved_imports -= pending
            shutil.rmtree(folder, ignore_errors=True)
            self._update(state, phase="cancelled" if state["cancelled"] else "complete", done=True)

    def close(self):
        if self.worker:
            with self.lock:
                for state in self.jobs.values():
                    state["_cancel"].set()
            self.worker.join()
