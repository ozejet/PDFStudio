"""Package a complete Windows bundle into one offline Inno Setup installer."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pdfstudio import __version__
from pdfstudio.windows_integration import registration_entries


def quote(value: str) -> str:
    # Escape Inno constants and quotes in literal build paths / registry strings.
    return '"' + value.replace('{', '{{').replace('"', '""') + '"'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True, help='Fresh bundle from build_windows.py')
    parser.add_argument('--iscc', type=Path, help='Inno Setup 7 ISCC.exe (build tool only)')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'dist/installers')
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    required = ['PDFStudio.exe', '_internal/web/dist/index.html',
                '_internal/web/dist/branding/pdfstudio.ico',
                '_internal/vendor/libreoffice/program/soffice.com',
                '_internal/vendor/prerequisites/VC_redist.x64.exe',
                '_internal/vendor/prerequisites/vc-redist.json',
                '_internal/vendor/prerequisites/webview2.json',
                '_internal/vendor/prerequisites/MicrosoftEdgeWebView2RuntimeInstallerX64.exe',
                '_internal/webview/lib/Microsoft.Web.WebView2.Core.dll']
    missing = [name for name in required if not (bundle / name).is_file()]
    python_dll = f'python{sys.version_info.major}{sys.version_info.minor}.dll'
    if not (bundle / '_internal' / python_dll).is_file():
        missing.append('_internal/' + python_dll)
    if missing:
        raise SystemExit('A complete Windows bundle is required: ' + ', '.join(missing))
    # Prevent shipping an older launcher under the new installer's version.
    from PyInstaller.utils.win32.versioninfo import read_version_info_from_executable
    info = str(read_version_info_from_executable(str(bundle / 'PDFStudio.exe')))
    if f"StringStruct('ProductVersion', '{__version__}')" not in info:
        raise SystemExit('Bundle version does not match ' + __version__ + '. Rebuild it first.')
    prerequisite = json.loads((bundle / '_internal/vendor/prerequisites/vc-redist.json').read_text())
    import hashlib
    redist = bundle / '_internal/vendor/prerequisites/VC_redist.x64.exe'
    with redist.open('rb') as stream:
        redist_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
    if redist_hash != prerequisite['sha256']:
        raise SystemExit('The bundled Microsoft prerequisite checksum does not match its manifest.')
    desktop = json.loads((bundle / '_internal/vendor/prerequisites/webview2.json').read_text())
    with (bundle / desktop['path'].replace('vendor/', '_internal/vendor/', 1)).open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != desktop['sha256']:
            raise SystemExit('The bundled WebView2 prerequisite checksum does not match its manifest.')
    compiler = args.iscc or shutil.which('ISCC.exe') or ROOT / 'build/tools/inno-7.1.0/ISCC.exe'
    if not Path(compiler).is_file():
        raise SystemExit('Inno Setup 7 is required on the build computer. Pass --iscc PATH/ISCC.exe.')
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    generated = ROOT / 'build/installer'
    generated.mkdir(parents=True, exist_ok=True)
    executable = Path('{app}') / 'versions' / __version__ / 'PDFStudio.exe'
    icon = executable.parent / '_internal/web/dist/branding/pdfstudio.ico'
    entries = []
    for path, name, value, kind in registration_entries(executable, icon):
        # These two shared keys contain other applications' registrations.
        shared = path in (r'Software\Classes\.pdf\OpenWithProgids', r'Software\RegisteredApplications')
        flags = 'uninsdeletevalue' if shared else 'uninsdeletekey'
        encoded = quote(str(value)) if kind != 'none' else '""'
        # {app} is an installer constant; other braces remain literal.
        encoded = encoded.replace('{{app}', '{app}')
        # Inno's 'none' creates only a key. OpenWithProgids needs a named
        # empty REG_SZ value (also accepted by the Windows shell).
        entry_type = {'string': 'string', 'expand': 'expandsz', 'none': 'string'}[kind]
        entries.append(f'Root: HKCU; Subkey: {quote(path)}; ValueType: {entry_type}; '
                       f'ValueName: {quote(name)}; ValueData: {encoded}; Flags: {flags}; Check: not IsTestInstall')
    (generated / 'registration.iss').write_text('\n'.join(entries) + '\n', encoding='utf-8-sig')
    version_numbers = '.'.join(str(int(n)) for n in __version__.split('.')) + '.0'
    command = [str(compiler), '/Qp', '/DAppVersion=' + __version__, '/DVersionNumbers=' + version_numbers,
               '/DBundleDir=' + str(bundle), '/DInstallerOutput=' + str(output),
               '/DGeneratedDir=' + str(generated), '/DRedistVersion=' + prerequisite['version'],
               '/DMinimumWebView2Version=' + desktop['minimum_version'],
               str(ROOT / 'packaging/windows-installer.iss')]
    subprocess.run(command, cwd=ROOT, check=True)
    installer = output / f'PDFStudio-Setup-{__version__}.exe'
    with installer.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    installer.with_suffix('.exe.sha256').write_text(digest + '  ' + installer.name + '\n', encoding='ascii')
    print('Installer:', installer)
    print('Distribute only this EXE. The checksum file is optional.')


if __name__ == '__main__':
    main()
