"""Minimal PDF generator from enhanced risalah data. Uses fpdf2.

Ponytail: flat text layout, no table borders, no images.
Formal output = DOCX. PDF is for quick reading/sharing.
"""

import os
from datetime import datetime
from io import BytesIO

from fpdf import FPDF

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def generate_pdf(enhanced, metadata=None, output_path=None, title="RISALAH RAPAT"):
    """Generate A4 PDF from enhanced data. Returns path or BytesIO."""
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    # Margins: left 25mm, right 20mm
    pdf.set_left_margin(25)
    pdf.set_right_margin(20)

    # Title
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(4)

    # Classification bar if not BIASA
    classification = enhanced.get("classification", "BIASA")
    if classification != "BIASA":
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(255, 0, 0)
        pdf.cell(0, 8, classification, new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

    # Metadata
    m = metadata or {}
    pdf.set_font("Helvetica", "", 11)
    meta_lines = [
        ("Hari/Tanggal", f"{m.get('hari', '___')}, {m.get('tanggal', '___')}"),
        ("Waktu", m.get("waktu", "___")),
        ("Tempat", m.get("tempat", "___")),
        ("Acara", m.get("acara", "___")),
    ]
    for label, value in meta_lines:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(35, 7, f"{label}  :")
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 7, value, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # Speaker identification
    si = enhanced.get("speaker_identification", [])
    if si:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "DAFTAR HADIR", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 11)
        for s in si:
            name = s.get("inferred_name", s.get("label", ""))
            role = s.get("inferred_role", "")
            pdf.cell(0, 6, f"  - {name} ({role})", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    # Ringkasan eksekutif
    ringkasan = enhanced.get("ringkasan_eksekutif", "")
    if ringkasan:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "RINGKASAN EKSEKUTIF", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 11)
        ringkasan_str = ringkasan if isinstance(ringkasan, str) else str(ringkasan)
        pdf.multi_cell(0, 6, ringkasan_str)
        pdf.ln(3)

    # Transcript
    transcript = enhanced.get("corrected_transcript", [])
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "ISI RISALAH", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for seg in transcript:
        time = seg.get("time", "00:00")
        speaker = seg.get("speaker", "")
        text = seg.get("text", "")
        line = f"[{time}] {speaker}: {text}"
        pdf.multi_cell(0, 5, line)
    pdf.ln(3)

    # Sections: pokok bahasan, keputusan, kesimpulan, tindak lanjut
    for section_label, key in [
        ("POKOK BAHASAN", "pokok_bahasan"),
        ("KEPUTUSAN", "keputusan_rapat"),
        ("KESIMPULAN", "kesimpulan"),
        ("TINDAK LANJUT", "tindak_lanjut"),
    ]:
        items = enhanced.get(key, [])
        if items:
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, section_label, new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 11)
            for item in items:
                if isinstance(item, dict):
                    tindakan = item.get("tindakan", "")
                    pic = item.get("pic", "")
                    deadline = item.get("batas_waktu", "")
                    pdf.cell(
                        0, 6, f"  - {tindakan} | PIC: {pic} | {deadline}",
                        new_x="LMARGIN", new_y="NEXT",
                    )
                else:
                    pdf.multi_cell(0, 6, f"  - {item}")
            pdf.ln(2)

    # Signature
    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 11)
    now = datetime.now()
    bulan = [
        "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember",
    ]
    pdf.cell(0, 7, f"Jakarta, {now.day} {bulan[now.month - 1]} {now.year}",
             new_x="LMARGIN", new_y="NEXT", align="R")

    pdf.ln(15)
    col_w = pdf.w - pdf.l_margin - pdf.r_margin
    x_start = pdf.l_margin
    for i, label in enumerate(["Pimpinan Rapat", "Mengetahui", "Sekretaris / Notulis"]):
        x = x_start + (col_w / 3) * i
        pdf.set_xy(x, pdf.get_y())
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(col_w / 3, 6, f"{label}\n\n\n\n(_______________)\n\nNama Jelas", align="C")

    # Output
    if output_path:
        pdf.output(output_path)
        print(f"PDF: {output_path}")
        return output_path
    buf = BytesIO()
    pdf.output(buf)
    buf.seek(0)
    return buf


if __name__ == "__main__":
    import json, sys

    if len(sys.argv) < 2:
        print("Usage: python risalah/pdf_generator.py <enhanced_json> [metadata_json]")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        data = json.load(f)
    meta = None
    if len(sys.argv) > 2:
        with open(sys.argv[2]) as f:
            meta = json.load(f)
    generate_pdf(data, meta)
