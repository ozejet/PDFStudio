"""Local text detection and static HTML preparation. No source content is executed."""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
import html
from html.parser import HTMLParser
import re
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urlsplit

MAX_TEXT_BYTES = 8 * 1024 * 1024
AUTO_PDF_BYTES = 512 * 1024
OFFICE_EXTENSIONS = {".doc", ".docx", ".ppt", ".pptx", ".odt", ".odp", ".rtf"}
HTML_EXTENSIONS = {".html", ".htm"}
MARKDOWN_EXTENSIONS = {".md", ".markdown"}
TEXT_EXTENSIONS = {".txt", ".text", ".log", ".vtt", ".srt", ".csv", ".tsv", ".json", ".xml", ".yaml", ".yml", ".ini", ".cfg", ".conf", ".toml", ".sql", ".css", ".py", ".js", ".ts", ".jsx", ".tsx", ".c", ".h", ".cpp", ".sh", ".bat", ".cmd", ".ps1", ".rst"}
BINARY_EXTENSIONS = {".exe", ".dll", ".com", ".msi", ".zip", ".7z", ".rar", ".mp3", ".mp4", ".avi", ".woff", ".woff2", ".ttf", ".xlsx", ".xls"}
ENCODINGS = {"utf-8", "utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "cp1252", "cp874"}
DEFAULT_LAYOUT = dict(paper="A4", orientation="portrait", fontSize=11, wrap=True)


class TextConfirmationRequired(ValueError):
    code = "open-as-text"


def readable(text):
    return not text or ("\x00" not in text and sum(c.isprintable() or c in "\n\r\t\f\x1b" or unicodedata.category(c) == "Cf" for c in text) / len(text) >= .98)


def decode_text(data: bytes, *, force=False, encoding=""):
    if len(data) > MAX_TEXT_BYTES:
        raise ValueError("Use a text file below 8 MB. Split larger logs into smaller files first.")
    if encoding and encoding not in ENCODINGS:
        raise ValueError("Choose a supported text encoding.")
    candidates = [encoding] if encoding else (["utf-16"] if data.startswith((b"\xff\xfe", b"\xfe\xff")) else ["utf-8-sig"])
    if not encoding and not data.startswith((b"\xff\xfe", b"\xfe\xff")) and len(data) >= 4 and b"\0" in data:
        if data[1::2].count(0) / len(data[1::2]) > .3:
            candidates.insert(0, "utf-16-le")
        elif data[0::2].count(0) / len(data[0::2]) > .3:
            candidates.insert(0, "utf-16-be")
    for candidate in candidates:
        try:
            value = data.decode(candidate)
            if readable(value):
                return value.replace("\r\n", "\n").replace("\r", "\n"), candidate
        except UnicodeError:
            pass
    if encoding:
        raise TextConfirmationRequired("The file could not be read with that encoding. Try another encoding; the original file is preserved.")
    try:
        legacy = data.decode("cp1252")
        if readable(legacy):
            if force:
                return legacy.replace("\r\n", "\n").replace("\r", "\n"), "cp1252"
            raise TextConfirmationRequired("This may be text in another encoding. Choose Open as text and an encoding to inspect it.")
    except UnicodeError:
        pass
    raise ValueError("This file is binary or could not be read as text. Its original file is preserved.")


def layout_options(options=None):
    result = {**DEFAULT_LAYOUT, **(options or {})}
    if result["paper"] not in {"A4", "Letter", "Legal"} or result["orientation"] not in {"portrait", "landscape"}:
        raise ValueError("Choose A4, Letter or Legal and portrait or landscape.")
    try:
        result["fontSize"] = float(result["fontSize"])
    except (TypeError, ValueError):
        raise ValueError("Choose a font size between 8 and 24.") from None
    if not 8 <= result["fontSize"] <= 24 or not isinstance(result["wrap"], bool):
        raise ValueError("Choose a font size between 8 and 24 and a valid wrapping option.")
    return {key: result[key] for key in DEFAULT_LAYOUT}


class StaticHTML(HTMLParser):
    """Keep static document structure; inline only explicitly supplied companion assets."""
    DROP = {"script", "iframe", "object", "embed", "applet", "noscript", "template", "math", "animate", "animatemotion", "animatetransform", "set"}
    SVG_TAGS = {name.lower(): name for name in "linearGradient radialGradient clipPath textPath foreignObject feBlend feColorMatrix feComponentTransfer feComposite feConvolveMatrix feDiffuseLighting feDisplacementMap feDistantLight feDropShadow feFlood feFuncA feFuncB feFuncG feFuncR feGaussianBlur feImage feMerge feMergeNode feMorphology feOffset fePointLight feSpecularLighting feSpotLight feTile feTurbulence".split()}
    VOID = {"area", "br", "col", "hr", "img", "input", "wbr", "source"}
    def __init__(self, assets=None, capture=None):
        super().__init__(convert_charrefs=True)
        self.assets = assets or {}
        self.capture = capture if capture is not None else {}
        self.parts, self.notes = [], set()
        self.skipped = []
        self.in_style = False
        self.svg_depth = 0
        self.image_bytes = 0

    def bounded_image(self, value):
        self.image_bytes += len(value.encode("utf-8"))
        if self.image_bytes > 32 * 1024 * 1024:
            self.notes.add("Some embedded images/styles exceeded the 32 MB preview budget. The original files remain available.")
            return ""
        return value

    def resource(self, value, *, css=False):
        value = html.unescape(value).strip()
        if not css and re.match(r"^data:image/(png|jpeg|gif|webp);base64,[a-z0-9+/=\s]+$", value, re.I):
            return self.bounded_image(value)
        try:
            url = urlsplit(value)
        except ValueError:
            self.notes.add("An image or stylesheet link could not be read.")
            return ""
        if not url.scheme and not url.netloc:
            key = Path(unquote(url.path).replace("\\", "/")).name.casefold()
            source = self.assets.get(key)
            if source:
                if isinstance(source, tuple):
                    if (css and source[0] == "css") or (not css and source[0] == "image"):
                        self.capture[key] = source
                        return source[1] if css else self.bounded_image(source[1])
                    return ""
                path = Path(source)
                if self.image_bytes + path.stat().st_size * 4 / 3 > 32 * 1024 * 1024:
                    self.notes.add("Some embedded images/styles exceeded the 32 MB preview budget. The original files remain available.")
                    return ""
                if css and path.suffix.lower() == ".css" and path.stat().st_size < 1024 * 1024:
                    result = self.bounded_image(decode_text(path.read_bytes())[0])
                    self.capture[key] = ("css", result)
                    return result
                if not css and path.suffix.lower() in {".png", ".jpg", ".jpeg"} and path.stat().st_size < 16 * 1024 * 1024:
                    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
                    result = self.bounded_image("data:" + mime + ";base64," + base64.b64encode(path.read_bytes()).decode("ascii"))
                    self.capture[key] = ("image", result)
                    return result
        self.notes.add("Some linked images or styles were unavailable. Include local companion files with the HTML; external resources stay offline.")
        return ""

    def css(self, text):
        text = re.sub(r"@import\s+[^;]+;?", "", text, flags=re.I)
        text = re.sub(r"@font-face\s*\{[^}]*\}", "", text, flags=re.I)
        def image(match):
            raw = match[1].strip(" \t\r\n\"'")
            value = raw if re.fullmatch(r"#[\w:.-]+", raw) else self.resource(raw)
            return 'url("' + value + '")' if value else "none"
        # CSS escapes could hide file/URL references from a simple matcher.
        text = re.sub(r"\\(?:[0-9a-fA-F]{1,6}\s?|.)", "", text)
        return re.sub(r"url\s*\(\s*(.*?)\s*\)", image, text, flags=re.I | re.S)

    def handle_starttag(self, tag, attrs):
        if self.skipped:
            if tag in self.DROP and tag not in {"embed"}:
                self.skipped.append(tag)
            return
        if tag in self.DROP:
            self.notes.add("This reader displays static HTML. Scripts and embedded applications are disabled.")
            if tag != "embed":
                self.skipped.append(tag)
            return
        values = dict(attrs)
        if tag in {"meta", "base"}:
            return
        if tag == "link":
            if "stylesheet" in values.get("rel", "").lower():
                css = self.resource(values.get("href", ""), css=True)
                if css:
                    self.parts.append("<style>" + self.css(css).replace("</", "<\\/") + "</style>")
            return
        if tag == "svg":
            self.svg_depth += 1
        allowed = []
        for name, value in attrs:
            value = value or ""
            if name.startswith("on") or name in {"srcdoc", "action", "formaction", "target", "srcset", "poster", "background", "ping", "autofocus", "autoplay"}:
                continue
            if name == "style" or re.search(r"url\s*\(", value, re.I):
                value = self.css(value)
            elif name == "src":
                value = self.resource(value) if tag == "img" else ""
            elif name in {"href", "xlink:href"}:
                value = self.resource(value) if tag in {"image", "feimage"} else value if value.startswith("#") else ""
            if value:
                original = re.search(r"(?<![\w:-])(" + re.escape(name) + r")\s*=", self.get_starttag_text(), re.I) if self.svg_depth else None
                allowed.append((original[1] if original else name) + '="' + html.escape(value, quote=True) + '"')
        output_tag = self.SVG_TAGS.get(tag, tag) if self.svg_depth else tag
        self.parts.append("<" + output_tag + (" " + " ".join(allowed) if allowed else "") + ">")
        self.in_style = tag == "style"

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if self.skipped:
            if tag == self.skipped[-1]:
                self.skipped.pop()
            return
        if tag not in self.DROP | self.VOID | {"meta", "base", "link"}:
            self.parts.append("</" + (self.SVG_TAGS.get(tag, tag) if self.svg_depth else tag) + ">")
        if tag == "svg":
            self.svg_depth = max(0, self.svg_depth - 1)
        self.in_style = False

    def handle_data(self, data):
        if not self.skipped:
            self.parts.append(self.css(data).replace("</", "<\\/") if self.in_style else html.escape(data))


def sanitize_html(text, assets=None, capture=None):
    parser = StaticHTML(assets, capture)
    parser.feed(text)
    parser.close()
    return "".join(parser.parts), sorted(parser.notes)


def formatted_html(text, kind, assets=None, capture=None):
    if kind == "markdown":
        from markdown import markdown
        value = markdown(text, extensions=["tables", "fenced_code", "sane_lists"])
    elif kind == "html":
        value = text
    else:
        value = '<pre class="plain-text">' + html.escape(text.expandtabs(4)) + "</pre>"
    return sanitize_html(value, assets, capture)


@dataclass
class Source:
    text: str
    kind: str
    encoding: str
    html: str
    fallback: bool = False
    warnings: list[str] = field(default_factory=list)
    layout: dict = field(default_factory=lambda: dict(DEFAULT_LAYOUT))
    assets: dict = field(default_factory=dict)


def read_source(data, name, *, force=False, encoding="", assets=None):
    suffix = Path(name).suffix.lower()
    if suffix in OFFICE_EXTENSIONS | {".pdf", ".png", ".jpg", ".jpeg"}:
        return None
    if suffix in BINARY_EXTENSIONS or data.startswith((b"MZ", b"PK\x03\x04", b"7z\xbc\xaf")):
        raise ValueError("This file type is not supported. Other files in the batch can still open.")
    text, detected = decode_text(data, force=force, encoding=encoding)
    kind = "text" if force else "html" if suffix in HTML_EXTENSIONS else "markdown" if suffix in MARKDOWN_EXTENSIONS else "text"
    captured = {}
    value, notes = formatted_html(text, kind, assets, captured)
    return Source(text, kind, detected, value, suffix not in HTML_EXTENSIONS | MARKDOWN_EXTENSIONS | TEXT_EXTENSIONS, notes, assets=captured)


def reader_html(content):
    policy = "default-src 'none'; style-src 'unsafe-inline'; img-src data:; font-src data:; base-uri 'none'; form-action 'none'; frame-src 'none'; connect-src 'none'"
    return '<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="' + html.escape(policy, quote=True) + '"><style>body{margin:24px;font:16px/1.65 sans-serif;overflow-wrap:anywhere}img{max-width:100%;height:auto}table{border-collapse:collapse;max-width:100%}td,th{border:1px solid #aaa;padding:6px}pre{white-space:pre-wrap;tab-size:4}</style></head><body>' + content + "</body></html>"
