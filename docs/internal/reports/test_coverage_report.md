# Test Coverage Report — RC1

**Date**: 2026-07-19
**Total tests**: 650 passed, 4 skipped
**Overall coverage**: 75%

## Coverage by Module

| Module | Coverage | Status |
|--------|----------|--------|
| Models | 100% (all 12 files) | ✅ Verified |
| Core (enums, config, database) | 100% | ✅ Verified |
| Auth router | 50% | ⚠️ Low |
| Routes (API v1) | 55-100% | ✅ Verified |
| Services | 29-100% | ⚠️ Mixed |
| Tasks (Celery) | 0% | ❌ Not tested |
| Middleware | 91-94% | ✅ |
| Utils | 98% | ✅ |

## Services Coverage Detail

| Service | Coverage | Notes |
|---------|----------|-------|
| usage_meter_service.py | 100% | |
| webhook_security_service.py | 100% | |
| webhook_service.py | 94% | |
| cache_service.py | 94% | |
| storage.py | 94% | |
| email_service.py | 92% | |
| model_loader.py | 90% | |
| feature_mapper.py | 91% | |
| medical_nlp.py | 91% | |
| rate_limit_service.py | 77% | |
| audit_service.py | 75% | New in Phase 6.5 |
| api_key_service.py | 65% | Key rotation branches |
| report_service.py | 60% | |
| quota_service.py | 57% | |
| model_manager.py | 57% | |
| shap_explainer.py | 57% | |
| security_service.py | 54% | |
| webhook_delivery_service.py | 52% | |
| prediction_history_service.py | 51% | |
| authorization_service.py | 45% | Permission checking |
| model_registry_service.py | 44% | |
| export_service.py | 43% | |
| user_dashboard_service.py | 39% | |
| notification_service.py | 39% | |
| email provider | 37% | |
| document_pipeline.py | 29% | |
| **Celery tasks** | **0%** | `audit_tasks.py`, `webhook_tasks.py` |

## Uncovered Critical Paths

1. **Celery tasks** — `webhook_tasks.py`, `audit_tasks.py` have zero coverage. Requires a running Celery worker (integration-level).
2. **Authorization service** — `authorization_service.py` at 45%: the `can()` method's org-role permission check logic is not tested for non-OWNER roles.
3. **Audit retention** — `audit_retention_service.py` apply_retention method not tested with real DB.
4. **Webhook delivery** — `webhook_delivery_service.py` at 52%: retry/backoff/dead-letter paths not covered.
5. **Document pipeline** — `document_pipeline.py` at 29%: NLP processing paths not tested.
6. **Security service** — `security_service.py` at 54%: session revocation, brute-force protection not tested.

## Recommendations

- Add Celery task tests via `celery.contrib.testing` worker
- Add integration tests for `authorization_service.can()` with all organization roles
- Add quota enforcement tests for tier-limit scenarios
- Target >80% coverage before GA release
