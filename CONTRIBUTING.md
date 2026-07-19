# Contributing to HealthPredict AI

## Development Setup

1. **Clone and enter the repo:**
   ```bash
   git clone https://github.com/your-username/Healthcare-Risk-Prediction.git
   cd Healthcare-Risk-Prediction
   ```

2. **Create a virtual environment and install dependencies:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r backend/requirements-dev.txt
   ```

3. **Start infrastructure services (PostgreSQL + Redis):**
   ```bash
   make docker-dev
   ```

4. **Apply database migrations:**
   ```bash
   make db-migrate
   ```

5. **Run the development server:**
   ```bash
   make dev
   ```

See `Makefile` for all available commands.

## Branch Naming

Use descriptive prefixes to keep the branch history clean:

- `feat/` — New features (e.g., `feat/api-key-rotation`)
- `fix/` — Bug fixes (e.g., `fix/csrf-cookie-path`)
- `refactor/` — Code restructuring without behavior change
- `docs/` — Documentation only
- `chore/` — Build, CI, or tooling changes
- `test/` — Adding or fixing tests

## Commit Conventions

Follow the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <short summary>
```

Examples:
```
feat(auth): add API key rotation endpoint
fix(predictions): handle empty feature set gracefully
docs(readme): update Docker setup instructions
```

- Keep commits focused on a single change.
- Use the imperative mood ("add" not "added").
- Limit the subject line to 72 characters.

## Pull Request Process

1. Create a feature branch off `main` using the naming convention above.
2. Write or update tests for your changes.
3. Ensure all existing tests pass: `make test`
4. Run linters and formatters: `make lint`
5. If adding new dependencies, add them to `backend/requirements.txt` (prod) or `backend/requirements-dev.txt` (dev).
6. Open a pull request against `main` with a clear description of the change.
7. Ensure CI passes (lint, type-check, security scan, tests, migrations, Docker build).
8. Request review from at least one maintainer.

## Coding Standards

- **Python:** Follow PEP 8. Line length is 79 characters for code, 72 for docstrings.
- **Formatting:** `black` with default settings.
- **Import ordering:** `isort` with the `black` profile.
- **Type hints:** Required for all function signatures. Run `mypy` to verify.
- **Linting:** `flake8` with `E203, W503` ignored.

## Testing Requirements

- All new code must have corresponding tests.
- Unit tests go in `tests/unit/`, integration tests in `tests/integration/`.
- Tests use SQLite by default (no external services needed for unit tests).
- The project coverage threshold is 50% (enforced in CI).
- Run the full suite before pushing: `make test`

## Security

- Never commit secrets, API keys, or passwords.
- Run `make security` (bandit + pip-audit) before opening a PR.
- Report vulnerabilities by opening a [GitHub Security Advisory](https://github.com/your-username/Healthcare-Risk-Prediction/security/advisories).
