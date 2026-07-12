import hashlib
import math
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.base import utc_now
from backend.app.models.report import UserReport


async def get_report_by_id(
    db: AsyncSession,
    report_id: UUID,
    user_id: UUID,
) -> UserReport:
    """Get a single report and verify ownership."""
    query = select(UserReport).where(
        UserReport.id == report_id,
        UserReport.user_id == user_id,
        UserReport.deleted_at.is_(None),
    )
    result = await db.execute(query)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found or you don't have access to it.",
        )
    return report


async def create_report(
    db: AsyncSession,
    user_id: UUID,
    filename: str,
    original_filename: str,
    mime_type: str,
    extension: str,
    file_size: int,
    storage_path: str,
    checksum: str,
) -> UserReport:
    """Create a new report in the database."""

    # Check for duplicates using checksum and user_id
    query = select(UserReport).where(
        UserReport.user_id == user_id,
        UserReport.checksum == checksum,
        UserReport.deleted_at.is_(None),
    )
    result = await db.execute(query)
    existing_report = result.scalar_one_or_none()

    if existing_report:
        # If it's the exact same file, return the existing report to prevent duplicates
        return existing_report

    report = UserReport(
        user_id=user_id,
        filename=filename,
        original_filename=original_filename,
        mime_type=mime_type,
        extension=extension,
        file_size=file_size,
        storage_path=storage_path,
        checksum=checksum,
        upload_status="uploaded",
        processing_status="pending",
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


async def soft_delete_report(
    db: AsyncSession,
    report_id: UUID,
    user_id: UUID,
) -> None:
    """Soft delete a report."""
    report = await get_report_by_id(db, report_id, user_id)
    report.deleted_at = utc_now()
    await db.commit()


def calculate_checksum(content: bytes) -> str:
    """Calculate SHA-256 checksum for duplicate detection."""
    sha256_hash = hashlib.sha256()
    sha256_hash.update(content)
    return sha256_hash.hexdigest()
