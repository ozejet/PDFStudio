"""Representative local-engine import benchmark; no user documents or UI claims."""
import ctypes
import io
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fitz
from PIL import Image
from pdfstudio.app import create_app


def memory_mb():
    from ctypes import wintypes as w
    class Counters(ctypes.Structure):
        _fields_ = [("cb", w.DWORD), ("faults", w.DWORD)] + [(name, ctypes.c_size_t) for name in ("peak", "working", "pagedPeak", "paged", "nonpagedPeak", "nonpaged", "pagefile", "peakPagefile", "private")]
    psapi = ctypes.WinDLL("psapi")
    psapi.GetProcessMemoryInfo.argtypes = [w.HANDLE, ctypes.c_void_p, w.DWORD]
    kernel = ctypes.WinDLL("kernel32")
    kernel.GetCurrentProcess.restype = w.HANDLE
    values = Counters(); values.cb = ctypes.sizeof(values)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(values), values.cb):
        raise ctypes.WinError()
    return {"working_mb": round(values.working / 1024**2, 1), "process_peak_mb": round(values.peak / 1024**2, 1)}


def main():
    image = io.BytesIO()
    Image.effect_noise((1275, 1650), 40).convert("RGB").save(image, format="JPEG", quality=72)
    fixtures = []
    for scanned in (False, True):
        with fitz.open() as pdf:
            for index in range(10):
                page = pdf.new_page()
                if scanned:
                    page.insert_image(page.rect, stream=image.getvalue())
                else:
                    page.insert_textbox((40, 50, 550, 800), ("Synthetic ordinary document paragraph for import measurement.\n\n" * 24), fontsize=11)
            fixtures.append(pdf.tobytes(deflate=True))
    app = create_app(Path(".runtime/benchmark-data"), testing=True)
    client = app.test_client()
    headers = {"X-Studio-Token": app.config["STUDIO_TOKEN"]}
    files = [(io.BytesIO(fixtures[index % 2]), f"synthetic-{index}.pdf") for index in range(100)]
    before = memory_mb()
    started = time.perf_counter()
    try:
        response = client.post("/api/import-jobs", headers=headers, data={"files": files})
        assert response.status_code == 200, response.json
        job = response.json["id"]
        while True:
            state = client.get("/api/import-jobs/" + job, headers=headers).json
            if state["done"]:
                break
            time.sleep(.01)
        duration = time.perf_counter() - started
        assert len(state["documents"]) == 100 and not state["errors"], state["errors"]
        after = memory_mb()
        rejected = client.post("/api/import-jobs", headers=headers, data={"files": [(io.BytesIO(fixtures[0]), "101.pdf")]})
        assert rejected.status_code == 400
        result = dict(files=100, pages=1000, scanned_files=50, source_mb=round(50 * sum(map(len, fixtures)) / 1024**2, 1), seconds=round(duration, 2), before=before, after=after, rejected_101st=True, scope="Local Flask engine including multipart upload staging and normalization; excludes real browser rendering")
        destination = Path(".runtime/import-benchmark-0.1.006.json")
        destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
    finally:
        app.extensions["imports"].close()
        app.extensions["workspace"].close()


if __name__ == "__main__":
    main()
