"""Local SQLite cache for job history. Fallback when Redis/API unavailable."""

import json
import os
import sqlite3
import time

_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "output",
    "job_cache.sqlite",
)


def _get_conn():
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS cached_jobs (
            job_id TEXT PRIMARY KEY,
            file_name TEXT,
            status TEXT,
            progress INTEGER DEFAULT 0,
            message TEXT DEFAULT '',
            result_path TEXT,
            preview_text TEXT,
            created_at TEXT DEFAULT '',
            updated_at TEXT DEFAULT '',
            cached_at REAL NOT NULL
        )"""
    )
    return conn


def cache_job(job_data: dict):
    """Insert or update a single job in the local cache."""
    data = job_data.copy()
    conn = _get_conn()
    conn.execute(
        """INSERT OR REPLACE INTO cached_jobs
        (job_id, file_name, status, progress, message, result_path, preview_text, created_at, updated_at, cached_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data.get("id", ""),
            data.get("file_name", ""),
            data.get("status", ""),
            data.get("progress", 0),
            data.get("message", ""),
            data.get("result_path"),
            data.get("preview_text"),
            data.get("created_at", ""),
            data.get("updated_at", ""),
            time.time(),
        ),
    )
    conn.commit()
    conn.close()


def cache_jobs(jobs: list[dict]):
    """Cache multiple jobs at once."""
    conn = _get_conn()
    now = time.time()
    for data in jobs:
        conn.execute(
            """INSERT OR REPLACE INTO cached_jobs
            (job_id, file_name, status, progress, message, result_path, preview_text, created_at, updated_at, cached_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data.get("id", ""),
                data.get("file_name", ""),
                data.get("status", ""),
                data.get("progress", 0),
                data.get("message", ""),
                data.get("result_path"),
                data.get("preview_text"),
                data.get("created_at", ""),
                data.get("updated_at", ""),
                now,
            ),
        )
    conn.commit()
    conn.close()


def get_cached_jobs(limit: int = 50) -> list[dict]:
    """Return most recent cached jobs."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT job_id, file_name, status, progress, message, result_path, preview_text, created_at, updated_at FROM cached_jobs ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "file_name": r[1],
            "status": r[2],
            "progress": r[3],
            "message": r[4],
            "result_path": r[5],
            "preview_text": r[6],
            "created_at": r[7],
            "updated_at": r[8],
        }
        for r in rows
    ]


def clear_cache():
    """Delete all cached jobs."""
    conn = _get_conn()
    conn.execute("DELETE FROM cached_jobs")
    conn.commit()
    conn.close()
