"""Build a self-contained Apple Silicon PDFStudio.app and local-use DMG."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import platform
import shutil
import subprocess
import sys
import tempfile

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pdfstudio import __version__


def run(command, **options):
    print("+", " ".join(map(str, command)), flush=True)
    return subprocess.run([str(item) for item in command], check=True, **options)


def sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def make_icon(destination: Path):
    with Image.open(ROOT / "assets/branding/pdfstudio-master.png") as source:
        master = source.convert("RGBA").resize((1024, 1024), Image.Resampling.LANCZOS)
        master.save(destination, format="ICNS")


def copy_python_licenses(destination: Path):
    packages = [
        "Flask", "PyMuPDF", "Pillow", "openpyxl", "pypdf", "Markdown",
        "blinker", "click", "itsdangerous", "Jinja2", "MarkupSafe", "Werkzeug", "et-xmlfile",
    ]
    records = []
    for requested in packages:
        distribution = importlib.metadata.distribution(requested)
        metadata = distribution.metadata
        name = metadata.get("Name", requested)
        record = {
            "name": name,
            "version": distribution.version,
            "license": metadata.get("License-Expression") or metadata.get("License") or "See included metadata/upstream",
            "homepage": metadata.get("Project-URL") or metadata.get("Home-page") or "",
        }
        target = destination / name.replace("/", "__")
        copied = []
        for relative in distribution.files or []:
            if relative.name.upper().startswith(("LICENSE", "COPYING", "NOTICE", "COPYRIGHT")):
                source = Path(distribution.locate_file(relative))
                if source.is_file():
                    target.mkdir(parents=True, exist_ok=True)
                    output = target / relative.name
                    if output.exists():
                        output = target / (relative.parent.name + "-" + relative.name)
                    shutil.copy2(source, output)
                    copied.append(output.name)
        record["files"] = sorted(set(copied))
        records.append(record)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "packages.json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    for parent in [Path(sys.base_prefix).resolve(), *Path(sys.base_prefix).resolve().parents]:
        license_file = parent / "LICENSE"
        if license_file.is_file() and "python@" in str(license_file):
            shutil.copy2(license_file, destination / "Python-LICENSE")
            break


def copy_npm_licenses(destination: Path):
    lock = json.loads((ROOT / "web/package-lock.json").read_text(encoding="utf-8"))
    records = []
    for package_path, locked in sorted(lock.get("packages", {}).items()):
        if not package_path.startswith("node_modules/"):
            continue
        source = ROOT / "web" / package_path
        package_json = source / "package.json"
        if not package_json.is_file():
            continue
        package = json.loads(package_json.read_text(encoding="utf-8"))
        name = package.get("name") or package_path.removeprefix("node_modules/")
        target = destination / name.replace("/", "__")
        copied = []
        for candidate in source.iterdir():
            if candidate.is_file() and candidate.name.upper().startswith(("LICENSE", "COPYING", "NOTICE", "COPYRIGHT")):
                target.mkdir(parents=True, exist_ok=True)
                shutil.copy2(candidate, target / candidate.name)
                copied.append(candidate.name)
        records.append({"name": name, "version": package.get("version", locked.get("version", "")), "license": package.get("license", "See upstream"), "files": sorted(copied)})
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "packages.json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")


def rewrite_bundle_manifest(runtime: Path, resources: Path):
    internal = runtime / "_internal"
    source_manifest = ROOT / "vendor/assets-manifest.json"
    original = json.loads(source_manifest.read_text(encoding="utf-8"))
    bundled, excluded = [], []
    for item in original.get("assets", []):
        record = dict(item)
        path = record.get("path")
        if path:
            relative = Path(path)
            if relative.parts[:2] == ("web", "public"):
                target = internal / "web/dist" / Path(*relative.parts[2:])
            else:
                target = internal / relative
            if target.is_file():
                record["sha256"] = sha256(target)
                record["bundled_path"] = target.relative_to(runtime).as_posix()
                bundled.append(record)
            else:
                excluded.append({"path": path, "reason": "Not part of the macOS runtime"})
        elif record.get("package") in {"pdfjs-dist", "tesseract.js", "tesseract.js-core"}:
            record["bundled_path"] = "_internal/web/dist/vendor"
            bundled.append(record)
    manifest = {
        "purpose": "Exact build-time assets included in this PDFStudio macOS application",
        "source_manifest": source_manifest.name,
        "application_version": __version__,
        "assets": bundled,
        "excluded": excluded,
    }
    data = (json.dumps(manifest, indent=2) + "\n").encode()
    packaged_manifest = internal / "vendor/assets-manifest.json"
    packaged_manifest.parent.mkdir(parents=True, exist_ok=True)
    packaged_manifest.write_bytes(data)
    (resources / "BUNDLE-ASSETS.json").write_bytes(data)


def write_info_plist(path: Path):
    revision = int(__version__.split(".")[-1])
    info = {
        "CFBundleDevelopmentRegion": "en",
        "CFBundleDisplayName": "PDF Studio",
        "CFBundleExecutable": "PDFStudio",
        "CFBundleIconFile": "PDFStudio",
        "CFBundleIdentifier": "io.pdfstudio.local",
        "CFBundleInfoDictionaryVersion": "6.0",
        "CFBundleName": "PDF Studio",
        "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": __version__,
        "CFBundleVersion": str(revision),
        "LSApplicationCategoryType": "public.app-category.productivity",
        "LSArchitecturePriority": ["arm64"],
        "LSMinimumSystemVersion": "13.0",
        "LSMultipleInstancesProhibited": True,
        "NSHighResolutionCapable": True,
        "NSHumanReadableCopyright": "PDFStudio adaptation published by upstream permission; third-party licenses apply",
        "NSSupportsAutomaticGraphicsSwitching": True,
    }
    with path.open("wb") as stream:
        plistlib.dump(info, stream, sort_keys=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist/macos")
    args = parser.parse_args()
    if sys.platform != "darwin" or platform.machine() != "arm64":
        raise SystemExit("This builder creates an Apple Silicon macOS bundle and must run on arm64 macOS.")
    if importlib.util.find_spec("PyInstaller") is None:
        raise SystemExit("PyInstaller is missing. Install the pinned requirements-dev dependency first.")

    required = [
        ROOT / "web/dist/index.html",
        ROOT / "web/dist/vendor/ocr/lang/eng.traineddata.gz",
        ROOT / "web/dist/vendor/ocr/lang/tha.traineddata.gz",
        ROOT / "vendor/fonts/Sarabun-Regular.ttf",
        ROOT / "assets/branding/pdfstudio-master.png",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("Prepare and build the browser assets first. Missing: " + ", ".join(missing))

    output = args.output_dir.resolve()
    build = ROOT / "build/macos"
    runtime_dist = build / "runtime-dist"
    if build.exists():
        shutil.rmtree(build)
    build.mkdir(parents=True)
    output.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--noupx",
        "--name", "PDFStudioBackend", "--target-arch", "arm64",
        "--distpath", runtime_dist, "--workpath", build / "pyinstaller", "--specpath", build / "spec",
        "--collect-all", "pymupdf", "--collect-all", "markdown",
    ]
    for module in ("tkinter", "_tkinter", "pytest", "PyInstaller", "pandas", "matplotlib", "IPython"):
        command += ["--exclude-module", module]
    for source, target in [
        (ROOT / "web/dist", "web/dist"),
        (ROOT / "vendor/fonts", "vendor/fonts"),
        (ROOT / "vendor/licenses", "vendor/licenses"),
        (ROOT / "vendor/README.md", "vendor"),
        (ROOT / "vendor/assets-manifest.json", "vendor"),
        (ROOT / "packaging/THIRD_PARTY_NOTICES.md", "."),
    ]:
        command += ["--add-data", str(source) + os.pathsep + target]
    command += [ROOT / "run.py"]
    build_environment = dict(os.environ)
    build_environment["PYINSTALLER_CONFIG_DIR"] = str(build / "pyinstaller-cache")
    run(command, cwd=ROOT, env=build_environment)

    old_app = output / "PDFStudio.app"
    if old_app.exists():
        shutil.rmtree(old_app)
    payload = build / "PDFStudioPayload"
    contents = payload / "Contents"
    macos = contents / "MacOS"
    resources = contents / "Resources"
    macos.mkdir(parents=True)
    resources.mkdir(parents=True)
    write_info_plist(contents / "Info.plist")
    make_icon(resources / "PDFStudio.icns")
    swift_environment = dict(os.environ)
    swift_environment["CLANG_MODULE_CACHE_PATH"] = str(build / "clang-cache")
    swift_environment["SWIFT_MODULECACHE_PATH"] = str(build / "swift-cache")
    run([
        "/usr/bin/swiftc", "-O", "-target", "arm64-apple-macos13.0",
        "-framework", "AppKit", "-o", macos / "PDFStudio", ROOT / "packaging/macos/PDFStudioLauncher.swift",
    ], env=swift_environment)

    runtime = resources / "runtime/PDFStudioBackend"
    shutil.copytree(runtime_dist / "PDFStudioBackend", runtime, symlinks=True)
    save_panel_contents = runtime / "PDFStudioSavePanel.app/Contents"
    save_panel_macos = save_panel_contents / "MacOS"
    save_panel_macos.mkdir(parents=True)
    with (save_panel_contents / "Info.plist").open("wb") as stream:
        plistlib.dump({
            "CFBundleDevelopmentRegion": "en",
            "CFBundleDisplayName": "PDF Studio Save Panel",
            "CFBundleExecutable": "PDFStudioSavePanel",
            "CFBundleIdentifier": "io.pdfstudio.local.savepanel",
            "CFBundleInfoDictionaryVersion": "6.0",
            "CFBundleName": "PDF Studio Save Panel",
            "CFBundlePackageType": "APPL",
            "CFBundleShortVersionString": __version__,
            "CFBundleVersion": str(int(__version__.split(".")[-1])),
            "LSMinimumSystemVersion": "13.0",
            "NSHighResolutionCapable": True,
        }, stream, sort_keys=True)
    run([
        "/usr/bin/swiftc", "-O", "-target", "arm64-apple-macos13.0",
        "-framework", "AppKit", "-o", save_panel_macos / "PDFStudioSavePanel",
        ROOT / "packaging/macos/PDFStudioSavePanel.swift",
    ], env=swift_environment)
    feedback = runtime / "_internal/web/dist/feedback-form.json"
    feedback.write_text('{"url":""}\n', encoding="utf-8")
    shutil.copy2(ROOT / "packaging/THIRD_PARTY_NOTICES.md", resources / "THIRD_PARTY_NOTICES.md")
    shutil.copy2(ROOT / "packaging/CORRESPONDING_SOURCE.md", resources / "CORRESPONDING_SOURCE.md")
    shutil.copy2(ROOT / "docs/macos/UPSTREAM_PERMISSION.md", resources / "UPSTREAM_PERMISSION.md")
    shutil.copy2(ROOT / "LICENSE", resources / "LICENSE-AGPL-3.0.txt")
    shutil.copy2(ROOT / "NOTICE.md", resources / "NOTICE.md")
    shutil.copy2(ROOT / "README.md", resources / "UPSTREAM-README.md")
    copy_python_licenses(resources / "licenses/python")
    copy_npm_licenses(resources / "licenses/npm")
    if (ROOT / "vendor/licenses").is_dir():
        shutil.copytree(ROOT / "vendor/licenses", resources / "licenses/vendor", dirs_exist_ok=True)
    shutil.copy2(ROOT / "packaging/licenses/AGPL-3.0.txt", resources / "licenses/PyMuPDF-AGPL-3.0.txt")
    rewrite_bundle_manifest(runtime, resources)
    (resources / "Install and Use.txt").write_text(
        "PDF Studio for Apple Silicon (experimental pre-release)\n\n"
        "Drag PDFStudio.app to Applications, then open it. The app starts a local-only engine "
        "and opens Safari. Use Quit PDF Studio in the web interface or Quit from the Dock/menu "
        "to stop the engine. Closing only the Safari tab does not stop the app.\n\n"
        "This build is ad-hoc signed and not Apple notarized. The upstream owner authorized this macOS "
        "adaptation under GNU AGPLv3 at https://github.com/BerlinoPotato/PDFStudio/issues/1#issuecomment-6397084771. "
        "Matching source and third-party notices are linked in CORRESPONDING_SOURCE.md. Office conversion "
        "is not included. Keep original documents and verify exported PDFs.\n",
        encoding="utf-8",
    )

    dmg = output / f"PDFStudio-{__version__}-arm64.dmg"
    archive = output / f"PDFStudio-{__version__}-arm64.app.zip"
    with tempfile.TemporaryDirectory(prefix="pdfstudio-macos-build-") as temporary:
        temporary_root = Path(temporary)
        app = temporary_root / "PDFStudio.app"
        # File Provider workspaces attach Finder metadata to .app directories.
        # Assemble without the suffix, then make a metadata-clean signing copy.
        run(["/usr/bin/ditto", "--norsrc", "--noextattr", payload, app])
        save_panel_app = app / "Contents/Resources/runtime/PDFStudioBackend/PDFStudioSavePanel.app"
        run(["/usr/bin/codesign", "--force", "--sign", "-", "--timestamp=none", save_panel_app])
        run(["/usr/bin/codesign", "--verify", "--deep", "--strict", "--verbose=2", save_panel_app])
        run(["/usr/bin/codesign", "--force", "--deep", "--sign", "-", "--timestamp=none", app])
        run(["/usr/bin/codesign", "--verify", "--deep", "--strict", "--verbose=2", app])
        if archive.exists():
            archive.unlink()
        run(["/usr/bin/ditto", "-c", "-k", "--norsrc", "--noextattr", "--keepParent", app, archive])
        stage = temporary_root / "dmg"
        stage.mkdir()
        run(["/usr/bin/ditto", "--norsrc", "--noextattr", app, stage / app.name])
        run(["/usr/bin/codesign", "--verify", "--deep", "--strict", "--verbose=2", stage / app.name])
        os.symlink("/Applications", stage / "Applications")
        shutil.copy2(resources / "Install and Use.txt", stage / "Install and Use.txt")
        if dmg.exists():
            dmg.unlink()
        run(["/usr/bin/hdiutil", "create", "-volname", "PDF Studio", "-srcfolder", stage, "-ov", "-format", "UDZO", dmg])

    print("Built app archive:", archive)
    print("Built DMG:", dmg)
    print("DMG SHA256:", sha256(dmg))


if __name__ == "__main__":
    main()
