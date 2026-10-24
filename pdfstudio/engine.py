from __future__ import annotations

import html
import io
import math
import re
import zipfile
from datetime import datetime
from pathlib import Path

import fitz

from .storage import Workspace, app_root


def timestamp(prefix="combine", extension="pdf"):
    return f"{prefix}_{datetime.now():%Y%m%d%H%M%S}.{extension}"


def page_range(value, count: int, *, repeat=False) -> list[int]:
    """Public page numbers are always 1-based. Ranges may run backwards."""
    if value in (None, "", "all"):
        return list(range(count))
    if isinstance(value, list):
        numbers = [int(v) for v in value]
    else:
        numbers = []
        for part in re.split(r"[,\s]+", str(value).strip()):
            match = re.fullmatch(r"(\d+)(?:-(\d+))?", part)
            if not match:
                raise ValueError(f"Invalid page range: {part}. Use 1-3, 5, 8-6.")
            start = int(match[1])
            stop = int(match[2] or start)
            numbers.extend(range(start, stop + (1 if stop >= start else -1), 1 if stop >= start else -1))
    if not numbers or len(numbers) > 50000 or any(n < 1 or n > count for n in numbers):
        raise ValueError(f"Page numbers must be between 1 and {count}.")
    return [n - 1 for n in (numbers if repeat else dict.fromkeys(numbers))]


def combine(workspace: Workspace, items: list[dict], pattern="") -> bytes:
    if not items:
        raise ValueError("Add at least one document.")
    sequence = []
    if pattern.strip():
        aliases = {str(it.get("label", chr(65 + i))).upper(): it for i, it in enumerate(items)}
        for token in re.split(r"[,\s]+", pattern.strip().upper()):
            match = re.fullmatch(r"([A-Z]+)(\d+(?:-\d+)?)", token)
            if not match or match[1] not in aliases:
                raise ValueError(f"Invalid sequence item: {token}. Example: A3-1,B2,A1.")
            item = aliases[match[1]]
            doc = workspace.document(item["id"])
            sequence.extend((doc, p, item) for p in page_range(match[2], len(doc.pages), repeat=True))
    else:
        for item in items:
            selected = item.get("pages", [])
            if selected:
                doc = workspace.document(item["id"])
                sequence.extend((doc, p, item) for p in page_range(selected, len(doc.pages), repeat=True))
    if not sequence:
        raise ValueError("Select at least one page before exporting.")
    if len(sequence) > 50000:
        raise ValueError("The output exceeds 50,000 pages.")
    with fitz.open() as output:
        opened = {}
        try:
            for doc, page, item in sequence:
                if doc.id not in opened:
                    opened[doc.id] = fitz.open(doc.path)
                output.insert_pdf(opened[doc.id], from_page=page, to_page=page, links=True, annots=True, widgets=True)
                rotation = int(item.get("rotations", {}).get(str(page + 1), item.get("rotation", 0)))
                output[-1].set_rotation((output[-1].rotation + rotation) % 360)
            return output.tobytes(garbage=4, deflate=True)
        finally:
            for source in opened.values():
                source.close()


def split(workspace: Workspace, key: str, groups: str):
    doc = workspace.document(key)
    groups = [g.strip() for g in str(groups).split(";") if g.strip()]
    if not groups:
        raise ValueError("Enter page groups separated by semicolons, such as 1-3; 4-6.")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        for i, group in enumerate(groups):
            pages = [p + 1 for p in page_range(group, len(doc.pages), repeat=True)]
            data = combine(workspace, [{"id": key, "pages": pages}])
            archive.writestr(f"{Path(doc.name).stem}_part_{i + 1:03d}.pdf", data)
    return buf.getvalue()


def rgb(value):
    value = str(value or "#000000").lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", value):
        raise ValueError("Choose a valid six-digit color.")
    return tuple(int(value[i:i + 2], 16) / 255 for i in (0, 2, 4))


def targets(item: dict, count: int):
    scope = item.get("scope", "current")
    if scope == "all":
        return list(range(count))
    if scope == "range":
        return page_range(item.get("range", ""), count)
    return page_range([int(item.get("page", 1))], count)


def corners(item: dict, page):
    values = item.get("corners")
    if not values:
        x, y, w, h = (float(item.get(k, default)) for k, default in [("x", .1), ("y", .1), ("w", .4), ("h", .1)])
        angle = math.radians(float(item.get("angle", 0)))
        origin = fitz.Point(x * page.rect.width, y * page.rect.height)
        u = fitz.Point(w * page.rect.width * math.cos(angle), w * page.rect.width * math.sin(angle))
        v = fitz.Point(-h * page.rect.height * math.sin(angle), h * page.rect.height * math.cos(angle))
        values = [[p.x / page.rect.width, p.y / page.rect.height] for p in [origin, origin + u, origin + u + v, origin + v]]
    if len(values) != 4 or any(len(p) != 2 for p in values):
        raise ValueError("An object has invalid corner coordinates.")
    result = [fitz.Point(float(p[0]) * page.rect.width, float(p[1]) * page.rect.height) for p in values]
    if any(not math.isfinite(p.x) or not math.isfinite(p.y) for p in result):
        raise ValueError("Object positions must be finite numbers.")
    return result


def text_css(font: str, fontsize: float, color: str, align: str):
    font_root = app_root() / "vendor" / "fonts"
    font_map = {"Sarabun": "Sarabun", "Sarabun Bold": "SarabunBold", "Helvetica": "sans-serif", "Times": "serif", "Courier": "monospace"}
    family = font_map.get(font, "Sarabun")
    css = "@font-face{font-family:Sarabun;src:url(Sarabun-Regular.ttf)}@font-face{font-family:SarabunBold;src:url(Sarabun-Bold.ttf)}"
    css += f"*{{font-family:{family};}}body{{margin:0;padding:0;color:{color};font-size:{fontsize}pt;line-height:1.25;text-align:{align if align in ['left','center','right'] else 'left'};white-space:pre-wrap;overflow-wrap:anywhere;}}"
    return css, fitz.Archive(str(font_root)) if font_root.exists() else None


def overlay_object(page, item: dict, workspace: Workspace):
    kind = item.get("type", "text")
    color = item.get("color", "#20365b")
    points = corners(item, page)
    box = fitz.Rect(min(p.x for p in points), min(p.y for p in points), max(p.x for p in points), max(p.y for p in points))
    if box.is_empty or box.width < .1 or box.height < .1:
        raise ValueError("An object is too small to export.")
    if kind in {"rect", "cover"}:
        page.draw_polyline(points + points[:1], color=None, fill=rgb(color), fill_opacity=float(item.get("opacity", 1)), width=0, overlay=True)
        return
    if kind == "pencil":
        values = item.get("points", [])
        if len(values) >= 2:
            path = [fitz.Point(float(p[0]) * page.rect.width, float(p[1]) * page.rect.height) for p in values[:20000]]
            page.draw_polyline(path, color=rgb(color), width=float(item.get("strokeWidth", 2)), lineCap=1, lineJoin=1, overlay=True)
        return
    width = max(1, math.hypot(points[1].x - points[0].x, points[1].y - points[0].y))
    height = max(1, math.hypot(points[3].x - points[0].x, points[3].y - points[0].y))
    angle = math.degrees(math.atan2(points[1].y - points[0].y, points[1].x - points[0].x))
    with fitz.open() as overlay:
        dest = overlay.new_page(width=width, height=height)
        if kind == "image":
            asset = workspace.assets.get(item.get("assetId", ""))
            if not asset:
                raise ValueError("An image is missing. Add it again, then save the profile.")
            dest.insert_image(dest.rect, filename=str(asset), keep_proportion=False)
        else:
            value = str(item.get("value", ""))
            fontsize = min(300, max(4, float(item.get("fontSize", 14))))
            css, archive = text_css(item.get("font", "Sarabun"), fontsize, color, item.get("align", "left"))
            digits = int(item.get("digits", 0) or 0)
            if digits:
                value = re.sub(r"\s", "", value)
                if len(value) > digits:
                    raise ValueError(f"Field {item.get('name', '')} has more characters than its {digits} digit boxes.")
                offsets = item.get("digitOffsets") or [i / digits for i in range(digits)]
                if len(offsets) != digits or offsets != sorted(offsets) or offsets[0] < 0 or offsets[-1] >= 1:
                    raise ValueError("Digit positions must be increasing fractions between 0 and 1, with one entry per digit box.")
                for i, char in enumerate(value):
                    cell = fitz.Rect(float(offsets[i]) * width, 0, float(offsets[i + 1] if i + 1 < digits else 1) * width, height)
                    spare, _ = dest.insert_htmlbox(cell, html.escape(char), css=css + "body{text-align:center}", archive=archive, scale_low=1)
                    if spare < 0:
                        raise ValueError("A digit box is too small for the selected font size.")
            else:
                spare, _ = dest.insert_htmlbox(dest.rect, html.escape(value).replace("\n", "<br>"), css=css, archive=archive, scale_low=1)
                if spare < 0:
                    raise ValueError(f"Text does not fit in {item.get('name', 'the selected box')}. Enlarge the box or reduce its font size.")
        page.show_pdf_page(box, overlay, rotate=-angle, keep_proportion=True, overlay=True)


def normalize_rotation(page):
    if not page.rotation:
        return
    # MuPDF's remove_rotation works from the MediaBox. Rebase that box to
    # the visible crop first; otherwise 90/270 expand the page and 180 can
    # displace content. CropBox uses top-down Y; MediaBox uses PDF Y.
    crop, media = page.cropbox, page.mediabox
    visible_pdf_box = fitz.Rect(crop.x0, media.y1 - crop.y1, crop.x1, media.y1 - crop.y0)
    page.set_mediabox(visible_pdf_box)
    page.remove_rotation()


def edit(workspace: Workspace, key: str, objects: list[dict]) -> bytes:
    if len(objects) > 5000:
        raise ValueError("This job exceeds the 5,000-object limit.")
    doc = workspace.document(key)
    # Normalize rotation in the output copy so visible-page coordinates have one contract.
    with fitz.open(doc.path) as output:
        for page in output:
            normalize_rotation(page)
        redactions = {}
        for item in objects:
            for index in targets(item, len(output)):
                page = output[index]
                if item.get("type") == "redact":
                    points = corners(item, page)
                    box = fitz.Rect(min(p.x for p in points), min(p.y for p in points), max(p.x for p in points), max(p.y for p in points)) & page.rect
                    if box.is_empty:
                        raise ValueError("A redaction box is outside the page.")
                    redactions.setdefault(index, []).append((box, item.get("color", "#000000")))
                else:
                    overlay_object(page, item, workspace)
        # Redact last: this removes both source content and any added content underneath.
        for index, boxes in redactions.items():
            page = output[index]
            for box, color in boxes:
                page.add_redact_annot(box, fill=rgb(color), cross_out=False)
            page.apply_redactions(images=2, graphics=2, text=0)
        return output.tobytes(garbage=4, deflate=True, clean=True)


def searchable(workspace: Workspace, key: str, pages: list[dict]):
    with fitz.open(workspace.document(key).path) as output:
        for record in pages:
            index = int(record["page"]) - 1
            if not 0 <= index < len(output):
                raise ValueError("Invalid OCR page.")
            page = output[index]
            normalize_rotation(page)
            fontfile = app_root() / "vendor/fonts/Sarabun-Regular.ttf"
            if not fontfile.exists():
                raise ValueError("The bundled OCR font is missing. Run the asset preparation step.")
            page.insert_font(fontname="SarabunOCR", fontfile=str(fontfile))
            for word in record.get("words", []):
                text = str(word.get("text", ""))
                if not text.strip():
                    continue
                x, y, w, h = (float(word[k]) for k in ("x", "y", "w", "h"))
                rect = fitz.Rect(x * page.rect.width, y * page.rect.height, (x + w) * page.rect.width, (y + h) * page.rect.height)
                fontsize = max(3, rect.height * .78)
                page.insert_text((rect.x0, rect.y0 + fontsize), text, fontname="SarabunOCR", fontsize=fontsize, render_mode=3, overlay=True)
        return output.tobytes(garbage=4, deflate=True)
