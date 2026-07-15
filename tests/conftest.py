import sys
import os
import json
import wave
import struct
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

TEST_AUDIO_PATH = "/tmp/test_audio.wav"
META = {
    "tanggal": "Senin, 15 Juli 2026",
    "waktu": "09:00 - selesai",
    "tempat": "Ruang Rapat Utama",
    "acara": "Rapat Koordinasi APBD",
    "penyelenggara": "Sekretariat Daerah",
    "pimpinan": "Bapak Ketua",
    "peserta": "SPEAKER_00, SPEAKER_01",
}

SAMPLE_SEGMENTS = [
    {"chunk": "chunk_001", "start": 0.0, "end": 5.0, "speaker": "SPEAKER_00", "text": "Selamat pagi, kita mulai rapat hari ini."},
    {"chunk": "chunk_001", "start": 5.0, "end": 10.0, "speaker": "SPEAKER_01", "text": "Terima kasih, Bapak Ketua."},
    {"chunk": "chunk_001", "start": 10.0, "end": 15.0, "speaker": "SPEAKER_00", "text": "Agenda pertama adalah APBD."},
]


@pytest.fixture(scope="session")
def test_audio():
    if not os.path.exists(TEST_AUDIO_PATH):
        sample_rate = 16000
        duration = 3
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        audio = (np.sin(2 * np.pi * 440 * t) * 32767 * 0.3).astype(np.int16)
        with wave.open(TEST_AUDIO_PATH, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio.tobytes())
    return TEST_AUDIO_PATH


@pytest.fixture
def meta():
    return META.copy()


@pytest.fixture
def segments():
    return [dict(s) for s in SAMPLE_SEGMENTS]


@pytest.fixture
def sample_docx_path(tmp_path):
    p = tmp_path / "test_risalah.docx"
    return str(p)
