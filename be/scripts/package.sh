#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

: "${PYTHON_BIN:=python}"

echo "==> syntax check"
"${PYTHON_BIN}" -m compileall -q medical_news scripts

echo "==> build python lambda package"
rm -rf dist
mkdir -p dist
"${PYTHON_BIN}" -m pip install -r requirements.txt --target dist
cp -R medical_news dist/
find dist -type d -name __pycache__ -prune -exec rm -rf {} +

echo "==> package"
rm -f function.zip
"${PYTHON_BIN}" - <<'PY'
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

root = Path("dist")
with ZipFile("function.zip", "w", ZIP_DEFLATED) as zf:
    for path in root.rglob("*"):
        if path.is_file():
            zf.write(path, path.relative_to(root).as_posix())
PY
