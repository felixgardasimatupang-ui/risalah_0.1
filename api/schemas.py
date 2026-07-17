from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel


class EngineEnum(str, Enum):  # noqa: UP042
    whisper = "whisper"
    assemblyai = "assemblyai"


class JobStatusEnum(str, Enum):  # noqa: UP042
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class JobCreate(BaseModel):
    engine: EngineEnum = EngineEnum.whisper
    chunk_minutes: int = 30
    title: str = "RISALAH RAPAT"
    classification: str = "BIASA"
    doc_number: str = "_______________"


class JobResponse(BaseModel):
    id: str
    status: JobStatusEnum
    progress: int = 0
    message: str = ""
    file_name: str = ""
    result_path: Optional[str] = None
    preview_text: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    dokumen_pendukung: Optional[dict] = None
    scan_result: Optional[dict] = None


class JobListResponse(BaseModel):
    total: int
    jobs: list[JobResponse]


class HealthResponse(BaseModel):
    status: str
    redis: bool
    celery: bool
    version: str = "2.0.0"


class WSMessage(BaseModel):
    type: str
    job_id: str
    progress: int = 0
    message: str = ""
    data: Any = None
