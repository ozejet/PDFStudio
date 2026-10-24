"""Prepare the signed offline WebView2 prerequisite and desktop license notices."""
from __future__ import annotations

import argparse
import hashlib
from importlib import metadata
import json
from pathlib import Path
import shutil
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_URL = "https://go.microsoft.com/fwlink/?linkid=2124701"
# PDF.js 6 uses Map.getOrInsertComputed (Chromium/WebView2 145+).
MINIMUM_VERSION = "145.0.0.0"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Use an already downloaded runtime installer")
    args = parser.parse_args()
    package = ROOT / "vendor/prerequisites/MicrosoftEdgeWebView2RuntimeInstallerX64.exe"
    package.parent.mkdir(parents=True, exist_ok=True)
    if not package.is_file():
        if args.offline:
            raise SystemExit("Download the Microsoft x64 Evergreen Standalone Installer first.")
        with urllib.request.urlopen(RUNTIME_URL, timeout=120) as response, package.open("wb") as stream:
            shutil.copyfileobj(response, stream)
    signature_script = (
        "$file=Get-Item -LiteralPath '" + str(package).replace("'", "''") + "';"
        "$sig=Get-AuthenticodeSignature -LiteralPath $file.FullName;"
        "@{status=[string]$sig.Status;signer=$sig.SignerCertificate.Subject;"
        "installerVersion=$file.VersionInfo.ProductVersion}|ConvertTo-Json -Compress"
    )
    signed = json.loads(subprocess.check_output(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", signature_script], text=True
    ))
    if signed["status"] != "Valid" or "O=Microsoft Corporation," not in signed["signer"]:
        raise SystemExit("The offline runtime must have a valid Microsoft signature: " + str(signed))
    with package.open("rb") as stream:
        checksum = hashlib.file_digest(stream, "sha256").hexdigest()
    descriptor = dict(
        path=package.relative_to(ROOT).as_posix(), source=RUNTIME_URL, sha256=checksum,
        minimum_version=MINIMUM_VERSION, **signed,
        documentation="https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution",
        preparation="Downloaded and signature-verified only; never executed or installed",
    )
    manifest = package.with_name("webview2.json")
    if manifest.exists():
        previous = json.loads(manifest.read_text(encoding="utf-8"))
        if previous["sha256"] != checksum:
            raise SystemExit("WebView2 differs from the pinned manifest; review the runtime before updating it.")
    manifest.write_text(json.dumps(descriptor, indent=2) + "\n", encoding="utf-8")
    notices = ROOT / "vendor/licenses/desktop-python"
    notices.mkdir(parents=True, exist_ok=True)
    for name in ("pywebview", "pythonnet", "clr_loader", "bottle", "proxy_tools", "cffi", "pycparser", "typing_extensions"):
        distribution = metadata.distribution(name)
        licenses = [file for file in distribution.files or []
                    if any(part.lower().startswith(("license", "copying", "notice")) for part in file.parts)]
        for index, license_file in enumerate(licenses):
            shutil.copy2(distribution.locate_file(license_file), notices / f"{name}-{index}-{license_file.name}")
        if not licenses:
            (notices / f"{name}-METADATA.txt").write_text(distribution.read_text("METADATA") or "", encoding="utf-8")
    (ROOT / "vendor/licenses/Microsoft-WebView2.txt").write_text(
        "Microsoft Edge WebView2 Runtime and Microsoft.Web.WebView2 SDK components\n"
        "Copyright Microsoft Corporation. All rights reserved.\n\n"
        "The official, unmodified, Microsoft-signed Evergreen Standalone Installer is included.\n"
        "Microsoft license terms and third-party notices accompany that installer/runtime.\n"
        "https://developer.microsoft.com/en-us/microsoft-edge/webview2/\n"
        "https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution\n",
        encoding="utf-8",
    )
    print("Verified offline desktop prerequisite:", checksum)


if __name__ == "__main__":
    main()
