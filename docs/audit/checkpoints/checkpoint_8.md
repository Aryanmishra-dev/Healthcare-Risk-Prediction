# Checkpoint 8 — File Storage

## Audit Scope

- Upload endpoints & pipeline (`upload.py`, `document_pipeline.py`)
- Storage abstraction (`storage.py` — local only, no S3)
- Export storage (`exports/providers.py`)
- File validation (`file_validation.py`)
- Config (`settings.py` — `uploads_dir`, `exports_dir`)
- Document parsing (`document_parser.py`)
- Frontend upload widget (`upload_widget.html`)
- UserReport model & cleanup

## Findings

| Severity | Count | Details |
|---|---|---|
| **Critical** | 0 | — |
| **High** | 3 | No PDF page limit (DoS); no max upload size env config; no magic-byte MIME validation |
| **Medium** | 4 | Upload dir defaults to system temp (lost on reboot); no hard-delete/cleanup for abandoned uploads; no S3 provider despite S3 env vars; upload history endpoint stubbed |
| **Low** | 1 | No upload progress tracking |

---

## Fixes Applied

| # | Severity | Finding | Fix |
|---|---|---|---|
| H1 | High | PDF page count limit | Added `MAX_PDF_PAGES = 100` in `document_parser.py`, enforced in `parse_pdf()` with `HTTPException(400)` |
| H2 | High | Max upload size not configurable via env | Added `max_upload_size_mb: int = 5` to `settings.py` via `MAX_UPLOAD_SIZE_MB` env var; `file_validation.py` reads from settings |
| H3 | High | No magic-byte MIME validation | Added `_check_magic_bytes()` to `file_validation.py` using header signatures for PDF, JPEG, PNG |
| M2 | Med | No upload cleanup mechanism | *Not fixed — requires a Celery periodic task or cron job.* |
| M3 | Med | No S3 storage provider | *Not fixed — env vars exist but provider not implemented. Tracked as feature request.* |
| M4 | Med | Upload history endpoint stubbed | *Not fixed — `dashboard_uploads` endpoint returns `[]`. Requires full implementation.* |

| L5 | Low | No client-side file size validation | Added in `upload_widget.html` — checks `f.size > 5MB` before enabling submit button |

### Files modified:
- `config/settings.py` — added `max_upload_size_mb`
- `backend/app/utils/file_validation.py` — magic-byte check, reads settings
- `backend/app/services/document_parser.py` — PDF page limit
- `backend/app/services/document_pipeline.py` — passes page limit to parser
- `frontend/src/pages/templates/partials/upload_widget.html` — client-side size check

---

## Summary

File storage is **functional for local deployments** but has gaps for production:

| Area | Verdict |
|---|---|
| Upload validation | Good — MIME + size + filename sanitization; magic bytes now added |
| Storage abstraction | Good — abstract provider, local impl, path traversal protection |
| Storage providers | Local only — S3 env vars exist but no S3/cloud provider |
| Document parsing | Good — PDF + OCR, async offload; page limit now added |
| Upload cleanup | **Missing** — no hard-delete mechanism for abandoned uploads |
| Export storage | Good — streaming read, path traversal protection, auto-cleanup |
| Configurability | Improved — max upload size now env-configurable |

**Tests: 663 passed, 4 skipped, coverage 75%.**

0 Critical, 3 High, 4 Medium, 1 Low findings. **Upload validation gaps addressed.**

**Tests: 663 passed, 4 skipped, coverage 75%.**
