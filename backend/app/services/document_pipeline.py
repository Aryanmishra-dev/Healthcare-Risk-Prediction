import asyncio
import logging
from uuid import UUID

from backend.app.core.database import AsyncSessionLocal
from backend.app.models.base import utc_now
from backend.app.models.report import UserReport
from backend.app.services.document_parser import parse_document
from backend.app.services.medical_nlp import extract_clinical_entities
from backend.app.services.notifications.notification_service import (
    notification_dispatcher,
)
from backend.app.services.storage import storage_provider

logger = logging.getLogger(__name__)


async def process_report_pipeline(report_id: UUID, user_id: UUID):
    """
    Background task to process an uploaded medical report through the pipeline.
    Stages:
    1. Uploaded -> OCR (Text extraction)
    2. Medical NLP
    3. Prediction Ready -> Completed
    """
    async with AsyncSessionLocal() as db:
        try:
            # 1. Fetch report
            report = await db.get(UserReport, report_id)
            if not report or report.user_id != user_id:
                logger.error(f"Report {report_id} not found or unauthorized.")
                return

            # Skip if already processed or deleted
            if report.deleted_at or report.processing_status == "completed":
                return

            asyncio.create_task(
                notification_dispatcher.dispatch(
                    user_id=user_id,
                    notification_type="report_processing_started",
                    category="Report",
                    priority="LOW",
                    title="Report Processing Started",
                    message=(
                        f"Your report {report.original_filename} "
                        "is being processed."
                    ),
                )
            )

            # Stage: OCR
            report.processing_status = "ocr"
            await db.commit()

            try:
                file_bytes = await storage_provider.get_file(
                    report.storage_path
                )
                # B5: CPU-bound PDF/image parsing — offload to thread pool
                raw_text = await asyncio.to_thread(
                    parse_document, file_bytes, report.mime_type
                )
                if not raw_text:
                    report.processing_status = "failed"
                    await db.commit()
                    asyncio.create_task(
                        notification_dispatcher.dispatch(
                            user_id=user_id,
                            notification_type="report_processing_failed",
                            category="Report",
                            priority="HIGH",
                            title="Report Processing Failed",
                            message=(
                                f"We could not extract text from "
                                f"{report.original_filename}."
                            ),
                        )
                    )
                    return
            except Exception:
                logger.exception(f"OCR failed for report {report_id}")
                report.processing_status = "failed"
                await db.commit()
                asyncio.create_task(
                    notification_dispatcher.dispatch(
                        user_id=user_id,
                        notification_type="report_processing_failed",
                        category="Report",
                        priority="HIGH",
                        title="Report Processing Failed",
                        message=(
                            f"We encountered an error processing "
                            f"{report.original_filename}."
                        ),
                    )
                )
                return

            # Stage: Medical NLP
            report.processing_status = "medical_nlp"
            await db.commit()

            try:
                # B5: CPU-bound NLP — offload to thread pool
                entities = await asyncio.to_thread(
                    extract_clinical_entities, raw_text
                )
                report.extracted_entities = entities
            except Exception:
                logger.exception(f"NLP failed for report {report_id}")
                report.processing_status = "failed"
                await db.commit()
                asyncio.create_task(
                    notification_dispatcher.dispatch(
                        user_id=user_id,
                        notification_type="report_processing_failed",
                        category="Report",
                        priority="HIGH",
                        title="Report Processing Failed",
                        message=(
                            f"We encountered an error extracting data "
                            f"from {report.original_filename}."
                        ),
                    )
                )
                return

            # Stage: Feature Extraction -> Not stored on report,
            # usually mapped at prediction time
            # Stage: Completed
            report.processing_status = "completed"
            report.processed_at = utc_now()
            await db.commit()

            asyncio.create_task(
                notification_dispatcher.dispatch(
                    user_id=user_id,
                    notification_type="report_processing_completed",
                    category="Report",
                    priority="NORMAL",
                    title="Report Processing Completed",
                    message=(
                        f"Your report {report.original_filename} "
                        "has been successfully processed."
                    ),
                )
            )

            logger.info(f"Report {report_id} processed successfully.")

        except Exception:
            logger.exception(f"Pipeline failed for report {report_id}")
            await db.rollback()
