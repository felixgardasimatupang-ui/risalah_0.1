from pydantic import BaseModel
from typing import List, Optional, Any
from enum import Enum


class EngineEnum(str, Enum):
    whisper = "whisper"
    assemblyai = "assemblyai"
    gemini = "gemini"


class JobStatusEnum(str, Enum):
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


class JobListResponse(BaseModel):
    total: int
    jobs: List[JobResponse]


class HealthResponse(BaseModel):
    status: str
    redis: bool
    celery: bool
    gemini: bool
    version: str = "2.0.0"


class WSMessage(BaseModel):
    type: str
    job_id: str
    progress: int = 0
    message: str = ""
    data: Any = None
