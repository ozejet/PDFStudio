"""Start PDF Studio. The production interface and all processing run locally."""
from __future__ import annotations

import argparse
import sys
import threading
import webbrowser


def main():
    if "--source-worker" in sys.argv:
        from pdfstudio.source_worker import worker_main
        position = sys.argv.index("--source-worker")
        try:
            worker_main(sys.argv[position + 1], sys.argv[position + 2])
        except ValueError as error:
            from pathlib import Path
            import json
            Path(sys.argv[position + 2]).with_suffix(".error.json").write_text(json.dumps({"error": str(error)}), encoding="utf-8")
            raise SystemExit(1)
        return
    from pdfstudio.windows_integration import set_app_identity
    set_app_identity()
    if "--dialog" in sys.argv:
        from pdfstudio.dialogs import dialog_main
        dialog_main()
        return
    parser = argparse.ArgumentParser(description="PDF Studio - local desktop workspace")
    parser.add_argument("files", nargs="*", help="Local files passed by Windows Open with")
    parser.add_argument("--port", type=int, default=0, help="Local port; default selects a free port")
    display = parser.add_mutually_exclusive_group()
    display.add_argument("--browser", action="store_true", help="Open a browser workspace instead of the desktop window")
    display.add_argument("--no-browser", action="store_true", help="Run the local engine without opening a window (automation)")
    parser.add_argument("--data-dir", help="Override the local profile directory (development/testing)")
    parser.add_argument("--register-windows", action="store_true", help="Register app/PDF icons and create Desktop/Start menu shortcuts for this user")
    args = parser.parse_args()
    if args.register_windows:
        if sys.platform != "win32" or not getattr(sys, "frozen", False):
            raise SystemExit("Use PDFStudio.exe --register-windows from the Windows application folder.")
        from pathlib import Path
        import json
        from pdfstudio.windows_integration import register_windows
        destination = Path(sys.executable).parent / "windows-integration.json"
        try:
            report = register_windows(Path(sys.executable))
        except (OSError, ValueError) as error:
            destination.write_text(json.dumps(dict(registered=False, error=str(error)), indent=2), encoding="utf-8")
            raise SystemExit(1)
        destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return
    from werkzeug.serving import make_server
    from pdfstudio.app import create_app
    from pdfstudio.storage import app_root
    if not (app_root() / "web/dist/index.html").exists():
        print("The browser interface is not built. See README.md for the development setup.")
        raise SystemExit(1)
    from pathlib import Path
    app = create_app(Path(args.data_dir) if args.data_dir else None)
    from pdfstudio.launch import open_launch_files
    open_launch_files(app, args.files)
    server = make_server("127.0.0.1", args.port, app, threaded=True)
    server.daemon_threads = False
    app.extensions["shutdown"] = server.shutdown
    url = f"http://127.0.0.1:{server.server_port}"
    print(f"PDF Studio is ready: {url}", flush=True)
    print("All document processing stays on this device. Use Quit in the app to stop.", flush=True)
    try:
        if sys.platform == "win32" and not args.browser and not args.no_browser:
            from pdfstudio.desktop import run_desktop
            run_desktop(app, url, server)
        else:
            if not args.no_browser:
                if sys.platform == "darwin":
                    from pdfstudio.app import open_external_url
                    threading.Timer(.4, lambda: open_external_url(url)).start()
                else:
                    threading.Timer(.4, lambda: webbrowser.open(url)).start()
            server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        app.extensions["imports"].close()
        app.extensions["sources"].close()
        app.extensions["workspace"].close()


if __name__ == "__main__":
    main()
