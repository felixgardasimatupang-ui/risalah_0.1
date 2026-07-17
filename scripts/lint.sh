#!/bin/bash
set -e
cd "$(dirname "$0")/.."
source .venv/bin/activate
ruff check api/ risalah/ ui/ --fix
echo "✅ Lint OK"
