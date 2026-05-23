# Contributing to Healthcare Risk Prediction

First off, thank you for considering contributing to Healthcare Risk Prediction. It's people like you that make Healthcare Risk Prediction such a great tool.

## General Guidelines

1. **Bug Reports**: Please use the GitHub issue tracker to report bugs. Ensure that your description is clear and has sufficient instructions to be able to reproduce the issue.
2. **Feature Requests**: We welcome feature requests! Please create an issue with a clear description of the feature and its intended use case.
3. **Pull Requests**:
   - Fork the repository and create your branch from `main`.
   - If you've added code that should be tested, add tests.
   - If you've changed APIs, update the documentation.
   - Ensure the test suite passes.
   - Make sure your code lints.

## Development Setup

1. Clone the repo: `git clone https://github.com/your-username/Healthcare_risk_prediction.git`
2. Install dependencies: `pip install -r backend/requirements-dev.txt`
3. Setup pre-commit hooks (if any): `pre-commit install`
4. Run tests: `pytest`

## Code Style

- We follow standard Python PEP 8 conventions.
- Use `black` for formatting and `flake8` for linting.

## Data & Models

- All model pipelines should be tracked via `dvc`. Do not commit large artifacts or data to the main repo.
- Ensure changes to models are properly versioned, calibrated, and explainable using SHAP.
- The checked-in `ml/dvc.yaml` regenerates deterministic launch stubs. Configure
  a real DVC remote before pulling or publishing production-scale data/model
  artifacts.
- Install DVC with `python -m pip install -r ml/requirements-dvc.txt`; it is
  isolated from the core dev requirements because of an upstream DVC dependency
  with no fixed security release yet.

Thank you for your contributions!
