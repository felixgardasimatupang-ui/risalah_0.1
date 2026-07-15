import os
import pytest
from risalah.docx_generator import generate_risalah, generate_preview_text


@pytest.fixture
def fallback_data(segments):
    from risalah.ai_enhancer import build_fallback
    return build_fallback(segments)


class TestDocxGenerator:
    def test_generate_preview(self, fallback_data, meta):
        preview = generate_preview_text(fallback_data, meta)
        assert meta["acara"] in preview
        assert meta["tanggal"] in preview
        assert fallback_data["corrected_transcript"][0]["speaker"] in preview

    def test_generate_risalah(self, fallback_data, meta, sample_docx_path):
        result = generate_risalah(fallback_data, meta, sample_docx_path)
        assert result == sample_docx_path
        assert os.path.exists(sample_docx_path)

    def test_generate_without_meta(self, fallback_data, sample_docx_path):
        result = generate_risalah(fallback_data, output_path=sample_docx_path)

    def test_docx_file_content(self, fallback_data, meta, sample_docx_path):
        generate_risalah(fallback_data, meta, sample_docx_path)
        assert os.path.getsize(sample_docx_path) > 1000

    def test_generate_preview_without_meta(self, fallback_data):
        preview = generate_preview_text(fallback_data)
        assert "PREVIEW" in preview
