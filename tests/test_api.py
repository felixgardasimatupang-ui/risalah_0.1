import json
import io
import pytest
from fastapi.testclient import TestClient
from api.app import app


@pytest.fixture
def client():
    return TestClient(app)


class TestApi:
    def test_health(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

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

    def test_get_nonexistent_job(self, client):
        resp = client.get("/api/jobs/nonexistent123")
        assert resp.status_code == 404
