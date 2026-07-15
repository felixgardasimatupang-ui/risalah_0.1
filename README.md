# Risalah Rapat Otomatis

Pipeline 6-stage untuk menghasilkan **Risalah Rapat** (official meeting minutes) dari file audio, khusus konteks pemerintahan Indonesia.

## Alur Pipeline

```
Audio Rekaman → Split 30 menit → Transkripsi (Whisper/AssemblyAI)
→ Speaker Diarization (Pyannote) → AI Enhancement (Gemini)
→ DOCX (Word) → Siap cetak & tanda tangan!
```

## Quick Start

```bash
# 1. Setup
./scripts/setup.sh

# 2. Edit .env - isi API key
nano .env

# 3. Jalankan pipeline
python risalah/pipeline.py rekaman_rapat.mp4
```

## Prasyarat

- Python 3.9+
- ffmpeg (`brew install ffmpeg`)
- API Key: [Gemini](https://aistudio.google.com/) (wajib)
- Token: [HuggingFace](https://huggingface.co/settings/tokens) (wajib untuk speaker diarization)
- API Key: [AssemblyAI](https://www.assemblyai.com/) (opsional)

## Struktur Project

```
transkip/
├── risalah/
│   ├── audio_processor.py    # Stage 1-2: Ingestion & Split
│   ├── transcriber.py        # Stage 3: Transkripsi
│   ├── diarizer.py           # Stage 4: Speaker Diarization
│   ├── ai_enhancer.py        # Stage 5: AI Enhancement (Gemini)
│   ├── docx_generator.py     # Stage 6: DOCX Generator
│   └── pipeline.py           # Orkestrator
├── output/
│   ├── chunks/               # Audio chunk 30 menit
│   ├── transcripts/          # Hasil transkrip JSON
│   ├── diarization/          # Hasil diarization JSON
│   ├── enhanced/             # Hasil AI enhancement JSON
│   └── docs/                 # Final DOCX risalah
└── scripts/
    ├── setup.sh
    └── run_pipeline.sh
```

## Opsi Lanjutan

```bash
# Pilih engine transkripsi
python risalah/pipeline.py rekaman.mp4 --engine assemblyai

# Jalankan stage tertentu saja
python risalah/pipeline.py rekaman.mp4 --stage transcribe-only
python risalah/pipeline.py rekaman.mp4 --stage docx-only

# Skip stage tertentu (gunakan cache)
python risalah/pipeline.py rekaman.mp4 --skip transcribe diarize
```

## Output DOCX

File DOCX di `output/docs/` berisi:
- Kop "RISALAH RAPAT"
- Informasi rapat (hari, tanggal, waktu, tempat, acara)
- Daftar hadir (nama & jabatan)
- Isi risalah (tabel pembicara + timestamp)
- Kesimpulan & keputusan
- Tindak lanjut
- Tanda tangan

## Istilah Pemerintahan yang Didukung

APBD, Perda, Permendagri, Musrenbang, Renja, Renstra, RPJMD, TUPOKSI, DPA, KUA-PPAS, SPJ, LPJ, SPM, Perkada, Inspektorat, dan lainnya.
