"""Paginate static text/HTML in a separate process; MuPDF never shares threads."""
from __future__ import annotations

import base64
import io
import html
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unicodedata

import fitz
from PIL import Image

from .source_formats import layout_options
from .storage import app_root
from .processes import run_converter


def render_pdf(content, options, *, cancel=None):
    with tempfile.TemporaryDirectory(prefix="pdfstudio-pages-") as folder:
        root = Path(folder)
        job = root / "job.json"
        output = root / "result.pdf"
        job.write_text(json.dumps(dict(html=content, options=options), ensure_ascii=False), encoding="utf-8")
        args = [sys.executable] + ([] if getattr(sys, "frozen", False) else [str(app_root() / "run.py")])
        try:
            result = run_converter(args + ["--source-worker", str(job), str(output)], timeout=120, cancel=cancel)
        except subprocess.TimeoutExpired:
            raise ValueError("PDF preparation took too long. Try a smaller text file or a smaller font.") from None
        if result.returncode or not output.is_file():
            error_file = output.with_suffix(".error.json")
            if error_file.is_file():
                raise ValueError(json.loads(error_file.read_text(encoding="utf-8"))["error"])
            raise ValueError("PDF preparation could not finish. Try simpler HTML or a smaller text file.")
        return output.read_bytes()


def worker_main(job_path, output_path):
    root = Path(job_path).parent
    job = json.loads(Path(job_path).read_text(encoding="utf-8"))
    options = layout_options(job["options"])
    counter = 0
    def image(match):
        nonlocal counter
        data = base64.b64decode(match[2])
        with Image.open(io.BytesIO(data)) as source:
            if source.width * source.height > 50_000_000:
                raise ValueError("Embedded image is too large.")
            counter += 1
            name = f"embedded-{counter}.png"
            source.convert("RGB").save(root / name)
        return name
    def svg_image(match):
        nonlocal counter
        with fitz.open(stream=match[0].encode("utf-8"), filetype="svg") as svg:
            page = svg[0]
            scale = min(2, (8_000_000 / max(1, page.rect.width * page.rect.height)) ** .5)
            counter += 1
            name = f"svg-{counter}.png"
            page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False).save(root / name)
            return f'<img src="{name}" width="{int(page.rect.width)}">'
    content = re.sub(r"<svg\b[^>]*>.*?</svg>", svg_image, job["html"], flags=re.I | re.S)
    content = re.sub(r"data:image/(png|jpeg|gif|webp);base64,([a-z0-9+/=\s]+)", image, content, flags=re.I)
    width, height = {"A4": (595, 842), "Letter": (612, 792), "Legal": (612, 1008)}[options["paper"]]
    if options["orientation"] == "landscape":
        width, height = height, width
    columns = max(10, int((width - 72) / (options["fontSize"] * .64)))
    def preformatted(match):
        text = html.unescape(re.sub(r"<[^>]*>", "", match[2])).expandtabs(4)
        lines = []
        for line in text.split("\n"):
            current, length = [], 0
            for char in line:
                size = 0 if unicodedata.combining(char) else 2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1
                if length + size > columns:
                    if not options["wrap"]:
                        raise ValueError("Some unwrapped lines do not fit the PDF page. Enable wrapping, choose landscape, or reduce the font size.")
                    lines.append("".join(current))
                    current, length = [], 0
                current.append(char)
                length += size
            lines.append("".join(current))
        return match[1] + html.escape("\n".join(lines)) + "</pre>"
    content = re.sub(r"(<pre\b[^>]*>)(.*?)</pre>", preformatted, content, flags=re.I | re.S)
    css = '@font-face{font-family:Studio;src:url("Sarabun-Regular.ttf")}@font-face{font-family:Studio;src:url("Sarabun-Bold.ttf");font-weight:bold}body{font-family:Studio;font-size:' + str(options["fontSize"]) + 'pt;line-height:1.5}pre,code{font-family:monospace,Studio}pre{white-space:' + ("pre-wrap" if options["wrap"] else "pre") + ';tab-size:4}img{max-width:100%;height:auto}table{border-collapse:collapse}td,th{border:0.5pt solid #aaa;padding:4pt}h1,h2,h3{page-break-after:avoid}'
    archive = fitz.Archive(str(root))
    archive.add(str(app_root() / "vendor/fonts"))
    story = fitz.Story(content or "<p>&nbsp;</p>", user_css=css, archive=archive)
    def rectangle(index, _filled):
        if index >= 2000:
            raise ValueError("Use a shorter document (up to 2,000 generated pages).")
        return fitz.Rect(0, 0, width, height), fitz.Rect(36, 36, width - 36, height - 36), None
    with story.write_with_links(rectangle) as pdf:
        if not len(pdf):
            pdf.new_page(width=width, height=height)
        pdf.save(output_path, garbage=3, deflate=True)
