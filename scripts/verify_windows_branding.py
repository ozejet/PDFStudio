"""Verify the EXE embeds the prepared logo at every size, plus product metadata."""
import argparse
import io
from pathlib import Path
import struct
import sys

import pefile
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pdfstudio import __version__
from scripts.prepare_branding import WINDOWS_SIZES


def verify(executable):
    pe = pefile.PE(str(executable))
    icons, groups = {}, []
    for resource in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if resource.id not in (3, 14):
            continue
        for item in resource.directory.entries:
            leaf = item.directory.entries[0].data.struct
            data = pe.get_data(leaf.OffsetToData, leaf.Size)
            if resource.id == 3:
                icons[item.id] = data
            else:
                groups.append(data)
    assert len(groups) == 1, "Expected one application logo resource"
    count = struct.unpack_from("<H", groups[0], 4)[0]
    sizes = set()
    for index in range(count):
        width, height, _colors, _reserved, _planes, _depth, _bytes, resource_id = struct.unpack_from("<BBBBHHIH", groups[0], 6 + index * 14)
        width, height = width or 256, height or 256
        sizes.add(width)
        assert width == height
        with Image.open(io.BytesIO(icons[resource_id])) as actual, Image.open(ROOT / f"web/public/branding/pdfstudio-{width}.png") as expected:
            assert actual.convert("RGBA").tobytes() == expected.convert("RGBA").tobytes(), f"Icon {width} differs from the supplied logo"
    assert sizes == set(WINDOWS_SIZES)
    strings = {}
    for block in pe.FileInfo:
        for entry in block:
            if entry.Key == b"StringFileInfo":
                for table in entry.StringTable:
                    strings.update(table.entries)
    assert strings[b"ProductName"] == b"PDF Studio"
    assert strings[b"FileDescription"] == b"PDF Studio"
    assert strings[b"FileVersion"].decode() == __version__
    pe.close()
    print(f"PASS: embedded PDF Studio logo at {sorted(sizes)} pixels; product/version {__version__}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    verify(parser.parse_args().executable)
