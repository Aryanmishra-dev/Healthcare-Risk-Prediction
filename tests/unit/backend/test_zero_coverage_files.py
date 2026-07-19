"""Tests for 0% coverage files: models, schemas, core modules."""

from unittest.mock import MagicMock, patch


class TestFileValidationUtils:
    def test_sanitize_filename_empty(self):
        from backend.app.utils.file_validation import sanitize_filename

        assert sanitize_filename("") == "unnamed_upload"

    def test_sanitize_filename_special_chars(self):
        from backend.app.utils.file_validation import sanitize_filename

        result = sanitize_filename("hello'world(test).pdf")
        assert "'" not in result
        assert "(" not in result

    def test_sanitize_filename_path_stripped(self):
        from backend.app.utils.file_validation import sanitize_filename

        result = sanitize_filename("/etc/passwd")
        assert "/" not in result

    def test_max_file_size_constant(self):
        from backend.app.utils.file_validation import MAX_FILE_SIZE_BYTES

        assert MAX_FILE_SIZE_BYTES == 5 * 1024 * 1024

    def test_allowed_mime_types_set(self):
        from backend.app.utils.file_validation import ALLOWED_MIME_TYPES

        assert "application/pdf" in ALLOWED_MIME_TYPES
        assert "image/jpeg" in ALLOWED_MIME_TYPES
        assert "image/png" in ALLOWED_MIME_TYPES
        assert len(ALLOWED_MIME_TYPES) == 4

    def test_allowed_extensions(self):
        from backend.app.utils.file_validation import ALLOWED_EXTENSIONS

        assert ".pdf" in ALLOWED_EXTENSIONS
        assert ".jpg" in ALLOWED_EXTENSIONS
        assert ".jpeg" in ALLOWED_EXTENSIONS
        assert ".png" in ALLOWED_EXTENSIONS

    def test_validate_mime_type_valid_pdf(self):
        from backend.app.utils.file_validation import validate_mime_type

        result = validate_mime_type("application/pdf", "report.pdf")
        assert result == "application/pdf"

    def test_validate_mime_type_fallback_to_extension(self):
        from backend.app.utils.file_validation import validate_mime_type

        result = validate_mime_type("application/octet-stream", "report.pdf")
        assert result == "application/pdf"

    def test_validate_mime_type_rejects_invalid(self):
        import pytest
        from fastapi import HTTPException

        from backend.app.utils.file_validation import validate_mime_type

        with pytest.raises(HTTPException) as exc:
            validate_mime_type("text/plain", "notes.txt")
        assert exc.value.status_code == 400
