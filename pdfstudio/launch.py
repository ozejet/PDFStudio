"""Import files handed to the application by Windows Open with."""
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import url2pathname


def local_path(value: str) -> Path:
    if value.lower().startswith("file:"):
        url = urlsplit(value)
        if url.netloc not in {"", "localhost"}:
            raise ValueError("Download the PDF to this device before opening it in PDF Studio.")
        return Path(url2pathname(url.path))
    if "://" in value:
        raise ValueError("Download the PDF to this device, then choose Open with PDF Studio.")
    return Path(value).expanduser().resolve()


def open_launch_files(app, filenames: list[str]):
    workspace = app.extensions["workspace"]
    documents, errors = [], []
    try:
        workspace.check_capacity(len(filenames))
    except ValueError as exc:
        errors.append({"name": "Requested files", "error": str(exc)})
        app.extensions["launch_errors"] = errors
        app.extensions["launched_with_files"] = bool(filenames)
        return documents, errors
    for value in filenames:
        path = None
        try:
            path = local_path(value)
            if not path.is_file():
                raise ValueError("The file could not be found. Download it first, then open the saved file.")
            documents.append(workspace.import_bytes(path.read_bytes(), path.name).public())
        except (OSError, ValueError, RuntimeError) as exc:
            message = str(exc) if isinstance(exc, (ValueError, RuntimeError)) else "The file could not be read. Check that it is still available."
            errors.append({"name": path.name if path else "Requested file", "error": message})
    app.extensions["launch_errors"] = errors
    app.extensions["launched_with_files"] = bool(filenames)
    return documents, errors
