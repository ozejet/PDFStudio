# PDF Studio project rules

- Bump the application version for every delivered change set, including small fixes, UI edits and maintenance. Do not reuse a previously delivered version.
- Use the public format `major.minor.revision`, with exactly three digits in the revision, such as `0.1.002`.
- Run `python scripts/bump_version.py` once per change set. `pdfstudio/__init__.py` is the canonical version; the script synchronizes Python and npm package metadata using their normalized numeric form.
- Run `python scripts/bump_version.py --check` before handoff. Keep the version visible in small text on the landing page and other app views, using the version returned by the backend.
- Rebuild affected UI and standalone outputs before delivery. Preserve open user sessions when applying updates.
- Keep document processing on the device and preserve source files.
