"""Configurable Microsoft Forms response link; no document or mail access."""
import json
import os
import threading
import uuid
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

FORM_HOSTS = ("forms.office.com", "forms.cloud.microsoft", "forms.microsoft.com")


def form_url(value):
    if not isinstance(value, str) or len(value) > 4096 or any(ord(char) < 32 for char in value):
        raise ValueError("Paste a Microsoft Forms response URL.")
    value = value.strip()
    if not value:
        return ""
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError:
        raise ValueError("Paste a valid Microsoft Forms response URL.") from None
    if parts.scheme.lower() != "https" or parts.hostname not in FORM_HOSTS or parts.username or parts.password or port not in (None, 443) or parts.fragment:
        raise ValueError("Use an HTTPS response link from Microsoft Forms.")
    query = parse_qsl(parts.query, keep_blank_values=True)
    response_page = parts.path.lower() == "/pages/responsepage.aspx" and any(key.lower() == "id" and value for key, value in query)
    short_page = parts.path.startswith("/r/") and parts.path[3:].isalnum()
    if not (response_page or short_page):
        raise ValueError("Use Collect responses in Microsoft Forms, then copy the response or embed URL. Editing links cannot collect feedback.")
    query = [(key, value) for key, value in query if key.lower() != "embed"] + [("embed", "true")]
    return urlunsplit(("https", parts.hostname, parts.path, urlencode(query), ""))


class Feedback:
    def __init__(self, data_dir, bundled_path=None):
        self.path = data_dir / "feedback-form.json"
        self.bundled_path = bundled_path
        self.lock = threading.RLock()

    def read(self):
        with self.lock:
            for path in (self.path, self.bundled_path):
                if path and path.is_file():
                    try:
                        data = json.loads(path.read_text(encoding="utf-8"))
                        return {"url": form_url(data.get("url", ""))}
                    except (OSError, ValueError, AttributeError):
                        continue
            return {"url": ""}

    def update(self, data):
        if not isinstance(data, dict) or set(data) != {"url"}:
            raise ValueError("Choose a valid Microsoft Forms response link.")
        value = {"url": form_url(data["url"])}
        with self.lock:
            temporary = self.path.with_name("feedback-form-" + uuid.uuid4().hex + ".tmp")
            try:
                temporary.write_text(json.dumps(value), encoding="utf-8")
                os.replace(temporary, self.path)
            finally:
                temporary.unlink(missing_ok=True)
        return value
