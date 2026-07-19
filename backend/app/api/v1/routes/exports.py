from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.router import get_current_user
from backend.app.core.database import get_db
from backend.app.models.base import utc_now
from backend.app.models.user import User
from backend.app.schemas.export import (
    ExportQueryParams,
    ExportRequest,
    ExportResponse,
    PaginatedExportResponse,
)
from backend.app.services.exports import export_provider
from backend.app.services.exports.export_service import ExportService

router = APIRouter(prefix="/exports", tags=["Exports"])


def get_export_service() -> ExportService:
    return ExportService(export_provider)


@router.post(
    "", response_model=ExportResponse, status_code=status.HTTP_202_ACCEPTED
)
async def request_export(
    payload: ExportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    export_service: ExportService = Depends(get_export_service),
):
    try:
        export_record = await export_service.request_export(
            db, current_user.id, payload.export_format
        )
        background_tasks.add_task(
            export_service.process_export_task, db, export_record.id
        )
        return export_record
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("", response_model=PaginatedExportResponse)
async def list_exports(
    params: ExportQueryParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    export_service: ExportService = Depends(get_export_service),
):
    return await export_service.get_exports(db, current_user.id, params)


@router.get("/{export_id}", response_model=ExportResponse)
async def get_export(
    export_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    export_service: ExportService = Depends(get_export_service),
):
    try:
        return await export_service.get_export(db, current_user.id, export_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{export_id}/download")
async def download_export(
    export_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    export_service: ExportService = Depends(get_export_service),
):
    try:
        export_record = await export_service.get_export(
            db, current_user.id, export_id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if export_record.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=(
                "Export is not ready for download. "
                f"Status: {export_record.status}"
            ),
        )

    if not export_record.storage_path:
        raise HTTPException(status_code=404, detail="Export file missing")

    # Mark downloaded
    export_record.downloaded_at = utc_now()
    await db.commit()

    stream = await export_provider.get_export_stream(
        export_record.storage_path
    )
    content_type = (
        "application/json"
        if export_record.export_format == "json"
        else "text/csv"
    )

    return StreamingResponse(
        stream,
        media_type=content_type,
        headers={
            "Content-Disposition": (
                f"attachment; filename={export_record.file_name}"
            ),
            "X-Checksum-Sha256": export_record.checksum or "",
        },
    )


@router.delete("/{export_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_export(
    export_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    export_service: ExportService = Depends(get_export_service),
):
    try:
        await export_service.delete_export(db, current_user.id, export_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return None
