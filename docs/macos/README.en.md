# PDF Studio for Apple Silicon macOS

> **Documentation preview only.** The macOS DMG, app bundle, and adapted source are not published in this fork. These instructions describe a locally tested personal review build.

This folder documents two local ways to run version 0.1.019. The packaged app is the normal choice. The source/Safari variant is for development and review.

## Packaged app: no Terminal or Homebrew required

The steps below apply only if you have received the local review package separately; there is no public download in this repository.

1. Open the locally supplied `PDFStudio-0.1.019-arm64.dmg`.
2. Drag **PDFStudio.app** onto the **Applications** link.
3. Eject the disk image, then open PDFStudio from Applications or Finder.
4. PDFStudio starts a local engine bound only to `127.0.0.1` and opens its interface in Safari. A repeat launch reuses the running engine.
5. Choose **Add files**, or drop files into the window. Use **Read**, **Organize**, **Edit / Fill**, or **Tools**.
6. Use **Save as PDF…**, **Save a copy**, or an export action. The macOS Save panel lets you choose the destination. Existing files are not overwritten; PDFStudio adds a numeric suffix.
7. Quit with the power button in the web interface or **Quit PDF Studio** from the app/Dock menu. Closing only the Safari tab does not stop the engine.

![DMG installation window](../screenshots/macos/01-dmg-install.png)

![Synthetic PDF open in Safari](../screenshots/macos/02-safari-read.png)

![Native Save As panel](../screenshots/macos/03-native-save-as.png)

The app stores settings under `~/Library/Application Support/PDFStudio`. Working documents and intermediate results are temporary; save the output you want before quitting.

## Source/Safari variant

The macOS-specific source changes described here are not published in this fork.

Prerequisites for this variant only: Apple Silicon Mac, Python 3.12 with Tk, Node/npm, and the repository dependencies. The reviewed setup used Homebrew Python 3.12.15 and PyInstaller 6.21.0. LibreOffice is not required unless Office conversion is intentionally enabled later.

From the repository root:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
npm --prefix web ci --ignore-scripts
.venv/bin/python scripts/prepare_assets.py --offline
npm --prefix web run build
```

Then double-click `Start PDF Studio on macOS.command`, or run:

```sh
.venv/bin/python run.py
```

The source variant opens Safari and keeps its Python process in the foreground. Quit from the PDFStudio web interface, or press `Ctrl-C` in its Terminal window. It depends on `.venv` and the built `web/dist`; the packaged app does not.

## Supported and limited

- Built and tested for arm64, macOS 13 or later. It was verified on an Apple M2 Pro Mac running macOS 27.0.1.
- PDF, image, text, Markdown, HTML, OCR, organize, edit/redact, and export paths are local. Keep originals and review important exports; PDF transformations can alter complex layout, forms, signatures, layers, or unusual fonts.
- LibreOffice is not bundled, so Office-to-PDF conversion is unavailable in this build.
- The bundle is ad-hoc signed, not Apple notarized. Do not bypass Gatekeeper or remove quarantine. If macOS rejects it, stop and obtain a trusted/notarized build.
- The upstream repository has no project-level license file. Viewing and forking on GitHub is distinct from permission to redistribute. Distribution permission for PDFStudio remains unresolved.
- PyMuPDF is AGPL/commercial. Any public distribution must satisfy the applicable source/copyleft/notices requirements or use a suitable commercial license, in addition to resolving PDFStudio's own rights.
- Automation displayed the native Save panel with a synthetic filename, but did not click the final Save button; destination-file creation through that panel remains unverified.

See the [release notes](RELEASE_NOTES-0.1.019.md) for verification details. The full dependency-notice inventory remains with the unpublished local review package.
