# Project: Risalah Rapat Otomatis

## Tech Stack
- **Backend**: Python 3.11+, FastAPI, Celery, Redis
- **Frontend**: Streamlit
- **AI/ML**: OpenAI Whisper, AssemblyAI, Pyannote (community-1), Google Gemini, Groq, 9router
- **Output**: python-docx (DOCX)
- **Deploy**: Docker, Docker Compose

## Code Conventions
- Python: snake_case, type hints
- Imports: stdlib → third-party → local
- Async untuk I/O, sync untuk CPU-bound
- Error handling: raise specific exceptions, log dengan print()
- Config dari environment via `.env` + `python-dotenv`

## Project Structure
```
transkip/
├── api/              # FastAPI backend (routes, tasks, ws, schemas)
├── risalah/          # Core pipeline modules
│   ├── utils.py      # Retry, caching, parallel execution helpers
│   ├── audio_processor.py
│   ├── transcriber.py
│   ├── diarizer.py
│   ├── ai_enhancer.py
│   ├── docx_generator.py
│   ├── file_scanner.py
│   └── pipeline.py   # Orkestrator utama
├── ui/               # Streamlit frontend
├── output/           # Generated output (chunks, transcripts, docs)
├── scripts/          # Shell scripts
└── opencode.json     # Agent configuration
```

## Pipeline Stages
1. Stage 1-2: Audio Ingestion & Split (risalah/audio_processor.py)
2. Stage 3: Transkripsi (risalah/transcriber.py)
3. Stage 4: Speaker Diarization (risalah/diarizer.py)
4. Stage 5: AI Enhancement (risalah/ai_enhancer.py)
5. Stage 6: DOCX Generation (risalah/docx_generator.py)

### Optimasi Pipeline
- **Paralel**: Stage 3 + 4 berjalan paralel via risalah/utils.py run_parallel()
- **Retry**: Semua panggilan API eksternal pakai @retry (exponential backoff)
- **Caching**: Hasil transkrip & diarization di-cache per-chunk (MD5 key)
- **AI Fallback Chain**: Groq → 9router → Gemini (prioritas kecepatan & ketersediaan)
- **Diarization**: Pyannote community-1 (prioritas) → 3.1 → SpeechBrain → VAD

## Agent Reference
- `@backend` — FastAPI, Celery, Redis, API routes
- `@pipeline` — Risalah pipeline modules (audio_processor, transcriber, diarizer, ai_enhancer, docx_generator, file_scanner, utils, pipeline)
- `@ui-dev` — Streamlit UI
- `@devops` — Docker, scripts, deployment
- `@explore` — Codebase exploration

## Commands
| Command | Description |
|---------|-------------|
| `run-pipeline` | `python risalah/pipeline.py <input> [--no-parallel] [--skip ...]` |
| `run-api` | `uvicorn api.app:app --reload --port 8000` |
| `run-ui` | `streamlit run ui/app.py --server.port 8501` |
| `test` | `python -m pytest` |
