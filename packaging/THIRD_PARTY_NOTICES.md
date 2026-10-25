# PDF Studio build and third-party notices

This build was produced from the PDFStudio source repository. No project-level
license file was present in the checked-out source. The upstream owner authorized
this Apple Silicon adaptation's source and macOS packages under GNU AGPLv3 in
<https://github.com/BerlinoPotato/PDFStudio/issues/1#issuecomment-6397084771>.
That authorization is scoped to the adaptation and to code for which that owner
holds copyright; it does not relicense the original repository or third-party code.

PDF processing uses PyMuPDF 1.28.0 under its GNU AGPL 3.0 option. The exact
PyMuPDF source archive is provided beside the release binaries. The adaptation's
matching source and build scripts are provided in the tagged repository and source
archive described by `CORRESPONDING_SOURCE.md`.

The application bundle includes Python and Python packages from PyPI, plus browser
packages from the npm registry. Package versions and available license files are
recorded under `Contents/Resources/licenses`. PDF.js, Tesseract.js, OCR language
models, Sarabun fonts, and their included component notices remain under their
respective upstream licenses.

This app is ad-hoc signed for local bundle integrity. It is not Apple notarized or
App Store reviewed, and it is published as an experimental pre-release.
