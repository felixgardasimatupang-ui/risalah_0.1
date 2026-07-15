#!/bin/bash
set -e

echo "=== SETUP RISALAH RAPAT PIPELINE ==="
echo ""

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "1. Virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate

echo "2. Upgrade pip..."
pip install --quiet --upgrade pip

echo "3. Install semua dependencies (termasuk PyMuPDF, openpyxl, Pillow)..."
pip install --quiet -r requirements.txt
pip install --quiet pyannote.audio 2>/dev/null || echo "   pyannote.audio butuh Python 3.10+ — speaker diarization skip"

echo ""
echo "4. Setup .env..."
if [ ! -f ".env" ]; then
    cp .env.template .env
    echo "   .env dibuat. Isi API key!"
fi

echo ""
echo "=== SETUP SELESAI ==="
echo ""
echo "Cara pakai:"
echo "  python risalah/pipeline.py rekaman.mp4                    # DOCX standar"
echo "  python risalah/pipeline.py folder_rapat/                  # Semua file di folder"
echo "  python risalah/pipeline.py rekaman.mp4 --preview          # Preview dulu"
echo "  python risalah/pipeline.py rekaman.mp4 --nomor 001/RISALAH/DINAS/2026"
echo "  python risalah/pipeline.py rekaman.mp4 --klasifikasi RAHASIA"
