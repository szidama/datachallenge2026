#!/bin/zsh
set -eu
cd "${0:A:h}"
for atlas_python in "$PWD/.venv/bin/python" "$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3" python3; do
  if "$atlas_python" -c 'import openpyxl' 2>/dev/null; then
    exec "$atlas_python" scripts/demonstration.py
  fi
done
print 'Installez Python et les dépendances indiquées dans README.md.'
exit 1
