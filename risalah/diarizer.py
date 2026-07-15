import os
import sys
import json
import torch
from tqdm import tqdm
from pydub import AudioSegment
from pydub.silence import detect_silence

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLOBAL_SPEAKER_MAP = {}

from risalah.utils import retry, cache_check, make_cache_key

CACHE_DIR_DIAR = os.path.join(PROJECT_ROOT, "output", "diarization")

def run_diarization(chunks, output_dir=None):
    if output_dir is None:
        output_dir = CACHE_DIR_DIAR
    os.makedirs(output_dir, exist_ok=True)

    ck = make_cache_key("diarization", *[c["name"] for c in chunks])
    return cache_check(output_dir, ck, lambda: _run_diarization_impl(chunks, output_dir))

def _run_diarization_impl(chunks, output_dir):
    hf_token = os.getenv("HF_TOKEN")
    if hf_token:
        return run_pyannote_diarization(chunks, hf_token, output_dir)
    try:
        import speechbrain
        return run_speechbrain_diarization(chunks, output_dir)
    except ImportError:
        print("speechbrain tidak terinstal. Fallback VAD (tanpa label speaker).")
        print("Gemini akan membedakan pembicara dari konteks percakapan.")
        return run_vad_segmentation(chunks, output_dir)

def run_pyannote_diarization(chunks, hf_token, output_dir=None):
    from pyannote.audio import Pipeline
    from pyannote.audio.pipelines.utils.hook import ProgressHook

    if output_dir is None:
        output_dir = CACHE_DIR_DIAR
    os.makedirs(output_dir, exist_ok=True)

    print("Memuat Pyannote speaker-diarization-community-1...")
    pipeline = None
    for model_name in ["pyannote/speaker-diarization-community-1", "pyannote/speaker-diarization-3.1"]:
        try:
            @retry(max_attempts=2, delay=10, backoff=2)
            def load_pipeline(m):
                return Pipeline.from_pretrained(m, use_auth_token=hf_token)
            pipeline = load_pipeline(model_name)
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
            @retry(max_attempts=2, delay=5, backoff=2)
            def process_chunk(c):
                with ProgressHook() as hook:
                    return pipeline(c["wav"], hook=hook)

            output = process_chunk(chunk)

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

def run_speechbrain_diarization(chunks, output_dir=None):
    from speechbrain.inference.speaker import SpeakerRecognition
    from sklearn.cluster import AgglomerativeClustering
    import numpy as np

    if output_dir is None:
        output_dir = os.path.join(PROJECT_ROOT, "output", "diarization")
    os.makedirs(output_dir, exist_ok=True)

    print("Memuat SpeechBrain ECAPA-TDNN (tanpa HF_TOKEN)...")
    try:
        embedding_model = SpeakerRecognition.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
        )
        embedding_model = embedding_model.to("cpu")
        embedding_model.eval()
        print("SpeechBrain siap (CPU). Ekstraksi embedding + clustering...")
    except Exception as e:
        print(f"SpeechBrain gagal: {e}. Fallback VAD.")
        return run_vad_segmentation(chunks, output_dir)

    GLOBAL_SPEAKER_MAP.clear()
    next_global_id = 0
    all_results = []

    for chunk in tqdm(chunks, desc="SpeechBrain diarization"):
        try:
            audio = AudioSegment.from_wav(chunk["wav"])
            audio_dur_ms = len(audio)
            sample_rate = audio.frame_rate

            silence_ranges = detect_silence(
                audio, min_silence_len=600, silence_thresh=-40, seek_step=100
            )

            raw_segments_ms = []
            prev_end = 0
            for start_ms, end_ms in silence_ranges:
                if start_ms > prev_end + 200:
                    raw_segments_ms.append((prev_end, start_ms))
                prev_end = end_ms
            if prev_end < audio_dur_ms - 200:
                raw_segments_ms.append((prev_end, audio_dur_ms))

            if not raw_segments_ms:
                raw_segments_ms = [(0, audio_dur_ms)]

            min_dur = 1000
            raw_segments_ms = [(s, e) for s, e in raw_segments_ms if e - s >= min_dur]
            if not raw_segments_ms:
                raise ValueError("Semua segmen terlalu pendek")

            embeddings = []
            valid_segments = []
            for start_ms, end_ms in raw_segments_ms:
                seg_audio = audio[start_ms:end_ms]
                if seg_audio.duration_seconds < 0.5:
                    continue
                seg_audio = seg_audio.set_frame_rate(16000).set_channels(1)
                samples = torch.tensor(
                    np.array(seg_audio.get_array_of_samples(), dtype=np.float32)
                ).unsqueeze(0)
                target_frames = 16000
                if samples.shape[1] < target_frames:
                    pad = torch.zeros(1, target_frames - samples.shape[1])
                    samples = torch.cat([samples, pad], dim=1)
                elif samples.shape[1] > target_frames * 10:
                    samples = samples[:, :target_frames * 10]
                with torch.no_grad():
                    emb = embedding_model.encode_batch(samples).squeeze().detach().numpy()
                embeddings.append(emb)
                valid_segments.append((start_ms, end_ms))
                embeddings.append(emb)
                valid_segments.append((start_ms, end_ms))

            if len(valid_segments) < 2:
                speakers = [{"start": round(s / 1000, 2), "end": round(e / 1000, 2), "speaker": "SPEAKER_00"}
                            for s, e in valid_segments]
            else:
                embeddings = np.vstack(embeddings)
                n_clusters = min(len(valid_segments) // 3 + 1, 10)
                n_clusters = max(2, min(n_clusters, len(embeddings)))
                clustering = AgglomerativeClustering(n_clusters=n_clusters, linkage="average")
                labels = clustering.fit_predict(embeddings)

                local_map = {}
                local_next = 0
                speakers = []
                for (start_ms, end_ms), label in zip(valid_segments, labels):
                    key = str(label)
                    if key not in local_map:
                        local_map[key] = f"SPEAKER_{local_next:02d}"
                        local_next += 1
                    global_key = local_map[key]
                    if global_key not in GLOBAL_SPEAKER_MAP:
                        GLOBAL_SPEAKER_MAP[global_key] = f"SPEAKER_{next_global_id:02d}"
                        next_global_id += 1
                    speakers.append({
                        "start": round(start_ms / 1000, 2),
                        "end": round(end_ms / 1000, 2),
                        "speaker": GLOBAL_SPEAKER_MAP[global_key],
                    })

            seg_data = {"chunk": chunk["name"], "speakers": speakers}
            json_path = os.path.join(output_dir, f"{chunk['name']}.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(seg_data, f, indent=2, ensure_ascii=False)
            all_results.append(seg_data)

        except Exception as e:
            print(f"SpeechBrain error {chunk['name']}: {e}")
            fallback = run_vad_segmentation([chunk], output_dir)
            if fallback:
                all_results.append(fallback[0])

    combined_path = os.path.join(output_dir, "diarization_lengkap.json")
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"SpeechBrain selesai. {len(GLOBAL_SPEAKER_MAP)} speaker unik global.")
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
        output_dir = CACHE_DIR_DIAR
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
