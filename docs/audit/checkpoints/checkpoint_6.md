# Checkpoint 6 — ML Pipeline

## Audit Scope

- Model loading / warmup / caching (`model_manager.py`, `model_loader.py`)
- Prediction orchestration (`prediction_pipeline.py`)
- SHAP explainability (`shap_explainer.py`)
- Feature extraction / mapping (`feature_mapper.py`)
- Document parsing & NLP (`document_parser.py`, `medical_nlp.py`)
- Startup validation (`dependencies.py` — model checks)
- Model artifacts (`ml/models/`)

## Findings

| Severity | Count | Details |
|---|---|---|
| **Critical** | 0 | — |
| **High** | 0 | ~~All 4 High findings fixed~~ |
| **Medium** | 2 | `PredictionPipeline` dead code (kept for test compat); extra-key splat in dead code |
| **Low** | 1 | `load_models()` dead code (kept for test compat) |

## Additional Fixes

| # | Finding | File(s) | Fix |
|---|---|---|---|
| M8 | MLflow download timeout | `model_manager.py` | Added `_MLFLOW_DOWNLOAD_TIMEOUT` (env `MLFLOW_DOWNLOAD_TIMEOUT`, default 120s); `asyncio.wait_for()` wraps `asyncio.to_thread()` in retry loop |
| — | Dead code markers | `prediction_pipeline.py`, `model_loader.py` | Added docstring noting test-compat purpose |

---

## Fixes Applied

| # | Finding | File(s) | Fix |
|---|---|---|---|
| H1 | Heart encoding undocumented | `model_loader.py` | Added docstring explaining BRFSS `1 - x` inversion convention |
| H2 | NLP absence-as-positive | `medical_nlp.py` | `_extract_regex` returns `None` (not `{"value":"no",...}`) for unmatched bool_flag |
| H3 | No negation detection | `medical_nlp.py` | Added `_is_negated()` with negation prefix patterns; applied to BP, cholesterol, smoking, activity, and all bool_flag extractions |
| H4 | Startup model readiness | `dependencies.py` | `validate_startup_config()` now checks `ml/models/` for all 9 required artifacts; validates `MODEL_SOURCE` env var |
| M5 | SHAP async loading | `main.py` | Changed to `await asyncio.to_thread(load_explainers)` — blockers before yield |
| M6 | Feature mapper keys | `feature_mapper.py` | Added `_translate_to_prediction_params()` + `*_to_params()` helpers; `map_to_all_models` docstring notes convention |
| M7 | Timeout configurable | `model_loader.py` | `PREDICTION_TIMEOUT` reads from `PREDICTION_TIMEOUT_SECONDS` env var (default 5.0s) |
| L12 | macOS memory divide | `model_manager.py` | Fixed double-divide: conditional on Darwin first, else Linux path |
| L13 | Late imports | `document_parser.py` | Moved `fitz`, `pytesseract`, `PIL.Image` to module level |

---

## Summary

The ML pipeline is **structurally sound with clinical safety gaps now closed**:

| Area | Verdict |
|---|---|
| Model loading/warmup | Good — retry logic, graceful degradation, config check |
| Prediction path | Good — 503/504 responses, configurable timeout |
| SHAP explainability | Good — loaded before first request |
| Document parsing | Good — module-level imports, PDF + OCR |
| Clinical NLP | **Negation detection added, no false positive for absent evidence** |
| Startup validation | Model readiness now validated before serving |
| Feature mapper | Translation layer bridges mapper keys → prediction params |

4 High, 4 Medium, 2 Low findings fixed. 2 Medium + 1 Low remain (non-blocking dead code).

**Tests: 663 passed, 4 skipped, coverage 75%.**
