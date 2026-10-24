"""Copy the selected design system and self-hosted fonts into the UI build."""
from pathlib import Path
import re
import shutil

root = Path(__file__).resolve().parents[1]
theme = (root / "design-system/talit02/source/system.css").read_text(encoding="utf-8")
theme = re.sub(r'@import\s+url\([^)]*\)\s*;\s*', '', theme)
(root / "web/src/talit02.css").write_text(theme, encoding="utf-8", newline="\n")
font_source = root / "design-system/talit02/fonts"
public = root / "web/public/fonts"
public.mkdir(parents=True, exist_ok=True)
for font in font_source.glob("*.woff2"):
    shutil.copyfile(font, public / font.name)
shutil.copyfile(font_source / "OFL.txt", public / "OFL.txt")
css = (font_source / "sarabun.css").read_text(encoding="utf-8").replace("url(sarabun-", "url(/fonts/sarabun-")
(root / "web/src/fonts.css").write_text(css, encoding="utf-8", newline="\n")
print("Prepared talit02 and local Sarabun fonts.")
