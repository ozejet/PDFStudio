"""Check this release's isolated standalone bundle without touching user sessions."""
import http.cookiejar
import json
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import Request, build_opener, HTTPCookieProcessor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pdfstudio import __version__

bundle = ROOT / 'dist' / ('update-' + __version__) / 'PDFStudio'
url = 'http://127.0.0.1:43917'
process = subprocess.Popen([str(bundle / 'PDFStudio.exe'), '--no-browser', '--port', '43917', '--data-dir', str(ROOT / 'tmp' / ('frozen-feedback-' + __version__))], creationflags=subprocess.CREATE_NO_WINDOW)
client = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
token = ''
try:
    for _ in range(60):
        try:
            client.open(url, timeout=2).close()
            break
        except OSError:
            if process.poll() is not None:
                raise RuntimeError('The standalone application did not start.')
            time.sleep(1)
    with client.open(url + '/api/config', timeout=10) as response:
        config = json.load(response)
        assert config['version'] == __version__
        assert config['feedback']['url'].startswith('https://forms.cloud.microsoft/')
        token = config['token']
    with client.open(url + '/feedback-form.json', timeout=10) as response:
        assert json.load(response)['url'] == config['feedback']['url']
    subprocess.run([sys.executable, str(ROOT / 'scripts/verify_http_runtime.py'), url, '--sources', '--controls'], cwd=ROOT, check=True)
    print('Standalone feedback default, bundled UI, synthetic document workflows and source controls verified.')
finally:
    if token and process.poll() is None:
        try:
            client.open(Request(url + '/api/quit', data=b'{}', headers={'Content-Type':'application/json', 'X-Studio-Token':token}), timeout=10).close()
        except OSError:
            pass
    try:
        process.wait(timeout=20)
    except subprocess.TimeoutExpired:
        process.terminate()
        process.wait(timeout=10)
