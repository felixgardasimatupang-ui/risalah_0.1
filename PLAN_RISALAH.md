# PLAN PROYEK RISALAH RAPAT OTOMATIS

## Ringkasan Eksekutif

Pipeline otomatis untuk menghasilkan **Risalah Rapat** (official meeting minutes) dari file audio rekaman rapat — khusus konteks pemerintahan Indonesia. 6-stage pipeline menggabungkan 5 teknologi AI:

```
Audio → Split 30 menit → Transkripsi (Whisper/AssemblyAI) ─┐
                          Speaker Diarization (Pyannote) ───┤→ Paralel!
                          Preprocessing (321 id_terms) ←────┘
                          AI Enhancement (Groq→9router→Gemini)
                          → DOCX (Word) → Siap cetak & tanda tangan!
```

**Ditambah UI Streamlit** untuk: upload & pipeline, real-time mic transcription, riwayat job, edit notulen, search, email share, dokumen pendukung.

---

## 1. Status Terkini

| Komponen | Status | Catatan |
|----------|--------|---------|
| Pipeline 6-stage | ✅ Selesai | Paralel, retry, caching |
| UI Streamlit | ✅ Selesai | 5 halaman |
| API + Celery | ✅ Selesai | Background jobs, Redis queue |
| Real-time mic | ✅ Selesai | Whisper base + normalisasi |
| Riwayat + search | ✅ Selesai | SQLite cache fallback |
| Edit notulen | ✅ Selesai | Edit teks → DOCX formal |
| Share email | ✅ Selesai | SMTP dari UI |
| Ringkasan eksekutif | ✅ Selesai | Section pertama DOCX |
| Action items enforce | ✅ Selesai | Prompt + tabel PJ+deadline |
| 321 id_terms | ✅ Selesai | Word-boundary, slang |
| Codespaces | ✅ Selesai | Devcontainer + skill bundle |
| Testing | ✅ 51 pass / 2 skip | 64 test cases |
| Docker | ✅ Selesai | API + UI + worker |

---

## 2. Arsitektur Pipeline

### Diagram Alir

```
┌─────────────────────────────────────────────────────────────────┐
│                      INPUT: File Audio / Mic                     │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 1-2: Audio Ingestion & Split (30 menit per segmen)       │
│  - Validasi format, konversi WAV 16kHz mono, normalisasi volume │
│  - Split otomatis tiap 30 menit, export MP3 + WAV               │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  STAGE 3 + 4: ⚡ PARALEL via ThreadPoolExecutor                  │
│  ┌──────────────────────┐  ┌──────────────────────────┐          │
│  │ Transkripsi           │  │ Diarization             │          │
│  │ Whisper / AssemblyAI  │  │ Pyannote → SpeechBrain  │          │
│  │ Caching per-chunk MD5 │  │ → VAD fallback          │          │
│  └──────────┬───────────┘  └───────────┬──────────────┘          │
└─────────────┼──────────────────────────┼──────────────────────────┘
              │          Merge via timestamp alignment              │
              ▼                          │                         │
┌──────────────────────────────────────────────────────────────────┐
│  Preprocessing: normalize_indonesian() — 321 id_terms + slang   │
└──────────────────────────┬───────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  STAGE 5: AI Enhancement (Groq → 9router → Gemini)               │
│  - Identifikasi pembicara (nama, jabatan dari konteks)           │
│  - Koreksi istilah pemerintahan (APBD, Perda, TUPOKSI, dll)     │
│  - Ekstraksi: pokok bahasan, keputusan, kesimpulan               │
│  - Tindak lanjut: tabel PJ + deadline (wajib)                    │
│  - Ringkasan eksekutif (wajib)                                   │
└──────────────────────────┬───────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  STAGE 6: Generate DOCX (formal government template)             │
│  - Kop, klasifikasi, metadata, daftar hadir                      │
│  - Ringkasan eksekutif → Isi risalah → Kesimpulan → Tindak lanjut│
│  - Lampiran dokumen → Tanda tangan                               │
│  - Bisa diedit user sebelum download                             │
└──────────────────────────────────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                      OUTPUT: File DOCX / TXT                      │
│                Siap cetak, tanda tangan, distribusi               │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Technology Stack

| Layer | Teknologi | Biaya |
|-------|-----------|-------|
| **Audio Processing** | `pydub` + `ffmpeg` | Gratis |
| **Transkripsi Lokal** | `openai-whisper` (large-v3 / base) | Gratis |
| **Transkripsi Cloud** | AssemblyAI API | Free tier |
| **Speaker Diarization** | `pyannote-audio` (community-1/3.1) | Gratis |
| **AI Enhancement** | Groq → 9router → Gemini | Gratis (ketiganya) |
| **Word Generation** | `python-docx` | Gratis |
| **Backend API** | FastAPI + Celery + Redis | Gratis |
| **Frontend** | Streamlit | Gratis |
| **Cache** | SQLite + Redis | Gratis |
| **Container** | Docker + Docker Compose | Gratis |
| **Cloud Dev** | GitHub Codespaces | Free tier |

---

## 4. Struktur File

```
transkip/
├── risalah/                    # Core pipeline
│   ├── utils.py               # Retry, caching, parallel helpers
│   ├── audio_processor.py     # Stage 1-2: Ingestion & Split
│   ├── transcriber.py         # Stage 3: Transkripsi
│   ├── diarizer.py            # Stage 4: Speaker Diarization
│   ├── ai_enhancer.py         # Stage 5: AI Enhancement
│   ├── docx_generator.py      # Stage 6: DOCX + preview + edit
│   ├── id_terms.py            # 321 koreksi istilah Indonesia
│   ├── file_scanner.py        # Scanner dokumen pendukung
│   ├── job_cache.py           # SQLite cache riwayat
│   ├── email_utils.py         # SMTP email share
│   └── pipeline.py            # Orkestrator
├── api/                       # FastAPI backend
│   ├── app.py, celery_app.py  # App & worker config
│   ├── config.py              # Environment config
│   ├── routes.py, schemas.py  # Endpoints & schemas
│   ├── tasks.py               # Celery tasks
│   └── websocket.py           # WS streaming
├── ui/                        # Streamlit frontend
│   └── app.py                 # 5 halaman
├── tests/                     # 64 test cases
├── output/                    # Generated files
├── scripts/                   # Shell utilities
├── .devcontainer/             # Codespaces config
└── docker-compose.yml         # Container orchestration
```

---

## 5. UI Streamlit (5 Pages)

| Halaman | Fungsi |
|---------|--------|
| **Upload & Transkripsi** | Upload file → pipeline → progress → download DOCX |
| **Rekam Langsung** | Browser mic → real-time Whisper transkrip → edit → download TXT |
| **Riwayat Job** | Search by file/konten, preview, export DOCX/TXT, edit & download DOCX, share email |
| **Dokumen Pendukung** | Lihat hasil scan folder: file tree + teks terekstrak + gambar |
| **Panduan** | Cara pakai, shortcut, FAQ |

---

## 6. Istilah Indonesia (321 Terms)

8 kategori, regex word-boundary, slang→formal:

| Kategori | Contoh |
|----------|--------|
| INSTITUSI | DPRD, APBD, KUA-PPAS, Perda, RPJMD |
| JABATAN | Sekda, Kadis, Kabid, Kasie, Camat, Lurah |
| DAERAH | kabupaten, provinsi, kecamatan, kelurahan |
| LEMBAGA | BAPPEDA, BPKAD, Inspektorat, Dinkes, Dishub |
| DOKUMEN | SPJ, LPJ, SPM, DPA, Perbup, Pergub, Permendagri |
| RAPAT | RDP, Paripurna, Pleno, Komisi, Fraksi |
| ASR_ERRORS | kulty→kabupaten, depresi→DPRD, milyar→miliar |
| SLANG | gak→tidak, udah→sudah, aja→saja, ngomong→berbicara |

---

## 7. Optimasi Pipeline

| Fitur | Detail |
|-------|--------|
| **Paralel** | Stage 3 + 4 via ThreadPoolExecutor, hemat ~50% waktu |
| **Retry** | @retry(3x, delay=2, backoff=2) untuk semua API |
| **Caching** | MD5 per-chunk, skip jika sudah diproses |
| **AI Fallback** | Groq (kecepatan) → 9router (reliabilitas) → Gemini (ketersediaan) |
| **Diarization Fallback** | Pyannote → SpeechBrain → VAD |
| **Pipeline Fallback** | Paralel gagal → sequential; Pyannote gagal → VAD |
| **Preprocessing** | `normalize_indonesian()` sebelum AI enhancement |

---

## 8. API & Infrastruktur

```bash
# API server
uvicorn api.app:app --reload --port 8000

# Celery worker
celery -A api.celery_app worker --loglevel=info

# UI
streamlit run ui/app.py --server.port 8501

# Docker all services
docker compose up --build
```

### Environment (.env)

```
# Wajib
HF_TOKEN=...                    # HuggingFace untuk Pyannote
GROQ_API_KEY=...                # Groq LLM (prioritas #1)

# Opsional
ASSEMBLYAI_API_KEY=...          # Cloud transkripsi
NINEROUTER_API_KEY=...          # 9router fallback (#2)
GEMINI_API_KEY=...              # Gemini fallback (#3)
REDIS_URL=redis://localhost:6379/0

# Email share (opsional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=...
SMTP_PASS=...
SMTP_FROM=...
```

---

## 9. Testing

**64 test cases — 51 pass, 2 skip (env deps), 0 failure.**

```
tests/
├── test_ai_enhancer.py         # 8 tests (skipped without API keys)
├── test_api.py                 # 5 tests (1 skip without Redis)
├── test_audio_processor.py     # 5 tests
├── test_diarizer.py            # 6 tests
├── test_docx_generator.py      # 5 tests
├── test_file_scanner.py        # 6 tests
├── test_id_terms.py            # 14 tests
├── test_job_cache.py           # 9 tests
├── test_pipeline.py            # 3 tests (2 skip without deps)
└── test_transcriber.py         # 3 tests (1 skip without API key)
```

---

## 10. Fitur Kompetitor yang Tidak Ada (Celah)

| Fitur | Prioritas | Status |
|-------|-----------|--------|
| Real-time transcription | P0 | ✅ Done |
| Search archive | P0 | ✅ Done |
| Ringkasan eksekutif | P0 | ✅ Done |
| Action items tabel | P0 | ✅ Done |
| Edit notulen | P1 | ✅ Done |
| Share email | P1 | ✅ Done |
| Share WA/Telegram | P2 | ❌ |
| Multi-bahasa | P2 | ❌ |
| Meeting platform bot | P3 | ❌ |
| Integrasi CRM | P3 | ❌ |
| Export PDF | P3 | ❌ |
| Knowledge base | P3 | ❌ |

---

## 11. Catatan Teknis

### Apple Silicon (Mac M-series)
- Whisper: `device="mps"` untuk GPU
- Pyannote: GPU via PyTorch MPS
- Semua test di MacBook Pro M-series

### Keterbatasan & Mitigasi
| Keterbatasan | Mitigasi |
|-------------|----------|
| Whisper tanpa diarization | Pyannote terpisah (paralel) |
| Pyannote butuh GPU | Fallback ke CPU / VAD |
| Groq rate limit | Fallback ke 9router → Gemini |
| Audio >3 jam | Split 30 menit otomatis |
| Redis tidak terinstall | SQLite cache sebagai fallback |

### Biaya
- **100% gratis**: Whisper lokal + Pyannote + Groq (free tier)
- **Fallback gratis**: 9router + Gemini juga gratis
- AssemblyAI hanya jika butuh akurasi maksimal
