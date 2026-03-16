"""
Document upload API route.

POST /api/v1/document/upload

Accepts a medical report file (PDF, JPG, JPEG, PNG ≤ 5 MB),
runs the document AI pipeline, and returns extracted clinical
entities plus mapped features for all three models.
"""

import logging

from fastapi import APIRouter, File, UploadFile, Depends, Request, Response

from app.utils.file_validation import validate_upload
from app.services.document_parser import parse_document
from app.services.medical_nlp import extract_clinical_entities
from app.services.feature_mapper import map_to_all_models

logger = logging.getLogger(__name__)

router = APIRouter(tags=["document-ai"])


@router.post("/document/upload")
async def upload_document(
    request: Request,
    response: Response,
    file: UploadFile = File(..., description="Medical report (PDF, JPG, JPEG, or PNG, ≤ 5 MB)"),
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
    # 1. Validate
    file_bytes, mime_type = await validate_upload(file)
    logger.info(
        "document_upload_received",
        extra={"mime": mime_type, "size_bytes": len(file_bytes)},
    )

    # 2. Extract text
    try:
        raw_text = parse_document(file_bytes, mime_type)
    except Exception as e:
        logger.error("document_parse_failed", extra={"error": str(e)})
        return {"error": f"Failed to extract text from document: {str(e)}"}

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

    logger.info("document_pipeline_complete", extra={
        "entities_found": sum(1 for v in entities.values() if v is not None),
    })

    return {
        "raw_text": raw_text[:2000],  # truncate for response size
        "entities": entities,
        "mapped_features": mapped_features,
    }
