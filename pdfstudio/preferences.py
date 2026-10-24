"""Small on-device preferences, shared by desktop and browser launches."""
import json
import os
import threading
import uuid

DEFAULTS = {"confirmQuit": True, "confirmCloseDocument": True, "confirmRefreshPdf": True}


class Preferences:
    def __init__(self, data_dir):
        self.path = data_dir / "preferences.json"
        self.lock = threading.Lock()

    def read(self):
        with self.lock:
            return self._read()

    def _read(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        return {key: data.get(key) if isinstance(data, dict) and isinstance(data.get(key), bool) else default for key, default in DEFAULTS.items()}

    def update(self, patch):
        if not isinstance(patch, dict) or any(key not in DEFAULTS or not isinstance(value, bool) for key, value in patch.items()):
            raise ValueError("Choose a valid confirmation preference.")
        with self.lock:
            value = {**self._read(), **patch}
            temporary = self.path.with_name("preferences-" + uuid.uuid4().hex + ".tmp")
            try:
                temporary.write_text(json.dumps(value), encoding="utf-8")
                os.replace(temporary, self.path)
            finally:
                temporary.unlink(missing_ok=True)
            return value
