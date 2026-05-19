# 3. Use DVC for Model and Data Versioning

Date: 2026-03-15

## Status
Accepted

## Context
Machine learning projects suffer from "it works on my machine" syndrome due to unversioned datasets, untracked hyperparameter changes, and implicitly defined pipelines. Git is not suitable for storing large `.csv` datasets or `.pkl` model artifacts.

## Decision
We will use **Data Version Control (DVC)** for data and model tracking, defining our workflow via `ml/dvc.yaml`.

## Consequences
- **Positive:** Clear, trackable, and reproducible DAGs (Directed Acyclic Graphs) for our pipelines (`process_data`, `train_diabetes`, `train_heart`, `train_lung`). Datasets and large `.pkl` forms stay out of Git while their hashes are tracked.
- **Negative:** Requires an external storage backend for DVC remote (S3, GCS, Azure Blob) which introduces infrastructure dependencies.
- **Mitigation:** Setup basic local/remote switching and document `dvc pull` and `dvc repro` in `docs/CONTRIBUTING.md`.
