# Project Documentation

This directory documents the India-first StreetGuard product, its architecture, and implemented
backend and dashboard phases. The root [README](../README.md) contains the project overview,
development roadmap, setup summary, and model baseline.

## Product and architecture

- [India-first scope](india-first-scope.md): product boundaries, rollout assumptions, and authority
  routing policy.
- [System architecture](architecture.md): service boundaries and data flow.

## Implementation runbooks

- [Phase 1 — Foundation](phase-1-foundation.md): API, PostgreSQL/PostGIS, RBAC, storage, migrations,
  and quality checks.
- [Phase 2 — Detection backend](phase-2-detection-backend.md): uploads, validation, asynchronous
  YOLO processing, and persisted results.
- [Phase 3 — India map](phase-3-india-map.md): geography, geocoding, location confirmation, map APIs,
  and dashboard behavior.
- [Phase 4 — Reporting](phase-4-reporting.md): report workflow, verification, privacy, public
  tracking, severity, duplicates, and aggregate analytics.
- [Phase 5 — Communications](phase-5-communications.md): verified authority directory, consent,
  SMTP relay integration, delivery logs, and rollout checks.
- [Phase 6 — Dashboard and analytics](phase-6-analytics.md): India state/city breakdowns, severity,
  trends, authority assignment closure, and data-quality constraints.
- [Phase 7 — Administration and authority operations](phase-7-administration.md): report assignment,
  authority memberships, permissions, audit logs, resolution workflow, and rollout constraints.
- [Phase 8 — Testing and security](phase-8-testing-security.md): automated checks, security review,
  location/map/upload/mobile tests, and live-integration limits.
- [Phase 9 — Production deployment](phase-9-production-deployment.md): production container images,
  external managed services, secret files, HTTPS, health checks, and rollout/smoke-test steps.

## Current status

Phases 1–9 have implementation, automated checks, and loopback-only local integration evidence; no
public production deployment has been performed. A fresh local Compose stack applied migrations,
passed API/web/worker health checks, completed a SigV4 signed upload and CPU inference workflow, and
returned signed annotated output; local PostGIS analytics and map queries also passed with an empty
dataset. Production PostgreSQL/PostGIS, Redis, object storage, OIDC, geocoding, map-tile, SMTP,
monitoring, DNS, and TLS still require environment-specific configuration and staging acceptance.
Portal sign-in currently uses short-lived access tokens entered into memory-only forms; regional
administrator scopes are not configured. The authority directory stays empty until evidence-reviewed
records are configured. State and city analytics rely on available reverse-geocoded labels;
first-response timestamps are not yet captured. The shared web preview has no database service, so
public report requests there still return 503. See the root README for remaining rollout work.

## Documentation guidelines

- Keep instructions consistent with source code and tested commands.
- Distinguish implemented behavior from planned work and live-service validation.
- Do not document unverified authorities, jurisdictions, or production-provider configuration as
  available.
- Never include credentials or private information.
