# PDF Studio

The current version appears in small text at the bottom right of the app,
including the landing page. Public versions use `0.0.000` formatting and advance
with every delivered change. To make a new change, run
`python scripts/bump_version.py`; verify with
`python scripts/bump_version.py --check` before building.

PDF Studio opens in its own Windows desktop window with a local Python processing engine. An optional browser mode uses the same interface and engine. Files,
fonts, OCR models and Office conversion stay on the device. It has no PLAR runtime
dependency and does not upload documents to a service.

## Start on this development computer

For installation on another Windows x64 computer, copy only
**dist\installers\PDFStudio-Setup-0.1.018.exe** and run it. The setup wizard
installs the complete application and creates a Start menu shortcut, with an
optional Desktop shortcut. You can keep the setup EXE in `bApps`; it does not
need any adjacent files. The application files are created in the chosen
installation folder automatically. Launch the installed shortcut afterward.

Double-click **dist\update-0.1.018\PDFStudio\PDFStudio.exe** to use this change set's
self-contained Windows build. Keep its adjacent runtime files together. It opens
its own desktop window; document processing runs in the bundled local process.
Use the **PDF Studio (browser)** Start menu shortcut, or `PDFStudio.exe --browser`,
for a separate browser workspace. `--no-browser` runs only the engine for automation.

To run from source, double-click **Start PDF Studio.cmd**, or run:

```powershell
python run.py
```

Windows **Open with → PDFStudio.exe** is supported. A local PDF passed by
Windows or a browser's downloaded-file menu opens directly in **Read** view.
Filenames with spaces and Unicode characters are supported. Each launch owns
its own workspace, so opening another PDF preserves any existing session.
Download remote PDFs first; the app does not fetch web URLs. From source:

```powershell
python run.py "C:\Documents\My PDF.pdf"
```

The launcher chooses a free loopback port and opens the desktop window on Windows.
Closing the window displays the same save reminder as **Quit PDF Studio**; **Keep
working** leaves the session intact. Confirming Quit closes the window and local
engine. In browser mode, keep the launcher running and use **Quit PDF Studio** in
the app to stop it. Uploaded working copies and temporary results are removed on
normal shutdown. Save result files before quitting.

The browser interface is already built in `web/dist`. Python and the packages in
`requirements.txt` are source-run prerequisites. The Windows application bundle
includes Python; users of that bundle do not install Python or npm.

## Feedback panel - version 0.1.018

This Bee build includes the supplied Bee Microsoft Forms response link as its
bundled feedback form. The new logo from version 0.1.017 is retained.

The landing page has no Feedback button or automatic invitation. After a file is
opened, a quiet **Feedback** text button appears beside Settings. **Settings >
Share feedback** remains available at any time, including before opening a file.
The button opens the approved side panel while keeping the current
reader/editor mounted. Closing and reopening the panel retains its embedded
Microsoft Forms page, including answers still present in that page. Refreshing
the form asks before clearing it. Closing the application ends this session;
PDF Studio does not save form answers locally.

Until connected, the panel shows a labeled structure preview with submission
disabled. Create a Microsoft Form named **PDF Studio feedback** with a required
five-level Rating question, a required long-answer Text question, and an optional
Choice question for Read / Organize / Edit / Fill / Tools / Other. Use a teal
style. In **Collect responses**, choose the intended audience and copy the
response link or the URL inside the embed code. Keep one-response-per-person off
if colleagues should provide feedback again later.

Paste the response URL into **Settings > Feedback > Form connection**, then choose **Save form
link**. Only HTTPS Microsoft Forms response URLs are accepted; editing links
are rejected. The setting is stored in the device's PDFStudio data folder and
survives updates. To supply a default when distributing the application, set
`url` in `web/public/feedback-form.json` before rebuilding. A saved device setting,
including an explicitly empty URL, overrides that bundled default.

Microsoft Forms owns the question layout, responses, sign-in and submission
confirmation. The app cannot inspect its cross-origin fields or verify a
successful submission. Open the form's **Responses > Open in Excel** to review
results. Work-account restrictions may prevent embedded sign-in; **Open in
browser** opens the configured form without navigating away from PDF Studio.
**Reload form** can clear unsubmitted answers and therefore asks first.

No Microsoft Graph credentials or recipient email address are stored in the app.
The earlier email-sending draft has been replaced by this embedded form. Forms
loads only after the connected panel is first opened; document processing still
stays local and PDF Studio does not attach documents to feedback.

Setup reference: [Microsoft Forms sharing and embed instructions](https://support.microsoft.com/en-gb/forms/send-a-form-to-get-responses).

## Workflows

- **Read:** single, continuous, two-page and four-page views; paragraph-group Read Aloud; zoom and rendering
  quality; view rotation; Unicode search; text selection/copy; Focus view.
  Reading settings are remembered locally using the document fingerprint.
  Ctrl+mouse-wheel over the pages zooms the PDF around the pointer. The toolbar
  and browser zoom remain unchanged; the Zoom selector is also available.
  **Hand** drags the page in either direction; **Select text** enables copying.
  Hold **Space** while dragging to pan temporarily. Hand is the default reading
  tool, and the choice is remembered with the document's reading settings.
  Left/Right and Page Up/Down change pages from the document or surrounding app.
  Up/Down scroll the page viewport. Text fields, menus, modifiers, text selections
  and open dialogs retain their own keys; a preview dialog controls only its reader.
  Wheel changes are grouped per animation frame. The existing bitmap/text layer
  scales immediately; a sharper page replaces it after a 160 ms pause. Outdated
  renders are canceled, and each canvas is capped at 8 million pixels. Continuous
  view keeps only visible and nearby pages rendered.
  The expand button enters **Focus view**, filling the current browser content
  area while keeping the browser's tabs and address bar. The app header,
  navigation, Files sidebar, footer and hint bar are hidden. Move the pointer to
  the top edge to reveal the floating document controls; they hide after moving
  away and leaving their fields. **Tab** reveals and enters the controls, and
  **Ctrl+F** opens PDF search. **Esc** or **Exit focus view** restores the normal
  layout. Page, zoom setting and reading position carry between both layouts;
  Fit page/width use the actual available document area.
  **Read Aloud** is a Read sub-function. Choose an installed local voice, page
  range (`current`, `all`, or numbers/ranges), and speed. Play, pause/resume and
  stop are available. The current paragraph is highlighted and brought into
  view. Long paragraphs use short speech chunks while keeping one paragraph
  highlight. Closing the controls or changing documents stops speech.
  Paragraph boundaries are inferred from PDF line spacing/indentation; complex
  columns and unusual reading order need review. Image-only scans have no
  selectable text to speak. Voices reported as remote are excluded.
- **Organize:** add PDFs and prepared copies of images, Office, text, Markdown and HTML files;
  select pages; drag or use buttons to order/duplicate file cards; add memos;
  rotate pages; combine, export selected pages and split ranges into a ZIP.
  Advanced patterns such as `A3-1,B2,A1` preserve reversed ranges and repeated pages.
- **Edit / Fill:** one workspace for text, images/signatures, pencil drawings,
  colored boxes/covers and permanent redaction. **Box / cover** is the single
  visual-box tool; underlying content remains in the exported PDF.
  **Redact content** removes underlying text, intersecting image pixels and
  touched vector graphics from the marked areas on export. There is no separate
  Redact menu. Selecting Redact content starts with opaque black fill; the fill
  color can be changed in the inspector.
  Move, resize and rotate supported objects, sample a page color, edit/delete,
  apply objects to the current page, page ranges or all pages, undo/redo, preview
  and save a copy using the shared controls. Text and image tools add objects
  over the original page. Hand and Space+drag pan the editing viewport.
- **Templates (hidden from navigation):** saved profiles and the underlying engine are retained. Place text/image fields, bind Excel/CSV columns, use constants
  and computed values, format amounts and dates, create digit boxes, preview an
  actual generated sample, save profiles and generate combined or per-row PDFs.
  Profiles include the template and placed images; spreadsheet rows are not saved.
- **Tools:** tables to Excel/CSV, local document-to-PDF conversion,
  PDF-to-Markdown. Table extraction
  uses a radio list to select exactly one PDF, independently of the sidebar.
  Changing the file, range, detection mode or output clears the old preview.
  Conversion is available before opening a PDF; its picker accepts the same
  formats as drag and drop. Upload percentage, current file/phase, elapsed time and the
  completed-file count stay visible. Conversion within a file is indeterminate.
  Prepared PDFs appear in individual result rows with Save As actions. Select
  several to save their full PDFs separately in one ZIP; use Organize for page selection.
  OCR / searchable PDF is removed from Tools; Read Aloud is under Read.

Drag-and-drop and **Add files** accept mixed batches: PDF; PNG/JPG/JPEG;
DOC/DOCX/ODT/RTF; PPT/PPTX/ODP; Markdown; HTML/HTM; and readable text such as
TXT, TEXT, LOG, VTT, SRT, CSV, JSON and XML. Clearly readable unfamiliar formats
open as text directly, with an **Opened as text** toast and **Change view** action.
Ambiguous encodings offer **Open as text**, an encoding choice and an optional
remembered choice for that extension. Unsupported binary files get a toast;
other valid files in the batch continue opening.

HTML opens in an isolated static reader without automatic PDF conversion.
Scripts, forms, navigation and external file/network access are disabled.
Companion PNG/JPG images and CSS are included only when explicitly supplied in
the same batch, with unique filenames. Inline SVG is supported. **Prepare PDF**
creates a temporary paginated copy when needed; review complex HTML layouts.

Text and Markdown prepare temporary PDF pages automatically up to 512 KB.
Larger text files open immediately in the text reader, with optional PDF preparation.
The text limit is 8 MB; generated documents are limited to 2,000 pages.
**Edit text** changes a working draft. **PDF layout** controls paper, orientation,
font size and wrapping; **Update PDF preview** applies the draft and layout.
Drafts persist when changing files or workflows. Refreshing a PDF that has page
arrangements or annotations requires a decision because those changes reset.
Original source files are preserved, and PDF output is written only through Save As.
Native text/HTML use scrolling; PDF previews support the PDF page navigation controls.
Single-file conversion uses **Save as PDF** in Read and does not require a merge.

On the landing page, the first ready file opens in **Read**. Adding
files to an existing workspace preserves the active document, workflow, page,
zoom, scroll position, focus and edits. Each ready file appears as soon as it has
finished; it can be used while later files continue preparing.

Routine updates use bottom-right toasts without taking keyboard focus. Success
messages dismiss after six seconds, pausing while hovered, focused or expanded.
Warnings and errors stay available until dismissed or resolved; batch failures
have expandable details. Progress appears on file cards and in a compact toast,
without a full-screen overlay. Failed files offer Retry; protected PDFs offer
**Enter password**, opening a dialog only when selected. One protected or failed
file does not interrupt the rest of a batch. Closing an unedited file is immediate;
closing a file with unsaved edits requires a decision. Quit retains its save reminder.

**Cancel conversion** (one file) or **Cancel remaining** (a batch) stops the
active Office/text converter and skips queued files. Completed files stay open,
with the current reader position preserved. The progress toast shows
**Cancelling…** until cleanup finishes. **Cancel preparation** keeps the previous
PDF preview and text draft. Cancellation does not require a confirmation.

The Quit, discard-document-edits and refresh-PDF dialogs each offer a separate,
unchecked **Don’t ask again** choice. It is saved only when the corresponding
Quit/Discard/Refresh action is chosen. Choosing Keep working/open preserves the
existing preference. Suppressed reminders mean that action proceeds immediately,
including clearing unsaved temporary work. **Settings → Confirmation reminders**
restores each reminder or all three. Preferences are stored in the local data
folder, so they survive private desktop sessions, port changes and app updates.
The Quit setting also controls the browser close/reload warning and desktop
window close. Password entry and Save As remain explicit user choices.

A session accepts **100 open files**. An incoming batch that would exceed that
count is rejected in full before upload or conversion; close files first.
The engine reserves slots for running imports and enforces the same limit.
The upload request limit remains 512 MB and the per-PDF limit 10,000 pages.
Only the current PDF opens a PDF.js worker; nearby continuous pages render
lazily. These limits do not guarantee performance for arbitrarily large PDFs.

**Combine & save**, **Export & save** and **Save a copy** open Save As directly,
without an intermediate acknowledgment dialog. Canceling or failing to save
leaves the result available in a persistent toast with Save As/Download actions
and through **Save last result**.

**Save As** uses the modern Windows Common Item Save dialog (`IFileSaveDialog`),
with a foreground, topmost owner and a Unicode folder/filename picker. It starts in Documents and remembers the last saved folder for the
session. The dialog stays above other windows until saved or canceled.
Combined PDFs default to
`combine_yyyymmddhhmmss.pdf` in local device time. Existing destination files
receive a suffix; source files are never overwritten. **Download** is also
available and follows the browser's download settings.

Closing/reloading the browser tab asks for confirmation while documents, results,
or an operation are open. Browsers supply the warning's wording and require prior
interaction with the page; the app cannot display its custom Quit dialog there.
Use **Quit PDF Studio** to see the full save reminder and stop the local process.

## Local storage and privacy

Saved profiles live under `%LOCALAPPDATA%\PDFStudio\profiles`. Imported documents
and generated intermediate files use an isolated temporary workspace. Only
explicitly saved profiles and exports persist. Reading settings and the appearance
choice use the current web renderer's local storage; desktop windows use a private
renderer profile, so those view preferences last for that desktop session.
Document contents are not placed in local storage.

The server binds to `127.0.0.1`, validates the request host and origin, and uses a
per-launch cookie/token. Its content policy permits local resources only.
Read-aloud excludes voices reported as remote by the renderer. Both desktop and
browser modes need the local process; this is not a hosted website or mobile service.

## Reproducible developer setup

Python 3.12 or newer and a current Node.js development installation are needed.
The supplied lock file records the exact frontend dependencies used for this build.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
npm.cmd ci --prefix web
python scripts/prepare_assets.py --libreoffice --vc-redist
python scripts/prepare_ui.py
npm.cmd run build --prefix web
.venv\Scripts\python.exe run.py
```

Asset preparation downloads dependencies during development/build only. It
does not install Office or OCR on the computer. Use
`python scripts/prepare_assets.py --offline` to refresh browser assets from the
already downloaded runtimes without a network connection. The talit02 source
settings are retained under `design-system/talit02/source`; the UI uses the
shadcn token contract and bundled Sarabun fonts.

## Verify

```powershell
python -m pytest -q
npm.cmd run build --prefix web
node --test tests/test_ui_interactions.mjs
node vendor/verify_ocr_runtime.mjs
python vendor/verify_office_runtime.py
```

The automated tests use synthetic PDFs and spreadsheets. They cover merge/split
order, repeated/reversed ranges, rotation/crop preservation, sources, redaction
versus covers, text/image/Thai rendering, template bindings and digit boxes,
profile persistence, table exports, searchable copies, filename collisions,
API isolation, Unicode Windows dialog arguments and native-save cancellation.
The standalone EXE was also checked over HTTP for built assets, upload, merge,
range redaction, rendering, Thai template generation, table-to-Excel export,
and bundled DOCX/PPTX/RTF conversion. The current Python suite has 98 tests,
including asynchronous imports, capacity reservations, whole-batch rejection,
Windows launch paths, real COM dialog setup, Unicode results and cleanup.
UI regression checks cover mixed-format drops, document wheel zoom and cursor
anchoring, continuous-view zoom, frame batching, Hand/Space panning, drawing and
typing isolation, deferred bitmap swaps/cancellation, browser-close protection,
Focus view entry/exit, automatic toolbar visibility and keyboard access,
viewport position restoration and clamped offsets,
warning countdown/reset/dismissal, single-PDF table radio selection and preview
invalidation, default Read on an empty workspace, and
paragraph speech/highlighting lifecycle. Additional checks cover early access to imported files, preservation of reading
position and keyboard focus, deferred password dialogs, direct native saving,
canceled/failed result recovery, toast expiry and focus pausing, clean versus
edited-file closure, document-wide page arrows, native HTML isolation, optional PDF
preparation, persistent text drafts, encoding choices and separate PDF exports.
There are 45 UI interaction checks. Source-format tests also verify Unicode,
long-line wrapping, static companion assets, SVG, preserved originals and
failed-preparation recovery.
English and Thai OCR recognition were verified with synthetic images against
the bundled runtime. Browser interaction and native dialog acceptance still
require a connected browser/manual check.

To repeat the HTTP check against a running app with synthetic files, run
`python scripts/verify_http_runtime.py http://127.0.0.1:PORT --quit`.
The optional `--office` check also imports the synthetic DOCX/PPTX fixtures under
`vendor/smoke-check` and a synthetic RTF. `--sources` checks text, VTT, Markdown,
native HTML, explicit PDF preparation, SVG and separate PDF ZIP export.
`--controls` checks reminder preferences and real converter/PDF-preparation cancellation.
`--quit` stops that app after the check.

## Standalone Windows distribution

```powershell
python -m pip install -r requirements-dev.txt
python scripts/prepare_desktop.py
python scripts/build_windows.py
```

Desktop preparation verifies the official signed offline WebView2 prerequisite
and copies dependency notices (use `--offline` when already downloaded).

This produces `dist/PDFStudio/PDFStudio.exe` with its adjacent runtime files.
This portable build requires the whole folder. To create a single setup EXE,
use [Inno Setup 7](https://jrsoftware.org/isdl.php) on the build computer:

```powershell
python scripts/build_installer.py --bundle dist/PDFStudio --iscc "C:\Path\To\Inno Setup 7\ISCC.exe"
```

The output is `dist/installers/PDFStudio-Setup-0.1.018.exe`. Only this EXE
needs to be distributed; the adjacent SHA256 file is optional. Python, the UI,
fonts, OCR models, Office conversion and all license notices are embedded.
The desktop window uses pywebview and the Microsoft WebView2 Runtime. Chrome is
not required, and there is no separate browser app installation. The included
offline WebView2 installer runs for the current user only when a sufficiently
recent runtime is missing. Windows 10 version 1607 or later is required.
The included Microsoft Visual C++ runtime is installed automatically if the
required version is missing; Windows requests administrator permission for that
prerequisite only. No downloads are made on the destination computer.

Setup installs for the current user under `%LOCALAPPDATA%\Programs\PDF Studio`
by default, or a folder selected in the wizard. It registers PDF Studio in
Windows Open With and Installed apps without changing the default PDF reader.
Updates install into separate `versions\0.1.018` folders and update shortcuts;
existing sessions keep using their original runtime until closed. Reinstalling
the same version or uninstalling while its runtime is open stops with a save
reminder and leaves the session running. Earlier installed versions are tracked
by the shared uninstall log. Uninstall removes installed files, retaining saved
profiles, source documents and exports.

To build while keeping this computer's existing bundle and sessions untouched:

```powershell
python scripts/build_windows.py --output-dir dist/update-0.1.018 --reuse-runtime-from dist/PDFStudio
python scripts/build_installer.py --bundle dist/update-0.1.018/PDFStudio
python scripts/verify_installer.py dist/installers/PDFStudio-Setup-0.1.018.exe
```

The installer check uses a separate path containing spaces, an apostrophe,
an ampersand and Thai characters. `/TESTMODE=1` skips OS registration,
shortcuts and machine-wide prerequisite installation during this check.
It verifies launch, the backend version, built
assets, synthetic PDF workflows, Office conversion, live-session protection
and uninstall preservation of synthetic source files. Clean-machine prerequisite
installation and release code signing remain unverified.

Keep the runtime/font license notices with distributions. PyMuPDF uses
AGPL/commercial licensing; the product's distribution license remains a release
decision. See `vendor/README.md` for exact versions, sources and licenses for
LibreOffice, PDF.js, OCR models, fonts and the Microsoft prerequisite.

## Current validation limits

- Table detection needs review for complex layouts and borderless tables.
  Image-only scans do not support search, Read Aloud or table/text extraction.
  OCR has been removed from the Tools UI at the user's request.
- Office output depends on source fonts and LibreOffice's layout/filter support.
- PDF-to-Markdown preserves extractable text with basic heading detection; it
  is not the complete MakeMD/Docling product.
- Payment PDF rename has been removed from Tools.
- Legacy Tawi/v3 mapping imports require an explicit coordinate convention and
  visual review. Legacy images must be reattached. Original mappings are preserved;
  real-document Tawi parity remains unverified.
- A signature image is an image overlay. Certificate-based digital signing and
  replacing existing PDF text are outside the agreed feature scope.
- ATP Next Avail Date is excluded. Existing PLAR tools are unchanged.


## Feedback review - version 0.1.006

All requested navigation/import/tool changes are implemented. Additional defects
confirmed during review and fixed in this version:

- Only the last password-protected PDF in an import batch reached the retry
  dialog. Failed files now retain their exact batch index and are queued.
- Table previews could remain visible after changing extraction settings.
  They now clear for every relevant input change.
- PDF search could retain its busy state after clearing a query or leave an
  extraction rejection unhandled. Cancellation/error cleanup now handles both.
- Re-adding an existing document could duplicate its Organize card. Adding
  documents now deduplicates both lists together.
- Office conversion was inaccessible until another PDF was open. Tools now
  opens without an active document.

No additional reproducible failure remains in the automated checks. The
remaining feature limitations are the items above: scan/text availability,
paragraph inference and reading order, local voice availability, Office font
layout, table detection, basic Markdown structure and Upwork-only rename rules.
Manual acceptance is still needed for the actual Windows dialog position,
real-device voice playback/timing and browser visual layouts. Browser UI
access was unavailable during this review; DOM interaction checks do not
replace that acceptance. Clean-machine installer/code-signing checks remain
separate distribution work.

A representative synthetic import benchmark on this laptop used 100 ten-page
PDFs (1,000 pages, 50 scanned-image files, 43.4 MB source total). The local-engine
import completed in **3.67 seconds**; working memory went from **104.0 MB** to
**107.0 MB**, with a process peak of **115.5 MB**. File 101 was rejected.
This includes multipart staging and PDF normalization, excludes real browser
rendering, and is not a promise for other documents or laptops. Reproduce with
`python scripts/benchmark_imports.py`.


## File-list correction - version 0.1.007

Tables to Excel / CSV and PDF to Markdown use simple filename lists with one
small native radio button per file. Long filenames wrap next to the control;
there are no individual cards or extra page-count labels. Only one file can be
selected. A shared text-field selector previously matched radios and gave them
full width, which hid filenames and made the rows excessively tall. Radios are
now excluded from that rule. The regression check covers the actual stylesheet
selectors as well as both tool selection flows. Payment PDF rename was removed
from Tools at the user's request.


## Combined editing workspace - version 0.1.008

Main navigation is Read, Organize, Edit / Fill and Tools. Edit / Fill contains
all editing and redaction actions, with one Box / cover tool replacing the two
identical rectangle/cover buttons. Permanent redaction remains a distinct action
inside the same toolbar. New redactions use opaque black fill initially and
retain editable color/page scope. Existing cover and redaction objects remain
supported. Page-range settings, undo/redo, preview and mixed-object exports use
the same inspector and history. Choosing a drawing tool clears the previous
object selection so the inspector configures the new object.


## Application branding - version 0.1.017

The new artwork supplied in `assets/branding/pdfstudio-master.png` is the
canonical branding image, replacing the earlier `docs/pdfstudio.png` artwork.
`python scripts/prepare_branding.py`
prepares transparent PNGs (16 through 512 pixels), a multi-resolution Windows
ICO, favicon, Apple touch icon and browser-app manifest. The UI build runs this
step automatically; `--check` detects stale assets. The master is excluded from
the runtime bundle. Header logos load 40/80-pixel assets, and
landing-page logos load 72/144-pixel assets. No runtime image processing is used.
Browser tabs/bookmarks use the supplied favicons; the page title is PDF Studio.

The Windows build embeds the ICO and product/version information. The native
Save As owner loads its small and large icon frames. After placing the complete
bundle in its final location, run `PDFStudio.exe --register-windows` once to
register its PDF ProgID and application icons for the current user and create
Desktop/Start menu shortcuts. The command writes `windows-integration.json` with
the result. Registration uses HKCU and does not replace the user's default PDF
choice. It updates both PDFStudio.PDF and Applications/PDFStudio.exe, supporting
existing Open With associations. Moving the bundle requires running this setup
again so paths remain valid. Unrelated existing shortcut files are preserved.

The ICO is also used by the desktop window, installer and Installed apps entry.
The 192/512-pixel manifest icons and 180-pixel touch icon are ready for future
browser installation; a stable browser-installed-app origin is not provided.
Ordinary Chrome/Edge windows retain their browser
taskbar icon. PDF Studio's launcher and pinned shortcuts use the PDF Studio icon.
Windows PDF thumbnails can show document previews independently of file icons.

Branding registration follows [Microsoft application registration](https://learn.microsoft.com/en-us/windows/win32/shell/app-registration)
and [shell refresh guidance](https://learn.microsoft.com/en-us/windows/win32/api/shlobj_core/nf-shlobj_core-shchangenotify).


## Interface text cleanup - version 0.1.010

Removed the header subtitle/local badge, sidebar drop/privacy messages, Organize
output-count/order preview and Save As hint. Advanced sequence and all import,
ordering, selection and export behavior remain available.
