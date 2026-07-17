import json
import os
import re
import sys
import time

import requests
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    from api.config import LLM_CONFIGS
except ImportError:
    LLM_CONFIGS = [
        {
            "name": "Groq",
            "base": os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
            "key": os.getenv("GROQ_API_KEY", ""),
            "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        },
        {
            "name": "9router",
            "base": os.getenv("NINEROUTER_BASE_URL", "http://localhost:20128/v1"),
            "key": os.getenv("NINEROUTER_API_KEY", ""),
            "model": os.getenv("NINEROUTER_MODEL", "groq/llama-3.3-70b-versatile"),
        },
        {
            "name": "Gemini",
            "base": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "key": os.getenv("GEMINI_API_KEY", ""),
            "model": os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        },
    ]


SYSTEM_PROMPT = """Anda adalah asisten risalah rapat pemerintah Indonesia yang ahli dalam bahasa Indonesia formal dan istilah tata negara.

Analisis transkrip rapat berikut dan hasilkan JSON valid (TANPA markdown, TANPA ```).

FORMAT WAJIB:
{
  "speaker_identification": [
    {"label": "SPEAKER_00", "inferred_role": "Ketua Rapat", "inferred_name": "Bapak Bambang Susilo", "reason": "dipanggil 'Pak Ketua' oleh peserta lain"}
  ],
  "ringkasan_eksekutif": "2-3 paragraf ringkasan esktrakutif tentang jalannya rapat, keputusan utama, dan arahan pimpinan rapat.",
  "corrected_transcript": [
    {"time": "00:02", "speaker": "Ketua Rapat", "speaker_original": "SPEAKER_00", "text": "teks setelah koreksi istilah pemerintahan"}
  ],
  "pokok_bahasan": ["item1"],
  "keputusan_rapat": ["keputusan1 — jika ada voting tulis hasilnya"],
  "kesimpulan": ["kesimpulan1"],
  "tindak_lanjut": [{"tindakan": "...", "pic": "...", "batas_waktu": "..."}],
  "agenda_rapat": ["agenda1"],
  "dokumen_terkait": ["dokumen yang disebut dalam rapat"]
}

PANDUAN IDENTIFIKASI PEMBICARA:
- Gunakan sapaan (Pak/Bu/Ibu + nama) sebagai petunjuk utama
- Perhatikan jabatan yang disebut: Sekda, Kadis, Kabid, Kasubag, Camat, Lurah, dll
- Perhatikan gaya bicara: pimpinan rapat biasanya membuka/menutup sesi, mempersilakan
- Jika ada nama disebut oleh pembicara lain, gunakan untuk identifikasi
- Urutan bicara: biasanya Ketua Rapat bicara duluan, lalu peserta sesuai agenda

PANDUAN KOREKSI ISTILAH PEMERINTAHAN:
- Istilah yang sering salah dengar oleh ASR:
  * "depresi/depri" → DPRD
  * "musrembang" → Musrenbang
  * "tupoksi" → TUPOKSI
  * "kua ppas/kua-pas" → KUA-PPAS
  * "kabupatin/kabupatn/kulti" → kabupaten
  * "pemprov/pemkab/pemda" → Pemprov/Pemkab/Pemda
  * "sekda/kadis/kabid" → Sekda/Kadis/Kabid
  * "dinas" + nama dinas (Dinkes, Diknas, Dishub, DPUPR, dll)
- Istilah anggaran: APBD, APBD Perubahan, DPA, KUA-PPAS, SPJ, LPJ, SPM
- Istilah perencanaan: Musrenbang, Renja, Renstra, RPJMD, RKPD
- Peraturan: Perda, Perbup, Pergub, Perwal, Permendagri
- Lembaga: BAPPEDA, BPKAD, Inspektorat, BKPSDM, BKD, BPBD

PANDUAN UMUM:
- corrected_transcript: TULIS SEMUA SEGMEN, jangan lewatkan satu pun
- ringkasan_eksekutif: Tulis 2-3 paragraf, cover latar belakang rapat, bahasan utama, keputusan kunci, dan arahan pimpinan
- Koreksi ejaan bahasa Indonesia yang tidak baku (misal: "gak" → "tidak", "udah" → "sudah")
- Jangan mengubah maksud asli pembicara
- Pertahankan gaya bahasa asli — koreksi hanya istilah yang memang salah dengar

PANDUAN TINDAK LANJUT (WAJIB):
- Wajib generate MINIMAL 1 item tindak_lanjut
- Setiap item WAJIB punya: "tindakan" (aksi konkret), "pic" (nama/ jabatan penanggung jawab), "batas_waktu" (tanggal/ periode)
- Jika rapat tidak membahas tindak lanjut secara eksplisit, tetap buat minimal 1 berdasarkan keputusan rapat
- Contoh: {"tindakan": "Menyusun DPA perubahan sesuai arahan Sekda", "pic": "Kabid Anggaran", "batas_waktu": "1 minggu"}

TRANSKRIP:
__TRANSKRIP_TEXT__"""

DOCUMENT_SUMMARY_PROMPT = """Anda adalah asisten risalah rapat pemerintah Indonesia.

Rangkum dokumen pendukung rapat berikut dalam JSON valid.
Dokumen bisa berupa: Nota Dinas, Laporan Kegiatan, RAB, Draft Perda, dll.

{
  "ringkasan": "ringkasan 2-3 paragraf isi dokumen",
  "poin_penting": ["poin penting yang relevan untuk rapat"],
  "angka_anggaran": [{"item": "nama pos anggaran", "jumlah": "Rp X.XXX.XXX"}],
  "keputusan_terkait": "keputusan yang perlu diambil rapat terkait dokumen ini",
  "istilah_kunci": ["APBD", "DPA", "KUA-PPAS", "dll"]
}

DOKUMEN:
__DOC_TEXT__"""

# ── English prompts (multi-language support) ─────────────────────
EN_SYSTEM_PROMPT = """You are a professional meeting minutes assistant with expertise in formal Indonesian government terminology.

Analyze the following meeting transcript and output valid JSON (NO markdown, NO ```).

REQUIRED FORMAT:
{
  "speaker_identification": [
    {"label": "SPEAKER_00", "inferred_role": "Ketua Rapat", "inferred_name": "Bapak Bambang Susilo", "reason": "dipanggil 'Pak Ketua' oleh peserta lain"}
  ],
  "ringkasan_eksekutif": "2-3 paragraph executive summary of the meeting.",
  "corrected_transcript": [
    {"time": "00:02", "speaker": "Ketua Rapat", "speaker_original": "SPEAKER_00", "text": "corrected transcript text"}
  ],
  "pokok_bahasan": ["subject1"],
  "keputusan_rapat": ["decision1"],
  "kesimpulan": ["conclusion1"],
  "tindak_lanjut": [{"tindakan": "action", "pic": "person in charge", "batas_waktu": "deadline"}],
  "agenda_rapat": ["agenda1"],
  "dokumen_terkait": ["documents mentioned in meeting"]
}

SPEAKER IDENTIFICATION GUIDELINES:
- Use forms of address (Pak/Bu/Ibu + name) as primary clues
- Note positions mentioned: Sekda, Kadis, Kabid, Kasubag, Camat, Lurah, etc.
- Note speaking style: chairperson typically opens/closes sessions
- If names are called by other speakers, use them for identification

GOVERNMENT TERM CORRECTION GUIDE:
- Terms often misheard by ASR: "depresi/depri" → DPRD, "musrembang" → Musrenbang
- Budget terms: APBD, DPA, KUA-PPAS, SPJ, LPJ
- Planning terms: Musrenbang, Renja, Renstra, RPJMD
- Regulations: Perda, Perbup, Pergub, Permendagri
- Institutions: BAPPEDA, BPKAD, Inspektorat, BKPSDM

GENERAL GUIDELINES:
- corrected_transcript: INCLUDE ALL SEGMENTS
- ringkasan_eksekutif: Write 2-3 paragraphs covering background, key discussions, decisions, and directives
- Keep sections in Indonesian (titles/terms), but reasoning in English

TINDAK LANJUT (MANDATORY):
- Generate MINIMUM 1 tindak_lanjut item
- Each item MUST have: "tindakan" (concrete action), "pic" (person in charge), "batas_waktu" (deadline)

TRANSKRIP:
__TRANSKRIP_TEXT__"""

EN_DOCUMENT_SUMMARY_PROMPT = """You are a meeting minutes assistant. Summarize the following supporting document in valid JSON.

{
  "ringkasan": "2-3 paragraph summary of the document",
  "poin_penting": ["important points relevant to the meeting"],
  "angka_anggaran": [{"item": "budget item name", "jumlah": "Rp X.XXX.XXX"}],
  "keputusan_terkait": "decisions the meeting needs to make regarding this document",
  "istilah_kunci": ["APBD", "DPA", "KUA-PPAS", "etc"]
}

DOKUMEN:
__DOC_TEXT__"""

EN_DOC_AWARE_SYSTEM_PROMPT = """You are a professional meeting minutes assistant for Indonesian government meetings.
You receive (1) supporting document text and (2) meeting transcript.

TASKS:
- Use SUPPORTING DOCUMENTS as reference for context, technical terms,
  government abbreviations, budget figures, and topics discussed.
- Correct transcription errors for government terms (APBD, Perda, Permendagri,
  Musrenbang, Renja, SPJ, TUPOKSI, DPA, KUA-PPAS, etc.).
- Identify speakers from address forms, positions, and context.

RULES:
- DO NOT change the speaker's original intent.
- DO NOT add fictitious information.
- DO NOT rewrite speaker sentences — only correct misheard terms/abbreviations.
- Preserve the speaker's original speaking style.

Output valid JSON (NO markdown, NO ```):

{
  "speaker_identification": [
    {"label": "SPEAKER_00", "inferred_role": "Ketua Rapat", "inferred_name": "...", "reason": "..."}
  ],
  "corrected_transcript": [
    {"time": "00:02", "speaker": "Ketua Rapat", "speaker_original": "SPEAKER_00", "text": "corrected text"}
  ],
  "pokok_bahasan": ["..."],
  "keputusan_rapat": ["...", {"nomor": "...", "isi": "..."}],
  "kesimpulan": ["..."],
  "tindak_lanjut": [{"tindakan": "...", "pic": "...", "batas_waktu": "..."}],
  "agenda_rapat": ["..."],
  "dokumen_terkait": ["referenced documents"],
  "dokumen_dirujuk": ["supporting document names relevant to discussion"]
}

SUPPORTING DOCUMENTS:
__DOC_CONTEXT__

TRANSKRIP:
__TRANSKRIP_TEXT__"""


def _get_lang():
    return os.getenv("RISALAH_LANG", "id")[:2]


def call_llm(prompt, max_retries=3):
    for cfg in LLM_CONFIGS:
        for attempt in range(max_retries):
            try:
                resp = requests.post(
                    f"{cfg['base']}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {cfg['key']}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": cfg["model"],
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                        "max_tokens": 4096,
                        "stream": False,
                    },
                    timeout=180,
                )
                if resp.status_code == 429:
                    print(f"  {cfg['name']} rate limit, coba lagi...")
                    time.sleep(10)
                    continue
                if resp.status_code != 200:
                    print(f"  {cfg['name']} HTTP {resp.status_code}, skip...")
                    break
                data = _parse_response(resp)
                text = data["choices"][0]["message"]["content"]
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


def _parse_response(resp):
    text = resp.text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        lines = [ln.strip() for ln in text.split('\n') if ln.strip()]
        if len(lines) > 1:
            return json.loads(lines[-1])
        raise





def extract_json_robust(text):
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text.strip(), flags=re.MULTILINE)
    text = text.strip()

    brace_depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if brace_depth == 0:
                start = i
            brace_depth += 1
        elif ch == "}":
            brace_depth -= 1
            if brace_depth == 0 and start >= 0:
                candidate = text[start : i + 1]
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
            enhanced["corrected_transcript"].append(
                {
                    "time": f"{mins:02d}:{secs:02d}",
                    "speaker": seg.get("speaker", "SPEAKER_UNKNOWN"),
                    "speaker_original": seg.get("speaker", "SPEAKER_UNKNOWN"),
                    "text": seg.get("text", ""),
                }
            )

    ct = enhanced["corrected_transcript"]
    actual_speakers = set(s["speaker"] for s in ct if s["speaker"])
    inferred_speakers = set(s["inferred_role"] for s in enhanced["speaker_identification"])

    orphans = actual_speakers - inferred_speakers
    for spk in orphans:
        enhanced["speaker_identification"].append(
            {
                "label": spk,
                "inferred_role": spk,
                "inferred_name": spk,
                "reason": "auto-fill dari data",
            }
        )

    for key in [
        "pokok_bahasan",
        "keputusan_rapat",
        "kesimpulan",
        "agenda_rapat",
        "dokumen_terkait",
    ]:
        if key not in enhanced or not isinstance(enhanced[key], list):
            enhanced[key] = []

    if "tindak_lanjut" not in enhanced or not isinstance(enhanced["tindak_lanjut"], list):
        enhanced["tindak_lanjut"] = []

    return enhanced



    return None


def enhance_with_two_phase(merged_data, output_dir, lang=None):
    """Two-phase: (1) identify speakers from sample, (2) build full output."""
    if lang is None:
        lang = _get_lang()
    sample = prepare_transcript_text(merged_data, max_lines=200, max_chars=8000)

    if lang == "en":
        speaker_prompt = (
            "You are a professional meeting minutes assistant for Indonesian government meetings.\n\n"
            "Analyze the following transcript excerpt and identify EVERY unique speaker.\n"
            "Use contextual clues:\n"
            "1. Forms of address: 'Pak/Bu/Ibu [Name]' used by other speakers\n"
            "2. Positions: 'Saya sebagai Sekretaris/Kadis/Kabid...'\n"
            "3. Role: who opens/closes the session → Chairperson\n"
            "4. Speaking style: formal/authoritative vs technical staff\n"
            "5. Agenda: 'Saya dari Dinas...' or 'Saya mewakili...'\n\n"
            "Output valid JSON (keep title/terms in Indonesian):\n"
            '{"speaker_identification": [{"label": "SPEAKER_00", "inferred_role": "Ketua Rapat", '
            '"inferred_name": "Bapak [Name if inferable]", "reason": "brief reason"}]}\n\n'
            "TRANSCRIPT EXCERPT:\n" + sample
        )
    else:
        speaker_prompt = (
            "Anda adalah asisten risalah rapat pemerintah Indonesia.\n\n"
            "Analisis cuplikan transkrip rapat berikut dan identifikasi SETIAP pembicara unik.\n"
            "Gunakan petunjuk kontekstual:\n"
            "1. Sapaan: 'Pak/Bu/Ibu [Nama]' yang diucapkan pembicara lain\n"
            "2. Jabatan: 'Saya sebagai Sekretaris/Kadis/Kabid...'\n"
            "3. Peran: siapa yang membuka/menutup sesi → Ketua Rapat\n"
            "4. Gaya bicara: formal/otoritatif vs staf teknis\n"
            "5. Agenda: 'Saya dari Dinas...' atau 'Saya mewakili...'\n\n"
            "Hasilkan JSON valid:\n"
            '{"speaker_identification": [{"label": "SPEAKER_00", "inferred_role": "Ketua Rapat", '
            '"inferred_name": "Bapak [Nama jika bisa diinfersi]", "reason": "alasan singkat"}]}\n\n'
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

    if lang == "en":
        summary_prompt = (
            "You are a professional meeting minutes assistant.\n\n"
            "Based on the following meeting transcript, extract structured data in JSON:\n"
            '{"pokok_bahasan": ["..."], "keputusan_rapat": ["..."], '
            '"kesimpulan": ["..."], "tindak_lanjut": [{"tindakan": "...", '
            '"pic": "...", "batas_waktu": "..."}], '
            '"agenda_rapat": ["..."], "dokumen_terkait": ["..."]}\n\n'
            "TRANSCRIPT:\n" + sample
        )
    else:
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
        result.append(
            {
                "time": f"{mins:02d}:{secs:02d}",
                "speaker": inferred_role,
                "speaker_original": spk,
                "text": text,
            }
        )
    return result


def enhance_transcript(merged_data, output_dir=None, lang=None):
    if output_dir is None:
        output_dir = os.path.join(PROJECT_ROOT, "output", "enhanced")
    os.makedirs(output_dir, exist_ok=True)
    if lang is None:
        lang = _get_lang()

    # Apply language-specific normalization before AI enhancement
    from risalah.id_terms import normalize_indonesian

    for seg in merged_data:
        if "text" in seg and seg["text"]:
            seg["text"] = normalize_indonesian(seg["text"])

    print(f"Enhancement via LLM (Groq → 9router → Gemini) — lang={lang}...")
    result = enhance_with_two_phase(merged_data, output_dir, lang)
    if result:
        return result

    print("Semua LLM gagal. Build_fallback...")
    return build_fallback(merged_data, output_dir)


def try_doc_aware_9router(merged_data, doc_preview, output_dir, doc_context, lang=None):
    if lang is None:
        lang = _get_lang()
    sample = prepare_transcript_text(merged_data, max_lines=100, max_chars=5000)
    doc_ctx_short = doc_preview[:5000] if len(doc_preview) > 5000 else doc_preview

    if lang == "en":
        sp_prompt = (
            "You are a meeting minutes assistant for Indonesian government meetings.\n\n"
            f"Supporting documents:\n{doc_ctx_short}\n\n"
            "Based on the following transcript and documents above, identify all speakers.\n"
            "Output valid JSON:\n"
            '{"speaker_identification": [{"label": "SPEAKER_00", '
            '"inferred_role": "...", "inferred_name": "...", "reason": "..."}]}\n\n'
            f"TRANSCRIPT EXCERPT:\n{sample}"
        )
    else:
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

    enhanced = build_doc_aware_enhanced(merged_data, doc_preview, speaker_map, lang)
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


def build_doc_aware_enhanced(merged_data, doc_preview, speaker_map, lang=None):
    if lang is None:
        lang = _get_lang()
    doc_ctx_short = doc_preview[:5000] if len(doc_preview) > 5000 else doc_preview
    sample = prepare_transcript_text(merged_data, max_lines=100, max_chars=5000)
    if lang == "en":
        sum_prompt = (
            "You are a meeting minutes assistant for Indonesian government meetings.\n\n"
            f"Supporting documents:\n{doc_ctx_short}\n\n"
            "Based on the transcript and documents above, extract meeting structure in JSON:\n"
            '{"pokok_bahasan": ["..."], "keputusan_rapat": ["..."], '
            '"kesimpulan": ["..."], "tindak_lanjut": [...], '
            '"agenda_rapat": ["..."], "dokumen_terkait": ["..."]}\n\n'
            "USE documents for context, but DO NOT add fictitious information.\n"
            f"TRANSCRIPT:\n{sample}"
        )
    else:
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


def enhance_document(document_text, output_dir=None, lang=None):
    if output_dir is None:
        output_dir = os.path.join(PROJECT_ROOT, "output", "enhanced")
    os.makedirs(output_dir, exist_ok=True)
    if lang is None:
        lang = _get_lang()

    max_chars = 25000
    text = document_text[:max_chars] if len(document_text) > max_chars else document_text
    doc_prompt = EN_DOCUMENT_SUMMARY_PROMPT if lang == "en" else DOCUMENT_SUMMARY_PROMPT
    prompt = doc_prompt.replace("__DOC_TEXT__", text)

    raw = call_llm(prompt, max_retries=3)
    if raw:
        result = extract_json_robust(raw)
        if result:
            return result

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


def enhance_transcript_with_doc_context(merged_data, doc_context, output_dir=None, lang=None):
    if output_dir is None:
        output_dir = os.path.join(PROJECT_ROOT, "output", "enhanced")
    os.makedirs(output_dir, exist_ok=True)
    if lang is None:
        lang = _get_lang()

    doc_preview = doc_context.get("all_text_combined", "")
    if not doc_preview.strip():
        print("  Dokumen kosong, fallback ke enhance_transcript biasa.")
        return enhance_transcript(merged_data, output_dir, lang)

    if len(doc_preview) > 15000:
        doc_preview = doc_preview[:7500] + "\n...[TENGAH DIHAPUS]...\n" + doc_preview[-7500:]

    transcript_text = prepare_transcript_text(merged_data, max_chars=12000)

    doc_prompt = EN_DOC_AWARE_SYSTEM_PROMPT if lang == "en" else DOC_AWARE_SYSTEM_PROMPT
    prompt = doc_prompt.replace("__DOC_CONTEXT__", doc_preview)
    prompt = prompt.replace("__TRANSKRIP_TEXT__", transcript_text)

    from risalah.id_terms import normalize_indonesian

    for seg in merged_data:
        if "text" in seg and seg["text"]:
            seg["text"] = normalize_indonesian(seg["text"])

    print(f"Doc-aware enhancement via LLM (Groq → 9router → Gemini) — lang={lang}...")
    result = try_doc_aware_9router(merged_data, doc_preview, output_dir, doc_context, lang)
    if result:
        return result

    print("Semua LLM gagal. Build_fallback...")
    return build_fallback(merged_data, output_dir)


def build_fallback(merged_data, output_dir=None):
    if output_dir is None:
        output_dir = os.path.join(PROJECT_ROOT, "output", "enhanced")
    os.makedirs(output_dir, exist_ok=True)

    fallback = {
        "speaker_identification": [],
        "corrected_transcript": [],
        "pokok_bahasan": [],
        "keputusan_rapat": [],
        "kesimpulan": [],
        "tindak_lanjut": [],
        "agenda_rapat": [],
        "dokumen_terkait": [],
    }

    seen = {}
    for seg in merged_data:
        mins = int(seg["start"]) // 60
        secs = int(seg["start"]) % 60
        speaker = seg.get("speaker", "SPEAKER_UNKNOWN")
        fallback["corrected_transcript"].append(
            {
                "time": f"{mins:02d}:{secs:02d}",
                "speaker": speaker,
                "speaker_original": speaker,
                "text": seg.get("text", ""),
            }
        )
        seen[speaker] = seen.get(speaker, 0) + 1

    for s, count in sorted(seen.items()):
        fallback["speaker_identification"].append(
            {
                "label": s,
                "inferred_role": s,
                "inferred_name": s,
                "reason": f"{count} segmen",
            }
        )

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
