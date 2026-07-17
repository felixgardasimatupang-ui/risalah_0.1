import json
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from api.config import config
from api.schemas import HealthResponse, JobListResponse, JobResponse
from api.tasks import get_job_status, process_audio_task, process_folder_task, update_job_status

router = APIRouter(prefix="/api", tags=["api"])


def _check_redis():
    try:
        import redis

        r = redis.from_url(config.REDIS_URL)
        r.ping()
        return True
    except Exception:
        return False


def _job_to_response(raw: dict) -> JobResponse:
    return JobResponse(
        id=raw.get("id", ""),
        status=raw.get("status", "failed"),
        progress=raw.get("progress", 0),
        message=raw.get("message", ""),
        file_name=raw.get("file_name", ""),
        result_path=raw.get("result_path"),
        preview_text=raw.get("preview_text"),
        created_at=raw.get("created_at", ""),
        updated_at=raw.get("updated_at", ""),
        dokumen_pendukung=raw.get("dokumen_pendukung"),
        scan_result=raw.get("scan_result"),
    )


@router.get("/health", response_model=HealthResponse)
def health_check():
    redis_ok = _check_redis()
    return HealthResponse(
        status="ok" if redis_ok else "degraded",
        redis=redis_ok,
        celery=redis_ok,
    )


ALLOWED_EXTS = {".mp3", ".wav", ".mp4", ".m4a", ".ogg", ".flac", ".webm", ".pdf", ".docx", ".xlsx", ".png", ".jpg", ".jpeg"}
MAX_SIZE_BYTES = 500 * 1024 * 1024


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):  # noqa: B008
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(400, f"Tipe file '{ext}' tidak diizinkan. Gunakan: {', '.join(sorted(ALLOWED_EXTS))}")

    os.makedirs(config.UPLOAD_DIR, exist_ok=True)
    file_id = str(uuid.uuid4())[:8]
    safe_name = f"{file_id}_{file.filename}"
    dest = os.path.join(config.UPLOAD_DIR, safe_name)
    content = await file.read()
    if len(content) > MAX_SIZE_BYTES:
        raise HTTPException(400, f"File terlalu besar ({len(content) / 1024 / 1024:.1f} MB). Maksimal {MAX_SIZE_BYTES / 1024 / 1024:.0f} MB.")
    with open(dest, "wb") as f:
        f.write(content)
    return {
        "file_id": file_id,
        "file_path": dest,
        "file_name": file.filename,
        "size_bytes": len(content),
    }


@router.post("/transcribe", response_model=JobResponse)
async def create_transcribe_job(
    file_path: str = Form(...),
    file_name: str = Form("audio"),
    engine: str = Form("whisper"),
    chunk_minutes: int = Form(30),
    title: str = Form("RISALAH RAPAT"),
    classification: str = Form("BIASA"),
    doc_number: str = Form("_______________"),
):
    if not os.path.exists(file_path):
        raise HTTPException(400, f"File tidak ditemukan: {file_path}")

    if engine not in ("whisper", "assemblyai"):
        raise HTTPException(400, f"Engine tidak dikenal: {engine}")

    job_id = str(uuid.uuid4())[:12]
    update_job_status(job_id, "pending", 0, "Menunggu antrian...")
    raw = get_job_status(job_id)
    if raw:
        raw["file_name"] = file_name
        raw["created_at"] = datetime.now().isoformat()
        import redis

        r = redis.from_url(config.REDIS_URL)
        r.set(f"job:{job_id}", json.dumps(raw))

    is_folder = os.path.isdir(file_path)
    if is_folder:
        process_folder_task.delay(
            job_id, file_path, engine, chunk_minutes, title, classification, doc_number
        )
    else:
        process_audio_task.delay(
            job_id, file_path, engine, chunk_minutes, title, classification, doc_number
        )

    return _job_to_response(get_job_status(job_id) or {})


@router.get("/jobs", response_model=JobListResponse)
def list_jobs(limit: int = 50, offset: int = 0):
    try:
        import redis

        r = redis.from_url(config.REDIS_URL)
        keys = r.keys("job:*")
        keys = sorted(keys, reverse=True)
        jobs = []
        for k in keys[offset : offset + limit]:
            raw = r.get(k)
            if raw:
                jobs.append(_job_to_response(json.loads(raw)))
        return JobListResponse(total=len(keys), jobs=jobs)
    except Exception:
        return JobListResponse(total=0, jobs=[])


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str):
    raw = get_job_status(job_id)
    if not raw:
        raise HTTPException(404, f"Job {job_id} tidak ditemukan")
    return _job_to_response(raw)


@router.delete("/jobs/{job_id}", response_model=JobResponse)
def cancel_job(job_id: str):
    raw = get_job_status(job_id)
    if not raw:
        raise HTTPException(404, f"Job {job_id} tidak ditemukan")
    update_job_status(job_id, "cancelled", 0, "Dibatalkan oleh user")
    try:
        from celery.task.control import revoke

        revoke(job_id, terminate=True)
    except Exception:
        pass
    return _job_to_response(get_job_status(job_id))


@router.get("/download/{job_id}")
def download_result(job_id: str):
    raw = get_job_status(job_id)
    if not raw:
        raise HTTPException(404, "Job tidak ditemukan")
    result_path = raw.get("result_path")
    if not result_path or not os.path.exists(result_path):
        raise HTTPException(404, "File hasil belum tersedia")
    return FileResponse(result_path, filename=os.path.basename(result_path))


@router.get("/stream/{job_id}")
async def stream_job_progress(job_id: str):
    async def event_generator():
        import redis as redis_lib

        r = redis_lib.from_url(config.REDIS_URL)
        pubsub = r.pubsub()
        pubsub.subscribe(f"job:{job_id}:updates")

        raw = r.get(f"job:{job_id}")
        if raw:
            data = json.loads(raw)
            yield f"data: {json.dumps(data)}\n\n"
            if data.get("status") in ("completed", "failed", "cancelled"):
                pubsub.unsubscribe()
                return

        while True:
            msg = pubsub.get_message(timeout=30)
            if msg and msg["type"] == "message":
                yield f"data: {msg['data'].decode()}\n\n"
                data = json.loads(msg["data"])
                if data.get("status") in ("completed", "failed", "cancelled"):
                    pubsub.unsubscribe()
                    return
            yield ": keepalive\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
