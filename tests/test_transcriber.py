import os

import pytest
from risalah.transcriber import transcribe_all, transcribe_with_whisper


def _assemblyai_configured():
    key = os.getenv("ASSEMBLYAI_API_KEY")
    return bool(key) and key != "your_assemblyai_api_key_here"


class TestTranscriber:
    @pytest.mark.slow
    def test_transcribe_all_empty(self):
        result = transcribe_all([], engine="whisper")
        assert result == []

    @pytest.mark.slow
    def test_transcribe_whisper_no_chunks(self):
        result = transcribe_with_whisper([])
        assert result == []

    @pytest.mark.slow
    @pytest.mark.skipif(not _assemblyai_configured(), reason="ASSEMBLYAI_API_KEY not set")
    def test_transcribe_assemblyai_no_chunks(self):
        result = transcribe_all([], engine="assemblyai")
        assert result == []
