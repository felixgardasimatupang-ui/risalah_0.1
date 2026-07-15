# Pipeline Workflow — Risalah Rapat Otomatis

## 1. High-Level Pipeline Flow

```mermaid
graph TB
    subgraph INPUT["📥 Input"]
        A[Audio File<br/>MP3/MP4/M4A/WAV/OGG]
    end

    subgraph STAGE1_2["Stage 1-2: Audio Ingestion & Split"]
        B[Validasi & Konversi<br/>→ WAV 16kHz mono]
        C{Split 30 menit}
        B --> C
    end

    subgraph PARALLEL["Stage 3-4: ⚡ Paralel"]
        direction TB
        D[Transkripsi<br/>Whisper / AssemblyAI]
        E[Speaker Diarization<br/>Pyannote / SpeechBrain / VAD]
    end

    subgraph MERGE["Merge"]
        F[Match transcript + diarization<br/>via timestamp alignment]
    end

    subgraph STAGE5["Stage 5: AI Enhancement"]
        G[Phase 1: Identifikasi Pembicara]
        H[Phase 2: Koreksi Istilah &<br/>Ekstraksi Struktur Risalah]
        G --> H
    end

    subgraph STAGE6["Stage 6: DOCX Generation"]
        I[Generate Word Document<br/>Format Risalah Resmi]
    end

    subgraph OUTPUT["📄 Output"]
        J[DOCX Siap Cetak & Tanda Tangan]
    end

    A --> B
    C --> D
    C --> E
    D & E --> F
    F --> G
    H --> I
    I --> J
```

---

## 2. Detail Paralelisasi Stage 3 & 4

```mermaid
sequenceDiagram
    participant P as Pipeline Orchestrator
    participant T as Thread 1: Transcriber
    participant D as Thread 2: Diarizer
    participant C as Cache Layer

    P->>P: Split audio into chunks (30m each)
    
    par Parallel Execution
        P->>T: transcribe_all(chunks)
        P->>D: run_diarization(chunks)
    end

    loop Per chunk
        T->>C: cache_check(transcript, chunk)
        alt Cache hit
            C-->>T: Return cached transcript
        else Cache miss
            T->>T: Whisper / AssemblyAI transcribe
            T->>C: store cache
        end
    end

    loop Per chunk
        D->>C: cache_check(diarization, chunk)
        alt Cache hit
            C-->>D: Return cached diarization
        else Cache miss
            D->>D: Pyannote / SpeechBrain / VAD
            D->>C: store cache
        end
    end

    P->>P: merge_transcript_with_diarization()
    Note over P: Fallback to sequential if parallel fails
```

---

## 3. Fallback Chain — AI Enhancement

```mermaid
graph LR
    START([Start Enhancement]) --> TRY{Try Groq}
    TRY -->|Success| DONE([Done])
    TRY -->|Fail| TRY2{Try 9router}
    TRY2 -->|Success| DONE
    TRY2 -->|Fail| TRY3{Try Gemini}
    TRY3 -->|Success| DONE
    TRY3 -->|Fail| BUILD[build_fallback]
    BUILD --> DONE

    style TRY fill:#22c55e,color:#000
    style TRY2 fill:#eab308,color:#000
    style TRY3 fill:#ef4444,color:#fff
    style BUILD fill:#6b7280,color:#fff
```

---

## 4. Fallback Chain — Speaker Diarization

```mermaid
graph LR
    START([Start Diarization]) --> TRY{Try Pyannote<br/>community-1}
    TRY -->|Success| DONE([Done])
    TRY -->|Fail| TRY2{Try Pyannote<br/>3.1}
    TRY2 -->|Success| DONE
    TRY2 -->|Fail| TRY3{Try SpeechBrain<br/>ECAPA-TDNN}
    TRY3 -->|Success| DONE
    TRY3 -->|Fail| VAD[VAD Segmentation<br/>all speakers = SPEAKER_00]
    VAD --> DONE

    style TRY fill:#22c55e,color:#000
    style TRY2 fill:#eab308,color:#000
    style TRY3 fill:#f97316,color:#000
    style VAD fill:#6b7280,color:#fff
```

---

## 5. Retry & Caching Mechanism

```mermaid
flowchart TD
    subgraph RETRY["Retry (Exponential Backoff)"]
        ATTEMPT[API Call] --> CHECK{Success?}
        CHECK -->|Yes| RET_OK[Return Result]
        CHECK -->|No| WAIT[Wait: delay × backoff^attempt]
        WAIT --> ATTEMPT2[Retry]
        ATTEMPT2 --> CHECK2{Success?}
        CHECK2 -->|Yes| RET_OK
        CHECK2 -->|No| MAX{Max attempts<br/>reached?}
        MAX -->|No| WAIT
        MAX -->|Yes| FAIL[Raise Error / Fallback]
    end

    subgraph CACHE["Caching per-Chunk"]
        INPUT[Chunk Name] --> HASH[MD5 Hash Key]
        HASH --> LOOKUP{Check cache dir}
        LOOKUP -->|Hit| CACHE_OK[Load from JSON]
        LOOKUP -->|Miss| PROCESS[Process Chunk]
        PROCESS --> SAVE[Save to JSON]
        SAVE --> CACHE_OK
    end

    RETRY --> CACHE
```

---

## 6. Data Flow Detail

```mermaid
flowchart LR
    subgraph FILES["File Progression"]
        A1[chunk_001.wav] --> T1[transcript_001.json]
        A1 --> D1[diarization_001.json]
        A2[chunk_002.wav] --> T2[transcript_002.json]
        A2 --> D2[diarization_002.json]
        A3[chunk_003.wav] --> T3[transcript_003.json]
        A3 --> D3[diarization_003.json]
    end

    subgraph MERGE_DATA["Merge"]
        T1 & T2 & T3 --> MERGED[merged_lengkap.json]
        D1 & D2 & D3 --> MERGED
    end

    subgraph ENHANCE["AI Enhancement"]
        MERGED --> ENHANCED[enhanced_lengkap.json]
    end

    subgraph DOCX["Generate"]
        ENHANCED --> DOCX_FILE[risalah_rapat.docx]
        ENHANCED --> META[metadata.json]
    end

    subgraph CACHE_DIRS["Cache Directories"]
        TRANS_CACHE[(output/transcripts/)]
        DIAR_CACHE[(output/diarization/)]
    end

    T1 & T2 & T3 -.-> TRANS_CACHE
    D1 & D2 & D3 -.-> DIAR_CACHE
```

---

## 7. Command Flow

```mermaid
flowchart TD
    CLI[python risalah/pipeline.py<br/>rekaman.mp4] --> LOAD[Load .env]
    LOAD --> SCAN{--skip?}
    SCAN -->|skip transcribe| DIARIZE_ONLY[Run diarization only]
    SCAN -->|skip diarize| TRANS_ONLY[Run transcription only]
    SCAN -->|default| FULL[Run full pipeline]
    
    FULL --> PARALLEL{--no-parallel?}
    PARALLEL -->|No| PAR[ThreadPoolExecutor<br/>Transcribe + Diarize]
    PARALLEL -->|Yes| SEQ[Sequential<br/>Transcribe → Diarize]
    
    PAR --> MERGE[merge & enhance]
    SEQ --> MERGE
    
    MERGE --> DOCX{--preview?}
    DOCX -->|Yes| TXT[Output TXT preview]
    DOCX -->|No| WORD[Generate DOCX]
    
    TXT --> END([Done ✓])
    WORD --> END
```

---

## 8. Command Reference

| Command | Description |
|---------|-------------|
| `python risalah/pipeline.py <input>` | Full pipeline (parallel, cached, retry) |
| `--engine assemblyai` | Use AssemblyAI instead of Whisper |
| `--no-parallel` | Disable parallel Stage 3+4 |
| `--skip transcribe diarize` | Skip specified stages (use cache) |
| `--preview` | TXT output only, skip DOCX |
| `--overwrite` | Re-process all chunks (ignore cache) |

---

*Last updated: 2026-07-15*
