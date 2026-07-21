"""
Document parsing layer for the medical document AI pipeline.

Extracts raw text from uploaded medical reports.
Supports:
  - PDF files via PyMuPDF (fitz)
  - Image files (JPG, JPEG, PNG) via pytesseract OCR
"""

import io
import logging

import fitz  # type: ignore[import-untyped]  # PyMuPDF
import pytesseract  # type: ignore[import-untyped]
from fastapi import HTTPException
from PIL import Image

logger = logging.getLogger(__name__)

# Maximum number of PDF pages to process (DoS protection).
MAX_PDF_PAGES = int(__import__("os").environ.get("MAX_PDF_PAGES", "100"))


def parse_pdf(file_bytes: bytes) -> str:
    """
    Extract text from a PDF file.

    Uses PyMuPDF (fitz) to iterate all pages and concatenate text.
    If no text is found (e.g., scanned PDF), falls back to OCR.
    """

    text_parts: list[str] = []
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        if doc.page_count > MAX_PDF_PAGES:
            raise HTTPException(
                status_code=400,
                detail=f"PDF has {doc.page_count} pages (max {MAX_PDF_PAGES}). "
                "Please upload a shorter document.",
            )
        for page_num, page in enumerate(doc):
            page_text = page.get_text("text")

            if not page_text.strip():
                logger.debug(
                    "pdf_page_no_text_falling_back_to_ocr",
                    extra={"page": page_num},
                )
                pix = page.get_pixmap(dpi=150)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                page_text = pytesseract.image_to_string(img)

            if page_text.strip():
                text_parts.append(page_text)
            logger.debug(
                "pdf_page_extracted",
                extra={"page": page_num, "chars": len(page_text)},
            )

        raw_text = "\n".join(text_parts).strip()

    if not raw_text:
        logger.warning("pdf_no_text_extracted_even_with_ocr")

    return raw_text


def parse_image(file_bytes: bytes) -> str:
    """
    Extract text from an image file using OCR (Tesseract).

    Uses pytesseract with Pillow for image handling.
    """

    image = Image.open(io.BytesIO(file_bytes))

    # Convert to RGB if necessary (e.g. RGBA PNGs)
    if image.mode not in ("L", "RGB"):
        image = image.convert("RGB")  # type: ignore[assignment]

    raw_text = pytesseract.image_to_string(image).strip()
    if not raw_text:
        logger.warning("ocr_no_text_extracted")
    return raw_text


def parse_document(file_bytes: bytes, mime_type: str) -> str:
    """
    Top-level dispatcher — choose the right parser based on MIME type.

    Returns:
        Raw extracted text from the document.

    Raises:
        ValueError: If the MIME type is not supported.
    """
    mime_type = mime_type.lower()

    if mime_type == "application/pdf":
        return parse_pdf(file_bytes)
    elif mime_type in ("image/jpeg", "image/jpg", "image/png"):
        return parse_image(file_bytes)
    else:
        raise ValueError(f"Unsupported document type for parsing: {mime_type}")
