"""Build a self-contained Windows folder. No downloads or installs at launch."""
from pathlib import Path
import argparse
import importlib.util
import os
import subprocess
import shutil
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from pdfstudio import __version__
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output-dir", type=Path, default=root / "dist")
parser.add_argument("--reuse-runtime-from", type=Path, help="Reuse unchanged runtime files from an existing bundle for a development update")
args = parser.parse_args()
missing_modules = [name for name in ("webview", "pythonnet", "clr_loader", "markdown") if importlib.util.find_spec(name) is None]
if missing_modules:
    raise SystemExit("Desktop build dependencies are missing from this Python environment: " + ", ".join(missing_modules) + ". Install requirements-dev.txt or use the prepared desktop build environment.")
bundle = args.output_dir.resolve() / "PDFStudio"
required = [root / "web/dist/index.html", root / "web/dist/branding/pdfstudio.ico", root / "vendor/fonts/Sarabun-Regular.ttf", root / "vendor/libreoffice/program/soffice.com", root / "web/dist/vendor/ocr/lang/eng.traineddata.gz", root / "web/dist/vendor/ocr/lang/tha.traineddata.gz", root / "vendor/prerequisites/webview2.json"]
missing = [str(p.relative_to(root)) for p in required if not p.exists()]
if missing:
    raise SystemExit("Prepare the UI and offline assets first. Missing: " + ", ".join(missing))
command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--onedir", "--windowed", "--name", "PDFStudio", "--collect-all", "pymupdf"]
command += ["--collect-all", "webview", "--collect-all", "pythonnet", "--collect-all", "clr_loader"]
command += ["--collect-all", "markdown"]
command += ["--hidden-import", "webview.platforms.winforms", "--hidden-import", "webview.platforms.edgechromium", "--hidden-import", "webview.platforms.win32"]
command += ["--icon", str(root / "web/dist/branding/pdfstudio.ico")]
from PyInstaller.utils.win32.versioninfo import VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct
numbers = tuple(map(int, __version__.split("."))) + (0,)
info = VSVersionInfo(ffi=FixedFileInfo(filevers=numbers, prodvers=numbers, mask=0x3f, flags=0, OS=0x40004, fileType=1, subtype=0, date=(0, 0)), kids=[StringFileInfo([StringTable("040904B0", [StringStruct(key, value) for key, value in {"FileDescription": "PDF Studio", "FileVersion": __version__, "InternalName": "PDFStudio", "OriginalFilename": "PDFStudio.exe", "ProductName": "PDF Studio", "ProductVersion": __version__}.items()])]), VarFileInfo([VarStruct("Translation", [1033, 1200])])])
version_file = root / "build/windows-version-info.txt"
version_file.parent.mkdir(parents=True, exist_ok=True)
version_file.write_text(str(info), encoding="utf-8")
command += ["--version-file", str(version_file)]
command += ["--distpath", str(args.output_dir.resolve())]
# These optional analysis/CLI dependencies are not used by this application's engine.
for module in ("pandas", "pytest", "matplotlib", "IPython"):
    command += ["--exclude-module", module]
for source, target in [("web/dist", "web/dist"), ("vendor/fonts", "vendor/fonts"), ("vendor/libreoffice", "vendor/libreoffice"), ("vendor/licenses", "vendor/licenses"), ("vendor/prerequisites", "vendor/prerequisites")]:
    if args.reuse_runtime_from and source in {"vendor/fonts", "vendor/libreoffice"}:
        if not (args.reuse_runtime_from / "_internal" / source).is_dir():
            raise SystemExit("The existing bundle does not contain " + source)
        continue
    command += ["--add-data", str(root / source) + ";" + target]
command += [str(root / "run.py")]
subprocess.run(command, cwd=root, check=True)
if args.reuse_runtime_from:
    # NTFS hard links avoid repeatedly copying 1.6 GB of unchanged vendor files.
    # These are normal files, not path-dependent symlinks; either bundle can move.
    def link_or_copy(source, destination):
        try:
            os.link(source, destination)
        except OSError:
            shutil.copy2(source, destination)
        return destination

    for name in ("fonts", "libreoffice"):
        shutil.copytree(args.reuse_runtime_from / "_internal/vendor" / name, bundle / "_internal/vendor" / name, copy_function=link_or_copy)
shutil.copy2(root / "README.md", bundle / "README.md")
for name in ("assets-manifest.json", "libreoffice-runtime.json", "prerequisites/vc-redist.json", "prerequisites/webview2.json"):
    source = root / "vendor" / name
    target = bundle / "_internal/vendor" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
print("Built:", bundle / "PDFStudio.exe")
print("Keep the entire PDFStudio folder together. It includes local PDF, OCR, fonts and Office conversion runtimes.")
