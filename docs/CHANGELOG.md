# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- HTMX frontend for Diabetes, Heart Disease, and Lung Cancer risk models.
- SHAP-based explainability integration.
- DVC pipeline for reproducibility of `train_diabetes`, `train_heart`, and `train_lung`.
- Docker and Docker Compose setup.
- Prometheus and Grafana for monitoring and observability.
- CSRF Token protection for HTMX endpoints.
- Basic Terraform placeholders in `deployment/infrastructure/` for ECS deployment.
- Initial Architecture Decision Records (ADRs) and Model Cards.

### Fixed
- DVC pipeline execution for `.ipynb` files.
- Forms logic for missing/invalid input.

### Security
- Added `X-API-Key` authentication for backend APIs.
- Integrated rate limiting using Redis.
