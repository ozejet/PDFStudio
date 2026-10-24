import hashlib
import io
import json
from pathlib import Path
import shutil

from PIL import Image
import pytest

from scripts.prepare_branding import ROOT, WINDOWS_SIZES, branding_files, prepare


def test_master_artwork_and_optimized_sizes():
    master = ROOT / "assets/branding/pdfstudio-master.png"
    files, revision = branding_files(master)
    assert revision == hashlib.sha256(master.read_bytes()).hexdigest()[:12]
    for name, data in files.items():
        if name.endswith(".png"):
            with Image.open(io.BytesIO(data)) as image:
                size = int(Path(name).stem.rsplit("-", 1)[1])
                assert image.size == (size, size)
                assert image.mode == "RGBA" and image.getextrema()[3] == (0, 255)
    assert len(files["branding/pdfstudio-40.png"]) < 5_000
    assert len(files["branding/pdfstudio-80.png"]) < 10_000
    assert all(data != master.read_bytes() for data in files.values())
    with Image.open(io.BytesIO(files["branding/pdfstudio.ico"])) as icon:
        assert icon.ico.sizes() == {(n, n) for n in WINDOWS_SIZES}
    with Image.open(io.BytesIO(files["branding/favicon.ico"])) as icon:
        assert icon.ico.sizes() == {(16, 16), (32, 32), (48, 48)}
    manifest = json.loads(files["site.webmanifest"])
    assert manifest["name"] == "PDF Studio"
    assert [item["sizes"] for item in manifest["icons"]] == ["192x192", "512x512"]


def test_build_preparation_detects_stale_assets_and_preserves_other_html(tmp_path):
    (tmp_path / "assets/branding").mkdir(parents=True)
    (tmp_path / "web").mkdir()
    shutil.copy2(ROOT / "assets/branding/pdfstudio-master.png", tmp_path / "assets/branding/pdfstudio-master.png")
    index = tmp_path / "web/index.html"
    index.write_text('<html><head><title>PDF Studio</title></head><body>unchanged</body></html>')
    prepare(tmp_path)
    text = index.read_text()
    stamp = index.stat().st_mtime_ns
    prepare(tmp_path, check=True)
    prepare(tmp_path)
    assert index.stat().st_mtime_ns == stamp
    assert text.count("<!-- branding:start -->") == 1 and "<body>unchanged</body>" in text
    assert "apple-touch-icon" in text and "site.webmanifest" in text
    (tmp_path / "web/public/branding/pdfstudio-16.png").write_bytes(b"stale")
    with pytest.raises(ValueError, match="rebuilding"):
        prepare(tmp_path, check=True)
