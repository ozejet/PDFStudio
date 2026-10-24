"""The desktop close lifecycle respects the user's saved reminder preference."""
import threading
from types import SimpleNamespace

from pdfstudio.desktop import DesktopHost


class FakeWindow:
    def __init__(self):
        self.events = SimpleNamespace(closing=Event())
        self.handled = True
        self.confirmed = False
        self.destroyed = False
        self.scripts = []
        self.dialogs = []
        self.evaluated = threading.Event()

    def evaluate_js(self, script):
        self.scripts.append(script)
        self.evaluated.set()
        return self.handled

    def create_confirmation_dialog(self, title, message):
        self.dialogs.append((title, message))
        return self.confirmed

    def destroy(self):
        self.destroyed = True


class Event:
    def __iadd__(self, callback):
        self.callback = callback
        return self


def host():
    window = FakeWindow()
    view = SimpleNamespace(settings={}, create_window=lambda *_args, **_kwargs: window)
    return DesktopHost(SimpleNamespace(), "http://127.0.0.1:12345", view)


def test_title_bar_close_is_cancelled_and_delegates_off_the_ui_thread():
    desktop = host()
    assert desktop.closing() is False
    assert desktop.window.evaluated.wait(2)
    assert "pdfstudio:close-request" in desktop.window.scripts[0]
    assert not desktop.window.destroyed and not desktop.window.dialogs
    desktop.quit()
    assert desktop.window.destroyed and desktop.closing() is True


def test_renderer_not_ready_requires_confirmation_before_exit():
    desktop = host()
    desktop.window.handled = False
    desktop.close_pending.acquire()
    desktop.request_close()
    assert desktop.window.dialogs and not desktop.window.destroyed
    desktop.window.confirmed = True
    desktop.close_pending.acquire()
    desktop.request_close()
    assert desktop.window.destroyed and desktop.approved.is_set()


def test_failed_renderer_gets_a_confirmed_exit_without_losing_work_silently():
    desktop = host()
    def broken(_script):
        raise RuntimeError("Renderer is unavailable")
    desktop.window.evaluate_js = broken
    desktop.close_pending.acquire()
    desktop.request_close()
    assert not desktop.window.destroyed
    desktop.window.confirmed = True
    desktop.close_pending.acquire()
    desktop.request_close()
    assert desktop.window.destroyed


def test_remembered_quit_choice_also_applies_to_the_title_bar(tmp_path):
    from pdfstudio.preferences import Preferences
    preferences = Preferences(tmp_path)
    preferences.update({"confirmQuit": False})
    desktop = host()
    desktop.app = SimpleNamespace(extensions={"preferences": preferences})
    desktop.close_pending.acquire()
    desktop.request_close()
    assert desktop.window.destroyed and desktop.approved.is_set()
    assert not desktop.window.dialogs and not desktop.window.scripts
