#!/bin/bash
set -e
cd "$(dirname "$0")/.."
echo "🧹 Clean..."
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
find . -type f -name '*.pyc' -delete 2>/dev/null || true
echo "✅ Clean OK"
