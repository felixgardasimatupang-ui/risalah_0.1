import os
import sys
import json
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
load_dotenv()


def validate_env():
    errors = []
    gemini = os.getenv("GEMINI_API_KEY")
    if not gemini or gemini == "your_gemini_api_key_here":
        errors.append("GEMINI_API_KEY belum diisi. Dapatkan gratis di https://aistudio.google.com/")

    hf = os.getenv("HF_TOKEN")
    if not hf:
        print("PERINGATAN: HF_TOKEN tidak diisi. Speaker diarization Pyannote tidak akan jalan.")
        print("           Daftar di https://huggingface.co/settings/tokens (gratis)")

    assembly = os.getenv("ASSEMBLYAI_API_KEY")
    if not assembly or assembly == "your_assemblyai_api_key_here":
        print("INFO: ASSEMBLYAI_API_KEY tidak diisi. Gunakan --engine whisper (default).")

    for dep, name in [("whisper", "openai-whisper"), ("pydub", "pydub"),
                       ("torch", "torch"), ("docx", "python-docx")]:
        try:
            __import__(dep)
        except ImportError:
            errors.append(f"{name} belum terinstall. Jalankan: pip install -r requirements.txt")

    if errors:
        print("\n" + "!" * 60)
        for e in errors:
            print(f"  ! {e}")
        print("!" * 60 + "\n")
        sys.exit(1)

    return True


def out(sub):
    p = os.path.join(PROJECT_ROOT, "output", sub)
    os.makedirs(p, exist_ok=True)
    return p


def load_json(path):
    return json.load(open(path)) if path and os.path.exists(path) else None


def stage_scan_folder(folder_path):
    from risalah.file_scanner import scan_folder, extract_all_text
    print("=" * 60)
    print("STAGE 0: SCAN FOLDER")
    print("=" * 60)
    scan = scan_folder(folder_path)
    extracted = extract_all_text(scan)
    return scan, extracted


def stage_ingest_split(audio_file, chunk_minutes):
    from risalah.audio_processor import process_audio
    print("=" * 60)
    print("STAGE 1-2: INGEST & SPLIT")
    print("=" * 60)
    return process_audio(audio_file, chunk_minutes=chunk_minutes)


def stage_transcribe(chunks, engine):
    from risalah.transcriber import transcribe_all
    print("=" * 60)
    print(f"STAGE 3: TRANSKRIPSI ({engine.upper()})")
    print("=" * 60)
    return transcribe_all(chunks, engine)


def stage_diarize(chunks, transcript):
    from risalah.diarizer import run_diarization_pipeline
    print("=" * 60)
    print("STAGE 4: DIARIZATION")
    print("=" * 60)
    return run_diarization_pipeline(chunks, transcript)


def stage_enhance(merged, extracted_text=None, no_gemini=False):
    from risalah.ai_enhancer import enhance_transcript, enhance_document
    print("=" * 60)
    print("STAGE 5: ENHANCEMENT")
    print("=" * 60)

    if no_gemini:
        from risalah.ai_enhancer import build_fallback
        enhanced = build_fallback(merged)
    else:
        enhanced = enhance_transcript(merged)

    if extracted_text and extracted_text.get("all_text_combined", "").strip():
        enhanced["dokumen_pendukung"] = extracted_text
        doc_text = extracted_text["all_text_combined"]
        if len(doc_text) > 500 and not no_gemini:
            summary = enhance_document(doc_text)
            if summary:
                enhanced["dokumen_ringkasan"] = summary
        ep = os.path.join(out("enhanced"), "enhanced_lengkap.json")
        json.dump(enhanced, open(ep, "w"), indent=2, ensure_ascii=False)

    return enhanced


def stage_generate_docx(enhanced, metadata, preview=False, doc_number="_______________",
                         classification="BIASA", title="RISALAH RAPAT"):
    from risalah.docx_generator import generate_risalah, generate_preview_text
    print("=" * 60)
    print("STAGE 6: GENERATE " + ("PREVIEW" if preview else "DOCX"))
    print("=" * 60)

    if preview:
        text = generate_preview_text(enhanced, metadata)
        preview_path = os.path.join(out("docs"), "preview_risalah.txt")
        with open(preview_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(text)
        print(f"\nPreview juga tersimpan: {preview_path}")
        return preview_path
    else:
        return generate_risalah(enhanced, metadata,
                                title=title, doc_number=doc_number,
                                classification=classification)


def process_single_audio(file_path, engine, chunk_minutes, skip, extracted_text,
                          preview, doc_number, classification, title):
    meta = None if "ingest" in skip else stage_ingest_split(file_path, chunk_minutes)
    if not meta:
        meta = load_json(os.path.join(out("chunks"), "metadata.json"))
    if not meta:
        return None

    transcript = stage_transcribe(meta["chunks"], engine) if "transcribe" not in skip else \
                 load_json(os.path.join(out("transcripts"), "transkrip_lengkap.json"))
    if not transcript:
        return None

    merged = stage_diarize(meta["chunks"], transcript) if "diarize" not in skip else \
             load_json(os.path.join(out("diarization"), "merged_lengkap.json"))
    if not merged:
        merged = [{"chunk": c["chunk"], "start": s["start"], "end": s["end"],
                    "speaker": s.get("speaker", "SPEAKER_UNKNOWN"), "text": s["text"]}
                  for c in transcript for s in c.get("segments", [])]

    no_gemini = "enhance" in skip
    enhanced = stage_enhance(merged, extracted_text, no_gemini)

    metadata = {"tanggal": datetime.now().strftime("%A, %d %B %Y"),
                "waktu": "_______________ - selesai",
                "tempat": "_______________",
                "acara": os.path.splitext(os.path.basename(file_path))[0]}

    return stage_generate_docx(enhanced, metadata, preview, doc_number, classification, title)


def run_pipeline(input_path, engine="whisper", chunk_minutes=30, skip_stages=None,
                 preview=False, doc_number="_______________", classification="BIASA",
                 title="RISALAH RAPAT"):
    if skip_stages is None:
        skip_stages = []

    folder_mode = os.path.isdir(input_path)
    extracted_text = None

    if folder_mode:
        scan, extracted_text = stage_scan_folder(input_path)
        audio_files = [f["path"] for f in scan.get("audio_files", [])]

        if not audio_files:
            dummy = {"tanggal": datetime.now().strftime("%A, %d %B %Y"),
                     "waktu": "_______________", "tempat": "_______________",
                     "acara": os.path.basename(input_path.rstrip("/"))}
            fallback = {
                "speaker_identification": [],
                "corrected_transcript": [{"time": "00:00", "speaker": "Dokumen",
                                          "speaker_original": "DOKUMEN",
                                          "text": extracted_text["all_text_combined"][:50000]}],
                "pokok_bahasan": [], "keputusan_rapat": [], "kesimpulan": [],
                "tindak_lanjut": [], "agenda_rapat": [], "dokumen_terkait": [],
                "dokumen_pendukung": extracted_text,
            }
            stage_generate_docx(fallback, dummy, preview, doc_number, classification, title)
            return

        print(f"\n{len(audio_files)} file audio ditemukan.")
        generated = []
        for i, af in enumerate(audio_files):
            print(f"\n{'='*60}")
            print(f"AUDIO {i+1}/{len(audio_files)}: {os.path.basename(af)}")
            print(f"{'='*60}")
            result = process_single_audio(af, engine, chunk_minutes, skip_stages,
                                          extracted_text if i == 0 else None,
                                          preview, doc_number, classification, title)
            if result:
                generated.append(result)

        print(f"\n{'='*60}")
        print(f"SELESAI: {len(generated)}/{len(audio_files)} file diproses")
        for g in generated:
            print(f"  - {g}")
        print(f"{'='*60}")

    else:
        result = process_single_audio(input_path, engine, chunk_minutes, skip_stages, None,
                                       preview, doc_number, classification, title)
        if result:
            print(f"\n{'='*60}")
            print(f"{'PREVIEW' if preview else 'RISALAH'}: {result}")
            print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="Risalah Rapat — dari Audio/Folder ke DOCX")
    parser.add_argument("input", help="File audio ATAU folder")
    parser.add_argument("--engine", choices=["whisper", "assemblyai", "gemini"], default="whisper")
    parser.add_argument("--chunk-minutes", type=int, default=30, help="Durasi per chunk (menit)")
    parser.add_argument("--preview", action="store_true", help="Preview TXT saja (tanpa DOCX)")
    parser.add_argument("--title", default="RISALAH RAPAT", help="Judul risalah")
    parser.add_argument("--nomor", default="_______________",
                        help="Nomor dokumen (contoh: 001/RISALAH/DINAS/2026)")
    parser.add_argument("--klasifikasi", choices=["BIASA", "TERBATAS", "RAHASIA"],
                        default="BIASA", help="Klasifikasi dokumen")
    parser.add_argument("--skip", nargs="*", choices=["ingest", "transcribe", "diarize",
                                                       "enhance", "docx"], default=[])
    parser.add_argument("--stage", choices=["all", "scan-only", "ingest-only",
                                            "transcribe-only", "diarize-only",
                                            "enhance-only", "docx-only"], default="all")

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: '{args.input}' tidak ditemukan")
        sys.exit(1)

    validate_env()

    stage_map = {
        "scan-only": ["ingest", "transcribe", "diarize", "enhance", "docx"],
        "ingest-only": ["transcribe", "diarize", "enhance", "docx"],
        "transcribe-only": ["ingest", "diarize", "enhance", "docx"],
        "diarize-only": ["ingest", "transcribe", "enhance", "docx"],
        "enhance-only": ["ingest", "transcribe", "diarize", "docx"],
        "docx-only": ["ingest", "transcribe", "diarize", "enhance"],
    }

    skip = list(args.skip)
    if args.stage in stage_map:
        skip.extend(stage_map[args.stage])

    if os.path.isdir(args.input) and args.stage == "scan-only":
        from risalah.file_scanner import scan_folder, extract_all_text
        s = scan_folder(args.input)
        if s["total_files"] > 0:
            extract_all_text(s)
        return

    run_pipeline(args.input, args.engine, args.chunk_minutes, list(set(skip)),
                 args.preview, args.nomor, args.klasifikasi, args.title)


if __name__ == "__main__":
    main()
