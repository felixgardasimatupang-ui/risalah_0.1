import json
import os
import pytest
from fastapi.testclient import TestClient
from api.app import app


def redis_available() -> bool:
    """Check if Redis is reachable (CI may not have it)."""
    try:
        import redis
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        r.ping()
        return True
    except Exception:
        return False


@pytest.fixture
def client():
    return TestClient(app)


class TestApi:
    def test_health(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        # Accept ok or degraded (Redis may not be running in CI)
        assert data["status"] in ("ok", "degraded")

    def test_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_list_jobs(self, client):
        resp = client.get("/api/jobs")
        assert resp.status_code == 200
        data = resp.json()
        assert "jobs" in data

    def test_transcribe_no_file(self, client):
        resp = client.post("/api/transcribe", json={})
        assert resp.status_code == 422

    @pytest.mark.skipif(not redis_available(), reason="Redis not available")
    def test_get_nonexistent_job(self, client):
        resp = client.get("/api/jobs/nonexistent123")
        assert resp.status_code == 404
