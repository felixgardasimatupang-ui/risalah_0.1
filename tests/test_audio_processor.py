import os
import pytest
from risalah.audio_processor import process_audio, validate_file, convert_to_wav_mono


class TestAudioProcessor:
    def test_convert_to_wav_mono(self, test_audio):
        from pydub import AudioSegment
        audio = AudioSegment.from_file(test_audio)
        converted = convert_to_wav_mono(audio, target_sr=16000)
        assert converted.channels == 1
        assert converted.frame_rate == 16000

    def test_process_audio(self, test_audio):
        result = process_audio(test_audio, chunk_minutes=30)
        assert "chunks" in result
        assert "sample_rate" in result
        assert len(result["chunks"]) > 0

    def test_validate_file_valid(self, test_audio):
        assert validate_file(test_audio) is True

    def test_validate_file_invalid(self):
        with pytest.raises(FileNotFoundError):
            validate_file("/tmp/nonexistent.wav")

    def test_process_audio_with_metadata(self, test_audio):
        result = process_audio(test_audio)
        assert result["original_file"].endswith("wav")
        assert result["sample_rate"] == 16000
