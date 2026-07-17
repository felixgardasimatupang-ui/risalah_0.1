"""Test Indonesian term normalization."""

import pytest
from risalah.id_terms import normalize_indonesian


class TestIdTerms:
    def test_word_boundary_no_partial_match(self):
        """Ensure 'bkn' doesn't match inside 'pembelajaran'."""
        result = normalize_indonesian("pembelajaran hari ini")
        # 'pembelajaran' should not be affected
        assert "pembelajaran" in result

    def test_institusi(self):
        result = normalize_indonesian("apbd perubahan sudah di setujui dprd")
        assert "APBD" in result
        assert "DPRD" in result

    def test_jabatan(self):
        result = normalize_indonesian("sekda dan kadis menghadiri rapat")
        assert "Sekda" in result
        assert "Kadis" in result

    def test_slang_to_formal(self):
        result = normalize_indonesian("gak tau, udah aja gitu")
        assert "tidak" in result
        assert "sudah" in result
        assert "saja" in result

    def test_daerah(self):
        result = normalize_indonesian("kulty bandung")
        assert "kabupaten" in result or "Kabupaten" in result

    def test_lembaga(self):
        result = normalize_indonesian("dinkes akan melakukan sosialisasi")
        assert "Dinkes" in result

    def test_dokumen(self):
        result = normalize_indonesian("spj sudah di tanda tangani")
        assert "SPJ" in result

    def test_rapat(self):
        result = normalize_indonesian("rapat paripurna hari ini")
        assert "Paripurna" in result

    def test_mata_uang(self):
        result = normalize_indonesian("anggaran 1 milyar rupiah")
        assert "miliar" in result

    def test_angka_kabur(self):
        result = normalize_indonesian("anggaran beberpa juta")
        assert "beberapa" in result

    def test_normalize_empty(self):
        assert normalize_indonesian("") == ""
        assert normalize_indonesian("   ") == ""

    def test_normalize_no_change(self):
        text = "Ini teks normal tanpa istilah khusus."
        assert normalize_indonesian(text) == text

    def test_sapaan(self):
        result = normalize_indonesian("bapak bapak dan ibu ibu")
        assert "Bapak" in result
        assert "Ibu" in result

    def test_multi_line(self):
        text = "gak tau\nudah aja\nbikin laporan"
        result = normalize_indonesian(text)
        assert "\n" in result
        assert "tidak" in result
        assert "sudah" in result
        assert "membuat" in result
