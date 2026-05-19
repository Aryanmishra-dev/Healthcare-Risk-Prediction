#!/usr/bin/env bash
set -euo pipefail

# Replays the production architecture migration from the original layout.
# Run from the repository root.

move() {
  local src="$1"
  local dst="$2"
  if [ -e "$src" ]; then
    mkdir -p "$(dirname "$dst")"
    git mv "$src" "$dst"
  fi
}

mkdir -p \
  backend/app/api/v1/routes backend/app/core backend/app/db backend/app/models \
  backend/app/schemas backend/app/middleware \
  frontend/src/pages frontend/src/assets frontend/src/styles \
  ml/pipelines/training ml/pipelines/evaluation/results ml/pipelines/inference \
  ml/feature_engineering ml/models ml/experiments ml/registry \
  shared/utils config deployment/docker deployment/scripts deployment/ci \
  monitoring/dashboards/provisioning/dashboards monitoring/dashboards/provisioning/datasources \
  data/raw tests/unit/backend tests/unit/ml tests/integration/api tests/e2e/load \
  docs/architecture docs/ml

move app/templates frontend/src/pages/templates
move app/static/dr_ai_avatar_v2.png frontend/src/assets/dr_ai_avatar_v2.png
move app/static/css/style.css frontend/src/styles/style.css
move app/services backend/app/services
move app/utils backend/app/utils
move app/routes/upload.py backend/app/api/v1/routes/upload.py
move app/routes/__init__.py backend/app/api/v1/routes/__init__.py
move app/main.py backend/app/main.py
move app/database.py backend/app/db/session.py
move app/logging_config.py backend/app/core/logging.py
move app/ab_testing.py backend/app/services/ab_testing.py
move app/risk_assistant.py ml/pipelines/inference/risk_assistant.py
move app/__init__.py backend/app/__init__.py

move fastapi_backend/schemas.py backend/app/schemas/prediction.py
move fastapi_backend/model_loader.py backend/app/services/model_loader.py
move fastapi_backend/shap_explainer.py backend/app/services/shap_explainer.py
move fastapi_backend/main.py backend/app/api/legacy_main.py
move fastapi_backend/__init__.py backend/app/api/__init__.py

move feature_store ml/feature_engineering/feature_store
move notebooks/brfss_cleaning.ipynb ml/experiments/brfss_cleaning.ipynb
move notebooks/train_heart_disease_model.py ml/pipelines/training/train_heart_disease_model.py
move notebooks/train_lung_cancer_model.py ml/pipelines/training/train_lung_cancer_model.py
move scripts/retrain.py ml/pipelines/training/train.py
move scripts/calibrate_lung_model.py ml/pipelines/training/calibrate_lung_model.py
move scripts/optuna_optimize.py ml/pipelines/training/optuna_optimize.py
move scripts/fairness_eval.py ml/pipelines/evaluation/fairness_eval.py
move scripts/mlflow_config.py ml/registry/mlflow_config.py
move scripts/model_registry.py ml/registry/model_registry.py
move scripts/upload_models_to_s3.py ml/registry/upload_models_to_s3.py
move evaluate_models.py ml/pipelines/evaluation/evaluate.py
move models/model_registry.json ml/registry/model_registry.json
move models/.gitkeep ml/models/.gitkeep
move results/.gitkeep ml/pipelines/evaluation/results/.gitkeep
move utils/__init__.py shared/utils/__init__.py
move utils/feature_engineering.py shared/utils/feature_engineering.py

move docs/adr docs/architecture/adr
move docs/model_cards docs/ml/model_cards
move CONTRIBUTING.md docs/CONTRIBUTING.md
move docker-compose.yml deployment/docker/docker-compose.yml
move Dockerfile backend/Dockerfile.backend
move deploy.sh deployment/scripts/deploy.sh
move start.sh deployment/scripts/start.sh
move .github deployment/ci/.github
move kubernetes deployment/kubernetes
move infrastructure deployment/infrastructure
move nginx deployment/nginx
move .env.example config/.env.example
move requirements.txt backend/requirements.txt
move requirements-dev.txt backend/requirements-dev.txt
move dvc.yaml ml/dvc.yaml

move monitoring/prometheus.yml monitoring/metrics/prometheus.yml
move monitoring/grafana_dashboard.json monitoring/dashboards/grafana_dashboard.json
move monitoring/grafana/provisioning/dashboards/dashboard.yml monitoring/dashboards/provisioning/dashboards/dashboard.yml
move monitoring/grafana/provisioning/datasources/prometheus.yml monitoring/dashboards/provisioning/datasources/prometheus.yml

move data/.gitkeep data/raw/.gitkeep
move tests/test_ab_testing.py tests/unit/backend/test_ab_testing.py
move tests/test_rate_limiter.py tests/unit/backend/test_rate_limiter.py
move tests/test_document_pipeline.py tests/unit/backend/test_document_pipeline.py
move tests/test_feature_engineering.py tests/unit/ml/test_feature_engineering.py
move tests/test_model_predictions.py tests/unit/ml/test_model_predictions.py
move tests/test_api.py tests/integration/api/test_api.py
move tests/test_api_endpoints.py tests/integration/api/test_api_endpoints.py
move tests/test_api_integration.py tests/integration/api/test_api_integration.py
move tests/test_infrastructure.py tests/integration/api/test_infrastructure.py
move tests/load/locustfile.py tests/e2e/load/locustfile.py

mkdir -p \
  backend/app/services backend/app/utils \
  frontend/public frontend/src/components/common frontend/src/components/layout \
  frontend/src/components/features frontend/src/hooks frontend/src/services \
  frontend/src/store frontend/src/utils \
  ml/feature_engineering/transformers ml/preprocessing \
  shared/constants shared/types \
  config data/interim data/processed data/external data/schemas \
  tests/unit/shared tests/integration/db tests/fixtures \
  docs/api docs/runbooks monitoring/alerts monitoring/logging

for package_dir in \
  backend backend/app backend/app/api backend/app/api/v1 backend/app/api/v1/routes \
  backend/app/core backend/app/db backend/app/models backend/app/schemas \
  backend/app/services backend/app/utils config ml ml/experiments ml/feature_engineering \
  ml/feature_engineering/feature_store ml/feature_engineering/transformers ml/models \
  ml/pipelines ml/pipelines/training ml/pipelines/evaluation \
  ml/pipelines/evaluation/results ml/pipelines/inference ml/preprocessing ml/registry \
  shared shared/constants shared/types shared/utils tests tests/unit tests/unit/backend \
  tests/unit/ml tests/unit/shared tests/integration tests/integration/api \
  tests/integration/db tests/e2e tests/e2e/load tests/fixtures
do
  mkdir -p "$package_dir"
  touch "$package_dir/__init__.py"
done

touch \
  frontend/public/.gitkeep \
  frontend/src/components/common/.gitkeep \
  frontend/src/components/layout/.gitkeep \
  frontend/src/components/features/.gitkeep \
  frontend/src/hooks/.gitkeep \
  frontend/src/services/.gitkeep \
  frontend/src/store/.gitkeep \
  frontend/src/utils/.gitkeep \
  data/interim/.gitkeep data/processed/.gitkeep data/external/.gitkeep data/schemas/.gitkeep \
  docs/api/.gitkeep docs/runbooks/.gitkeep monitoring/alerts/.gitkeep monitoring/logging/.gitkeep
