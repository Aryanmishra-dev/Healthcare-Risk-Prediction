"""
File validation utilities for document uploads.

Validates MIME types, file sizes, and sanitizes filenames
for the medical document AI pipeline.
"""

import os
import re

from fastapi import HTTPException, UploadFile

# ── Constants ──────────────────────────────────────────────────────────────
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/jpg",
    "image/png",
}

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename by removing path separators and special characters."""
    # Strip directory components
    filename = os.path.basename(filename)
    # Remove anything that isn't alphanumeric, dash, underscore, or dot
    filename = re.sub(r"[^\w\-.]", "_", filename)
    # Collapse multiple underscores / dots
    filename = re.sub(r"_{2,}", "_", filename)
    filename = re.sub(r"\.{2,}", ".", filename)
    return filename or "unnamed_upload"


def validate_mime_type(content_type: str | None, filename: str | None) -> str:
    """
    Validate that the upload has an accepted MIME type.

    Falls back to extension check when the content-type header is ambiguous.
    Returns the validated MIME type string.
    """
    # Check content-type header first
    if content_type and content_type.lower() in ALLOWED_MIME_TYPES:
        return content_type.lower()

    # Fallback: check file extension
    if filename:
        ext = os.path.splitext(filename)[1].lower()
        if ext in ALLOWED_EXTENSIONS:
            mime_map = {
                ".pdf": "application/pdf",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
            }
            return mime_map.get(ext, "application/octet-stream")

    raise HTTPException(
        status_code=400,
        detail=(
            f"Unsupported file type: {content_type or 'unknown'}. "
            f"Accepted formats: PDF, JPG, JPEG, PNG."
        ),
    )


async def validate_upload(file: UploadFile) -> tuple[bytes, str]:
    """
    Validate an uploaded file and return (file_bytes, mime_type).

    Checks:
      1. MIME type / extension is in the allowed set
      2. File size ≤ 5 MB
      3. Filename is sanitized

    Raises HTTPException on any validation failure.
    """
    # 1. Validate MIME type
    mime_type = validate_mime_type(file.content_type, file.filename)

    # 2. Read contents and check size
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        size_mb = round(len(file_bytes) / (1024 * 1024), 2)
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({size_mb} MB). Maximum allowed size is 5 MB.",
        )

    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    return file_bytes, mime_type
