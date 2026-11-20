# StreetGuard Application Architecture

## Phase 1 architecture decision

StreetGuard uses a modular monolith until measured scale requires service decomposition:

```text
Next.js client (future)
        |
        v
FastAPI application
        |
        +--> PostgreSQL + PostGIS
        +--> S3-compatible private storage
        +--> Redis/Celery AI worker (Phase 2)
        +--> OIDC identity provider
```

The existing `src/detector/predict.py` and model checkpoint remain unchanged in Phase 1. Phase 2 will
extract reusable inference behavior from the script while preserving YOLO11n and its configuration.

## Boundaries

- `src/streetguard/main.py`: FastAPI construction and lifecycle.
- `src/streetguard/config.py`: validated, environment-driven configuration.
- `src/streetguard/security/`: framework-independent role/permission and principal contracts.
- `src/streetguard/domain/`: workflow invariants independent of HTTP and persistence.
- `src/streetguard/models/`: SQLAlchemy and GeoAlchemy2 persistence model.
- `src/streetguard/storage.py`: provider-neutral private object-storage operations.
- `migrations/`: immutable PostgreSQL/PostGIS migration history.
- `tests/`: fast tests for security, workflow, schema, configuration and infrastructure adapters.

## Database policy

PostgreSQL is the source of truth for reports and their geospatial references. PostGIS stores points
as `geography(Point, 4326)` and imported boundaries as `geometry(MultiPolygon, 4326)`. GiST indexes
support viewport and proximity queries. Uploaded binaries remain in private object storage; database
records contain object keys and metadata only.

Report status transitions are append-only auditable events. AI processing can only move a submitted
report toward `awaiting_verification`; an AI result cannot verify, repair, or resolve road damage.

## Identity policy

The application consumes OIDC identity claims rather than storing passwords. Phase 1 defines roles,
permissions, and a principal contract. Token verification middleware and user provisioning belong to
Phase 2; production configuration must use HTTPS OIDC endpoints and cannot use local development
credentials.

## Storage policy

Original uploads are private. Signed URLs are short-lived and content-length bounded. Public output
must use separate derived objects with EXIF and other sensitive metadata removed. The storage adapter
does not claim that a signed URL grants or records delivery; every access remains auditable at the
application layer.

## Scaling policy

Phase 1 deliberately avoids premature microservices. When the upload feature arrives, FastAPI will
enqueue work and a separate Celery process will run YOLO inference. The map API will later issue
bounded PostGIS viewport queries and server-side clustering instead of sending the complete report set
to a browser.
