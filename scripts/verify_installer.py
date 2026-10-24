"""Exercise the real installer without changing user shortcuts or registration."""
from __future__ import annotations

import argparse
import http.cookiejar
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pdfstudio import __version__


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('installer', type=Path)
    parser.add_argument('--target', type=Path, help='Fresh test path inside the project tmp directory')
    parser.add_argument('--resume', action='store_true', help='Continue checks after a completed test installation')
    args = parser.parse_args()
    installer = args.installer.resolve(strict=True)
    target = (args.target or ROOT / 'tmp' / ('installer-' + __version__) / "Owner's & local \u0e44\u0e17\u0e22").resolve()
    assert target.is_relative_to(ROOT / 'tmp')
    if target.exists() and not args.resume:
        raise SystemExit('Test destination already exists; use a fresh test directory: ' + str(target))
    target.parent.mkdir(parents=True, exist_ok=True)
    logfile = target.parent / 'install.log'

    def install(log=logfile):
        return subprocess.run([str(installer), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
                               '/TESTMODE=1', '/DIR=' + str(target), '/LOG=' + str(log)],
                              timeout=1800).returncode

    if args.resume:
        assert target.is_dir()
    else:
        assert install() == 0, logfile
    version_dir = target / 'versions' / __version__
    executable = version_dir / 'PDFStudio.exe'
    assert executable.is_file() and list((version_dir / '_internal').glob('python3[0-9]*.dll'))
    assert not (version_dir / 'windows-integration.json').exists()
    # An interrupted setup can leave an empty unins000.dat. Inno chooses a
    # new number on retry; use the latest completed uninstall log.
    uninstall_logs = [path for path in (target / 'uninstall').glob('unins*.dat')
                      if path.stat().st_size and path.with_suffix('.exe').is_file()]
    assert uninstall_logs, 'No completed installer uninstall log was found'
    uninstaller = max(uninstall_logs, key=lambda path: path.stat().st_mtime).with_suffix('.exe')
    # Source documents saved by a user in either directory must survive uninstall.
    sources = [target / 'synthetic-source.txt', version_dir / 'synthetic-source.txt']
    for source in sources:
        source.write_text('Preserve this synthetic user document.', encoding='utf-8')
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
    base = f'http://127.0.0.1:{port}'
    process = subprocess.Popen([str(executable), '--no-browser', '--port', str(port),
                                '--data-dir', str(target.parent / 'test-data')],
                               creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        deadline = time.monotonic() + 60
        while True:
            try:
                with urllib.request.urlopen(base + '/api/health', timeout=2) as response:
                    assert json.load(response)['version'] == __version__
                break
            except OSError:
                if time.monotonic() > deadline or process.poll() is not None:
                    raise AssertionError('Installed application failed to start')
                time.sleep(.25)
        print('PASS: standalone setup installed and launched from a Unicode path', flush=True)
        client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        with client.open(base + '/', timeout=10) as response:
            response.read()  # The landing page supplies the per-launch cookie.
        with client.open(base + '/api/config', timeout=10) as response:
            config = json.load(response)
        import fitz
        with fitz.open() as pdf:
            pdf.new_page().insert_text((50, 50), 'Preserve this open synthetic session.')
            content = pdf.tobytes()
        boundary = 'pdfstudio-installer-session-test'
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="files"; '
                'filename="open-session.pdf"\r\nContent-Type: application/pdf\r\n\r\n').encode()
        body += content + f'\r\n--{boundary}--\r\n'.encode()
        request = urllib.request.Request(base + '/api/documents', data=body,
                                        headers={'X-Studio-Token': config['token'],
                                                 'Content-Type': 'multipart/form-data; boundary=' + boundary})
        with client.open(request, timeout=30) as response:
            document = json.load(response)['documents'][0]
        # A live reinstall must fail before it changes any of the runtime files.
        reinstall_log = target.parent / 'reinstall.log'
        assert install(reinstall_log) != 0
        assert process.poll() is None
        assert 'Your session has been left open' in reinstall_log.read_text(encoding='utf-8-sig')
        subprocess.run([str(uninstaller), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART'], timeout=60)
        assert process.poll() is None and executable.is_file()
        with client.open(base + '/api/config', timeout=10) as response:
            preserved = json.load(response)
        assert preserved['token'] == config['token']
        assert document['id'] in [item['id'] for item in preserved['documents']]
        print('PASS: reinstall and uninstall preserve the running session and its open PDF', flush=True)
        subprocess.run([sys.executable, str(ROOT / 'scripts/verify_http_runtime.py'), base,
                        '--office', '--sources', '--encoding-recovery', '--controls', '--quit'], check=True, timeout=600)
        process.wait(timeout=60)
    finally:
        if process.poll() is None:
            # This is exclusively the synthetic session created by this test.
            process.terminate()
            process.wait(timeout=30)
    subprocess.run([str(uninstaller), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART'],
                   check=True, timeout=900)
    # Inno's uninstaller delegates to a temporary copy, so wait for deletion.
    deadline = time.monotonic() + 180
    while executable.exists() and time.monotonic() < deadline:
        time.sleep(.25)
    assert not executable.exists()
    assert all(source.read_text(encoding='utf-8') == 'Preserve this synthetic user document.' for source in sources)
    print('PASS: uninstall removed installed binaries and preserved synthetic user documents', flush=True)


if __name__ == '__main__':
    main()
