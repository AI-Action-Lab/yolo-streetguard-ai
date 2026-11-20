# Phase 1 — Architecture and Database Foundation

## Objective

Create the deployable, typed and testable backend foundation without changing the trained model,
dataset, or existing inference behavior.

## Architecture delivered

- FastAPI application and OpenAPI metadata.
- Environment-validated Pydantic settings.
- Structured JSON logging outside local development.
- Async SQLAlchemy connection lifecycle.
- PostgreSQL/PostGIS ORM model and immutable initial migration.
- Roles and permissions seeded for all six planned platform roles.
- Domain-level report status transition guard.
- Short-lived, content-length-bounded S3 signed URL adapter.
- Private local S3-compatible storage and PostGIS Docker Compose services.
- Ruff, mypy, pytest and GitHub Actions checks.

## Important paths

### Created

- `pyproject.toml`
- `requirements.txt`
- `requirements-dev.txt`
- `.env.example`
- `Dockerfile`
- `docker-compose.yml`
- `.github/workflows/phase1-ci.yml`
- `src/streetguard/`
- `migrations/`
- `tests/test_*.py`
- `docs/architecture.md`

### Modified

- `README.md`
- `docs/README.md`
- `requirments.txt` (compatibility pointer)

No existing detector, dataset conversion, validation, model, or notebook file was changed.

## Dependencies

Application dependencies are declared in `pyproject.toml`:

- FastAPI/Pydantic Settings for the API and configuration.
- SQLAlchemy/psycopg/GeoAlchemy2 for PostgreSQL and PostGIS.
- Alembic for migrations.
- boto3 for S3-compatible storage.
- structlog for structured logs.
- pytest, Ruff, mypy and coverage tooling for development.

The `model` optional dependency group preserves Pillow, PyYAML and Ultralytics requirements for the
existing detector and dataset tooling. Exact model inference metrics remain tied to the current
Ultralytics 8.4.189 training evidence.

## Local installation

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

Do not commit `.env`. The local values are development-only; production configuration must use a
remote database, unique object-storage credentials, TLS, and HTTPS OIDC endpoints.

## Database and storage startup

```powershell
docker compose up -d database storage
alembic upgrade head
```

The migration enables `postgis` and `pgcrypto`, creates the core relational/geospatial schema and
indexes, and seeds roles, permissions and grants. The local S3-compatible service creates its
private bucket on startup. Verify migration SQL without a database:

```powershell
alembic upgrade head --sql
```

Expected result: SQL contains `CREATE EXTENSION IF NOT EXISTS postgis`, report tables, GiST indexes,
and deterministic RBAC inserts.

## Run the API

```powershell
uvicorn streetguard.main:app --reload
```

Expected endpoints:

- `GET http://localhost:8000/api/v1/health/live` returns `{"status":"ok"}`.
- `GET http://localhost:8000/api/v1/health/ready` returns `{"status":"ready"}` only after PostgreSQL
  accepts a query; otherwise it returns HTTP 503.
- `GET http://localhost:8000/docs` exposes OpenAPI in development/test only.

Alternatively:

```powershell
docker compose up --build
```

## Quality commands

```powershell
ruff check src/streetguard tests migrations
ruff format --check src/streetguard tests migrations
mypy src/streetguard
pytest
alembic upgrade head --sql
```

Expected unit result: 17 focused Phase 1 tests passing. A live migration apply and service smoke test
also require Docker or externally provisioned PostgreSQL/PostGIS and S3-compatible storage.

## Completion checklist

- [x] Clean FastAPI process starts without loading the YOLO checkpoint.
- [x] Existing project/model code remains unchanged.
- [x] Configuration has a `.env.example` and production validation.
- [x] Core report, image, detection, location, authority, audit and delivery entities exist.
- [x] Spatial columns and GiST indexes exist for locations/boundaries.
- [x] Roles/permissions are seeded in the migration.
- [x] Illegal report transitions are blocked by domain rules.
- [x] Signed uploads are bounded and private downloads are short-lived.
- [x] Migrations compile to PostgreSQL SQL.
- [x] Lint, formatting, type checks and unit tests run from one documented command set.
- [x] CI executes those checks for pushes and pull requests.
- [x] Docker-enabled local migration and API readiness smoke test.

## Troubleshooting

### API readiness is 503

Confirm `DATABASE_URL`, the PostGIS container, `alembic upgrade head`, and database network/DNS. Do
not treat a working liveness endpoint as database readiness.

### `psycopg` or `greenlet` import failure

Reinstall from metadata:

```powershell
python -m pip install -e ".[dev,model]"
```

### PostGIS type creation fails

Use a PostgreSQL image/provider with PostGIS enabled. The first migration must run with permission to
enable the `postgis` extension.

### Local S3 signed uploads fail

`STORAGE_ENDPOINT_URL` is the Compose-only service address; `STORAGE_PUBLIC_ENDPOINT_URL` is the
browser-reachable address used in signed URLs. The local bucket is private and created by the
development S3 service. Production must use a managed S3-compatible provider with private access,
HTTPS, and server-side encryption.

### Import errors when launching Uvicorn

Install the package rather than manipulating `PYTHONPATH` manually:

```powershell
python -m pip install -e .
```

### Production refuses to start

This is intentional when localhost database addresses, development object-storage credentials,
disabled storage TLS, or HTTP OIDC endpoints are supplied with `APP_ENV=production`.

## Git commit recommendation

Commit Phase 1 as one cohesive, reviewable change, for example:

```text
feat: establish application and geospatial foundation

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
```
