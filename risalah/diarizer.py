import os
import sys
import json
import torch
from tqdm import tqdm
from pydub import AudioSegment
from pydub.silence import detect_silence

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLOBAL_SPEAKER_MAP = {}

def run_diarization(chunks, output_dir=None):
    hf_token = os.getenv("HF_TOKEN")
    if hf_token:
        return run_pyannote_diarization(chunks, hf_token, output_dir)
    else:
        print("HF_TOKEN tidak ada. Gunakan segmentasi VAD (tanpa label speaker).")
        print("Gemini akan membedakan pembicara dari konteks percakapan.")
        return run_vad_segmentation(chunks, output_dir)

def run_pyannote_diarization(chunks, hf_token, output_dir=None):
    from pyannote.audio import Pipeline
    from pyannote.audio.pipelines.utils.hook import ProgressHook

    if output_dir is None:
        output_dir = os.path.join(PROJECT_ROOT, "output", "diarization")
    os.makedirs(output_dir, exist_ok=True)

    print("Memuat Pyannote speaker-diarization-3.1...")
    pipeline = None
    for model_name in ["pyannote/speaker-diarization-3.1", "pyannote/speaker-diarization-community-1"]:
        try:
            pipeline = Pipeline.from_pretrained(model_name, use_auth_token=hf_token)
            break
        except Exception as e:
            print(f"{model_name} gagal: {e}")

    if pipeline is None:
        print("Semua Pyannote gagal. Fallback VAD.")
        return run_vad_segmentation(chunks, output_dir)

    if torch.backends.mps.is_available():
        pipeline.to(torch.device("mps"))
    elif torch.cuda.is_available():
        pipeline.to(torch.device("cuda"))

    GLOBAL_SPEAKER_MAP.clear()
    next_global_id = 0

    all_results = []
    for chunk in tqdm(chunks, desc="Pyannote"):
        try:
            with ProgressHook() as hook:
                output = pipeline(chunk["wav"], hook=hook)

            speakers = []
            for segment, track, speaker in output.itertracks(yield_label=True):
                if speaker not in GLOBAL_SPEAKER_MAP:
                    GLOBAL_SPEAKER_MAP[speaker] = f"SPEAKER_{next_global_id:02d}"
                    next_global_id += 1
                speakers.append({
                    "start": round(segment.start, 2),
                    "end": round(segment.end, 2),
                    "speaker": GLOBAL_SPEAKER_MAP[speaker],
                })

            seg_data = {"chunk": chunk["name"], "speakers": speakers}
            json_path = os.path.join(output_dir, f"{chunk['name']}.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(seg_data, f, indent=2, ensure_ascii=False)
            all_results.append(seg_data)

        except Exception as e:
            print(f"Pyannote error {chunk['name']}: {e}")

    combined_path = os.path.join(output_dir, "diarization_lengkap.json")
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"Pyannote selesai. {len(GLOBAL_SPEAKER_MAP)} speaker unik global.")
    return all_results

def run_vad_segmentation(chunks, output_dir=None):
    if output_dir is None:
        output_dir = os.path.join(PROJECT_ROOT, "output", "diarization")
    os.makedirs(output_dir, exist_ok=True)

    all_results = []
    for chunk in tqdm(chunks, desc="VAD segmentasi"):
        try:
            audio = AudioSegment.from_wav(chunk["wav"])
            audio_dur_sec = len(audio) / 1000

            silence_ranges = detect_silence(
                audio, min_silence_len=600, silence_thresh=-40, seek_step=100
            )

            if not silence_ranges:
                speakers = [{"start": 0, "end": round(audio_dur_sec, 2), "speaker": "SPEAKER_00"}]
            else:
                segments = []
                prev_end = 0
                for start_ms, end_ms in silence_ranges:
                    if start_ms > prev_end + 200:
                        segments.append({
                            "start": round(prev_end / 1000, 2),
                            "end": round(start_ms / 1000, 2),
                            "speaker": "SPEAKER_00",
                        })
                    prev_end = end_ms

                audio_dur_ms = len(audio)
                if prev_end < audio_dur_ms - 200:
                    segments.append({
                        "start": round(prev_end / 1000, 2),
                        "end": round(audio_dur_ms / 1000, 2),
                        "speaker": "SPEAKER_00",
                    })

                speakers = segments if segments else [{"start": 0, "end": round(audio_dur_sec, 2), "speaker": "SPEAKER_00"}]

        except Exception as e:
            print(f"VAD error {chunk['name']}: {e}")
            speakers = [{"start": 0, "end": 600, "speaker": "SPEAKER_00"}]

        seg_data = {"chunk": chunk["name"], "speakers": speakers}
        json_path = os.path.join(output_dir, f"{chunk['name']}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(seg_data, f, indent=2, ensure_ascii=False)
        all_results.append(seg_data)

    combined_path = os.path.join(output_dir, "diarization_lengkap.json")
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"VAD selesai. {len(all_results)} chunk (semua speaker=SPEAKER_00, Gemini akan bedakan).")
    return all_results

def merge_transcript_with_diarization(transcript_data, diarization_data):
    merged = []
    for trans_chunk in transcript_data:
        chunk_name = trans_chunk["chunk"]
        dia_chunk = next((d for d in diarization_data if d["chunk"] == chunk_name), None)

        for seg in trans_chunk.get("segments", []):
            seg_start = seg["start"]
            seg_speaker = seg.get("speaker", "")

            if seg_speaker and seg_speaker != "SPEAKER_UNKNOWN":
                speaker = seg_speaker
            elif dia_chunk:
                speaker = "SPEAKER_UNKNOWN"
                for ds in dia_chunk.get("speakers", []):
                    if ds["start"] - 0.5 <= seg_start <= ds["end"] + 0.5:
                        speaker = ds["speaker"]
                        break
            else:
                speaker = "SPEAKER_UNKNOWN"

            merged.append({
                "chunk": chunk_name,
                "start": seg["start"],
                "end": seg["end"],
                "speaker": speaker,
                "text": seg["text"],
            })

    return merged

def run_diarization_pipeline(audio_chunks, transcript_segments, output_dir=None):
    if output_dir is None:
        output_dir = os.path.join(PROJECT_ROOT, "output", "diarization")
    os.makedirs(output_dir, exist_ok=True)

    diarization_results = run_diarization(audio_chunks, output_dir)
    if not diarization_results:
        print("Diarization kosong. Semua speaker = SPEAKER_UNKNOWN.")
        merged = []
        for chunk_data in transcript_segments:
            for seg in chunk_data.get("segments", []):
                merged.append({
                    "chunk": chunk_data["chunk"],
                    "start": seg["start"],
                    "end": seg["end"],
                    "speaker": seg.get("speaker", "SPEAKER_UNKNOWN"),
                    "text": seg["text"],
                })
        return merged

    merged = merge_transcript_with_diarization(transcript_segments, diarization_results)

    merged_path = os.path.join(output_dir, "merged_lengkap.json")
    with open(merged_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    speaker_counts = {}
    for m in merged:
        speaker_counts[m["speaker"]] = speaker_counts.get(m["speaker"], 0) + 1

    print(f"Merge: {len(merged)} segmen, {len(speaker_counts)} speaker:")
    for spk, count in sorted(speaker_counts.items()):
        print(f"  {spk}: {count} segmen")
    return merged

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    if len(sys.argv) < 2:
        print("Usage: python risalah/diarizer.py <metadata_json> [transcript_json]")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        meta = json.load(f)

    transcript_segments = None
    if len(sys.argv) > 2:
        with open(sys.argv[2]) as f:
            transcript_segments = json.load(f)

    run_diarization_pipeline(meta["chunks"], transcript_segments)
