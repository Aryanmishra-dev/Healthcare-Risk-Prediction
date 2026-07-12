# CI/CD Architecture

## Workflows
The project uses GitHub Actions for continuous integration and continuous deployment. Workflows are defined in `.github/workflows/`.

### `ci.yml`
This workflow runs on every push and PR to `main` and `develop`.
- **lint-and-format**: Checks code formatting using `black` and `isort`, and lints using `flake8`.
- **type-check**: Ensures static typing correctness using `mypy`.
- **security-scan**: Runs `bandit` to catch common security issues in Python code and `safety` to check for known vulnerabilities in dependencies.
- **test**: Runs the full `pytest` suite (including integration tests) with PostgreSQL and Redis services spun up using GitHub Actions Service Containers. Uploads coverage reports.
- **migrations-check**: Verifies that the Alembic migration history is intact by upgrading to `head` and downgrading back to `base`.
- **docker-build**: Builds the Docker image and ensures that the multi-stage build processes successfully.

## Continuous Deployment
Currently, deployment is triggered manually after the `ci.yml` workflow succeeds and a Release Candidate is tagged. Integration into a CD tool (e.g. ArgoCD) is planned for the Kubernetes cluster.
