#!/bin/bash
set -e
cd "$(dirname "$0")/.."
source .venv/bin/activate
ruff format api/ risalah/ ui/
echo "✅ Format OK"
