# Risalah Rapat Otomatis

Pipeline 6-stage + UI Streamlit untuk menghasilkan **Risalah Rapat** (official meeting minutes) dari audio, khusus konteks pemerintahan Indonesia.

## Fitur

| Fitur | Status |
|-------|--------|
| **Pipeline 6-stage** — Audio → Split → Transkrip → Diarize → AI → DOCX | ✅ |
| **Transkripsi Dual Engine** — Whisper lokal (gratis) / AssemblyAI (cloud) | ✅ |
| **Speaker Diarization** — Pyannote dengan fallback VAD | ✅ |
| **AI Enhancement** — Groq → 9router → Gemini fallback chain | ✅ |
| **321 koreksi istilah Indonesia** — word-boundary regex, slang→formal | ✅ |
| **DOCX formal pemerintah** — kop risalah, daftar hadir, lampiran, ttd | ✅ |
| **Paralel transkrip + diarize** — hemat ~50% waktu | ✅ |
| **Caching per-chunk (MD5)** — skip file sudah diproses | ✅ |
| **Real-time mic transcription** — via Whisper base + normalisasi | ✅ |
| **Riwayat job** — SQLite cache (fallback saat Redis down) | ✅ |
| **Ringkasan eksekutif** — section pertama di DOCX + preview | ✅ |
| **Action items** — tabel tindak lanjut dgn PJ + deadline | ✅ |
| **Edit notulen** — edit teks → download ulang DOCX formal | ✅ |
| **Share email** — kirim DOCX via SMTP dari UI | ✅ |
| **Search by konten** — cari di preview_text | ✅ |
| **Dokumen pendukung** — scan folder + ekstraksi teks (OCR) | ✅ |
| **Codespaces ready** — devcontainer, skill bundle, 1-click setup | ✅ |
| **100% gratis tanpa batas** — offline capable, multi-file batch | ✅ |

## Alur Pipeline

```
Audio → Split 30 menit → Transkripsi (Whisper/AssemblyAI) ─┐
                          Speaker Diarization (Pyannote) ───┤→ Paralel!
                          Preprocessing (321 id_terms) ←────┘
                          AI Enhancement (Groq→9router→Gemini)
                          → DOCX (Word) → Siap cetak & tanda tangan!
```

## Quick Start

```bash
# 1. Setup environment
./scripts/setup.sh

# 2. Edit .env - isi API key
nano .env

# 3. Jalankan pipeline (CLI)
python risalah/pipeline.py rekaman_rapat.mp4

# ATAU jalankan UI Streamlit
streamlit run ui/app.py
```

## Prasyarat

- Python 3.10+ (3.9 terbatas)
- ffmpeg (`brew install ffmpeg`)
- API Key: [Groq](https://console.groq.com/keys) (wajib, gratis)
- Token: [HuggingFace](https://huggingface.co/settings/tokens) (wajib untuk diarization)
- API Key: [Gemini](https://aistudio.google.com/) (fallback, opsional)
- API Key: [AssemblyAI](https://www.assemblyai.com/) (opsional)

## Struktur Project

```
transkip/
├── risalah/                    # Core pipeline modules
│   ├── utils.py               # Retry, caching, parallel execution
│   ├── audio_processor.py     # Stage 1-2: Ingestion & Split
│   ├── transcriber.py         # Stage 3: Transkripsi
│   ├── diarizer.py            # Stage 4: Speaker Diarization
│   ├── ai_enhancer.py         # Stage 5: AI Enhancement (Groq→9router→Gemini)
│   ├── docx_generator.py      # Stage 6: DOCX Generator + edit + preview
│   ├── id_terms.py            # 321 koreksi istilah Indonesia
│   ├── file_scanner.py        # Scanner folder dokumen pendukung
│   ├── job_cache.py           # SQLite cache riwayat job
│   ├── email_utils.py         # SMTP email share
│   └── pipeline.py            # Orkestrator utama
├── api/                       # FastAPI backend
│   ├── app.py                 # Routes, upload, download, streaming
│   ├── celery_app.py          # Celery worker config
│   ├── config.py              # Environment config (LLM, Redis, dll)
│   ├── routes.py              # API endpoints
│   ├── schemas.py             # Pydantic schemas
│   ├── tasks.py               # Celery background tasks
│   └── websocket.py           # WebSocket progress streaming
├── ui/                        # Streamlit frontend
│   └── app.py                 # 5 pages: Upload, Rekam Langsung, Riwayat, Dokumen, Panduan
├── tests/                     # 64 test cases (51 pass in CI)
├── output/                    # Generated output
│   ├── chunks/                # Audio chunk 30 menit
│   ├── transcripts/           # Transkrip JSON (cache otomatis)
│   ├── diarization/           # Diarization JSON (cache otomatis)
│   ├── enhanced/              # AI enhancement JSON
│   ├── docs/                  # Final DOCX risalah
│   └── extracted_text/        # Text ekstraksi dokumen pendukung
├── scripts/                   # Shell utilities
├── .devcontainer/             # Codespaces: devcontainer.json + setup.sh + skill bundle
├── docker-compose.yml         # API + UI + Celery worker
├── Dockerfile                 # Container image
└── .env.template              # Template konfigurasi
```

## UI Pages (Streamlit)

| Page | Function |
|------|----------|
| **Upload & Transkripsi** | Upload file → pipeline → download DOCX |
| **Rekam Langsung** | Browser mic → real-time transcript → edit → download |
| **Riwayat Job** | Search, preview, export DOCX/TXT, edit & download, share email |
| **Dokumen Pendukung** | Lihat hasil scan folder + extracted text |
| **Panduan** | Cara pakai lengkap |

## CLI Options

```bash
# Pipeline lengkap
python risalah/pipeline.py rekaman.mp4

# Pilih engine transkripsi
python risalah/pipeline.py rekaman.mp4 --engine assemblyai

# Nonaktifkan paralel
python risalah/pipeline.py rekaman.mp4 --no-parallel

# Skip stage tertentu
python risalah/pipeline.py rekaman.mp4 --skip transcribe diarize

# Preview TXT saja (tanpa DOCX)
python risalah/pipeline.py rekaman.mp4 --preview

# Jalankan stage tertentu
python risalah/pipeline.py rekaman.mp4 --stage transcribe-only
python risalah/pipeline.py rekaman.mp4 --stage docx-only
```

## API / Celery

```bash
# Jalankan API server
uvicorn api.app:app --reload --port 8000

# Jalankan Celery worker (background job)
celery -A api.celery_app worker --loglevel=info

# Jalankan UI
streamlit run ui/app.py --server.port 8501
```

## Docker

```bash
# Build & jalankan semua service
docker compose up --build

# Service:
# - API: http://localhost:8000
# - UI:  http://localhost:8501
```

## Codespaces

Buka repo di GitHub → klik "Code" → "Open in Codespaces". Semua skill & agent terkonfigurasi otomatis.

## Optimasi Pipeline

| Fitur | Keterangan |
|-------|-----------|
| **Paralel** | Transkripsi + Diarization via ThreadPoolExecutor |
| **Retry** | Exponential backoff (3x) untuk semua API eksternal |
| **Caching** | per-chunk MD5, skip jika sudah diproses |
| **AI Fallback** | Groq (prioritas) → 9router → Gemini |
| **Diarization Fallback** | Pyannote → SpeechBrain → VAD |
| **Pipeline Fallback** | Paralel fail → sequential; Pyannote fail → VAD |
| **Preprocessing** | 321 istilah + slang normalization sebelum AI |

## Istilah Pemerintahan (321 Terms)

8 kategori: INSTITUSI, JABATAN, DAERAH, LEMBAGA, DOKUMEN, RAPAT, ASR_ERRORS, SLANG.
Contoh: APBD, Perda, Permendagri, TUPOKSI, Musrenbang, DPA, KUA-PPAS, Sekda, Kadis, dll.

## Output DOCX

File DOCX di `output/docs/`:
- Kop "RISALAH RAPAT" + klasifikasi (BIASA/TERBATAS/RAHASIA)
- Informasi rapat (hari, tanggal, waktu, tempat, acara)
- Daftar hadir (nama & jabatan)
- Ringkasan eksekutif
- Isi risalah (tabel pembicara + timestamp)
- Kesimpulan, keputusan, tindak lanjut (tabel PJ + deadline)
- Lampiran dokumen terkait
- Tanda tangan (Pimpinan, Mengetahui, Notulis)

## Testing

```bash
# Semua test
pytest tests/ -v

# Test spesifik
pytest tests/test_docx_generator.py
pytest tests/test_id_terms.py
pytest tests/test_job_cache.py
```

Hasil: **51 passed, 2 skipped** (env deps), 0 failure.
