"""Bump the public version and synchronize package metadata, or verify it."""
import argparse
import json
from pathlib import Path
import re
import tomllib

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--check", action="store_true", help="Check consistency without changing files")
args = parser.parse_args()
source = root / "pdfstudio/__init__.py"
text = source.read_text(encoding="utf-8")
match = re.search(r'__version__ = "(\d+)\.(\d+)\.(\d+)"', text)
if not match:
    raise SystemExit("The application version is missing or invalid.")
major, minor, revision = map(int, match.groups())
if not args.check:
    revision += 1
    if revision > 999:
        minor, revision = minor + 1, 0
public = f"{major}.{minor}.{revision:03d}"
numeric = f"{major}.{minor}.{revision}"
project = root / "pyproject.toml"
package = root / "web/package.json"
lock = root / "web/package-lock.json"
package_data = json.loads(package.read_text(encoding="utf-8"))
lock_data = json.loads(lock.read_text(encoding="utf-8"))
if args.check:
    if match.group(0) != f'__version__ = "{public}"':
        raise SystemExit("The public revision must have exactly three digits.")
    metadata = tomllib.loads(project.read_text(encoding="utf-8"))["project"]["version"]
    if any(value != numeric for value in (metadata, package_data["version"], lock_data["version"], lock_data["packages"][""]["version"])):
        raise SystemExit("Package versions are out of sync. Run scripts/bump_version.py.")
else:
    source.write_text(text[:match.start()] + f'__version__ = "{public}"' + text[match.end():], encoding="utf-8")
    project.write_text(re.sub(r'(?m)^version = "[^"]+"$', f'version = "{numeric}"', project.read_text(encoding="utf-8")), encoding="utf-8")
    package_data["version"] = numeric
    lock_data["version"] = numeric
    lock_data["packages"][""]["version"] = numeric
    package.write_text(json.dumps(package_data, indent=2) + "\n", encoding="utf-8")
    lock.write_text(json.dumps(lock_data, indent=2) + "\n", encoding="utf-8")
print("PDF Studio " + public + (" - version metadata verified" if args.check else " - version bumped"))
