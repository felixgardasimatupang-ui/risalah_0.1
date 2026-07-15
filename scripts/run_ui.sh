#!/bin/bash
# Jalankan Streamlit UI
# Prasyarat: API server harus berjalan dulu

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR" || exit 1

echo "=== Risalah Rapat UI ==="
echo ""

if [ ! -f .env ]; then
    echo "❌ .env tidak ditemukan"
    exit 1
fi

echo "Memulai Streamlit UI..."
echo "  http://localhost:8501"
echo ""

streamlit run ui/app.py --server.port 8501 --server.address 0.0.0.0
