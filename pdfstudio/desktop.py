"""Dedicated Windows host for the existing, local PDF Studio interface."""
from __future__ import annotations

import threading
import webbrowser

from .storage import app_root


class DesktopHost:
    def __init__(self, app, url, webview):
        self.app, self.webview = app, webview
        self.approved = threading.Event()
        self.close_pending = threading.Lock()
        webview.settings["ALLOW_DOWNLOADS"] = True
        webview.settings["ALLOW_FILE_URLS"] = False
        self.window = webview.create_window(
            "PDF Studio", url, width=1280, height=850, min_size=(900, 600),
            text_select=True, zoomable=True, background_color="#eef1f5",
        )
        self.window.events.closing += self.closing

    def closing(self):
        if self.approved.is_set():
            return True
        # The native closing event runs on the UI thread. Evaluate JavaScript
        # from a worker after cancelling this attempt, so neither loop blocks.
        if self.close_pending.acquire(blocking=False):
            threading.Thread(target=self.request_close, daemon=True).start()
        return False

    def request_close(self):
        try:
            preferences = getattr(self.app, "extensions", {}).get("preferences")
            if preferences and not preferences.read()["confirmQuit"]:
                self.quit()
                return
            handled = self.window.evaluate_js(
                "Boolean(window.__pdfStudioReady && "
                "window.dispatchEvent(new Event('pdfstudio:close-request')))"
            )
            if not handled and self.window.create_confirmation_dialog(
                "Quit PDF Studio",
                "Save any results you want to keep before quitting. "
                "Temporary documents and unsaved edits will be cleared. Quit PDF Studio?",
            ):
                self.quit()
        except Exception:
            # A renderer failure must still allow an explicit, confirmed exit.
            if self.window.create_confirmation_dialog(
                "Quit PDF Studio", "The interface is unavailable. Quit and clear this temporary session?"
            ):
                self.quit()
        finally:
            self.close_pending.release()

    def quit(self):
        self.approved.set()
        self.window.destroy()

    def start(self):
        self.webview.start(
            gui="edgechromium", private_mode=True,
            icon=str(app_root() / "web/dist/branding/pdfstudio.ico"),
        )


def run_desktop(app, url, server):
    import webview

    host = DesktopHost(app, url, webview)
    app.extensions["shutdown"] = host.quit
    worker = threading.Thread(target=server.serve_forever, name="pdfstudio-local-server")
    worker.start()
    try:
        host.start()
    except Exception:
        # Retain access to this session if the desktop renderer cannot start.
        # The browser uses the same engine, documents, and per-launch token.
        app.extensions["shutdown"] = server.shutdown
        webbrowser.open(url)
        worker.join()
    finally:
        server.shutdown()
        worker.join()
