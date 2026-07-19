import math
import os
import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import Response
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.router import get_current_user
from backend.app.core.database import get_db
from backend.app.models.report import UserReport
from backend.app.models.user import User
from backend.app.schemas.report import (
    ReportPaginated,
    ReportQueryParams,
    ReportResponse,
    ReportUploadResponse,
)
from backend.app.services.document_pipeline import process_report_pipeline
from backend.app.services.report_service import (
    calculate_checksum,
    create_report,
    get_report_by_id,
    soft_delete_report,
)
from backend.app.services.storage import storage_provider
from backend.app.utils.file_validation import validate_upload

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post(
    "/upload",
    response_model=ReportUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_report(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(
        ..., description="Medical report (PDF, JPG, JPEG, or PNG, <= 5 MB)"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a medical report.
    Validates file, stores it locally, and queues background processing.
    """
    file_bytes, mime_type = await validate_upload(file)
    checksum = calculate_checksum(file_bytes)

    # Check if a duplicate exists using the service function
    # Wait, create_report already does duplicate checking.

    report_uuid = str(uuid.uuid4())
    original_filename = file.filename or "unknown"
    extension = (
        os.path.splitext(original_filename)[1].lower()
        if original_filename
        else ""
    )
    safe_filename = f"{report_uuid}{extension}"

    # Check duplicate early to avoid saving file if not needed
    existing = await db.scalar(
        select(UserReport).where(
            UserReport.user_id == current_user.id,
            UserReport.checksum == checksum,
            UserReport.deleted_at.is_(None),
        )
    )
    if existing:
        return existing

    storage_path = await storage_provider.save_file(
        user_id=current_user.id,
        report_uuid=report_uuid,
        filename=safe_filename,
        content=file_bytes,
    )

    report = await create_report(
        db=db,
        user_id=current_user.id,
        filename=safe_filename,
        original_filename=original_filename,
        mime_type=mime_type,
        extension=extension,
        file_size=len(file_bytes),
        storage_path=storage_path,
        checksum=checksum,
    )

    background_tasks.add_task(
        process_report_pipeline, report.id, current_user.id
    )

    return report


@router.get("", response_model=ReportPaginated)
async def get_reports(
    params: ReportQueryParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated uploaded reports with filters."""
    query = select(UserReport).where(
        UserReport.user_id == current_user.id, UserReport.deleted_at.is_(None)
    )

    if params.status:
        query = query.where(UserReport.processing_status == params.status)
    if params.search:
        search_term = f"%{params.search}%"
        query = query.where(UserReport.original_filename.ilike(search_term))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Pagination
    offset = (params.page - 1) * params.size
    query = (
        query.order_by(desc(UserReport.uploaded_at))
        .offset(offset)
        .limit(params.size)
    )

    result = await db.execute(query)
    items = result.scalars().all()

    pages = math.ceil(total / params.size) if total > 0 else 0

    return ReportPaginated(
        items=items,
        total=total,
        page=params.page,
        size=params.size,
        pages=pages,
    )


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single report's metadata."""
    return await get_report_by_id(db, report_id, current_user.id)


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete a report."""
    await soft_delete_report(db, report_id, current_user.id)
    return None


@router.get("/{report_id}/download")
async def download_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download the actual report file."""
    report = await get_report_by_id(db, report_id, current_user.id)
    try:
        content = await storage_provider.get_file(report.storage_path)
    except Exception:
        raise HTTPException(status_code=404, detail="File not found on disk")

    return Response(
        content=content,
        media_type=report.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{report.original_filename}"'
        },
    )
