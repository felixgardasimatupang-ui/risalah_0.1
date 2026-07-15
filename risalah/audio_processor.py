import os
import sys
import json
import math
from pydub import AudioSegment
from pydub.silence import detect_silence
from tqdm import tqdm

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CHUNK_MINUTES = 30

SUPPORTED_FORMATS = {
    '.mp3': 'mp3', '.mp4': 'mp4', '.m4a': 'm4a', '.wav': 'wav',
    '.ogg': 'ogg', '.flac': 'flac', '.aac': 'aac', '.wma': 'wma',
    '.mov': 'mov', '.avi': 'avi', '.mkv': 'mkv',
}

def validate_file(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File tidak ditemukan: {file_path}")
    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if size_mb > 2000:
        print(f"PERINGATAN: File sangat besar ({size_mb:.0f} MB). Proses bisa lama.")
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_FORMATS:
        raise ValueError(f"Format {ext} tidak didukung. Gunakan: {list(SUPPORTED_FORMATS.keys())}")
    return True

def convert_to_wav_mono(audio, target_sr=16000):
    if audio.channels > 1:
        audio = audio.set_channels(1)
    if audio.frame_rate != target_sr:
        audio = audio.set_frame_rate(target_sr)
    return audio

def normalize_volume_intelligent(audio, target_dbfs=-20.0):
    noise_segments = detect_silence(audio, min_silence_len=500, silence_thresh=-50, seek_step=100)
    if noise_segments:
        noise_sample = audio[noise_segments[0][0]:noise_segments[0][1]]
        noise_floor = noise_sample.dBFS if noise_sample.dBFS != float('-inf') else -60
        if audio.dBFS - noise_floor < 15:
            print(f"Ruang dengung sempit ({audio.dBFS - noise_floor:.1f} dB). Normalisasi ringan.")
            gain = min(target_dbfs - audio.dBFS, 10)
            return audio.apply_gain(gain)
    gain = target_dbfs - audio.dBFS
    if gain > 25:
        print(f"Audio sangat pelan. Gain terbatas ke 25dB (dari {gain:.0f}dB).")
        gain = 25
    return audio.apply_gain(gain)

def process_audio(file_path, output_dir=None, chunk_minutes=DEFAULT_CHUNK_MINUTES):
    if output_dir is None:
        output_dir = os.path.join(PROJECT_ROOT, "output", "chunks")
    os.makedirs(output_dir, exist_ok=True)

    validate_file(file_path)

    chunk_duration_ms = chunk_minutes * 60 * 1000
    print(f"Memuat: {file_path}")
    try:
        audio = AudioSegment.from_file(file_path)
    except Exception as e:
        raise RuntimeError(f"Gagal membaca audio (mungkin corrupt): {e}")

    if len(audio) == 0:
        raise RuntimeError("File audio kosong (0 durasi)")

    print(f"Konversi 16kHz mono...")
    audio = convert_to_wav_mono(audio)

    print(f"Normalisasi volume cerdas...")
    audio = normalize_volume_intelligent(audio)

    total_duration_ms = len(audio)
    total_minutes = total_duration_ms / 60000
    num_chunks = math.ceil(total_duration_ms / chunk_duration_ms)
    print(f"Durasi: {total_minutes:.1f} menit -> {num_chunks} chunk @ {chunk_minutes} menit")

    chunks = []
    for i in tqdm(range(num_chunks), desc="Split audio"):
        start_ms = i * chunk_duration_ms
        end_ms = min(start_ms + chunk_duration_ms, total_duration_ms)
        chunk = audio[start_ms:end_ms]
        chunk_name = f"chunk_{i+1:03d}"

        mp3_path = os.path.join(output_dir, f"{chunk_name}.mp3")
        chunk.export(mp3_path, format="mp3", bitrate="128k")

        wav_path = os.path.join(output_dir, f"{chunk_name}.wav")
        chunk.export(wav_path, format="wav")

        chunks.append({
            "index": i + 1,
            "name": chunk_name,
            "mp3": mp3_path,
            "wav": wav_path,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "start_min": round(start_ms / 60000, 1),
            "end_min": round(end_ms / 60000, 1),
            "duration_ms": end_ms - start_ms,
        })

    metadata = {
        "original_file": os.path.abspath(file_path),
        "total_duration_ms": total_duration_ms,
        "total_duration_min": round(total_minutes, 1),
        "num_chunks": num_chunks,
        "chunk_minutes": chunk_minutes,
        "chunk_duration_ms": chunk_duration_ms,
        "sample_rate": 16000,
        "channels": 1,
        "chunks": chunks,
    }

    meta_path = os.path.join(output_dir, "metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"OK: {num_chunks} chunk -> {output_dir}")
    return metadata

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python risalah/audio_processor.py <file_audio> [chunk_minutes]")
        sys.exit(1)
    cm = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_CHUNK_MINUTES
    process_audio(sys.argv[1], chunk_minutes=cm)
