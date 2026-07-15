import os
import sys
import json
import re
import time
import requests
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    from api.config import LLM_CONFIGS
except ImportError:
    LLM_CONFIGS = [
        {"name": "Groq", "base": "https://api.groq.com/openai/v1",
         "key": os.getenv("GROQ_API_KEY", ""), "model": "llama-3.3-70b-versatile"},
        {"name": "9router", "base": os.getenv("NINEROUTER_BASE_URL", "http://localhost:20128/v1"),
         "key": os.getenv("NINEROUTER_API_KEY", ""), "model": "light-free"},
    ]


SYSTEM_PROMPT = """Anda adalah asisten risalah rapat pemerintah Indonesia.

Analisis transkrip rapat berikut dan hasilkan JSON valid (TANPA markdown, TANPA ```).

FORMAT WAJIB:
{
  "speaker_identification": [
    {"label": "SPEAKER_00", "inferred_role": "Ketua Rapat", "inferred_name": "Bapak Bambang Susilo", "reason": "penjelasan singkat"}
  ],
  "corrected_transcript": [
    {"time": "00:02", "speaker": "Ketua Rapat", "speaker_original": "SPEAKER_00", "text": "teks setelah koreksi istilah pemerintahan"}
  ],
  "pokok_bahasan": ["item1"],
  "keputusan_rapat": ["keputusan1"],
  "kesimpulan": ["kesimpulan1"],
  "tindak_lanjut": [{"tindakan": "...", "pic": "...", "batas_waktu": "..."}],
  "agenda_rapat": ["agenda1"],
  "dokumen_terkait": ["dokumen yang disebut"]
}

PANDUAN:
- corrected_transcript: TULIS SEMUA SEGMEN transkrip, jangan lewatkan satu pun
- Koreksi istilah pemerintahan: APBD, Perda, Permendagri, Musrenbang, Renja, Renstra, RPJMD, TUPOKSI, DPA, KUA-PPAS, SPJ, LPJ, SPM, Sekda, Kadis, Kabid, BAPPEDA, BPKAD, Inspektorat, APIP, SAKIP, LKPD
- Identifikasi pembicara dari sapaan (Pak/Bu/Ibu + nama), jabatan, gaya bicara

TRANSKRIP:
__TRANSKRIP_TEXT__"""

DOCUMENT_SUMMARY_PROMPT = """Anda adalah asisten risalah rapat pemerintah Indonesia.

Rangkum dokumen pendukung rapat berikut dalam JSON valid:

{
  "ringkasan": "...",
  "poin_penting": ["poin1"],
  "angka_anggaran": [{"item": "...", "jumlah": "Rp X"}],
  "keputusan_terkait": "..."
}

DOKUMEN:
__DOC_TEXT__"""

def call_llm(prompt, max_retries=3):
    for cfg in LLM_CONFIGS:
        for attempt in range(max_retries):
            try:
                resp = requests.post(
                    f"{cfg['base']}/chat/completions",
                    headers={"Authorization": f"Bearer {cfg['key']}", "Content-Type": "application/json"},
                    json={"model": cfg['model'], "messages": [{"role": "user", "content": prompt}],
                          "temperature": 0.3, "max_tokens": 4096},
                    timeout=180,
                )
                if resp.status_code == 429:
                    print(f"  {cfg['name']} rate limit, coba lagi...")
                    time.sleep(10)
                    continue
                if resp.status_code != 200:
                    print(f"  {cfg['name']} HTTP {resp.status_code}, skip...")
                    break
                text = resp.json()["choices"][0]["message"]["content"]
                print(f"  {cfg['name']} OK ({len(text)} chars)")
                return text
            except requests.exceptions.ConnectionError:
                print(f"  {cfg['name']} tidak terhubung, skip...")
                break
            except Exception as e:
                print(f"  {cfg['name']} error: {str(e)[:80]}")
                if attempt < max_retries - 1:
                    time.sleep(5)
    return None


def init_gemini():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        raise ValueError("GEMINI_API_KEY tidak valid")
    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except ImportError:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        return genai

def extract_json_robust(text):
    text = re.sub(r'^```(?:json)?\s*', '', text.strip(), flags=re.MULTILINE)
    text = re.sub(r'\s*```$', '', text.strip(), flags=re.MULTILINE)
    text = text.strip()

    brace_depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == '{':
            if brace_depth == 0:
                start = i
            brace_depth += 1
        elif ch == '}':
            brace_depth -= 1
            if brace_depth == 0 and start >= 0:
                candidate = text[start:i+1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    pass
                start = -1

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None

def prepare_transcript_text(merged_data, max_lines=0, max_chars=12000):
    lines = []
    for seg in merged_data:
        mins = int(seg["start"]) // 60
        secs = int(seg["start"]) % 60
        speaker = seg.get("speaker", "SPEAKER_UNKNOWN")
        text = seg.get("text", "")
        lines.append(f"[{mins:02d}:{secs:02d}] {speaker}: {text}")
    if max_lines > 0 and len(lines) > max_lines:
        lines = lines[:max_lines]
    result = "\n".join(lines)
    if len(result) > max_chars:
        half = max_chars // 2
        result = result[:half] + "\n...[TENGAH DIHAPUS]...\n" + result[-half:]
    return result

def validate_and_repair(enhanced, merged_data):
    if "speaker_identification" not in enhanced:
        enhanced["speaker_identification"] = []

    if "corrected_transcript" not in enhanced or not enhanced["corrected_transcript"]:
        enhanced["corrected_transcript"] = []
        for seg in merged_data:
            mins = int(seg["start"]) // 60
            secs = int(seg["start"]) % 60
            enhanced["corrected_transcript"].append({
                "time": f"{mins:02d}:{secs:02d}",
                "speaker": seg.get("speaker", "SPEAKER_UNKNOWN"),
                "speaker_original": seg.get("speaker", "SPEAKER_UNKNOWN"),
                "text": seg.get("text", ""),
            })

    ct = enhanced["corrected_transcript"]
    actual_speakers = set(s["speaker"] for s in ct if s["speaker"])
    inferred_speakers = set(s["inferred_role"] for s in enhanced["speaker_identification"])

    orphans = actual_speakers - inferred_speakers
    for spk in orphans:
        enhanced["speaker_identification"].append({
            "label": spk,
            "inferred_role": spk,
            "inferred_name": spk,
            "reason": "auto-fill dari data",
        })

    for key in ["pokok_bahasan", "keputusan_rapat", "kesimpulan", "agenda_rapat", "dokumen_terkait"]:
        if key not in enhanced or not isinstance(enhanced[key], list):
            enhanced[key] = []

    if "tindak_lanjut" not in enhanced or not isinstance(enhanced["tindak_lanjut"], list):
        enhanced["tindak_lanjut"] = []

    return enhanced

def try_gemini(prompt, merged_data, output_dir, label="Gemini"):
    try:
        client = init_gemini()
        is_new_api = hasattr(client, "models")
    except ValueError as e:
        print(f"  {label} init gagal: {e}")
        return None

    for attempt in range(5):
        try:
            print(f"  {label} ({attempt + 1}/5)...")
            if is_new_api:
                response = client.models.generate_content(
                    model="gemini-2.0-flash", contents=prompt
                )
            else:
                model = client.GenerativeModel("gemini-2.0-flash")
                response = model.generate_content(prompt)
            result = extract_json_robust(response.text)
            if result:
                result = validate_and_repair(result, merged_data)
                n_s = len(result.get("speaker_identification", []))
                n_seg = len(result.get("corrected_transcript", []))
                if n_seg > 10:
                    enhanced_path = os.path.join(output_dir, "enhanced_lengkap.json")
                    with open(enhanced_path, "w", encoding="utf-8") as f:
                        json.dump(result, f, indent=2, ensure_ascii=False)
                    print(f"  {label} OK: {n_s} speaker, {n_seg} segmen.")
                    return result
                print(f"  {label} hanya {n_seg} segmen, ulang...")
            else:
                print("  Response tidak valid JSON, ulang...")
        except Exception as e:
            err_msg = str(e)
            print(f"  {label} error: {err_msg[:120]}...")
            m = re.search(r'retry_delay\s*\{\s*seconds:\s*(\d+)\s*\}', err_msg)
            if m:
                wait = int(m.group(1)) + 2
                print(f"    Tunggu {wait} detik...")
                time.sleep(wait)
            elif attempt < 4:
                time.sleep(10)
    return None

def enhance_with_two_phase(merged_data, output_dir):
    """Two-phase: (1) identify speakers from sample, (2) build full output."""
    sample = prepare_transcript_text(merged_data, max_lines=200, max_chars=8000)
    speaker_prompt = (
        "Anda adalah asisten risalah rapat pemerintah Indonesia.\n\n"
        "Analisis transkrip cuplikan rapat berikut dan identifikasi semua pembicara.\n"
        "Hasilkan JSON valid:\n"
        '{"speaker_identification": [{"label": "SPEAKER_00", "inferred_role": "...", '
        '"inferred_name": "...", "reason": "..."}]}\n\n'
        "Petunjuk: cari sapaan (Pak/Bu/Ibu), jabatan, gaya bicara, konteks.\n\n"
        "CUPLIKAN TRANSKRIP:\n" + sample
    )
    print("Phase 1: Identifikasi pembicara...")
    raw = call_llm(speaker_prompt)
    speaker_map = {}
    if raw:
        result = extract_json_robust(raw)
        if result and "speaker_identification" in result:
            for s in result["speaker_identification"]:
                speaker_map[s["label"]] = s
            print(f"  {len(speaker_map)} speaker teridentifikasi")

    summary_prompt = (
        "Anda adalah asisten risalah rapat pemerintah Indonesia.\n\n"
        "Berdasarkan transkrip rapat berikut, ekstrak dalam JSON valid:\n"
        '{"pokok_bahasan": ["..."], "keputusan_rapat": ["..."], '
        '"kesimpulan": ["..."], "tindak_lanjut": [{"tindakan": "...", '
        '"pic": "...", "batas_waktu": "..."}], '
        '"agenda_rapat": ["..."], "dokumen_terkait": ["..."]}\n\n'
        "TRANSKRIP:\n" + sample
    )
    print("Phase 2: Ekstrak struktur risalah...")
    raw2 = call_llm(summary_prompt)
    summary = extract_json_robust(raw2) if raw2 else {}

    enhanced = {
        "speaker_identification": list(speaker_map.values()),
        "corrected_transcript": build_corrected_transcript(merged_data, speaker_map),
        "pokok_bahasan": summary.get("pokok_bahasan", []) if summary else [],
        "keputusan_rapat": summary.get("keputusan_rapat", []) if summary else [],
        "kesimpulan": summary.get("kesimpulan", []) if summary else [],
        "tindak_lanjut": summary.get("tindak_lanjut", []) if summary else [],
        "agenda_rapat": summary.get("agenda_rapat", []) if summary else [],
        "dokumen_terkait": summary.get("dokumen_terkait", []) if summary else [],
    }
    enhanced = validate_and_repair(enhanced, merged_data)

    ep = os.path.join(output_dir, "enhanced_lengkap.json")
    with open(ep, "w", encoding="utf-8") as f:
        json.dump(enhanced, f, indent=2, ensure_ascii=False)
    n_spk = len(enhanced.get("speaker_identification", []))
    n_seg = len(enhanced.get("corrected_transcript", []))
    print(f"Two-phase OK: {n_spk} speaker, {n_seg} segmen.")
    return enhanced

def build_corrected_transcript(merged_data, speaker_map):
    """Build corrected_transcript from merged_data using speaker_map."""
    result = []
    for seg in merged_data:
        mins = int(seg["start"]) // 60
        secs = int(seg["start"]) % 60
        spk = seg.get("speaker", "SPEAKER_UNKNOWN")
        info = speaker_map.get(spk, {})
        inferred_role = info.get("inferred_role", spk) if info else spk
        text = seg.get("text", "")
        result.append({
            "time": f"{mins:02d}:{secs:02d}",
            "speaker": inferred_role,
            "speaker_original": spk,
            "text": text,
        })
    return result

def enhance_transcript(merged_data, output_dir=None):
    if output_dir is None:
        output_dir = os.path.join(PROJECT_ROOT, "output", "enhanced")
    os.makedirs(output_dir, exist_ok=True)

    transcript_text = prepare_transcript_text(merged_data)
    prompt = SYSTEM_PROMPT.replace("__TRANSKRIP_TEXT__", transcript_text)

    print("Enhancement via 9router (prioritas)...")
    result = enhance_with_two_phase(merged_data, output_dir)
    if result:
        return result

    print("Gemini fallback for full transcript...")
    result = try_gemini(prompt, merged_data, output_dir, "Gemini")
    return result

def try_doc_aware_9router(merged_data, doc_preview, output_dir, doc_context):
    sample = prepare_transcript_text(merged_data, max_lines=100, max_chars=5000)
    doc_ctx_short = doc_preview[:5000] if len(doc_preview) > 5000 else doc_preview

    sp_prompt = (
        "Anda adalah asisten risalah rapat pemerintah Indonesia.\n\n"
        f"Dokumen pendukung:\n{doc_ctx_short}\n\n"
        "Berdasarkan transkrip rapat berikut dan dokumen di atas, identifikasi semua pembicara.\n"
        "Hasilkan JSON valid:\n"
        '{"speaker_identification": [{"label": "SPEAKER_00", '
        '"inferred_role": "...", "inferred_name": "...", "reason": "..."}]}\n\n'
        f"CUPLIKAN TRANSKRIP:\n{sample}"
    )
    raw = call_llm(sp_prompt)
    speaker_map = {}
    if not raw:
        return None
    result = extract_json_robust(raw)
    if not result or "speaker_identification" not in result:
        return None
    for s in result["speaker_identification"]:
        speaker_map[s["label"]] = s
    print(f"  9router: {len(speaker_map)} speaker teridentifikasi")

    enhanced = build_doc_aware_enhanced(merged_data, doc_preview, speaker_map)
    enhanced["dokumen_analisis_mode"] = True
    enhanced["dokumen_sumber"] = [
        {"file": s["file"], "type": "dokumen" if s.get("text") else "audio"}
        for s in doc_context.get("document_sources", []) + doc_context.get("image_sources", [])
    ]
    ep = os.path.join(output_dir, "enhanced_lengkap.json")
    with open(ep, "w", encoding="utf-8") as f:
        json.dump(enhanced, f, indent=2, ensure_ascii=False)
    n_spk = len(enhanced.get("speaker_identification", []))
    n_seg = len(enhanced.get("corrected_transcript", []))
    print(f"  + {len(doc_context.get('document_sources', []))} dokumen dianalisis sebagai konteks.")
    print(f"Doc-aware OK: {n_spk} speaker, {n_seg} segmen.")
    return enhanced

def build_doc_aware_enhanced(merged_data, doc_preview, speaker_map):
    doc_ctx_short = doc_preview[:5000] if len(doc_preview) > 5000 else doc_preview
    sample = prepare_transcript_text(merged_data, max_lines=100, max_chars=5000)
    sum_prompt = (
        "Anda adalah asisten risalah rapat pemerintah Indonesia.\n\n"
        f"Dokumen pendukung:\n{doc_ctx_short}\n\n"
        "Berdasarkan transkrip dan dokumen di atas, ekstrak struktur risalah dalam JSON:\n"
        '{"pokok_bahasan": ["..."], "keputusan_rapat": ["..."], '
        '"kesimpulan": ["..."], "tindak_lanjut": [...], '
        '"agenda_rapat": ["..."], "dokumen_terkait": ["..."]}\n\n'
        "GUNAKAN dokumen untuk memahami konteks, tapi JANGAN menambahkan informasi fiktif.\n"
        f"TRANSKRIP:\n{sample}"
    )
    raw2 = call_llm(sum_prompt)
    summary = extract_json_robust(raw2) if raw2 else {}
    enhanced = {
        "speaker_identification": list(speaker_map.values()),
        "corrected_transcript": build_corrected_transcript(merged_data, speaker_map),
        "pokok_bahasan": summary.get("pokok_bahasan", []) if summary else [],
        "keputusan_rapat": summary.get("keputusan_rapat", []) if summary else [],
        "kesimpulan": summary.get("kesimpulan", []) if summary else [],
        "tindak_lanjut": summary.get("tindak_lanjut", []) if summary else [],
        "agenda_rapat": summary.get("agenda_rapat", []) if summary else [],
        "dokumen_terkait": summary.get("dokumen_terkait", []) if summary else [],
    }
    return validate_and_repair(enhanced, merged_data)

def enhance_document(document_text, output_dir=None):
    if output_dir is None:
        output_dir = os.path.join(PROJECT_ROOT, "output", "enhanced")
    os.makedirs(output_dir, exist_ok=True)

    max_chars = 25000
    text = document_text[:max_chars] if len(document_text) > max_chars else document_text
    prompt = DOCUMENT_SUMMARY_PROMPT.replace("__DOC_TEXT__", text)

    raw = call_llm(prompt, max_retries=3)
    if raw:
        result = extract_json_robust(raw)
        if result:
            return result

    try:
        client = init_gemini()
        is_new_api = hasattr(client, "models")
        if is_new_api:
            response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        else:
            response = client.GenerativeModel("gemini-2.0-flash").generate_content(prompt)
        result = extract_json_robust(response.text)
        return result
    except Exception:
        return None

DOC_AWARE_SYSTEM_PROMPT = """Anda adalah asisten risalah rapat pemerintah Indonesia.
Anda menerima (1) teks dokumen pendukung rapat dan (2) transkrip rapat.

TUGAS:
- Gunakan DOKUMEN PENDUKUNG sebagai referensi untuk memahami konteks, istilah teknis,
  singkatan pemerintahan, angka-angka anggaran, dan topik yang dibahas.
- Koreksi kesalahan transkripsi untuk istilah pemerintahan (APBD, Perda, Permendagri,
  Musrenbang, Renja, SPJ, TUPOKSI, DPA, KUA-PPAS, dll).
- Identifikasi pembicara dari sapaan, jabatan, dan konteks.

LARANGAN:
- JANGAN mengubah maksud asli pembicara.
- JANGAN menambahkan informasi fiktif atau yang tidak ada di transkrip.
- JANGAN menulis ulang kalimat pembicara — koreksi hanya singkatan/istilah yang salah dengar.
- Pertahankan gaya bahasa asli pembicara.

Hasilkan JSON valid (TANPA markdown, TANPA ```):

{
  "speaker_identification": [
    {"label": "SPEAKER_00", "inferred_role": "Ketua Rapat", "inferred_name": "...", "reason": "..."}
  ],
  "corrected_transcript": [
    {"time": "00:02", "speaker": "Ketua Rapat", "speaker_original": "SPEAKER_00", "text": "teks terkoreksi"}
  ],
  "pokok_bahasan": ["..."],
  "keputusan_rapat": ["...", {"nomor": "...", "isi": "..."}],
  "kesimpulan": ["..."],
  "tindak_lanjut": [{"tindakan": "...", "pic": "...", "batas_waktu": "..."}],
  "agenda_rapat": ["..."],
  "dokumen_terkait": ["dokumen yang dirujuk"],
  "dokumen_dirujuk": ["nama dokumen pendukung yang relevan dengan pembahasan"]
}

DOKUMEN PENDUKUNG:
__DOC_CONTEXT__

TRANSKRIP:
__TRANSKRIP_TEXT__"""


def enhance_transcript_with_doc_context(merged_data, doc_context, output_dir=None):
    if output_dir is None:
        output_dir = os.path.join(PROJECT_ROOT, "output", "enhanced")
    os.makedirs(output_dir, exist_ok=True)

    doc_preview = doc_context.get("all_text_combined", "")
    if not doc_preview.strip():
        print("  Dokumen kosong, fallback ke enhance_transcript biasa.")
        return enhance_transcript(merged_data, output_dir)

    if len(doc_preview) > 15000:
        doc_preview = doc_preview[:7500] + "\n...[TENGAH DIHAPUS]...\n" + doc_preview[-7500:]

    transcript_text = prepare_transcript_text(merged_data, max_chars=12000)

    prompt = DOC_AWARE_SYSTEM_PROMPT.replace("__DOC_CONTEXT__", doc_preview)
    prompt = prompt.replace("__TRANSKRIP_TEXT__", transcript_text)

    print("Doc-aware enhancement via 9router/Groq (prioritas)...")
    result = try_doc_aware_9router(merged_data, doc_preview, output_dir, doc_context)
    if result:
        return result

    print("9router gagal. Fallback Gemini+Doc...")
    result = try_gemini(prompt, merged_data, output_dir, "Gemini+Doc")
    if result:
        result["dokumen_analisis_mode"] = True
        result["dokumen_sumber"] = [
            {"file": s["file"], "type": "dokumen" if s.get("text") else "audio"}
            for s in doc_context.get("document_sources", []) + doc_context.get("image_sources", [])
        ]
        ep = os.path.join(output_dir, "enhanced_lengkap.json")
        json.dump(result, open(ep, "w"), indent=2, ensure_ascii=False)
        print(f"  + {len(doc_context.get('document_sources', []))} dokumen dianalisis sebagai konteks.")
        return result

    print("Semua gagal. Fallback build_fallback.")
    return None
    sample = prepare_transcript_text(merged_data, max_lines=100, max_chars=5000)
    doc_ctx_short = doc_preview[:5000] if len(doc_preview) > 5000 else doc_preview

    sp_prompt = (
        "Anda adalah asisten risalah rapat pemerintah Indonesia.\n\n"
        f"Dokumen pendukung:\n{doc_ctx_short}\n\n"
        "Berdasarkan transkrip rapat berikut dan dokumen di atas, identifikasi semua pembicara.\n"
        "Hasilkan JSON valid:\n"
        '{"speaker_identification": [{"label": "SPEAKER_00", '
        '"inferred_role": "...", "inferred_name": "...", "reason": "..."}]}\n\n'
        f"CUPLIKAN TRANSKRIP:\n{sample}"
    )
    print("  Phase 1: speaker + doc context...")
    raw = call_llm(sp_prompt)
    speaker_map = {}
    if raw:
        result = extract_json_robust(raw)
        if result and "speaker_identification" in result:
            for s in result["speaker_identification"]:
                speaker_map[s["label"]] = s
            print(f"  {len(speaker_map)} speaker teridentifikasi")

    sum_prompt = (
        "Anda adalah asisten risalah rapat pemerintah Indonesia.\n\n"
        f"Dokumen pendukung:\n{doc_ctx_short}\n\n"
        "Berdasarkan transkrip dan dokumen di atas, ekstrak struktur risalah dalam JSON:\n"
        '{"pokok_bahasan": ["..."], "keputusan_rapat": ["..."], '
        '"kesimpulan": ["..."], "tindak_lanjut": [...], '
        '"agenda_rapat": ["..."], "dokumen_terkait": ["..."]}\n\n'
        "GUNAKAN dokumen untuk memahami konteks, tapi JANGAN menambahkan informasi fiktif.\n"
        f"TRANSKRIP:\n{sample}"
    )
    print("  Phase 2: struktur + doc context...")
    raw2 = call_llm(sum_prompt)
    summary = extract_json_robust(raw2) if raw2 else {}

    enhanced = {
        "speaker_identification": list(speaker_map.values()),
        "corrected_transcript": build_corrected_transcript(merged_data, speaker_map),
        "pokok_bahasan": summary.get("pokok_bahasan", []) if summary else [],
        "keputusan_rapat": summary.get("keputusan_rapat", []) if summary else [],
        "kesimpulan": summary.get("kesimpulan", []) if summary else [],
        "tindak_lanjut": summary.get("tindak_lanjut", []) if summary else [],
        "agenda_rapat": summary.get("agenda_rapat", []) if summary else [],
        "dokumen_terkait": summary.get("dokumen_terkait", []) if summary else [],
        "dokumen_analisis_mode": True,
    }
    enhanced = validate_and_repair(enhanced, merged_data)

    ep = os.path.join(output_dir, "enhanced_lengkap.json")
    with open(ep, "w", encoding="utf-8") as f:
        json.dump(enhanced, f, indent=2, ensure_ascii=False)
    print(f"Two-phase + doc OK: {len(speaker_map)} speaker, {len(enhanced['corrected_transcript'])} segmen.")
    return enhanced


def build_fallback(merged_data, output_dir=None):
    if output_dir is None:
        output_dir = os.path.join(PROJECT_ROOT, "output", "enhanced")
    os.makedirs(output_dir, exist_ok=True)

    fallback = {
        "speaker_identification": [],
        "corrected_transcript": [],
        "pokok_bahasan": [], "keputusan_rapat": [],
        "kesimpulan": [], "tindak_lanjut": [],
        "agenda_rapat": [], "dokumen_terkait": [],
    }

    seen = {}
    for seg in merged_data:
        mins = int(seg["start"]) // 60
        secs = int(seg["start"]) % 60
        speaker = seg.get("speaker", "SPEAKER_UNKNOWN")
        fallback["corrected_transcript"].append({
            "time": f"{mins:02d}:{secs:02d}",
            "speaker": speaker,
            "speaker_original": speaker,
            "text": seg.get("text", ""),
        })
        seen[speaker] = seen.get(speaker, 0) + 1

    for s, count in sorted(seen.items()):
        fallback["speaker_identification"].append({
            "label": s,
            "inferred_role": s,
            "inferred_name": s,
            "reason": f"{count} segmen",
        })

    fallback_path = os.path.join(output_dir, "enhanced_lengkap.json")
    with open(fallback_path, "w", encoding="utf-8") as f:
        json.dump(fallback, f, indent=2, ensure_ascii=False)
    return fallback

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python risalah/ai_enhancer.py <merged_json>")
        sys.exit(1)
    with open(sys.argv[1]) as f:
        data = json.load(f)
    enhance_transcript(data)
