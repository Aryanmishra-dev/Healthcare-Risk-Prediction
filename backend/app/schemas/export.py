from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ExportRequest(BaseModel):
    export_format: str = Field("json", pattern="^(json|csv)$")


class ExportResponse(BaseModel):
    id: UUID
    export_type: str
    export_format: str
    status: str
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    checksum: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    downloaded_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedExportResponse(BaseModel):
    items: List[ExportResponse]
    total: int
    page: int
    size: int
    pages: int


class ExportQueryParams(BaseModel):
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)
    status: Optional[str] = None
