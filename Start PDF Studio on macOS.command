#!/bin/zsh
set -euo pipefail

project_dir="${0:A:h}"
cd "$project_dir"

if [[ ! -x "$project_dir/.venv/bin/python" ]]; then
  /usr/bin/osascript -e 'display alert "PDF Studio is not set up" message "Follow docs/macos/README.en.md or README.th.md to create the local Python environment first." as critical'
  exit 1
fi

if [[ ! -f "$project_dir/web/dist/index.html" ]]; then
  /usr/bin/osascript -e 'display alert "PDF Studio web files are missing" message "Build the browser interface first with npm --prefix web run build." as critical'
  exit 1
fi

exec "$project_dir/.venv/bin/python" "$project_dir/run.py" "$@"
