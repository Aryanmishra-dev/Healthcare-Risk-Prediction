# Phase 2.4 Summary: Report Storage & Document Management

## Files Modified
* `backend/app/models/report.py` - Expanded `UserReport` model with extensive file, storage, and processing metadata.
* `backend/migrations/versions/0005_phase2_4_report_storage.py` - Created manual schema migration script for `user_reports` table.
* `backend/app/main.py` - Registered the new `reports_router` in the application lifecycle.
* `backend/requirements.txt` - Added `aiofiles` dependency for async local storage access.

## Files Created
* `backend/app/services/storage.py` - Introduced abstract `StorageProvider` and `LocalStorageProvider` mapping files safely into `uploads/{user_id}/{report_uuid}/`.
* `backend/app/services/report_service.py` - Implemented core business logic for report CRUD operations and SHA-256 duplicate detection.
* `backend/app/services/document_pipeline.py` - Created asynchronous background worker to process text parsing and NLP extraction.
* `backend/app/schemas/report.py` - Implemented robust Pydantic schemas for the report endpoints.
* `backend/app/api/v1/routes/reports.py` - Created REST endpoints for report upload, retrieval, download, and deletion.
* `tests/integration/api/test_reports.py` - Created API integration tests.

## Storage Architecture
We implemented an abstract `StorageProvider` pattern that currently leverages `LocalStorageProvider` for rapid development. Files are written securely avoiding path traversal vulnerabilities. When the platform is ready to scale, adding a `S3StorageProvider` or `R2StorageProvider` will be a localized, seamless addition without altering business logic.

## API Endpoints
* `POST /api/v1/reports/upload` - Securely stores file, calculates checksum to reject duplicates, stores metadata, and spins off a background task for processing.
* `GET /api/v1/reports` - Paginated endpoint for listing an authenticated user's uploaded reports, with filtering and searching capabilities.
* `GET /api/v1/reports/{report_id}` - Detailed view of a single report, including processing status.
* `DELETE /api/v1/reports/{report_id}` - Safe soft-delete mechanism.
* `GET /api/v1/reports/{report_id}/download` - Serves the raw file content efficiently directly from the StorageProvider.

## Security Measures
* **Strict Ownership Validation:** Every report endpoint enforces that a user can only access their own reports (`user_id` bounding).
* **Path Traversal Protection:** The storage provider sanitizes the filename and explicitly validates that all path resolution remains nested securely under the designated upload directory.
* **Checksum Duplicate Detection:** Deduplicates data at the database level by ensuring identical files (based on SHA-256) are returned directly without redundant processing or storage.
* **Safe Download Content-Disposition:** Files are returned with appropriate attachment headers.

## Database Changes
`user_reports` was transformed from an MVP tracking table into a robust file system map. We've dropped fields like `file_name` and `extracted_metadata` to conform to the explicit roadmap fields (`filename`, `original_filename`, `storage_path`, `checksum`, `upload_status`, `processing_status`, `parser_version`, `uploaded_at`, etc.). A proper SHA-256 index was added to speed up duplicate detection queries.

## Test Results
Integration tests have been incorporated into the primary suite (`pytest`).
The full suite executed with 256 passed, 4 skipped, 0 failures, maintaining global coverage ~75.2%.

## Remaining Technical Debt & Performance Considerations
* **Celery:** The `BackgroundTasks` implementation is a great short-term asynchronous execution mechanism, but it shares the event loop and memory limits with the FastAPI worker. As requested, we have deferred Celery. When reports scale or ML models grow heavy, this should be the priority to offload parsing.
* **Virus Scanning:** A placeholder is noted for file upload validation. Future enhancements could pipe streams through a ClamAV daemon before committing bytes to the storage provider.
