from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ReportUploadResponse(BaseModel):
    id: UUID
    filename: str
    upload_status: str
    processing_status: str

    model_config = {"from_attributes": True}


class ReportResponse(BaseModel):
    id: UUID
    filename: str
    original_filename: str
    mime_type: str
    file_size: int
    upload_status: str
    processing_status: str
    parser_version: str
    prediction_count: int
    extracted_entities: Optional[Dict[str, Any]] = None
    uploaded_at: datetime
    processed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ReportPaginated(BaseModel):
    items: List[ReportResponse]
    total: int
    page: int
    size: int
    pages: int


class ReportQueryParams(BaseModel):
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)
    status: Optional[str] = None
    search: Optional[str] = None
