"""Prepare exact-size logo assets at build time; the app never resizes the master."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PNG_SIZES = (16, 20, 24, 32, 40, 48, 64, 72, 80, 96, 128, 144, 180, 192, 256, 512)
WINDOWS_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def branding_files(source: Path) -> tuple[dict[str, bytes], str]:
    original = source.read_bytes()
    revision = hashlib.sha256(original).hexdigest()[:12]
    with Image.open(io.BytesIO(original)) as master:
        if master.width != master.height or master.width < 512:
            raise ValueError("Use a square logo master of at least 512 pixels.")
        master = master.convert("RGBA")
        frames = {size: master.resize((size, size), Image.Resampling.LANCZOS) for size in PNG_SIZES}
    files = {}
    for size, frame in frames.items():
        output = io.BytesIO()
        frame.save(output, "PNG", optimize=True)
        files[f"branding/pdfstudio-{size}.png"] = output.getvalue()
    for name, sizes in (("pdfstudio.ico", WINDOWS_SIZES), ("favicon.ico", (16, 32, 48))):
        output = io.BytesIO()
        frames[max(sizes)].save(output, "ICO", sizes=[(n, n) for n in sizes], append_images=[frames[n] for n in sizes])
        files["branding/" + name] = output.getvalue()
    files["favicon.ico"] = files["branding/favicon.ico"]
    manifest = dict(id="/", name="PDF Studio", short_name="PDF Studio", start_url="/", scope="/", display="standalone", background_color="#eef1f5", theme_color="#20365b", icons=[dict(src=f"/branding/pdfstudio-{size}.png?v={revision}", sizes=f"{size}x{size}", type="image/png", purpose="any") for size in (192, 512)])
    files["site.webmanifest"] = (json.dumps(manifest, indent=2) + "\n").encode()
    record = dict(source_sha256=hashlib.sha256(original).hexdigest(), source_bytes=len(original), png_sizes=PNG_SIZES, windows_sizes=WINDOWS_SIZES, files={name: len(data) for name, data in files.items()})
    files["branding/assets.json"] = (json.dumps(record, indent=2) + "\n").encode()
    return files, revision


def icon_links(html: str, revision: str) -> str:
    block = f'''<!-- branding:start -->
<link rel="icon" href="/branding/favicon.ico?v={revision}" sizes="16x16 32x32 48x48">
<link rel="icon" type="image/png" sizes="16x16" href="/branding/pdfstudio-16.png?v={revision}">
<link rel="icon" type="image/png" sizes="32x32" href="/branding/pdfstudio-32.png?v={revision}">
<link rel="icon" type="image/png" sizes="48x48" href="/branding/pdfstudio-48.png?v={revision}">
<link rel="apple-touch-icon" sizes="180x180" href="/branding/pdfstudio-180.png?v={revision}">
<link rel="manifest" href="/site.webmanifest?v={revision}">
<meta name="theme-color" content="#20365b">
<!-- branding:end -->'''
    if "<!-- branding:start -->" in html:
        return re.sub(r"<!-- branding:start -->[\s\S]*?<!-- branding:end -->", lambda _: block, html)
    return html.replace("</head>", block + "</head>")


def prepare(root: Path = ROOT, *, check=False):
    source = root / "assets/branding/pdfstudio-master.png"
    files, revision = branding_files(source)
    expected = {root / "web/public" / name: data for name, data in files.items()}
    index = root / "web/index.html"
    expected[index] = icon_links(index.read_text(encoding="utf-8"), revision).encode()
    for path, data in expected.items():
        if path.exists() and path.read_bytes() == data:
            continue
        if check:
            raise ValueError(f"Branding assets need rebuilding: {path.relative_to(root)}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return files


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    files = prepare(check=args.check)
    print(f"Branding {'verified' if args.check else 'prepared'}: {len(files)} assets; master stays outside the runtime bundle.")
