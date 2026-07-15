# PLAN PROYEK RISALAH RAPAT OTOMATIS

## Ringkasan Eksekutif

Proyek ini membangun pipeline otomatis untuk menghasilkan **Risalah Rapat** (official meeting minutes) dari file audio rekaman rapat — khusus untuk konteks pemerintahan Indonesia. Pipeline menggabungkan 5 teknologi AI gratis & powerfull secara berurutan:

```
Audio Rekaman → Split 30 menit → Transkripsi (Whisper/AssemblyAI) → 
Speaker Diarization (Pyannote) → AI Enhancement (Gemini) → DOCX (Word)
```

---

## 1. Arsitektur Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                      INPUT: File Audio                          │
│                (MP3, MP4, M4A, WAV, OGG, dll)                   │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 1: Audio Ingestion & Preprocessing                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ - Validasi format file                                     │  │
│  │ - Konversi ke WAV 16kHz mono (standar ASR)                │  │
│  │ - Normalisasi volume (dB)                                  │  │
│  │ - Noise reduction opsional                                 │  │
│  └──────────────────────┬────────────────────────────────────┘  │
└─────────────────────────┼────────────────────────────────────────┘
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│  STAGE 2: Audio Splitting (30 menit per segmen)                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ - Deteksi durasi total                                     │   │
│  │ - Split otomatis tiap 30 menit (1.800.000 ms)             │   │
│  │ - Export ke MP3 + WAV (dual format)                       │   │
│  │ - Penamaan: chunk_001.mp3, chunk_002.mp3, ...             │   │
│  └──────────────────────┬───────────────────────────────────┘   │
└─────────────────────────┼─────────────────────────────────────────┘
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│  STAGE 3: Transkripsi (Dual Engine)                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  OPTION A: Whisper Lokal (Gratis, offline, privat)       │   │
│  │  - Model: large-v3 (akurasi tinggi)                      │   │
│  │  - Bahasa: Indonesia (id)                                │   │
│  │  - Output: teks + segments (timestamp)                   │   │
│  │                                                          │   │
│  │  OPTION B: AssemblyAI Cloud (Akurasi maksimal)           │   │
│  │  - Speaker diarization bawaan                            │   │
│  │  - Bahasa Indonesia (id)                                 │   │
│  └──────────────────────┬───────────────────────────────────┘   │
└─────────────────────────┼─────────────────────────────────────────┘
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│  STAGE 4: Speaker Diarization (Pyannote)                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ - Model: pyannote/speaker-diarization-3.1                │   │
│  │ - Identifikasi "siapa bicara kapan"                     │   │
│  │ - Output: segmentasi speaker dengan timestamp           │   │
│  │ - Mapping speaker ke label (SPEAKER_00, SPEAKER_01...)  │   │
│  │ - Matching ke teks transkrip via timestamp              │   │
│  └──────────────────────┬───────────────────────────────────┘   │
└─────────────────────────┼─────────────────────────────────────────┘
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│  STAGE 5: AI Enhancement dengan Gemini                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Langkah 5a: Tebak Nama & Jabatan Pembicara              │   │
│  │  - Analisis konteks percakapan                           │   │
│  │  - Identifikasi pola sapaan & gaya bicara               │   │
│  │  - Inferensi nama & peran (Ketua, Sekretaris, dll)      │   │
│  │                                                          │   │
│  │  Langkah 5b: Koreksi Istilah Pemerintahan               │   │
│  │  - Deteksi istilah salah dengar (ASR error)             │   │
│  │  - Koreksi ke istilah baku pemerintahan Indonesia       │   │
│  │  - Contoh: "APBD", "Perda", "Permendagri", dll          │   │
│  │                                                          │   │
│  │  Langkah 5c: Struktur ke Format Risalah                 │   │
│  │  - Ekstraksi: Pokok bahasan, Keputusan, Kesimpulan      │   │
│  │  - Deteksi: Agenda rapat, Poin voting                   │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│  STAGE 6: Generate DOCX (Microsoft Word)                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Format Risalah Resmi:                                     │   │
│  │ - Kop: "RISALAH RAPAT"                                   │   │
│  │ - Informasi Rapat: Hari, Tgl, Waktu, Tempat, acara       │   │
│  │ - Daftar Hadir: Nama, Jabatan, Instansi                  │   │
│  │ - Isi Risalah: tabel pembicara | isi | timestamp          │   │
│  │ - Kesimpulan & Keputusan                                 │   │
│  │ - Tanda Tangan: Pimpinan, Sekretaris, Notulis            │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│                      OUTPUT: File DOCX                           │
│                Siap cetak & distribusi resmi                      │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. Technology Stack

| Layer | Teknologi | Lisensi | Biaya | Keunggulan |
|-------|-----------|---------|-------|------------|
| **Audio Processing** | `pydub` + `ffmpeg` | MIT | Gratis | Konversi, split, normalisasi |
| **Transkripsi Lokal** | `openai-whisper` (large-v3) | MIT | Gratis | Offline, privasi terjaga |
| **Transkripsi Cloud** | AssemblyAI API | Proprietary | Ada free tier | Akurasi tinggi, diarization built-in |
| **Speaker Diarization** | `pyannote-audio` 3.1 | MIT | Gratis | State-of-the-art speaker detection |
| **AI Enhancement** | Google Gemini API | Proprietary | Free tier (60 query/menit) | Konteks bahasa Indonesia kuat |
| **Word Generation** | `python-docx` | MIT | Gratis | Format DOCX profesional |
| **Orkestrasi** | Python 3.9+ | PSF | Gratis | Script pipeline terintegrasi |

---

## 3. Struktur File Project

```
transkip/
├── .env                          # API Keys (AssemblyAI, Gemini, HuggingFace)
├── .env.template                 # Template env
├── requirements.txt              # Dependencies
├── PLAN_RISALAH.md               # Dokumen ini
├── README.md                     # Panduan lengkap
│
├── risalah/                      # 🆕 Module utama risalah
│   ├── __init__.py
│   ├── config.py                 # Konfigurasi global
│   ├── audio_processor.py        # Stage 1-2: Ingestion & Split
│   ├── transcriber.py            # Stage 3: Transkripsi (Whisper/AssemblyAI)
│   ├── diarizer.py               # Stage 4: Speaker Diarization (Pyannote)
│   ├── ai_enhancer.py            # Stage 5: Gemini Enhancement
│   ├── docx_generator.py         # Stage 6: DOCX Generator
│   └── pipeline.py               # 🏁 Orkestrator utama
│
├── scripts/                      # 🆕 Script utilitas
│   ├── run_pipeline.sh           # Satu-perintah: jalankan semua
│   └── setup.sh                  # Install semua dependencies
│
├── output/                       # 🆕 Folder output terstruktur
│   ├── chunks/                   # Audio chunk 30 menit
│   ├── transcripts/              # Hasil transkrip (.txt)
│   ├── diarization/              # Hasil diarization (.json)
│   ├── enhanced/                 # Hasil AI enhancement (.json)
│   └── docs/                     # Final DOCX risalah
│
├── hasil_transkrip_cloud/        # (existing)
├── hasil_transkrip_lokal/        # (existing)
├── transcribe.py                 # (existing - cloud)
└── transcribe_local.py           # (existing - local)
```

---

## 4. Detail Implementasi per Stage

### Stage 1: Audio Ingestion & Preprocessing
**File:** `risalah/audio_processor.py`

```python
# Pseudocode:
# 1. Terima input file (any format via pydub)
# 2. Validasi: file exists, format didukung
# 3. Konversi ke WAV 16kHz mono (standar ASR)
# 4. Normalisasi volume ke -20dB
# 5. Simpan ke folder output/chunks/
# 6. Return metadata: durasi, sample_rate, channels
```

**Fitur:**
- Deteksi otomatis format file
- Konversi multi-format via ffmpeg
- Normalisasi volume (audio terlalu kecil/besar)
- Opsional: noise reduction dasar

### Stage 2: Audio Splitting
**File:** `risalah/audio_processor.py`

```python
# Pseudocode:
# 1. Load audio dengan pydub
# 2. Hitung jumlah chunk: ceil(durasi_total / 1_800_000ms)
# 3. Loop: extract segment [i*30min, (i+1)*30min]
# 4. Export dual: .mp3 (untuk transkrip) + .wav (untuk diarization)
# 5. Simpan dengan penamaan: chunk_{i:03d}.mp3/.wav
```

**Fitur:**
- Handle audio >10 jam (split otomatis)
- Progress bar (tqdm)
- Naming yang informatif

### Stage 3: Transkripsi (Dual Engine)
**File:** `risalah/transcriber.py`

**Option A (default): Whisper Lokal**
```python
# Pseudocode:
# 1. Load model whisper large-v3
# 2. Transkrip tiap chunk dengan language="id"
# 3. Gunakan GPU (MPS untuk Apple Silicon) jika ada
# 4. Output: teks + segments (timestamp per kata)
# 5. Simpan ke output/transcripts/
```

**Option B: AssemblyAI Cloud**
```python
# Pseudocode:
# 1. Load API key dari .env
# 2. Kirim tiap chunk ke AssemblyAI
# 3. Config: speaker_labels=True, language_code="id"
# 4. Terima hasil dengan utterances (sudah ada speaker)
# 5. Simpan ke output/transcripts/
```

**Keunggulan yang ditingkatkan:**
- Menggunakan **Whisper large-v3** (sebelumnya hanya `base`)
- Dual engine: bisa pilih lokal (gratis) atau cloud (akurat)
- Fallback otomatis jika satu gagal

### Stage 4: Speaker Diarization
**File:** `risalah/diarizer.py`

```python
# Pseudocode:
# 1. Load pipeline Pyannote dari HuggingFace
# 2. Terapkan ke file WAV tiap chunk
# 3. Output: daftar (start_time, end_time, speaker)
# 4. Simpan ke output/diarization/ sebagai JSON
```
```json
{
  "chunk": "chunk_001.wav",
  "diarization": [
    {"start": 0.2, "end": 1.5, "speaker": "SPEAKER_00"},
    {"start": 1.8, "end": 3.9, "speaker": "SPEAKER_01"},
    ...
  ]
}
```

**Fitur:**
- Align hasil diarization ke teks transkrip (via timestamp)
- Handle overlapping speech
- Output format JSON terstruktur

### Stage 5: AI Enhancement dengan Gemini
**File:** `risalah/ai_enhancer.py`

Kombinasi 3 sub-tahap dalam satu panggilan Gemini:

**5a: Identifikasi Pembicara**
```
System Prompt: Kamu adalah asisten risalah rapat pemerintah Indonesia.
Identifikasi setiap pembicara dari konteks percakapan.
Cari petunjuk: sapaan (Pak, Bu, Ibu, Bapak), gaya bicara formal,
posisi yang disebut (Sekretaris, Ketua, Anggota).
Beri label: [Ketua Rapat], [Sekretaris], [Anggota 1], [Anggota 2], dll.
```

**5b: Koreksi Istilah Pemerintahan**
```
System Prompt: Koreksi istilah-istilah pemerintahan yang mungkin
salah transkripsi. Contoh koreksi umum:
- "APB" → "APBD" (Anggaran Pendapatan dan Belanja Daerah)
- "Peraturan daerah" → "Perda"
- "Peraturan menteri" → "Permen"
- "Musyawarah perencanaan pembangunan" → "Musrenbang"
- dll.
```

**5c: Ekstraksi Struktur Risalah**
```
Extract:
1. POKOK BAHASAN: Topik utama yang dibahas
2. KEPUTUSAN: Keputusan yang diambil
3. KESIMPULAN: Kesimpulan rapat
4. TINDAK LANJUT: Action items & PIC
5. LAMPIRAN: Dokumen yang disebut
```

### Stage 6: DOCX Generator
**File:** `risalah/docx_generator.py`

Template risalah yang dihasilkan:

```python
# Struktur DOCX:
# ┌──────────────────────────────────────────────┐
# │         RISALAH RAPAT                        │
# │                                              │
# │ Hari/Tanggal  : Senin, 15 Juli 2026         │
# │ Waktu         : 09.00 - 11.30 WIB            │
# │ Tempat        : Ruang Rapat Lt. 2            │
# │ Acara         : Rapat Koordinasi Program...  │
# │                                              │
# │ DAFTAR HADIR:                                │
# │ No | Nama | Jabatan | Instansi | Ket.        │
# │ ---|------|---------|----------|---          │
# │ 1  | ...  | Ketua   | ...      | Hadir       │
# │                                              │
# │ ISI RISALAH:                                 │
# │ No | Waktu  | Pembicara     | Isi            │
# │ ---|--------|---------------|----------------│
# │ 1  | 00:02  | Ketua Rapat   | "Selamat..."   │
# │ 2  | 00:05  | Sekretaris    | "Laporan..."   │
# │                                              │
# │ KESIMPULAN & KEPUTUSAN:                      │
# │ 1. ...                                       │
# │ 2. ...                                       │
# │                                              │
# │ Jakarta, 15 Juli 2026                        │
# │ Pimpinan Rapat              Sekretaris       │
# │ (_______________)          (_______________) │
# └──────────────────────────────────────────────┘
```

**Fitur:**
- Tabel rapi dengan border
- Styling header, bold, italic
- Page break antar bab
- Auto-generate dari data terstruktur

---

## 5. Prompt Gemini untuk Risalah (Key Component)

### Prompt Utama (Single API Call untuk semua enhancement)

```
ANDA ADALAH ASISTEN RISALAH RAPAT PEMERINTAHAN INDONESIA.

TUGAS:
Analisis transkrip rapat berikut dan hasilkan:
1. IDENTIFIKASI PEMBICARA: Tebak nama/jabatan dari konteks (contoh: "Pembicara A" → "Ketua Rapat (Bapak Bambang)")
2. KOREKSI ISTILAH: Koreksi istilah pemerintahan yang salah transkrip
3. STRUKTUR RISALAH: Ekstrak keputusan, kesimpulan, tindak lanjut

KONTEKS PEMERINTAHAN YANG HARUS DIKENALI:
- Struktur organisasi: Kepala Dinas, Sekretaris, Kabid, Kasubag, dll
- Istilah anggaran: APBD, DPA, KUA-PPAS, Silpa, dll
- Istilah perencanaan: Musrenbang, Renja, Renstra, RPJMD
- Istilah hukum: Perda, Perkada, SK, SE, dll
- Istilah teknis: TUPOKSI, SOP, SPJ, LPJ, SPM

FORMAT OUTPUT:
## IDENTIFIKASI PEMBICARA
- SPEAKER_A: [Nama/Jabatan yang diinferensikan]
- SPEAKER_B: [Nama/Jabatan yang diinferensikan]

## TRANSKRIP TERNORMALISASI
[WAKTU] [PEMBICARA]: [teks yang sudah dikoreksi]

## POKOK BAHASAN
1. ...

## KEPUTUSAN RAPAT
1. ...

## KESIMPULAN
1. ...

## TINDAK LANJUT
| No | Tindakan | PIC | Batas Waktu |
|----|----------|-----|-------------|
| 1  | ...      | ... | ...         |

===
TRANSKRIP:
{{transkrip_mentah}}
```

---

## 6. Instalasi & Setup

### Prasyarat
```bash
# Python 3.9+
python3 --version

# ffmpeg (wajib)
brew install ffmpeg     # macOS
# sudo apt install ffmpeg  # Linux

# HuggingFace token (gratis) untuk Pyannote
# Daftar di: https://huggingface.co/settings/tokens
```

### Install
```bash
# Clone / masuk folder
cd transkip

# Aktifkan virtual environment
source .venv/bin/activate

# Install dependencies
pip install -U pip
pip install -r requirements.txt

# Install tambahan untuk risalah
pip install pyannote.audio python-docx google-genai
```

### Konfigurasi .env
```env
# AssemblyAI (opsional, untuk cloud transkripsi)
ASSEMBLYAI_API_KEY=your_key

# Gemini API (wajib untuk AI enhancement)
GEMINI_API_KEY=your_key

# HuggingFace token (wajib untuk Pyannote speaker diarization)
HF_TOKEN=your_token
```

### Cara Penggunaan
```bash
# 1. Pipeline lengkap (satu perintah)
source .venv/bin/activate
python risalah/pipeline.py rekaman_rapat.mp4

# 2. Atau stage-by-stage
python risalah/pipeline.py rekaman_rapat.mp4 --stage all
python risalah/pipeline.py rekaman_rapat.mp4 --stage transcribe-only

# 3. Output DOCX di folder output/docs/
ls output/docs/
```

---

## 7. Alur Eksekusi

```
User: punya file audio rekaman rapat (misal: rapat_dinas.mp3)

Step 1: python risalah/pipeline.py rapat_dinas.mp3
Step 2: Pipeline otomatis menjalankan 6 stage
Step 3: Output: output/docs/risalah_rapat_dinas.docx

User: Buka DOCX → langsung siap cetak/tanda tangan!
```

---

## 8. Rencana Eksekusi (Sprint)

| Sprint | Fokus | Deliverable |
|--------|-------|-------------|
| **Sprint 1** | Foundation | Stage 1-2: Audio Processor (ingestion + split) |
| **Sprint 2** | Transcription | Stage 3: Transcriber (Whisper + AssemblyAI) |
| **Sprint 3** | Diarization | Stage 4: Pyannote speaker identification |
| **Sprint 4** | AI Enhancement | Stage 5: Gemini integration + prompt engineering |
| **Sprint 5** | DOCX Output | Stage 6: Word document generator |
| **Sprint 6** | Integration | Pipeline orkestrasi + testing + dokumentasi |

---

## 9. Catatan Teknis Penting

### Apple Silicon (Mac M1/M2/M3/M4)
- Whisper: Gunakan `device="mps"` untuk akselerasi GPU
- Pyannote: GPU support via PyTorch MPS
- Semua test sudah dilakukan di MacBook Pro M-series

### Keterbatasan & Mitigasi
| Keterbatasan | Mitigasi |
|-------------|----------|
| Whisper tanpa diarization | Pyannote sebagai post-process |
| Pyannote butuh GPU (lambda) | Fallback ke CPU (lebih lambat) |
| Gemini free tier 60q/menit | Batch processing per chunk |
| Audio panjang >3 jam | Split 30 menit otomatis |

### Optimasi Biaya
- **100% gratis** jika: Whisper lokal + Pyannote + Gemini free tier
- **Berbayar minimal** jika: AssemblyAI ($0.01/menit) untuk akurasi maksimal
- Gemini: 60 permintaan gratis per menit → cukup untuk rapat rata-rata

---

## 10. Kesimpulan

Proyek ini mentransformasi workflow manual "dengar → catat → ketik" menjadi
**otomatis 6-stage pipeline** yang menghasilkan dokumen risalah siap-pakai.

**Dengan kombinasi:**
- **Whisper** (transkripsi gratis & akurat)
- **Pyannote** (identifikasi pembicara state-of-the-art)
- **Gemini** (koreksi istilah pemerintah + struktur risalah)
- **python-docx** (format Word profesional)

**Pengguna cukup menjalankan 1 perintah** dan mendapatkan file DOCX
risalah rapat yang lengkap, terstruktur, dan siap didistribusikan.
