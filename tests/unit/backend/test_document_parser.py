"""Tests for the document parser (11% coverage -> target 80%)."""

import sys
from unittest.mock import MagicMock, patch

import pytest


class TestParseDocument:
    def test_dispatches_pdf(self):
        from backend.app.services.document_parser import parse_document

        with patch("backend.app.services.document_parser.parse_pdf") as mock:
            mock.return_value = "pdf text"
            result = parse_document(b"fake pdf", "application/pdf")
            assert result == "pdf text"
            mock.assert_called_once_with(b"fake pdf")

    def test_dispatches_jpeg(self):
        from backend.app.services.document_parser import parse_document

        with patch("backend.app.services.document_parser.parse_image") as mock:
            mock.return_value = "image text"
            result = parse_document(b"fake jpeg", "image/jpeg")
            assert result == "image text"
            mock.assert_called_once_with(b"fake jpeg")

    def test_dispatches_png(self):
        from backend.app.services.document_parser import parse_document

        with patch("backend.app.services.document_parser.parse_image") as mock:
            mock.return_value = "png text"
            result = parse_document(b"fake png", "image/png")
            assert result == "png text"

    def test_unsupported_mime_raises(self):
        from backend.app.services.document_parser import parse_document

        with pytest.raises(ValueError, match="Unsupported document type"):
            parse_document(b"data", "text/plain")

    def test_mime_case_insensitive(self):
        from backend.app.services.document_parser import parse_document

        with patch("backend.app.services.document_parser.parse_pdf") as mock:
            mock.return_value = "pdf text"
            result = parse_document(b"data", "APPLICATION/PDF")
            assert result == "pdf text"

    def test_jpg_variant(self):
        from backend.app.services.document_parser import parse_document

        with patch("backend.app.services.document_parser.parse_image") as mock:
            mock.return_value = "jpg text"
            result = parse_document(b"data", "image/jpg")
            assert result == "jpg text"


def _mock_pdf_modules():
    """Helper: inject mock modules for fitz, pytesseract, PIL into sys.modules."""
    mock_fitz = MagicMock()
    mock_tess = MagicMock()
    mock_pil = MagicMock()
    mock_pil_module = MagicMock()
    mock_pil_module.Image = mock_pil
    sys.modules["fitz"] = mock_fitz
    sys.modules["pytesseract"] = mock_tess
    sys.modules["PIL"] = mock_pil_module
    sys.modules["PIL.Image"] = mock_pil
    return mock_fitz, mock_tess, mock_pil


class TestParsePdf:
    def test_extracts_text(self):
        mock_fitz, _, _ = _mock_pdf_modules()
        # Clear any cached import
        if "backend.app.services.document_parser" in sys.modules:
            del sys.modules["backend.app.services.document_parser"]

        from backend.app.services.document_parser import parse_pdf

        mock_doc = MagicMock()
        mock_doc.page_count = 1
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Page 1 content\n"
        mock_doc.__enter__.return_value = mock_doc
        mock_doc.__iter__.return_value = iter([mock_page])
        mock_fitz.open.return_value = mock_doc

        result = parse_pdf(b"fake pdf")
        assert "Page 1 content" in result

    def test_ocr_fallback_when_no_text(self):
        mock_fitz, mock_tess, _ = _mock_pdf_modules()
        if "backend.app.services.document_parser" in sys.modules:
            del sys.modules["backend.app.services.document_parser"]

        from backend.app.services.document_parser import parse_pdf

        mock_doc = MagicMock()
        mock_doc.page_count = 1
        mock_page = MagicMock()
        mock_page.get_text.return_value = ""
        mock_page.get_pixmap.return_value.tobytes.return_value = b"png"
        mock_doc.__enter__.return_value = mock_doc
        mock_doc.__iter__.return_value = iter([mock_page])
        mock_fitz.open.return_value = mock_doc
        mock_tess.image_to_string.return_value = "OCR extracted text"

        result = parse_pdf(b"fake scanned pdf")
        assert "OCR extracted text" in result
        mock_tess.image_to_string.assert_called_once()

    def test_rejects_excessive_pages(self):
        mock_fitz, _, _ = _mock_pdf_modules()
        if "backend.app.services.document_parser" in sys.modules:
            del sys.modules["backend.app.services.document_parser"]

        from backend.app.services.document_parser import parse_pdf

        mock_doc = MagicMock()
        mock_doc.page_count = 999
        mock_doc.__enter__.return_value = mock_doc
        mock_fitz.open.return_value = mock_doc

        from fastapi import HTTPException

        with pytest.raises(HTTPException, match="has.*pages"):
            parse_pdf(b"too many pages")

    def test_empty_document_returns_empty_string(self):
        mock_fitz, mock_tess, _ = _mock_pdf_modules()
        if "backend.app.services.document_parser" in sys.modules:
            del sys.modules["backend.app.services.document_parser"]

        from backend.app.services.document_parser import parse_pdf

        mock_doc = MagicMock()
        mock_doc.page_count = 1
        mock_page = MagicMock()
        mock_page.get_text.return_value = ""
        mock_page.get_pixmap = MagicMock(return_value=MagicMock())
        mock_page.get_pixmap.return_value.tobytes.return_value = b"dummy"
        mock_doc.__enter__.return_value = mock_doc
        mock_doc.__iter__.return_value = iter([mock_page])
        mock_fitz.open.return_value = mock_doc
        mock_tess.image_to_string.return_value = ""

        result = parse_pdf(b"empty pdf")
        assert result == ""


class TestParseImage:
    def test_extracts_text_from_rgb_image(self):
        _, mock_tess, _ = _mock_pdf_modules()
        if "backend.app.services.document_parser" in sys.modules:
            del sys.modules["backend.app.services.document_parser"]

        from backend.app.services.document_parser import parse_image

        mock_tess.image_to_string.return_value = "Extracted image text"

        result = parse_image(b"fake image")
        assert result == "Extracted image text"

    def test_converts_rgba_to_rgb(self):
        _, mock_tess, mock_pil = _mock_pdf_modules()
        if "backend.app.services.document_parser" in sys.modules:
            del sys.modules["backend.app.services.document_parser"]

        from backend.app.services.document_parser import parse_image

        rgba_img = MagicMock()
        rgba_img.mode = "RGBA"
        rgba_img.convert.return_value = MagicMock()
        mock_pil.open.return_value = rgba_img
        mock_tess.image_to_string.return_value = ""

        result = parse_image(b"rgba image")
        assert result == ""

    def test_handles_empty_extraction(self):
        _, mock_tess, _ = _mock_pdf_modules()
        if "backend.app.services.document_parser" in sys.modules:
            del sys.modules["backend.app.services.document_parser"]

        from backend.app.services.document_parser import parse_image

        mock_tess.image_to_string.return_value = ""

        result = parse_image(b"empty image")
        assert result == ""
