import os
import pytest
from risalah.pipeline import stage_ingest_split, process_single_audio


class TestPipeline:
    def test_stage_ingest(self, test_audio):
        result = stage_ingest_split(test_audio, 30)
        assert "chunks" in result
        assert "sample_rate" in result
        assert len(result["chunks"]) > 0

    @pytest.mark.slow
    def test_run_pipeline_audio_only(self, test_audio):
        result = process_single_audio(
            test_audio, "whisper", 30, {"transcribe", "diarize", "enhance", "docx"},
            None, True, "001", "BIASA", "RISALAH RAPAT",
        )
        assert result is not None

    @pytest.mark.slow
    def test_process_with_meta(self, test_audio, meta):
        result = process_single_audio(
            test_audio, "whisper", 30, {"transcribe", "diarize", "enhance", "docx"},
            None, True, "001", "BIASA", "RISALAH RAPAT",
        )
        assert result is not None
