import os
import re

# ── Government terms & institutions ─────────────────────────
INSTITUSI = {
    # DPR/DPRD
    "depresi": "DPRD",
    "depri": "DPRD",
    "dprd": "DPRD",
    "dpr ri": "DPR RI",
    "dpr": "DPR",
    # APBD
    "apbd": "APBD",
    "apbd perubahan": "APBD Perubahan",
    "apbd murni": "APBD Murni",
    # KUA-PPAS
    "kua ppas": "KUA-PPAS",
    "kua-pas": "KUA-PPAS",
    "kua ppa": "KUA-PPAS",
    # Permendagri
    "permendagri": "Permendagri",
    "permen dagri": "Permendagri",
    # Perda
    "perda": "Perda",
    # RPJMD
    "rpjmd": "RPJMD",
    "r p j m d": "RPJMD",
    # Musrenbang
    "musrembang": "Musrenbang",
    "musrenbang": "Musrenbang",
    "musrenbangdesk": "Musrenbangdes",
    "musrenbangcam": "Musrenbangcam",
    "musrenbangkab": "Musrenbang Kabupaten",
    "musrenbangprov": "Musrenbang Provinsi",
    # Renja / Renstra
    "renja": "Renja",
    "renstra": "Renstra",
    # TUPOKSI
    "tupoksi": "TUPOKSI",
    "tupoks": "TUPOKSI",
    # SAKIP
    "sakip": "SAKIP",
    "sa kip": "SAKIP",
    # LKPD
    "lkpd": "LKPD",
    "elka pede": "LKPD",
    # APIP
    "apip": "APIP",
}


JABATAN = {
    # Sekda
    "sekda": "Sekda",
    "sekertaris daerah": "Sekretaris Daerah",
    "sekretaris daerah": "Sekretaris Daerah",
    "sekretaris": "Sekretaris",
    "sepertaris": "Sekretaris",
    "sepetaris": "Sekretaris",
    # Kadis
    "kadis": "Kadis",
    "kepala dinas": "Kepala Dinas",
    # Kabid
    "kabid": "Kabid",
    "kepala bidang": "Kepala Bidang",
    # Kasie / Kasubag / Kabag
    "kasie": "Kasie",
    "kasubag": "Kasubag",
    "kepala seksi": "Kepala Seksi",
    "kabag": "Kabag",
    "kepala sub bagian": "Kepala Sub Bagian",
    "kepala subbagian": "Kepala Sub Bagian",
    # Gubernur
    "gubernur": "Gubernur",
    "gubernut": "Gubernur",
    # Bupati
    "bupati": "Bupati",
    "bupatin": "Bupati",
    # Wali Kota
    "walikota": "Wali Kota",
    "walkot": "Wali Kota",
    "wali kota": "Wali Kota",
    # Camat / Lurah / Kades
    "camat": "Camat",
    "lurah": "Lurah",
    "kades": "Kades",
    "kepala desa": "Kepala Desa",
    # Ketua / Wakil / Anggota
    "ketua rapat": "Ketua Rapat",
    "ketua": "Ketua",
    "wakil ketua": "Wakil Ketua",
    "anggota": "Anggota",
    "pimpinan": "Pimpinan",
    "notulis": "Notulis",
    "sekretaris rapat": "Sekretaris Rapat",
    # Asisten
    "asisten": "Asisten",
    "asisten satu": "Asisten I",
    "asisten dua": "Asisten II",
    "asisten tiga": "Asisten III",
    # Kepala
    "kepala": "Kepala",
}


DAERAH = {
    "kulty": "kabupaten",
    "kulti": "kabupaten",
    "kabupatin": "kabupaten",
    "kabupatn": "kabupaten",
    "kabupeten": "kabupaten",
    "kabupaten": "Kabupaten",
    "kecamatan": "Kecamatan",
    "kecamatin": "Kecamatan",
    "kecamatan": "Kecamatan",
    "provinsi": "Provinsi",
    "provins": "Provinsi",
    "propinsi": "Provinsi",
    "pemprov": "Pemprov",
    "pemkab": "Pemkab",
    "pemdes": "Pemdes",
    "pemda": "Pemda",
    "pemerintah daerah": "Pemerintah Daerah",
    "pemerintah": "Pemerintah",
}


LEMBAGA = {
    "acrbpr": "BPN",
    "bpn": "BPN",
    "bpbd": "BPBD",
    "bpjs": "BPJS",
    "bpkp": "BPKP",
    "bkpm": "BKPM",
    "bkpp": "BKPP",
    "bkn": "BKN",
    "bkd": "BKD",
    "bkpsdm": "BKPSDM",
    "bappeda": "BAPPEDA",
    "bappeda litbang": "Bappeda Litbang",
    "bpkad": "BPKAD",
    "inspektorat": "Inspektorat",
    "kesbangpol": "Kesbangpol",
    "satpol pp": "Satpol PP",
    "satpol": "Satpol PP",
    "dinporabudpar": "Disporabudpar",
    "diknas": "Diknas",
    "dinas pendidikan": "Dinas Pendidikan",
    "dinkes": "Dinkes",
    "dinas kesehatan": "Dinas Kesehatan",
    "dinsos": "Dinsos",
    "dinas sosial": "Dinas Sosial",
    "dinpertan": "Dinpertan",
    "dinas pertanian": "Dinas Pertanian",
    "disperindag": "Disperindag",
    "disnakertrans": "Disnakertrans",
    "dpupr": "DPUPR",
    "dputr": "DPUTR",
    "dcktr": "DCKTR",
    "dlh": "DLH",
    "dishub": "Dishub",
    "disdag": "Disdag",
    "bkpsdm": "BKPSDM",
    "bkd": "BKD",
    "bpp": "BPP",
    "bppd": "BPPD",
    "bpr": "BPR",
    "bumd": "BUMD",
    "bumn": "BUMN",
    "bumdes": "BUMDes",
}


DOKUMEN = {
    "spj": "SPJ",
    "lpj": "LPJ",
    "spm": "SPM",
    "dpa": "DPA",
    "dpa": "DPA",
    "sku": "SKU",
    "sk": "SK",
    "peraturan daerah": "Peraturan Daerah",
    "peraturan bupati": "Peraturan Bupati",
    "peraturan walikota": "Peraturan Wali Kota",
    "peraturan gubernur": "Peraturan Gubernur",
    "perbup": "Perbup",
    "perwal": "Perwal",
    "pergub": "Pergub",
    "perkada": "Perkada",
    "permen": "Permen",
    "peraturan menteri": "Peraturan Menteri",
    "perpres": "Perpres",
    "peraturan presiden": "Peraturan Presiden",
    "inpres": "Inpres",
    "instruksi presiden": "Instruksi Presiden",
    "se": "SE",
    "surat edaran": "Surat Edaran",
    "sop": "SOP",
    "standard operating procedure": "SOP",
}

RAPAT = {
    "rapat": "Rapat",
    "rapat dengar pendapat": "Rapat Dengar Pendapat",
    "rdp": "RDP",
    "sidang": "Sidang",
    "pleno": "Pleno",
    "komisi": "Komisi",
    "fraksi": "Fraksi",
    "pembahasan": "Pembahasan",
    "fit and proper test": "Uji Kelayakan dan Kepatutan",
    "musdes": "Musdes",
    "musdus": "Musdus",
    "muskel": "Muskel",
    "musrenbangdes": "Musrenbangdes",
    "musrenbangcam": "Musrenbangcam",
    "anggaran": "Anggaran",
    "rapat paripurna": "Rapat Paripurna",
    "paripurna": "Paripurna",
    "voting": "Voting",
    "musyawarah": "Musyawarah",
    "mufakat": "Mufakat",
    "interupsi": "Interupsi",
    "skors": "Skors",
    "kuorum": "Kuorum",
}

# ── Common Whisper ASR errors for Indonesian ────────────────
ASR_ERRORS = {
    # Numbers & mata uang
    "ratus": "ratus",
    "ribu": "ribu",
    "juta": "juta",
    "miliar": "miliar",
    "triliun": "triliun",
    "rupiah": "rupiah",
    "milyar": "miliar",
    "beberpa": "beberapa",
    "persen": "persen",
    "per sen": "persen",
    "prosen": "persen",
    # Waktu
    "menit": "menit",
    "detik": "detik",
    "jam": "jam",
    "hari": "hari",
    "minggu": "minggu",
    "bulan": "bulan",
    "tahun": "tahun",
    # Tempat
    "ruang rapat": "Ruang Rapat",
    "aula": "Aula",
    "gedung": "Gedung",
    "kantor": "Kantor",
    "balai": "Balai",
    "kota": "Kota",
    "kelurahan": "Kelurahan",
    "desa": "Desa",
    # Sapaan yang salah dengar
    "bapak bapak": "Bapak-Bapak",
    "ibu ibu": "Ibu-Ibu",
    "saudara saudara": "Saudara-Saudara",
    "selam": "selamat",
    "sejah": "sejahtera",
    "terabagi": "terbagi",
}

# ── Indonesian slang → formal (safe for government) ────────
SLANG = {
    "gak": "tidak",
    "ga": "tidak",
    "nggak": "tidak",
    "ngga": "tidak",
    "kagak": "tidak",
    "kaga": "tidak",
    "tak": "tidak",
    "udah": "sudah",
    "udh": "sudah",
    "ud": "sudah",
    "dah": "sudah",
    "aja": "saja",
    "aj": "saja",
    "doang": "saja",
    "doank": "saja",
    "dlu": "dulu",
    "duluan": "dulu",
    "bikin": "membuat",
    "buat": "untuk",
    "ngomong": "berbicara",
    "ngomongin": "membicarakan",
    "bilang": "mengatakan",
    "bilangin": "sampaikan",
    "nanya": "bertanya",
    "nanyain": "menanyakan",
    "jawab": "menjawab",
    "jwb": "jawab",
    "tanya": "tanya",
    "tanyain": "tanyakan",
    "liat": "lihat",
    "liatin": "melihat",
    "lht": "lihat",
    "pake": "menggunakan",
    "pakek": "menggunakan",
    "pkai": "menggunakan",
    "pki": "pakai",
    "make": "menggunakan",
    "mending": "sebaiknya",
    "mendingan": "sebaiknya",
    "gimana": "bagaimana",
    "gmn": "bagaimana",
    "kayak": "seperti",
    "kya": "seperti",
    "kek": "seperti",
    "bgt": "sekali",
    "banget": "sekali",
    "pisan": "sekali",
    "sih": "",
    "dok": "saja",
    "kok": "",
    "loh": "",
    "lho": "",
    "dong": "",
    "deh": "",
    "yah": "ya",
    "ngg": "tidak",
    "enggak": "tidak",
    "engga": "tidak",
    "nggak": "tidak",
    "ngga": "tidak",
    "mau": "mau",
    "pengen": "ingin",
    "pgn": "ingin",
    "pengin": "ingin",
    "pengen": "ingin",
    "kepengen": "menginginkan",
    "kepingin": "ingin",
    "kpn": "kapan",
    "kapan": "kapan",
    "orng": "orang",
    "org": "orang",
    "orang": "orang",
    "dpt": "dapat",
    "dapet": "mendapat",
    "dapat": "dapat",
    "msh": "masih",
    "masi": "masih",
    "mas": "masih",
    "sih": "",
    "utk": "untuk",
    "unt": "untuk",
    "buat": "untuk",
    "dgn": "dengan",
    "sm": "dengan",
    "sama": "dengan",
    "ama": "dengan",
    "jg": "juga",
    "uga": "juga",
    "tp": "tetapi",
    "tpi": "tetapi",
    "tapi": "tetapi",
    "tettapi": "tetapi",
    "klo": "kalau",
    "kl": "kalau",
    "kal": "kalau",
    "kalu": "kalau",
    "kalo": "kalau",
    "sdh": "sudah",
    "suda": "sudah",
    "ud": "sudah",
    "dlm": "dalam",
    "dr": "dari",
    "pd": "pada",
    "ada": "ada",
    "ad": "ada",
    "kpd": "kepada",
    "pda": "pada",
    "ttp": "tetap",
    "tetep": "tetap",
    "trs": "terus",
    "teruz": "terus",
    "mkin": "makin",
    "makin": "makin",
    "jgn": "jangan",
    "janagn": "jangan",
    "blh": "boleh",
    "kmu": "kamu",
    "lu": "Anda",
    "lo": "Anda",
    "gw": "saya",
    "gue": "saya",
    "w": "saya",
    "sy": "saya",
    "ak": "saya",
    "aku": "saya",
    "kita": "kita",
    "kami": "kami",
}

# ── Merge all corrections (longer keys first → avoid partial match) ──
def _build_combined() -> None:
    combined = {}
    for d in [RAPAT, INSTITUSI, JABATAN, DAERAH, LEMBAGA, DOKUMEN, ASR_ERRORS, SLANG]:
        combined.update(d)
    return combined


ALL_CORRECTIONS = _build_combined()


def correct_terms(text: str) -> str:
    """Koreksi istilah dengan regex word-boundary agar tidak salah match."""
    if not text:
        return text

    items = sorted(ALL_CORRECTIONS.items(), key=lambda x: -len(x[0]))

    for wrong, correct in items:
        if not correct:
            # Filler removal — hapus kata dengan spacing
            text = re.sub(r'\s+' + re.escape(wrong) + r'\s+', ' ', text)
            text = re.sub(r'^' + re.escape(wrong) + r'\s+', '', text)
            text = re.sub(r'\s+' + re.escape(wrong) + r'$', '', text)
            continue

        pattern = re.compile(r'\b' + re.escape(wrong) + r'\b', re.IGNORECASE)
        text = pattern.sub(correct, text)

    return text


def correct_transcript(merged: list[dict]) -> list[dict]:
    """Apply id_terms corrections to all segments in merged transcript."""
    for seg in merged:
        if "text" in seg and seg["text"]:
            seg["text"] = correct_terms(seg["text"])
    return merged


def _capitalize_sentences(text: str) -> str:
    """Capitalize first letter of each sentence."""
    return re.sub(r'(^|[.!?]\s+)([a-z])', lambda m: m.group(1) + m.group(2).upper(), text)


def normalize_indonesian(text: str) -> str:
    """Full normalization: slang removal, government terms, ASR fixes, sentence case.
    Skips normalization for non-Indonesian languages."""
    lang = os.getenv("RISALAH_LANG", "id")[:2]  # handle system LANG like "en_US.UTF-8"
    if lang != "id":
        return text.strip()
    text = correct_terms(text)

    # Collapse multiple spaces (preserve newlines)
    text = re.sub(r'[ \t]+', ' ', text)

    # Trim punctuation spacing
    text = re.sub(r'\s+([,.;:!?])', r'\1', text)

    text = _capitalize_sentences(text)

    return text.strip()
