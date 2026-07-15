#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

if [ $# -lt 1 ]; then
    echo "Penggunaan: ./scripts/run_pipeline.sh <file_audio> [engine]"
    echo "  engine: whisper (default) atau assemblyai"
    exit 1
fi

AUDIO_FILE="$1"
ENGINE="${2:-whisper}"

if [ ! -f "$AUDIO_FILE" ]; then
    echo "Error: File '$AUDIO_FILE' tidak ditemukan."
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "Error: .venv tidak ditemukan. Jalankan ./scripts/setup.sh dulu."
    exit 1
fi

source .venv/bin/activate

echo "============================================"
echo "  RISALAH RAPAT PIPELINE"
echo "  Audio : $AUDIO_FILE"
echo "  Engine: $ENGINE"
echo "============================================"
echo ""

python risalah/pipeline.py "$AUDIO_FILE" --engine "$ENGINE"

echo ""
echo "Selesai! Cek folder output/docs/ untuk file DOCX."
