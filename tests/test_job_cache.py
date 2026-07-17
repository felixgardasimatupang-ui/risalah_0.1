import os
import time
import pytest
from risalah.job_cache import cache_job, cache_jobs, get_cached_jobs, clear_cache

SAMPLE_JOB = {
    "id": "test-job-001",
    "file_name": "rapat.mp3",
    "status": "completed",
    "progress": 100,
    "message": "Selesai!",
    "result_path": "/tmp/test.docx",
    "preview_text": "Ini preview",
    "created_at": "2026-07-17T10:00:00",
    "updated_at": "2026-07-17T10:05:00",
}


class TestJobCache:
    def setup_method(self):
        clear_cache()

    def _count(self):
        return len(get_cached_jobs(limit=999))

    def test_cache_single_job(self):
        cache_job(SAMPLE_JOB)
        assert self._count() == 1
        jobs = get_cached_jobs()
        assert jobs[0]["id"] == "test-job-001"
        assert jobs[0]["status"] == "completed"

    def test_cache_multiple_jobs(self):
        jobs = [
            {**SAMPLE_JOB, "id": f"job-{i}", "file_name": f"file-{i}.mp3"}
            for i in range(3)
        ]
        cache_jobs(jobs)
        assert self._count() == 3
        all_jobs = get_cached_jobs(limit=10)
        assert len(all_jobs) == 3

    def test_cache_update_existing(self):
        cache_job(SAMPLE_JOB)
        updated = {**SAMPLE_JOB, "status": "failed", "message": "Error test"}
        cache_job(updated)
        assert self._count() == 1
        jobs = get_cached_jobs()
        assert jobs[0]["status"] == "failed"
        assert jobs[0]["message"] == "Error test"

    def test_cache_empty_get(self):
        assert self._count() == 0
        assert get_cached_jobs() == []

    def test_cache_limit(self):
        jobs = [{**SAMPLE_JOB, "id": f"job-{i}"} for i in range(10)]
        cache_jobs(jobs)
        assert len(get_cached_jobs(limit=3)) == 3
        assert len(get_cached_jobs(limit=999)) == 10

    def test_cache_clear(self):
        cache_job(SAMPLE_JOB)
        assert self._count() == 1
        clear_cache()
        assert self._count() == 0

    def test_cache_order_desc(self):
        for i in range(3):
            j = {**SAMPLE_JOB, "id": f"job-{i}", "created_at": f"2026-07-1{7-i}T00:00:00"}
            cache_job(j)
            time.sleep(0.01)
        jobs = get_cached_jobs()
        # ordered by created_at DESC
        assert jobs[0]["id"] == "job-0"

    def test_cache_fields_preserved(self):
        cache_job(SAMPLE_JOB)
        jobs = get_cached_jobs()
        j = jobs[0]
        assert j["file_name"] == "rapat.mp3"
        assert j["result_path"] == "/tmp/test.docx"
        assert j["preview_text"] == "Ini preview"

    def test_cache_partial_data(self):
        cache_job({"id": "minimal"})
        jobs = get_cached_jobs()
        assert len(jobs) == 1
        assert jobs[0]["id"] == "minimal"
        assert jobs[0]["file_name"] == ""
