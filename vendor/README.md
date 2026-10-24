# Offline runtime assets

These assets are acquired during development/package preparation, not when a
user opens a document. PDF Studio must serve them from its loopback server.

Run `python scripts/prepare_assets.py` after `npm install --prefix web`.
Use `--offline` to refresh browser copies from existing local downloads without
network access. Use `--libreoffice` on Windows x64 to prepare the optional local
Office conversion engine. Use `--vc-redist` to download the pinned official
Microsoft Visual C++ x64 prerequisite and its license without running it.
The script writes SHA256/source metadata to
`vendor/assets-manifest.json`; npm package versions are pinned by
`web/package-lock.json`.

Run `python scripts/prepare_desktop.py` with the desktop Python dependencies
installed to prepare the official Microsoft-signed x64 offline WebView2 installer,
its SHA256/signature descriptor, and desktop dependency license notices. `--offline`
verifies the existing download. Setup includes it without downloading at install time.

| Asset | Local source | Browser URL | License/source |
| --- | --- | --- | --- |
| Sarabun regular/bold TTF | `vendor/fonts` | `/vendor/fonts/` | Included OFL-1.1; [Google Fonts upstream](https://github.com/google/fonts/tree/main/ofl/sarabun) |
| PDF.js worker, CMaps, standard fonts, decoder WASM | `web/node_modules/pdfjs-dist` | `/vendor/pdfjs/` | Included Apache-2.0 and component notices; [Mozilla PDF.js](https://github.com/mozilla/pdf.js) |
| Tesseract.js worker | `web/node_modules/tesseract.js` | `/vendor/ocr/worker.min.js` | Included Apache-2.0; [Tesseract.js](https://github.com/naptha/tesseract.js) |
| Tesseract WASM cores (SIMD/LSTM variants) | `web/node_modules/tesseract.js-core` | `/vendor/ocr/core/` | Included Apache-2.0/component notices |
| English/Thai OCR models | `vendor/tessdata` | `/vendor/ocr/lang/{eng,tha}.traineddata.gz` | Included Apache-2.0; [official tessdata_fast](https://github.com/tesseract-ocr/tessdata_fast) |
| LibreOffice Windows x64 administrative image | `vendor/libreoffice` | No public URL; backend process only | Included runtime LICENSE/NOTICE files; [official licenses](https://www.libreoffice.org/licenses/) |
| Microsoft Visual C++ v14 x64 prerequisite | `vendor/prerequisites/VC_redist.x64.exe` | No public URL; later installer prerequisite | Included Microsoft terms; [official downloads](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist) |

## Browser integration

Set PDF.js `workerSrc` to `/vendor/pdfjs/pdf.worker.min.mjs`; set `cMapUrl`
to `/vendor/pdfjs/cmaps/`, `cMapPacked` to `true`, `standardFontDataUrl` to
`/vendor/pdfjs/standard_fonts/`, `wasmUrl` to `/vendor/pdfjs/wasm/`, and
`iccUrl` to `/vendor/pdfjs/iccs/`.

Tesseract.js `createWorker('eng+tha', 1, { workerPath, corePath, langPath })`
must explicitly use `/vendor/ocr/worker.min.js`, `/vendor/ocr/core`, and
`/vendor/ocr/lang`. OEM `1` selects LSTM: official tessdata_fast models do not
contain the legacy recognizer. `gzip: true` is the default. Do not allow the
library's CDN defaults. See [official local installation options](https://github.com/naptha/tesseract.js/blob/master/docs/local-installation.md).

## LibreOffice distribution

The script pins LibreOffice 26.2.6 Windows x64, verifies the official SHA256,
and uses MSI `/a` (administrative extraction), not a machine installation.
Keep the full extracted image and its licenses. The generated
`vendor/libreoffice-runtime.json` records the console executable path. Invoke
`soffice.com --headless --convert-to pdf --outdir OUTPUT INPUT` with a private
`-env:UserInstallation=file:///...` profile inside PDF Studio's runtime folder.
Use a separate profile per concurrent job or serialize conversions.
The Sarabun regular/bold fonts and their OFL notice are also copied into the
runtime's own `share/fonts/truetype` directory; they are not installed systemwide.

LibreOffice's covered sources can be obtained from the pinned official
[26.2.6 source directory](https://download.documentfoundation.org/libreoffice/src/26.2.6/).
Retain this notice and runtime license texts in distributed packages. The
application communicates with the unmodified runtime as a separate process.
Actual document fidelity depends on source fonts, document complexity, and
LibreOffice filter support. This Windows x64 image is not a macOS/Linux/ARM64
runtime. It adds substantial package size.

The Windows image uses the Microsoft Visual C++ runtime already present on this
development computer. `vendor/prerequisites/VC_redist.x64.exe` is the official,
Microsoft-signed 14.51.36247.0 installer, downloaded only. It has not been run.
The later standalone installer can include this prerequisite. Keep the included
Microsoft terms and evaluate their redistribution conditions before release.
Windows System32 DLLs have not been copied into the app. Clean-machine installer
verification remains necessary.

## Reproducible smoke checks

After asset preparation and npm installation, run from the repository root:

```powershell
node vendor/verify_ocr_runtime.mjs
python vendor/verify_office_runtime.py
```

OCR checks recognize synthetic English and Thai text with local gzip models and
the installed local Tesseract WASM engine. Both returned confidence 95 during
preparation. They validate model/font compatibility, not browser worker loading
or real-world document accuracy. Browser offline verification belongs to app QA.

The Office check generates synthetic ODF inputs, exports genuine DOCX/PPTX,
then converts both to PDF. Artifacts remain in `vendor/smoke-check` for review;
exclude this folder and `vendor/downloads` from the application package.
Preparation produced a 28,106-byte Word PDF and a 24,698-byte PowerPoint PDF.
Synthetic conversion does not guarantee fidelity for every Office document.
