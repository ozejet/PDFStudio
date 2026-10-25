from __future__ import annotations

import json
import hashlib
import os
import re
import shutil
import tempfile
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import fitz
from PIL import Image

MAX_OPEN_DOCUMENTS = 100

def app_root() -> Path:
    import sys
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))


def user_data() -> Path:
    import sys
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "PDFStudio"
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share")) / "PDFStudio"


def safe_name(value: str, default: str = "document") -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(value)).strip(" .")[:180]
    if not name or name.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}:
        return default
    return name


@dataclass
class Document:
    id: str
    name: str
    path: Path
    pages: list[dict] = field(default_factory=list)
    kind: str = "pdf"
    fingerprint: str = ""
    source_path: Path | None = None
    source: object | None = None
    revision: int = 0

    def public(self):
        return {"id": self.id, "name": self.name, "pages": self.pages, "kind": self.kind, "size": self.path.stat().st_size, "fingerprint": self.fingerprint,
                "pdfReady": bool(self.pages), "sourceKind": self.source.kind if self.source else "", "revision": self.revision,
                "textFallback": self.source.fallback if self.source else False, "warnings": list(self.source.warnings) if self.source else [],
                "url": f"/api/documents/{self.id}/file?revision={self.revision}" if self.pages else ""}


class Workspace:
    """Each application process owns an isolated temporary workspace."""

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = Path(data_dir or user_data())
        self.profile_dir = self.data_dir / "profiles"
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="pdfstudio-")
        self.root = Path(self.temp.name)
        self.documents: dict[str, Document] = {}
        self.assets: dict[str, Path] = {}
        self.artifacts: dict[str, tuple[Path, str]] = {}
        self.lock = threading.RLock()
        self.reserved_imports = 0

    def check_capacity(self, count=1):
        if len(self.documents) + self.reserved_imports + count > MAX_OPEN_DOCUMENTS:
            raise ValueError(f"PDF Studio can open up to {MAX_OPEN_DOCUMENTS} files. Close files before adding this entire batch; no files in this batch were opened.")

    def close(self):
        self.temp.cleanup()

    def document(self, key: str, *, pdf=True) -> Document:
        try:
            document = self.documents[str(key)]
        except KeyError:
            raise ValueError("This document is no longer open. Add the file again.") from None
        if pdf and not document.pages:
            raise ValueError("Choose Prepare PDF for this document before using PDF tools.")
        return document

    def import_source(self, data, name, source, pdf_bytes=None):
        with self.lock:
            self.check_capacity()
            if pdf_bytes:
                path = self.root / ("prepared-" + uuid.uuid4().hex + ".pdf")
                path.write_bytes(pdf_bytes)
                try:
                    document = self._import_pdf(path, name, source.kind)
                finally:
                    path.unlink(missing_ok=True)
            else:
                key = uuid.uuid4().hex
                path = self.root / (key + ".source")
                path.write_bytes(data)
                document = Document(key, safe_name(name), path, kind=source.kind, fingerprint=hashlib.sha256(data).hexdigest())
                self.documents[key] = document
            original = self.root / (document.id + ".original")
            original.write_bytes(data)
            document.source_path, document.source = original, source
            return document

    def import_pdf(self, path: Path, name: str, kind="pdf", password="") -> Document:
        with self.lock:
            self.check_capacity()
            return self._import_pdf(path, name, kind, password)

    def _import_pdf(self, path: Path, name: str, kind="pdf", password="") -> Document:
        raw = path.read_bytes()
        # Opening from memory also releases malformed files reliably on Windows.
        try:
            opened = fitz.open(stream=raw, filetype="pdf")
        except (fitz.FileDataError, fitz.EmptyFileError):
            raise ValueError("This file is damaged or is not a valid PDF.") from None
        with opened as pdf:
            if pdf.needs_pass and not pdf.authenticate(password):
                raise ValueError("This PDF needs a password. Enter its password and add it again.")
            if not pdf.is_pdf or not len(pdf):
                raise ValueError("The file does not contain a readable PDF page.")
            if len(pdf) > 10000:
                raise ValueError("This file exceeds the 10,000-page limit.")
            key = uuid.uuid4().hex
            dest = self.root / f"{key}.pdf"
            pdf.save(dest, encryption=fitz.PDF_ENCRYPT_NONE, garbage=3, deflate=True)
            pages = [{"number": i + 1, "width": p.rect.width, "height": p.rect.height, "rotation": p.rotation} for i, p in enumerate(pdf)]
        item = Document(key, safe_name(name, "document.pdf"), dest, pages, kind, hashlib.sha256(raw).hexdigest())
        with self.lock:
            self.documents[key] = item
        return item

    def import_bytes(self, data: bytes, name: str, password="", *, force_text=False, encoding="", assets=None) -> Document:
        suffix = Path(name).suffix.lower()
        from .source_formats import OFFICE_EXTENSIONS, AUTO_PDF_BYTES, read_source
        if suffix not in OFFICE_EXTENSIONS | {".pdf", ".png", ".jpg", ".jpeg"}:
            if data.startswith(b"%PDF-"):
                suffix = ".pdf"
            else:
                source = read_source(data, name, force=force_text, encoding=encoding, assets=assets)
                pdf_bytes = None
                if source.kind != "html" and len(data) <= AUTO_PDF_BYTES:
                    from .source_worker import render_pdf
                    try:
                        pdf_bytes = render_pdf(source.html, source.layout)
                    except ValueError as error:
                        source.warnings.append(str(error) + " The text is available to read.")
                elif source.kind != "html":
                    source.warnings.append("This larger text file is ready to read. Choose Prepare PDF when you need page previews or PDF export.")
                return self.import_source(data, name, source, pdf_bytes)
        path = self.root / f"upload-{uuid.uuid4().hex}{suffix}"
        path.write_bytes(data)
        try:
            if suffix in {".png", ".jpg", ".jpeg"}:
                with Image.open(path) as im:
                    if im.width * im.height > 50_000_000:
                        raise ValueError("Use an image below 50 megapixels.")
                    im.verify()
                with fitz.open(path) as image:
                    pdf_bytes = image.convert_to_pdf()
                path.unlink()
                path = path.with_suffix(".pdf")
                path.write_bytes(pdf_bytes)
                return self.import_pdf(path, name, "image")
            if suffix in OFFICE_EXTENSIONS:
                from .utilities import office_to_pdf
                output = office_to_pdf(path, self.root / f"office-{uuid.uuid4().hex}")
                return self.import_pdf(output, Path(name).stem + ".pdf", "office")
            if suffix != ".pdf":
                raise ValueError("Choose PDF, PNG, JPG, Word, or PowerPoint files.")
            return self.import_pdf(path, name, password=password)
        finally:
            path.unlink(missing_ok=True)

    def add_asset(self, data: bytes, name: str) -> dict:
        with Image.open(__import__("io").BytesIO(data)) as im:
            if im.width * im.height > 50_000_000:
                raise ValueError("The image is too large. Use an image below 50 megapixels.")
            im.verify()
        key = uuid.uuid4().hex
        path = self.root / f"asset-{key}{Path(name).suffix.lower()}"
        path.write_bytes(data)
        self.assets[key] = path
        return {"id": key, "name": safe_name(name), "url": f"/api/assets/{key}"}

    def artifact(self, data: bytes, name: str) -> dict:
        key = uuid.uuid4().hex
        name = safe_name(name)
        path = self.root / f"out-{key}{Path(name).suffix}"
        path.write_bytes(data)
        self.artifacts[key] = (path, name)
        return {"id": key, "name": name, "size": len(data), "url": f"/api/artifacts/{key}"}

    def profile_list(self):
        result = []
        for p in self.profile_dir.glob("*/profile.json"):
            try:
                record = json.loads(p.read_text(encoding="utf-8"))
                result.append({"id": p.parent.name, "name": record["name"], "fieldCount": len(record.get("objects", []))})
            except (ValueError, KeyError, OSError):
                continue
        return sorted(result, key=lambda x: x["name"].casefold())

    def save_profile(self, record: dict, document: Document) -> dict:
        key = record.get("id", "")
        if not re.fullmatch(r"[a-f0-9]{32}", key):
            key = uuid.uuid4().hex
        folder = self.profile_dir / key
        folder.mkdir(exist_ok=True)
        record = dict(record, id=key, schema="pdfstudio.profile/v1", coordinates="normalized-visible-page", name=safe_name(record.get("name", "Untitled profile")))
        for item in record.get("objects", []):
            if item.get("assetId"):
                source = self.assets.get(item["assetId"])
                if source:
                    shutil.copyfile(source, folder / ("asset-" + item["assetId"] + source.suffix))
        shutil.copyfile(document.path, folder / "template.pdf")
        draft = folder / "profile.tmp"
        draft.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        draft.replace(folder / "profile.json")
        return record

    def load_profile(self, key: str):
        if not re.fullmatch(r"[a-f0-9]{32}", key):
            raise ValueError("Invalid profile identifier.")
        folder = self.profile_dir / key
        record = json.loads((folder / "profile.json").read_text(encoding="utf-8"))
        doc = self.import_pdf(folder / "template.pdf", record["name"] + ".pdf")
        for path in folder.glob("asset-*"):
            asset_id = path.stem.removeprefix("asset-")
            self.assets[asset_id] = path
        return record, doc
