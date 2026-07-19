"""
Document upload API route.

POST /api/v1/document/upload

Accepts a medical report file (PDF, JPG, JPEG, PNG ≤ 5 MB),
runs the document AI pipeline, and returns extracted clinical
entities plus mapped features for all three models.
"""

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from backend.app.services.document_parser import parse_document
from backend.app.services.feature_mapper import map_to_all_models
from backend.app.services.medical_nlp import extract_clinical_entities
from backend.app.utils.file_validation import validate_upload

logger = logging.getLogger(__name__)

router = APIRouter(tags=["document-ai"])


class TextExtractionRequest(BaseModel):
    text: str


@router.post("/document/text")
async def extract_from_text(payload: TextExtractionRequest):
    """
    Extract clinical features directly from transcribed voice text.
    """
    raw_text = payload.text
    if not raw_text.strip():
        return {"error": "No text provided for extraction."}

    entities = extract_clinical_entities(raw_text)
    mapped_features = map_to_all_models(entities)

    logger.info(
        "text_pipeline_complete",
        extra={
            "entities_found": sum(
                1 for v in entities.values() if v is not None
            ),
        },
    )

    return {
        "raw_text": raw_text[:2000],
        "entities": entities,
        "mapped_features": mapped_features,
    }


@router.post("/document/upload")
async def upload_document(
    file: UploadFile = File(
        ..., description="Medical report (PDF, JPG, JPEG, or PNG, ≤ 5 MB)"
    )
):
    """
    Upload a medical report and extract clinical features.

    Pipeline:
      1. Validate file type and size
      2. Extract raw text (PDF parser or OCR)
      3. Extract clinical entities via NLP
      4. Map entities to all three ML model input formats

    Returns JSON:
      {
        "raw_text": "...",
        "entities": { ... },
        "mapped_features": {
          "diabetes": { ... },
          "heart": { ... },
          "lung": { ... }
        }
      }
    """
    return await process_uploaded_document(file)


async def process_uploaded_document(file: UploadFile):
    """Run validation, text extraction, NLP, and feature mapping for an upload."""
    file_bytes, mime_type = await validate_upload(file)
    logger.info(
        "document_upload_received",
        extra={"mime": mime_type, "size_bytes": len(file_bytes)},
    )

    # 2. Extract text
    try:
        raw_text = parse_document(file_bytes, mime_type)
    except Exception as e:
        logger.exception("document_parse_failed")
        raise HTTPException(
            status_code=422,
            detail="Failed to extract text from document. The file may be corrupt or unreadable.",
        ) from e

    if not raw_text:
        return {
            "raw_text": "",
            "entities": {},
            "mapped_features": {},
            "warning": "No text could be extracted from the document. Try a clearer image or a text-based PDF.",
        }

    # 3. Extract clinical entities
    entities = extract_clinical_entities(raw_text)

    # 4. Map to model features
    mapped_features = map_to_all_models(entities)

    logger.info(
        "document_pipeline_complete",
        extra={
            "entities_found": sum(
                1 for v in entities.values() if v is not None
            ),
        },
    )

    return {
        "raw_text": raw_text[:2000],  # truncate for response size
        "entities": entities,
        "mapped_features": mapped_features,
    }
