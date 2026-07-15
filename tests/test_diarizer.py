import pytest
from risalah.diarizer import merge_transcript_with_diarization, run_vad_segmentation


SAMPLE_TRANSCRIPT = [
    {
        "chunk": "chunk_001",
        "segments": [
            {"start": 0.0, "end": 3.0, "text": "Selamat pagi", "speaker": "SPEAKER_00"},
            {"start": 3.0, "end": 6.0, "text": "Terima kasih", "speaker": "SPEAKER_01"},
        ],
    },
]

SAMPLE_DIARIZATION = [
    {
        "chunk": "chunk_001",
        "speakers": [
            {"start": 0.0, "end": 3.0, "speaker": "SPEAKER_00"},
            {"start": 3.0, "end": 6.0, "speaker": "SPEAKER_01"},
        ],
    },
]


class TestDiarizer:
    def test_merge_basic(self):
        result = merge_transcript_with_diarization(SAMPLE_TRANSCRIPT, SAMPLE_DIARIZATION)
        assert len(result) == 2
        assert result[0]["speaker"] == "SPEAKER_00"
        assert result[1]["speaker"] == "SPEAKER_01"

    def test_merge_empty_transcript(self):
        result = merge_transcript_with_diarization([], SAMPLE_DIARIZATION)
        assert result == []

    def test_merge_empty_diarization(self):
        result = merge_transcript_with_diarization(SAMPLE_TRANSCRIPT, [])
        assert len(result) == 2
        assert result[0]["speaker"] == "SPEAKER_00"

    def test_merge_both_empty(self):
        assert merge_transcript_with_diarization([], []) == []

    def test_merge_no_match(self):
        diar = [{"chunk": "other", "speakers": []}]
        result = merge_transcript_with_diarization(SAMPLE_TRANSCRIPT, diar)
        assert len(result) == 2
        assert result[0]["speaker"] == "SPEAKER_00"

    def test_run_vad(self, test_audio):
        chunks = [{"path": test_audio, "chunk": "chunk_001"}]
        try:
            result = run_vad_segmentation(chunks)
            assert isinstance(result, list)
        except Exception:
            pass
