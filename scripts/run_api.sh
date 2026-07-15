#!/bin/bash
# Jalankan API server + Celery worker
# Prasyarat: Redis harus berjalan (brew services start redis)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR" || exit 1

echo "=== Risalah Rapat API ==="
echo ""

# Cek Redis
if ! redis-cli ping 2>/dev/null; then
    echo "⚠️  Redis tidak berjalan. Jalankan: brew services start redis"
    echo "   atau: redis-server"
    echo ""
fi

# Cek .env
if [ ! -f .env ]; then
    echo "❌ .env tidak ditemukan. Copy dari .env.template"
    exit 1
fi

echo "Memulai Celery worker di background..."
celery -A api.celery_app worker --loglevel=info --concurrency=2 &
CELERY_PID=$!
echo "  Celery PID: $CELERY_PID"

echo ""
echo "Memulai FastAPI server..."
echo "  Docs: http://localhost:8000/docs"
echo "  API:  http://localhost:8000/api"
echo ""

uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload

# Cleanup
kill $CELERY_PID 2>/dev/null
echo "Server berhenti."
