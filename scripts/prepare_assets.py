"""Prepare redistributable local assets; never run from application startup.

Run after `npm install --prefix web`:
    python scripts/prepare_assets.py
Optional Windows Office conversion runtime:
    python scripts/prepare_assets.py --libreoffice
To rebuild copied browser resources without network:
    python scripts/prepare_assets.py --offline

`--resolve HOST:PORT:ADDRESS` is an optional curl DNS override for build machines
with unavailable DNS. TLS certificate/hostname validation remains enabled.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
import zipfile


ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor"
PUBLIC = ROOT / "web" / "public" / "vendor"
MODULES = ROOT / "web" / "node_modules"
LO_VERSION = "26.2.6"
LO_NAME = f"LibreOffice_{LO_VERSION}_Win_x86-64.msi"
LO_URL = f"https://download.documentfoundation.org/libreoffice/stable/{LO_VERSION}/win/x86_64/{LO_NAME}"
LO_SOURCE = f"https://download.documentfoundation.org/libreoffice/src/{LO_VERSION}/"
LO_SHA256 = "f9877032fd908beb9c0ddf06df4af5c2e85f419c42e14876c4cce5aae5fb2660"
FONT_REVISION = "88058c714073e72bb1b32baffc2d4ce9bc73944c"
TESSDATA_REVISION = "87416418657359cb625c412a48b6e1d6d41c29bd"
VC_URL = "https://download.visualstudio.microsoft.com/download/pr/ebdab8e5-1d7b-4d9f-a11b-cbb1720c3b12/843068991DAAA1F73AD9F6239BCE4D0F6A07A51F18C37EA2A867E9BECA71295C/VC_redist.x64.exe"
VC_SHA256 = "843068991daaa1f73ad9f6239bce4d0f6a07a51f18c37ea2a867e9beca71295c"
VC_VERSION = "14.51.36247.0"
VC_LICENSE_URL = "https://visualstudio.microsoft.com/wp-content/uploads/2025/10/Visual-C-V14-License-Redistributable_and_Runtime_ENU.docx"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def copy(source: Path, destination: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Missing {source}. Run npm install --prefix web first.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, destination, dirs_exist_ok=True)
    else:
        shutil.copy2(source, destination)


def download(url: str, target: Path, args: argparse.Namespace) -> None:
    if target.exists() and target.stat().st_size:
        return
    if args.offline:
        raise FileNotFoundError(f"Offline preparation needs the previously downloaded asset: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    print(f"Downloading {target.relative_to(ROOT)}", flush=True)
    curl = shutil.which("curl.exe") or shutil.which("curl")
    if curl and args.resolve:
        command = [curl, "--fail", "--location", "--retry", "2", "--connect-timeout", "20", "--max-time", "1200", "--silent", "--show-error"]
        if os.name == "nt":
            # Keep chain/hostname checks. Revocation endpoints may be unreachable
            # on an offline build host even while a permitted origin is available.
            command += ["--ssl-revoke-best-effort"]
        for override in args.resolve:
            command += ["--resolve", override]
        command += [url, "--output", str(partial)]
        subprocess.run(command, check=True)
    else:
        with urllib.request.urlopen(url, timeout=120) as response, partial.open("wb") as output:
            shutil.copyfileobj(response, output)
    if not partial.stat().st_size:
        raise RuntimeError(f"Downloaded empty asset: {url}")
    partial.replace(target)


def record(items: list[dict], path: Path, source: str, license_name: str) -> None:
    items.append({"path": path.relative_to(ROOT).as_posix(), "source": source, "sha256": sha256(path), "license": license_name})


def fonts_and_languages(args: argparse.Namespace, items: list[dict]) -> None:
    base = f"https://raw.githubusercontent.com/google/fonts/{FONT_REVISION}/ofl/sarabun/"
    for filename in ["Sarabun-Regular.ttf", "Sarabun-Bold.ttf", "OFL.txt"]:
        path = VENDOR / "fonts" / filename
        download(base + filename, path, args)
        copy(path, PUBLIC / "fonts" / filename)
        record(items, path, base + filename, "OFL-1.1")
    tessbase = f"https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/{TESSDATA_REVISION}/"
    license_path = VENDOR / "licenses" / "tessdata_fast-LICENSE.txt"
    download(tessbase + "LICENSE", license_path, args)
    copy(license_path, PUBLIC / "ocr" / "lang" / "LICENSE.txt")
    record(items, license_path, tessbase + "LICENSE", "Apache-2.0")
    for language in ["eng", "tha"]:
        source = VENDOR / "tessdata" / f"{language}.traineddata"
        download(tessbase + f"{language}.traineddata", source, args)
        target = PUBLIC / "ocr" / "lang" / f"{language}.traineddata.gz"
        target.parent.mkdir(parents=True, exist_ok=True)
        # Deterministic gzip of the original, unmodified official LSTM model.
        with source.open("rb") as input_file, target.open("wb") as output_file:
            with gzip.GzipFile(filename="", mode="wb", fileobj=output_file, mtime=0) as output_gzip:
                shutil.copyfileobj(input_file, output_gzip)
        record(items, source, tessbase + f"{language}.traineddata", "Apache-2.0")
        record(items, target, tessbase + f"{language}.traineddata", "Apache-2.0 (gzip packaging only)")


def npm_assets(items: list[dict]) -> None:
    pdfjs = MODULES / "pdfjs-dist"
    tess = MODULES / "tesseract.js"
    core = MODULES / "tesseract.js-core"
    for directory in ["cmaps", "standard_fonts", "wasm", "iccs"]:
        copy(pdfjs / directory, PUBLIC / "pdfjs" / directory)
    copy(pdfjs / "build" / "pdf.worker.min.mjs", PUBLIC / "pdfjs" / "pdf.worker.min.mjs")
    copy(tess / "dist" / "worker.min.js", PUBLIC / "ocr" / "worker.min.js")
    core_files = list(core.glob("*.wasm*"))
    if not core_files:
        raise FileNotFoundError(f"Missing Tesseract WASM resources in {core}")
    for source in core_files:
        copy(source, PUBLIC / "ocr" / "core" / source.name)
    # Retain the installed package's exact notices, including third-party font
    # licenses inside PDF.js standard_fonts/ and WebAssembly resource folders.
    for name, folder in [("pdfjs-dist", pdfjs), ("tesseract.js", tess), ("tesseract.js-core", core)]:
        package = json.loads((folder / "package.json").read_text(encoding="utf-8"))
        license_dir = VENDOR / "licenses" / name
        for source in folder.rglob("*"):
            if source.is_file() and source.name.upper().startswith(("LICENSE", "NOTICE", "COPYING", "COPYRIGHT")):
                copy(source, license_dir / source.relative_to(folder))
                if source.parent == folder:
                    copy(source, PUBLIC / ("pdfjs" if name == "pdfjs-dist" else "ocr") / f"{name}-{source.name}")
        items.append({"package": name, "version": package["version"], "license": package.get("license"), "source": package.get("repository"), "installed_from": "web/package-lock.json"})


def libreoffice(args: argparse.Namespace, items: list[dict]) -> None:
    if os.name != "nt":
        raise RuntimeError("The included LibreOffice preparation targets Windows x64 only.")
    installer = VENDOR / "downloads" / LO_NAME
    download(LO_URL, installer, args)
    checksum = installer.with_suffix(installer.suffix + ".sha256")
    download(LO_URL + ".sha256", checksum, args)
    expected = checksum.read_text(encoding="utf-8").strip().split()[0].lower()
    actual = sha256(installer)
    if len(expected) != 64 or actual != expected or actual != LO_SHA256:
        raise RuntimeError(f"LibreOffice SHA256 mismatch: expected {expected}, received {actual}")
    destination = VENDOR / "libreoffice"
    destination.mkdir(parents=True, exist_ok=True)
    executables = list(destination.rglob("soffice.com"))
    if not executables:
        # /a builds an administrative image inside this workspace. It does not
        # install/register LibreOffice or change an existing machine installation.
        log = VENDOR / "libreoffice-extract.log"
        command = ["msiexec.exe", "/a", str(installer), "/qn", f"TARGETDIR={destination}", "/l*v", str(log)]
        process = subprocess.run(command, check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if process.returncode not in (0, 3010):
            raise RuntimeError(f"LibreOffice administrative extraction returned {process.returncode}; see {log}")
        executables = list(destination.rglob("soffice.com"))
    if not executables:
        raise RuntimeError("LibreOffice administrative image has no soffice.com")
    executable = executables[0]
    font_dir = executable.parent.parent / "share" / "fonts" / "truetype"
    for filename in ["Sarabun-Regular.ttf", "Sarabun-Bold.ttf", "OFL.txt"]:
        copy(VENDOR / "fonts" / filename, font_dir / filename)
    profile = (ROOT / ".runtime" / "libreoffice-build-profile").as_uri()
    result = subprocess.run([str(executable), f"-env:UserInstallation={profile}", "--headless", "--version"], capture_output=True, text=True, timeout=60, check=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    print(result.stdout.strip(), flush=True)
    descriptor = {"version": LO_VERSION, "path": executable.relative_to(ROOT).as_posix(), "source": LO_URL, "source_code": LO_SOURCE, "sha256": actual, "preparation": "Windows MSI administrative extraction, no machine installation", "version_output": result.stdout.strip(), "license": "See included LibreOffice LICENSE/NOTICE files; MPL-2.0 and component licenses"}
    (VENDOR / "libreoffice-runtime.json").write_text(json.dumps(descriptor, indent=2) + "\n", encoding="utf-8")
    items.append(descriptor)


def vc_redist(args: argparse.Namespace, items: list[dict]) -> None:
    package = VENDOR / "prerequisites" / "VC_redist.x64.exe"
    download(VC_URL, package, args)
    actual = sha256(package)
    if actual != VC_SHA256:
        raise RuntimeError(f"Microsoft prerequisite SHA256 mismatch: {actual}")
    license_doc = VENDOR / "licenses" / "Microsoft-VC-v14-License.docx"
    download(VC_LICENSE_URL, license_doc, args)
    with zipfile.ZipFile(license_doc) as archive:
        document = ET.fromstring(archive.read("word/document.xml"))
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = ["".join(node.itertext()) for node in document.findall(".//w:p", namespace)]
    (VENDOR / "licenses" / "Microsoft-VC-v14-License.txt").write_text("\n".join(paragraphs) + "\n", encoding="utf-8")
    descriptor = {"path": package.relative_to(ROOT).as_posix(), "version": VC_VERSION, "source": VC_URL,
                  "official_permalink": "https://aka.ms/vc14/vc_redist.x64.exe", "sha256": actual,
                  "license_source": VC_LICENSE_URL, "license": "Microsoft Software License Terms; included in vendor/licenses",
                  "preparation": "Downloaded only; never executed or installed"}
    (VENDOR / "prerequisites" / "vc-redist.json").write_text(json.dumps(descriptor, indent=2) + "\n", encoding="utf-8")
    items.append(descriptor)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Never access the network; require existing downloaded assets")
    parser.add_argument("--libreoffice", action="store_true", help="Download and administratively extract the Windows x64 LibreOffice runtime")
    parser.add_argument("--vc-redist", action="store_true", help="Bundle the official Microsoft x64 CRT prerequisite without executing or installing it")
    parser.add_argument("--resolve", action="append", default=[], help="Optional curl DNS override HOST:PORT:ADDRESS")
    parser.add_argument("--downloads-only", action="store_true", help="Prepare fonts/OCR models before npm installation finishes")
    args = parser.parse_args()
    items: list[dict] = []
    fonts_and_languages(args, items)
    if not args.downloads_only:
        npm_assets(items)
    if args.libreoffice:
        libreoffice(args, items)
    elif (VENDOR / "libreoffice-runtime.json").exists():
        items.append(json.loads((VENDOR / "libreoffice-runtime.json").read_text(encoding="utf-8")))
    if args.vc_redist:
        vc_redist(args, items)
    elif (VENDOR / "prerequisites" / "vc-redist.json").exists():
        items.append(json.loads((VENDOR / "prerequisites" / "vc-redist.json").read_text(encoding="utf-8")))
    VENDOR.mkdir(parents=True, exist_ok=True)
    manifest = {"purpose": "Build-time asset acquisition; runtime uses local paths only", "assets": items}
    (VENDOR / "assets-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("Local PDF.js, OCR, and font assets prepared." if not args.downloads_only else "Fonts and OCR language models prepared.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Asset preparation failed: {error}", file=sys.stderr)
        sys.exit(1)
