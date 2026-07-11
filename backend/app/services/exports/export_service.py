import uuid
import hashlib
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, update

from backend.app.models.export import DataExport
from backend.app.services.exports.generators import generate_user_data_json
from backend.app.services.exports.providers import ExportProvider
from backend.app.services.notifications.notification_service import notification_dispatcher
from backend.app.models.base import utc_now
from backend.app.schemas.export import ExportQueryParams, PaginatedExportResponse

class ExportService:
    def __init__(self, provider: ExportProvider):
        self.provider = provider

    async def request_export(self, db: AsyncSession, user_id: uuid.UUID, export_format: str = "json") -> DataExport:
        # Check if there is already a pending or processing export
        result = await db.execute(
            select(DataExport)
            .where(DataExport.user_id == user_id)
            .where(DataExport.status.in_(["pending", "processing"]))
        )
        existing = result.scalars().first()
        if existing:
            raise ValueError("An export is already in progress.")
            
        export_record = DataExport(
            user_id=user_id,
            export_type="full",
            export_format=export_format,
            status="pending",
        )
        db.add(export_record)
        await db.commit()
        await db.refresh(export_record)
        
        # Dispatch notification
        import asyncio
        asyncio.create_task(
            notification_dispatcher.dispatch(
                user_id=user_id,
                notification_type="export_requested",
                category="System",
                priority="LOW",
                title="Data Export Requested",
                message="Your data export has been requested and is currently being processed."
            )
        )
        
        return export_record

    async def process_export_task(self, db: AsyncSession, export_id: uuid.UUID) -> None:
        """Background task to generate and store the export."""
        export_record = await db.get(DataExport, export_id)
        if not export_record:
            return
            
        user_id = export_record.user_id
        export_record.status = "processing"
        export_record.started_at = utc_now()
        await db.commit()
        await db.refresh(export_record)
        
        try:
            # 1. Generate content
            if export_record.export_format == "json":
                content = await generate_user_data_json(db, export_record.user_id)
                filename = f"export_{export_record.user_id}_{export_record.id}.json"
            else:
                raise NotImplementedError("Format not supported yet")
                
            # 2. Calculate checksum and metadata
            checksum = hashlib.sha256(content).hexdigest()
            file_size = len(content)
            
            # 3. Save via Provider
            storage_path = await self.provider.save_export(
                user_id=str(export_record.user_id),
                export_id=str(export_record.id),
                filename=filename,
                content=content
            )
            
            # 4. Update DB
            export_record.status = "completed"
            export_record.storage_path = storage_path
            export_record.file_name = filename
            export_record.file_size = file_size
            export_record.checksum = checksum
            export_record.completed_at = utc_now()
            export_record.expires_at = utc_now() + timedelta(days=7) # Expires in 7 days
            await db.commit()
            
            # 5. Notify success
            import asyncio
            asyncio.create_task(
                notification_dispatcher.dispatch(
                    user_id=user_id,
                    notification_type="export_ready",
                    category="System",
                    priority="HIGH",
                    title="Data Export Ready",
                    message="Your data export has been generated and is ready for download."
                )
            )
            
        except Exception as e:
            export_record.status = "failed"
            await db.commit()
            
            import asyncio
            asyncio.create_task(
                notification_dispatcher.dispatch(
                    user_id=export_record.user_id,
                    notification_type="export_failed",
                    category="System",
                    priority="HIGH",
                    title="Data Export Failed",
                    message="An error occurred while generating your data export."
                )
            )
            raise e

    async def get_exports(self, db: AsyncSession, user_id: uuid.UUID, params: ExportQueryParams) -> PaginatedExportResponse:
        query = select(DataExport).where(DataExport.user_id == user_id)
        
        if params.status:
            query = query.where(DataExport.status == params.status)
            
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query) or 0
        
        # Paginate
        offset = (params.page - 1) * params.size
        query = query.order_by(desc(DataExport.created_at)).offset(offset).limit(params.size)
        
        result = await db.execute(query)
        items = result.scalars().all()
        
        import math
        pages = math.ceil(total / params.size) if total > 0 else 0
        
        return PaginatedExportResponse(
            items=items,
            total=total,
            page=params.page,
            size=params.size,
            pages=pages
        )

    async def get_export(self, db: AsyncSession, user_id: uuid.UUID, export_id: uuid.UUID) -> DataExport:
        export_record = await db.get(DataExport, export_id)
        if not export_record or export_record.user_id != user_id:
            raise ValueError("Export not found")
        
        # Mark as expired lazily
        if export_record.status == "completed" and export_record.expires_at and export_record.expires_at < utc_now():
            export_record.status = "expired"
            await db.commit()
            
        return export_record
        
    async def delete_export(self, db: AsyncSession, user_id: uuid.UUID, export_id: uuid.UUID) -> None:
        export_record = await self.get_export(db, user_id, export_id)
        if export_record.storage_path:
            try:
                await self.provider.delete_export(export_record.storage_path)
            except Exception:
                pass # Continue deleting record even if file deletion fails
                
        await db.delete(export_record)
        await db.commit()
