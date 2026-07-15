import pytest
from risalah.ai_enhancer import build_fallback, enhance_transcript, enhance_transcript_with_doc_context


class TestAiEnhancer:
    def test_build_fallback_basic(self, segments):
        result = build_fallback(segments)
        assert isinstance(result, dict)
        assert "corrected_transcript" in result
        assert "speaker_identification" in result
        assert len(result["corrected_transcript"]) == len(segments)

    def test_build_fallback_empty(self):
        result = build_fallback([])
        assert result["corrected_transcript"] == []
        assert result["speaker_identification"] == []

    def test_build_fallback_speaker_labels(self, segments):
        result = build_fallback(segments)
        for entry in result["corrected_transcript"]:
            assert "speaker" in entry
            assert "text" in entry
            assert "time" in entry

    def test_build_fallback_identification(self, segments):
        result = build_fallback(segments)
        assert len(result["speaker_identification"]) > 0
        for s in result["speaker_identification"]:
            assert "label" in s
            assert "inferred_name" in s

    def test_build_fallback_sections_present(self, segments):
        result = build_fallback(segments)
        assert "pokok_bahasan" in result
        assert "keputusan_rapat" in result
        assert "tindak_lanjut" in result

    @pytest.mark.slow
    def test_enhance_with_doc_context_empty_doc(self, segments):
        """Doc context kosong harus fallback ke enhance_transcript biasa."""
        doc_ctx = {"all_text_combined": "", "document_sources": [], "image_sources": []}
        result = enhance_transcript_with_doc_context(segments, doc_ctx)
        assert isinstance(result, dict)
        assert "corrected_transcript" in result

    @pytest.mark.slow
    def test_enhance_with_doc_context_basic(self, segments, tmp_path):
        """Doc context dengan isi, verify dokumen_analisis_mode flag."""
        doc_ctx = {
            "all_text_combined": "APBD tahun 2025 sebesar Rp 5 triliun untuk pembangunan infrastruktur.",
            "document_sources": [{"file": "anggaran.pdf", "text": "APBD 2025 Rp 5T"}],
            "image_sources": [],
        }
        result = enhance_transcript_with_doc_context(segments, doc_ctx, output_dir=str(tmp_path))
        assert isinstance(result, dict)
        assert "corrected_transcript" in result
        assert result.get("dokumen_analisis_mode") is True
        assert len(result["corrected_transcript"]) == len(segments)

    @pytest.mark.slow
    def test_enhance_with_doc_context_large_doc(self, segments):
        """Doc context > 15000 chars harus di-truncate."""
        big_text = " ".join(["kalimat"] * 3000)
        doc_ctx = {
            "all_text_combined": big_text,
            "document_sources": [{"file": "besar.pdf", "text": big_text[:100]}],
            "image_sources": [],
        }
        result = enhance_transcript_with_doc_context(segments, doc_ctx)
        assert isinstance(result, dict)
        assert "corrected_transcript" in result
