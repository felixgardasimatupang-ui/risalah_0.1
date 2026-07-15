import os
import pytest
from risalah.file_scanner import scan_folder, classify


class TestFileScanner:
    def test_scan_empty_dir(self, tmp_path):
        results = scan_folder(str(tmp_path))
        assert isinstance(results, dict)
        assert results["audio_files"] == []

    def test_scan_with_audio_files(self, tmp_path):
        for fname in ["test.mp3", "test.wav", "test.txt"]:
            (tmp_path / fname).write_text("")
        results = scan_folder(str(tmp_path))
        assert len(results["audio_files"]) >= 1

    def test_classify_audio(self):
        assert classify(".mp3") == "audio"
        assert classify(".wav") == "audio"

    def test_classify_document(self):
        assert classify(".txt") == "text"
        assert classify(".pdf") == "document"

    def test_classify_image(self):
        assert classify(".jpg") == "image"
        assert classify(".png") == "image"

    def test_scan_nonexistent_dir(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            scan_folder(str(tmp_path / "nonexistent"))
