# Phase 8 — Testing and Security

## Status and objective

The automated checks, loopback-only service integration, and read-only security review are complete.
One medium-confidence authorization finding was fixed and covered by a regression test. Live
provider integration and production load testing remain pending; the shared preview still has no
configured database service.

This phase validates location accuracy handling, bounded map queries, upload limits, communication
flows, mobile layout, and the administration authorization path without creating synthetic reports or
sending external messages.

## Security review and remediation

The review found that authority creation, update, and verification required a global-administrator
role claim but did not check the matching local account's active state. A signed token could remain
usable for these mutations after its local account was deactivated.

`require_global_administrator` in `src/streetguard/api/communications.py` now resolves the local user
by OIDC subject and denies mutations when that user exists but is inactive. The regression test sends
create, update, and verify requests as an inactive global administrator and expects `403` for all
three. No authority writes are allowed by the test. The guard continues to trust a valid role claim
when no local user row exists, matching the existing identity model.

| # | Severity | Finding | Confidence | Status |
|---|----------|---------|------------|--------|
| 1 | 🟡 MEDIUM | Inactive local global-admin accounts could continue mutating authorities with a still-valid token. | 8/10 | Fixed and regression-tested |

The review was read-only and did not perform active exploitation. Live OIDC revocation behavior was
not tested.

## Acceptance checks

- **Automated tests:** 87 backend tests pass, including the inactive-admin regression.
- **Location accuracy:** `tests/test_locations.py` passes with the full suite.
- **Map:** `tests/test_map_api.py` passes; a browser smoke loaded the India map and 27 OpenFreeMap
  resources. The largest client-observed duration was 19 ms during this local session; this is not a
  production load benchmark.
- **Upload limits:** `tests/test_images.py` passes with the full suite.
- **Email and WhatsApp:** communication tests use a fake SMTP relay, and the three frontend sharing
  tests verify user-controlled email/WhatsApp drafts. No external email or WhatsApp messages were sent.
- **Mobile:** the dashboard was checked at 390 × 844; map and intelligence panel stack vertically with
  no horizontal document overflow.
- **Build and static checks:** Ruff, formatting, mypy, frontend type-check/build, and offline Alembic
  SQL generation pass.
- **Local integration:** fresh PostGIS migrations, API readiness, local S3 signed upload, Celery
  inference, signed result download, and empty-data analytics/map queries pass. The local object
  store is not production storage and this test does not exercise OIDC or external providers.

## Reproduction commands

From the repository root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check src\streetguard tests migrations
.\.venv\Scripts\ruff.exe format --check src\streetguard tests migrations
.\.venv\Scripts\mypy.exe src\streetguard
.\.venv\Scripts\alembic.exe upgrade head --sql

$env:PATH = "$PWD\.venv\node-runtime\node-v26.13.1-win-x64;$env:PATH"
Set-Location apps\web
npm.cmd run lint
npm.cmd run test:sharing
npm.cmd run build
```

Expected results: `87 passed` for the backend suite, `3 passed` for sharing tests, clean Ruff/mypy
output, and successful web build and offline migration SQL generation. The suite emits an existing
Starlette/httpx deprecation warning from the test-client dependency.

## Environment limitations and next validation

The shared preview's report API still returns `503 Map data store is unavailable`; the separate local
Compose stack validates only local PostGIS and the development S3-compatible service. Identity
provider revocation, provider-backed email/WhatsApp delivery, production map performance, and
production storage/database behavior remain unverified. Configure service credentials outside the
repository before production tests. Never commit secrets or send real messages as part of automated
tests.

Suggested commit title: `security: reject inactive authority administrators`.

## Completion checklist

- [x] Full backend and frontend automated checks pass.
- [x] Security review finding is fixed and covered by a regression test.
- [x] Location, map, upload, communications, and mobile checks are recorded.
- [ ] Run live database, OIDC, email/WhatsApp, and production performance smoke tests.
