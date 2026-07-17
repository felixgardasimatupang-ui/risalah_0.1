import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import whisper
from tqdm import tqdm

from risalah.utils import cache_check, make_cache_key, retry

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(PROJECT_ROOT, "output", "transcripts")


def transcribe_with_whisper(chunks, output_dir=None, model_name=None, lang=None) -> None:
    if model_name is None:
        model_name = os.getenv("WHISPER_MODEL", "large-v3")
    if output_dir is None:
        output_dir = CACHE_DIR
    if lang is None:
        lang = os.getenv("RISALAH_LANG", "id")[:2]
    os.makedirs(output_dir, exist_ok=True)

    device = "cpu"
    print(f"Device: {device.upper()}")

    @retry(max_attempts=3, delay=5, backoff=2)
    def load_model(m) -> None:
        return whisper.load_model(m, device=device)

    model = None
    for m in [model_name, "large-v3", "large", "medium", "small", "base"]:
        try:
            model = load_model(m)
            print(f"Model: {m}")
            break
        except Exception as e:
            print(f"Whisper {m} gagal: {e}")

    if model is None:
        raise RuntimeError("Tidak ada model Whisper tersedia")

    all_results = []
    for chunk in tqdm(chunks, desc="Whisper"):
        chunk_cache_key = make_cache_key(chunk["name"], "whisper")

        def do_transcribe(c=chunk) -> None:
            result = model.transcribe(c["mp3"], language=lang, verbose=False, fp16=False)
            segments = [
                {
                    "start": round(s["start"], 2),
                    "end": round(s["end"], 2),
                    "text": s["text"].strip(),
                }
                for s in result["segments"]
            ]
            return {"chunk": c["name"], "text": result["text"].strip(), "segments": segments}

        try:
            data = cache_check(output_dir, chunk_cache_key, do_transcribe)
            all_results.append(data)
            json_path = os.path.join(output_dir, f"{data['chunk']}.json")
            with open(json_path, "w", encoding="utf-8") as fp:
                json.dump(data, fp, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Whisper error {chunk['name']}: {e}")

    combined_path = os.path.join(output_dir, "transkrip_lengkap.json")
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"Whisper selesai. {len(all_results)} chunk.")
    return all_results


def transcribe_with_assemblyai(chunks, output_dir=None, lang=None) -> None:
    import assemblyai as aai
    from dotenv import load_dotenv

    load_dotenv()

    if lang is None:
        lang = os.getenv("RISALAH_LANG", "id")[:2]

    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key or api_key == "your_assemblyai_api_key_here":
        raise ValueError("ASSEMBLYAI_API_KEY tidak valid")

    aai.settings.api_key = api_key
    if output_dir is None:
        output_dir = CACHE_DIR
    os.makedirs(output_dir, exist_ok=True)

    config = aai.TranscriptionConfig(
        speaker_labels=True, language_code=lang, punctuate=True, format_text=True
    )
    transcriber = aai.Transcriber()

    all_results = [None] * len(chunks)

    @retry(max_attempts=3, delay=5, backoff=2)
    def transcribe_one(idx, chunk) -> None:
        cache_key = make_cache_key(chunk["name"], "assemblyai")

        def do_transcribe() -> None:
            transcript = transcriber.transcribe(chunk["mp3"], config=config)
            if transcript.status == aai.TranscriptStatus.error:
                raise RuntimeError(transcript.error)
            segments = []
            if transcript.utterances:
                for u in transcript.utterances:
                    segments.append(
                        {
                            "start": round(u.start / 1000, 2),
                            "end": round(u.end / 1000, 2),
                            "speaker": f"SPEAKER_{u.speaker}",
                            "text": u.text,
                        }
                    )
            else:
                for s in transcript.segments:
                    segments.append(
                        {
                            "start": round(s.start / 1000, 2),
                            "end": round(s.end / 1000, 2),
                            "speaker": "SPEAKER_UNKNOWN",
                            "text": s.text,
                        }
                    )
            return {"chunk": chunk["name"], "text": transcript.text, "segments": segments}

        return cache_check(output_dir, cache_key, do_transcribe)

    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {ex.submit(transcribe_one, i, c): i for i, c in enumerate(chunks)}
        for f in tqdm(as_completed(futures), total=len(chunks), desc="AssemblyAI"):
            idx, data = f.result()
            all_results[idx] = data
            json_path = os.path.join(output_dir, f"{data['chunk']}.json")
            with open(json_path, "w", encoding="utf-8") as fp:
                json.dump(data, fp, indent=2, ensure_ascii=False)

    combined_path = os.path.join(output_dir, "transkrip_lengkap.json")
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    return all_results


def transcribe_all(chunks, engine="whisper", output_dir=None, lang=None) -> None:
    if output_dir is None:
        output_dir = CACHE_DIR
    os.makedirs(output_dir, exist_ok=True)
    if lang is None:
        lang = os.getenv("RISALAH_LANG", "id")[:2]

    engines = {
        "whisper": transcribe_with_whisper,
        "assemblyai": transcribe_with_assemblyai,
    }

    if engine not in engines:
        raise ValueError(f"Engine '{engine}' tidak dikenal. Pilih: {list(engines.keys())}")

    ck = make_cache_key("transcribe_all", engine, lang, *[c["name"] for c in chunks])
    result = cache_check(output_dir, ck, lambda: engines[engine](chunks, output_dir, lang))
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python risalah/transcriber.py <metadata_json> [engine]")
        sys.exit(1)
    meta_path = sys.argv[1]
    engine = sys.argv[2] if len(sys.argv) > 2 else "whisper"
    with open(meta_path) as f:
        meta = json.load(f)
    transcribe_all(meta["chunks"], engine)
