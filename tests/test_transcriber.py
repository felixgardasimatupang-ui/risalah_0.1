import pytest
from risalah.transcriber import transcribe_all, transcribe_with_whisper


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
    def test_transcribe_assemblyai_no_chunks(self):
        result = transcribe_all([], engine="assemblyai")
        assert result == []
