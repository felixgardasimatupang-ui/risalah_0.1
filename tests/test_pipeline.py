import os

import pytest
from risalah.pipeline import stage_ingest_split, process_single_audio


def _redis_ok():
    try:
        import redis
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        r.ping()
        return True
    except Exception:
        return False


class TestPipeline:
    def test_stage_ingest(self, test_audio):
        result = stage_ingest_split(test_audio, 30)
        assert "chunks" in result
        assert "sample_rate" in result
        assert len(result["chunks"]) > 0

    @pytest.mark.slow
    @pytest.mark.skipif(not _redis_ok(), reason="Redis not available")
    def test_run_pipeline_audio_only(self, test_audio):
        result = process_single_audio(
            test_audio, "whisper", 30, {"transcribe", "diarize", "enhance", "docx"},
            None, True, "001", "BIASA", "RISALAH RAPAT",
        )
        assert result is not None

    @pytest.mark.slow
    @pytest.mark.skipif(not _redis_ok(), reason="Redis not available")
    def test_process_with_meta(self, test_audio, meta):
        result = process_single_audio(
            test_audio, "whisper", 30, {"transcribe", "diarize", "enhance", "docx"},
            None, True, "001", "BIASA", "RISALAH RAPAT",
        )
        assert result is not None
