"""Exercise the bundled Office converter with synthetic Word/PowerPoint files.

Artifacts stay in vendor/smoke-check for inspection. Requires only Python's
standard library and the extracted LibreOffice runtime; no installed Office.
"""
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "vendor" / "smoke-check"
FOLDER.mkdir(exist_ok=True)
NAMESPACES = '''xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"
xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"
xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0"
xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"
office:version="1.3"'''

(FOLDER / "word-test.fodt").write_text(
    '<?xml version="1.0" encoding="UTF-8"?><office:document ' + NAMESPACES + '''
office:mimetype="application/vnd.oasis.opendocument.text">
<office:body><office:text><text:p>PDF Studio local Word conversion test.</text:p>
</office:text></office:body></office:document>''', encoding="utf-8")
(FOLDER / "slides-test.fodp").write_text(
    '<?xml version="1.0" encoding="UTF-8"?><office:document ' + NAMESPACES + '''
office:mimetype="application/vnd.oasis.opendocument.presentation">
<office:automatic-styles><style:page-layout style:name="PM1">
<style:page-layout-properties fo:page-width="28cm" fo:page-height="21cm"
style:print-orientation="landscape"/></style:page-layout></office:automatic-styles>
<office:master-styles><style:master-page style:name="Default" style:page-layout-name="PM1"/>
</office:master-styles><office:body><office:presentation>
<draw:page draw:name="Slide 1" draw:master-page-name="Default">
<draw:frame svg:x="2cm" svg:y="2cm" svg:width="24cm" svg:height="5cm">
<draw:text-box><text:p>PDF Studio local PowerPoint conversion test.</text:p></draw:text-box>
</draw:frame></draw:page></office:presentation></office:body></office:document>''', encoding="utf-8")

EXE = ROOT / "vendor" / "libreoffice" / "program" / "soffice.com"
BASE = [str(EXE), "-env:UserInstallation=" + (FOLDER / "profile").as_uri(),
        "--headless", "--norestore", "--convert-to"]
for extension, name, source_extension in [("docx", "word-test", "fodt"), ("pptx", "slides-test", "fodp")]:
    result = subprocess.run(BASE + [extension, "--outdir", str(FOLDER), str(FOLDER / f"{name}.{source_extension}")],
                            capture_output=True, text=True, timeout=90, check=True)
    print(result.stdout.strip(), flush=True)
    source = FOLDER / f"{name}.{extension}"
    assert source.exists(), result.stderr
    result = subprocess.run(BASE + ["pdf", "--outdir", str(FOLDER), str(source)],
                            capture_output=True, text=True, timeout=90, check=True)
    print(result.stdout.strip(), flush=True)
    output = FOLDER / f"{name}.pdf"
    assert output.read_bytes().startswith(b"%PDF-"), result.stderr
    print(f"PASS {output.name}: {output.stat().st_size} bytes", flush=True)
