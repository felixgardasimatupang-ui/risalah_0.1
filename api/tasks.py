import json
import os
import sys
from datetime import datetime

from api.celery_app import celery_app
from api.config import config

sys.path.insert(0, config.PROJECT_ROOT)


def update_job_status(job_id, status, progress=0, message="", result_path=None, preview_text=None):
    import redis as redis_lib

    r = redis_lib.from_url(config.REDIS_URL)
    key = f"job:{job_id}"
    data = {
        "id": job_id,
        "status": status,
        "progress": progress,
        "message": message,
        "result_path": result_path,
        "preview_text": preview_text,
        "updated_at": datetime.now().isoformat(),
    }
    existing = r.get(key)
    if existing:
        existing_data = json.loads(existing)
        existing_data.update(data)
        data = existing_data
    else:
        data["created_at"] = datetime.now().isoformat()
    r.set(key, json.dumps(data))
    r.expire(key, 86400 * 7)
    r.publish(f"job:{job_id}:updates", json.dumps({"type": "progress", **data}))
    return data


def get_job_status(job_id):
    import redis as redis_lib

    r = redis_lib.from_url(config.REDIS_URL)
    key = f"job:{job_id}"
    raw = r.get(key)
    if raw:
        return json.loads(raw)
    return None


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def process_audio_task(
    self,
    job_id,
    file_path,
    engine="whisper",
    chunk_minutes=30,
    title="RISALAH RAPAT",
    classification="BIASA",
    doc_number="_______________",
):
    try:
        update_job_status(job_id, "running", 5, "Memulai pipeline...")

        from risalah.ai_enhancer import enhance_transcript
        from risalah.audio_processor import process_audio
        from risalah.diarizer import run_diarization_pipeline
        from risalah.docx_generator import generate_preview_text, generate_risalah
        from risalah.transcriber import transcribe_all

        update_job_status(job_id, "running", 15, "Ingest & split audio...")
        meta = process_audio(file_path, chunk_minutes=chunk_minutes)

        update_job_status(job_id, "running", 35, f"Transkripsi ({engine}) + Diarization (paralel)...")
        from risalah.diarizer import merge_transcript_with_diarization, run_diarization
        from risalah.utils import run_parallel

        def do_transcribe():
            return transcribe_all(meta["chunks"], engine)

        def do_diarize():
            return run_diarization(meta["chunks"])

        t_result = None
        d_result = None
        try:
            t_result, d_result = run_parallel(do_transcribe, do_diarize)
        except Exception:
            t_result = do_transcribe()

        if t_result and d_result:
            merged = merge_transcript_with_diarization(t_result, d_result)
        elif t_result:
            merged = [
                {"chunk": c["chunk"], "start": s["start"], "end": s["end"],
                 "speaker": s.get("speaker", "SPEAKER_UNKNOWN"), "text": s["text"]}
                for c in t_result for s in c.get("segments", [])
            ]
        else:
            merged = run_diarization_pipeline(meta["chunks"], None)

        update_job_status(job_id, "running", 75, "AI Enhancement...")
        enhanced = enhance_transcript(merged)

        metadata = {
            "tanggal": datetime.now().strftime("%A, %d %B %Y"),
            "waktu": "_______________ - selesai",
            "tempat": "_______________",
            "acara": os.path.splitext(os.path.basename(file_path))[0],
        }

        update_job_status(job_id, "running", 90, "Generate DOCX...")
        docx_path = generate_risalah(
            enhanced, metadata, title=title, doc_number=doc_number, classification=classification
        )
        preview = generate_preview_text(enhanced, metadata)

        update_job_status(
            job_id, "completed", 100, "Selesai!", result_path=docx_path, preview_text=preview
        )
        return {"job_id": job_id, "status": "completed", "result": docx_path}

    except Exception as exc:
        update_job_status(job_id, "failed", 0, f"Error: {str(exc)}")
        raise self.retry(exc=exc) from exc


@celery_app.task(bind=True)
def process_folder_task(
    self,
    job_id,
    folder_path,
    engine="whisper",
    chunk_minutes=30,
    title="RISALAH RAPAT",
    classification="BIASA",
    doc_number="_______________",
):
    try:
        update_job_status(job_id, "running", 5, "Scanning folder...")

        from risalah.ai_enhancer import build_fallback, enhance_transcript
        from risalah.docx_generator import generate_preview_text, generate_risalah
        from risalah.file_scanner import extract_all_text, scan_folder

        scan = scan_folder(folder_path)
        update_job_status(job_id, "running", 15, "Ekstrak teks dokumen...")
        extracted = extract_all_text(scan)

        audio_files = [f["path"] for f in scan.get("audio_files", [])]

        if not audio_files:
            dummy_merged = []
            fallback = build_fallback(dummy_merged)
            fallback["dokumen_pendukung"] = extracted
            metadata = {
                "tanggal": datetime.now().strftime("%A, %d %B %Y"),
                "waktu": "_______________",
                "tempat": "_______________",
                "acara": os.path.basename(folder_path.rstrip("/")),
            }
            docx_path = generate_risalah(
                fallback,
                metadata,
                title=title,
                doc_number=doc_number,
                classification=classification,
            )
            preview = generate_preview_text(fallback, metadata)
            update_job_status(
                job_id,
                "completed",
                100,
                "Selesai (folder tanpa audio)",
                result_path=docx_path,
                preview_text=preview,
            )
            return {"job_id": job_id, "status": "completed", "result": docx_path}

        update_job_status(job_id, "running", 20, f"Memproses {len(audio_files)} audio...")

        all_enhanced_segments = []
        for i, af in enumerate(audio_files):
            pct = 20 + int(60 * (i + 1) / len(audio_files))
            update_job_status(
                job_id, "running", pct, f"Audio {i + 1}/{len(audio_files)}: {os.path.basename(af)}"
            )

            from risalah.audio_processor import process_audio
            from risalah.diarizer import merge_transcript_with_diarization, run_diarization
            from risalah.transcriber import transcribe_all
            from risalah.utils import run_parallel

            meta = process_audio(af, chunk_minutes=chunk_minutes)

            def do_transcribe_inner(meta=meta):
                return transcribe_all(meta["chunks"], engine)

            def do_diarize_inner(meta=meta):
                return run_diarization(meta["chunks"])

            try:
                t_inner, d_inner = run_parallel(do_transcribe_inner, do_diarize_inner)
                if t_inner and d_inner:
                    merged = merge_transcript_with_diarization(t_inner, d_inner)
                elif t_inner:
                    merged = [
                        {"chunk": c["chunk"], "start": s["start"], "end": s["end"],
                         "speaker": s.get("speaker", "SPEAKER_UNKNOWN"), "text": s["text"]}
                        for c in t_inner for s in c.get("segments", [])
                    ]
                else:
                    merged = []
            except Exception:
                transcript = do_transcribe_inner()
                merged = [
                    {"chunk": c["chunk"], "start": s["start"], "end": s["end"],
                     "speaker": s.get("speaker", "SPEAKER_UNKNOWN"), "text": s["text"]}
                    for c in transcript for s in c.get("segments", [])
                ] if transcript else []

            if i == 0:
                all_enhanced_segments = merged
            else:
                all_enhanced_segments.extend(merged)

        update_job_status(job_id, "running", 85, "AI Enhancement seluruh sesi...")
        enhanced = enhance_transcript(all_enhanced_segments)
        if extracted.get("all_text_combined", "").strip():
            enhanced["dokumen_pendukung"] = extracted

        metadata = {
            "tanggal": datetime.now().strftime("%A, %d %B %Y"),
            "waktu": "_______________ - selesai",
            "tempat": "_______________",
            "acara": os.path.basename(folder_path.rstrip("/")),
        }

        update_job_status(job_id, "running", 95, "Generate DOCX...")
        docx_path = generate_risalah(
            enhanced, metadata, title=title, doc_number=doc_number, classification=classification
        )
        preview = generate_preview_text(enhanced, metadata)

        update_job_status(
            job_id, "completed", 100, "Selesai!", result_path=docx_path, preview_text=preview
        )
        return {"job_id": job_id, "status": "completed", "result": docx_path}

    except Exception as exc:
        update_job_status(job_id, "failed", 0, f"Error: {str(exc)}")
        raise
