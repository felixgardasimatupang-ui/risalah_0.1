#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

show_usage() {
    echo "Penggunaan: ./scripts/run_pipeline.sh <input> [options]"
    echo ""
    echo "  input: file audio ATAU folder berisi audio + dokumen"
    echo ""
    echo "Options:"
    echo "  --engine whisper|assemblyai|gemini   Engine transkripsi (default: whisper)"
    echo "  --no-parallel                        Nonaktifkan paralel transkrip+diarize"
    echo "  --preview                            Preview TXT saja (tanpa DOCX)"
    echo "  --skip transcribe diarize            Skip stage tertentu"
    echo "  --nomor NOMOR                        Nomor dokumen"
    echo "  --klasifikasi BIASA|TERBATAS|RAHASIA Klasifikasi (default: BIASA)"
    echo "  --doc-analysis                       Analisis dokumen pendukung"
    echo "  --title TITLE                        Judul risalah"
    echo ""
    echo "Contoh:"
    echo "  ./scripts/run_pipeline.sh rekaman.mp4"
    echo "  ./scripts/run_pipeline.sh folder_rapat/ --engine assemblyai"
    echo "  ./scripts/run_pipeline.sh rekaman.mp4 --preview"
    echo "  ./scripts/run_pipeline.sh rekaman.mp4 --no-parallel"
    exit 1
}

if [ $# -lt 1 ]; then
    show_usage
fi

INPUT="$1"
shift

if [ ! -e "$INPUT" ]; then
    echo "Error: '$INPUT' tidak ditemukan."
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "Error: .venv tidak ditemukan. Jalankan ./scripts/setup.sh dulu."
    exit 1
fi

source .venv/bin/activate

echo "============================================"
echo "  RISALAH RAPAT PIPELINE"
echo "  Input : $INPUT"
echo "============================================"
echo ""

python risalah/pipeline.py "$INPUT" "$@"

echo ""
echo "Selesai! Cek folder output/docs/ untuk file DOCX."
