# Phase 9 — Production Deployment

## Status and deployment model

The repository now has a production deployment scaffold for a single Linux Docker host. It runs the
web frontend, FastAPI, Celery inference worker, one-shot migration job, and Caddy reverse proxy.
PostgreSQL/PostGIS, Redis, S3-compatible storage, OIDC, and SMTP are external services; credentials
and provider endpoints are not committed.

This phase is **not a public production launch**. No hosting provider, domain, production credentials,
or service endpoints were supplied, and the shared preview's report API returns `503`. Provisioning
those resources and passing the live smoke tests are still required before launch.

## Deployment components

| Component | Production configuration |
|---|---|
| Frontend | Next.js standalone image, running as UID 10001 |
| API | Lean FastAPI/Pillow image, running as UID 10001; production docs/OpenAPI disabled |
| Inference | Separate CPU-only PyTorch/Ultralytics Celery image using the verified, read-only model artifact |
| Migrations | One-shot `alembic upgrade head` job that gates API and worker startup |
| Database | External PostgreSQL with PostGIS and encrypted connections |
| Queue | External Redis, configured through a mounted secret |
| Object storage | External private S3-compatible bucket over HTTPS |
| Domains and HTTPS | Caddy reverse proxy for separate app/API domains and automatic certificates |
| Monitoring | API readiness, frontend and worker health checks; container logs capped at 50 MB each |

Only Caddy publishes ports 80 and 443. Set an A record, and an AAAA record only if IPv6 is reachable,
for both domains. The host firewall must allow inbound 80/443 (TCP, and UDP 443 for HTTP/3); do not
open database, Redis, or object-storage ports to the public internet. The deployment is single-host
and is not highly available; use a managed container platform and registry for a multi-instance
rollout.

## Configuration and secret files

1. Copy `.env.production.example` to `.env.production`. Set the real app/API domains, ACME email,
   public API URL, OIDC endpoints, storage endpoint/bucket, CORS origin, model path, and checksum.
   The template's `.example.in` values are placeholders.
2. Create the directory named by `SECRETS_DIR` and create these files inside it:

   | File | Contents |
   |---|---|
   | `database_url` | Full SQLAlchemy URL for PostgreSQL/PostGIS, including TLS, e.g. `postgresql+psycopg://user:password@db.example.in:5432/streetguard?sslmode=require` |
   | `redis_url` | TLS Redis URL, e.g. `rediss://user:password@redis.example.in:6380/0` |
   | `storage_access_key` | S3-compatible access key |
   | `storage_secret_key` | S3-compatible secret key |
   | `google_maps_api_key` | Geocoding provider key; required by the template's strict India scope |
   | `smtp_password` | SMTP password; use an empty file only if SMTP username/host are also unset |

   Pydantic reads these files from `/run/secrets`. The deployment process runs as UID/GID 10001;
   make the files owned by that identity and readable only by it (for example, `chown 10001:10001`
   and `chmod 0400` on Linux). URL-encode reserved characters in database and Redis credentials.
   Keep `.env.production` and the secret directory outside version control. Do not put secret values
   in `.env.production`.
3. Place the trained checkpoint at `MODEL_ARTIFACT_PATH`. Verify that its SHA-256 matches
   `MODEL_CHECKSUM`; the image does not contain model weights.
4. Configure the external database with PostGIS, backups/PITR, and a database/user restricted to
   this application. Configure the storage bucket as private with suitable lifecycle/backup policies,
   server-side encryption, and CORS for the exact web origin. Use
   `STORAGE_PUBLIC_ENDPOINT_URL` only when the browser-facing endpoint differs from the API/worker
   endpoint; presigned URLs are signed for their exact host.
   Ensure the app host can reach the database, Redis, storage, OIDC JWKS, geocoder, map tiles, and
   SMTP provider.

The API and worker are separate images: image-validation libraries stay in the API, while PyTorch and
Ultralytics are installed only in the worker image. The worker currently uses CPU inference
(`DETECTION_DEVICE=cpu`) and one concurrency slot; size the host and queue based on a measured
workload before increasing concurrency.
The local inference smoke only confirms model loading and CPU execution on synthetic input; it is not
an accuracy or throughput benchmark.

## Deploy and operate

From the checked-out release on the Linux host:

```sh
docker compose --env-file .env.production -f docker-compose.production.yml config --quiet
docker compose --env-file .env.production -f docker-compose.production.yml up -d --build
docker compose --env-file .env.production -f docker-compose.production.yml ps
docker compose --env-file .env.production -f docker-compose.production.yml logs --tail=200 migrate api worker frontend proxy
```

The migration job must complete successfully before the API/worker start. The API readiness check
queries the database; it returns unhealthy/503 until the database is reachable. Keep a database
backup before each migration. Treat schema migrations as forward-only unless a reviewed rollback plan
exists.

Run the external smoke checks after DNS, TLS, migrations, and services are ready:

```sh
npm --prefix apps/web run smoke:production -- https://streetguard.example.in https://api.streetguard.example.in
```

The script requires HTTPS and verifies the frontend, HSTS headers, API liveness, and API/database
readiness. It does not create reports, send messages, validate user sign-in, or test real detection
uploads. Run additional authenticated workflow tests in a production-like staging environment before
public launch.

Health endpoints are `/api/v1/health/live` and `/api/v1/health/ready`. Use the Docker health status
and bounded container logs for initial monitoring. Route those signals to an external alerting/log
platform with retention before production; this repository does not provision a monitoring vendor,
metrics backend, or on-call alerts.

## Validation and remaining acceptance

- [x] Compose syntax and required variable/secret wiring validated with placeholder values.
- [x] Frontend standalone production image built successfully.
- [x] Frontend image starts and returns HTTP 200.
- [x] Backend tests, including mounted-secret loading, pass.
- [x] Build and verify the lean API/migration image and CPU-only inference image as non-root.
- [x] Verify containerized offline migrations; production API loads mounted secrets, returns liveness
  200, and disables `/docs`.
- [x] Verify the worker loads the checked model and completes a local CPU inference smoke.
- [x] Run a fresh loopback-only Compose startup: PostGIS migrations completed on first boot, API
  liveness/readiness and frontend returned 200, and the Celery worker returned `pong`.
- [x] Exercise a synthetic JPEG through the SigV4 signed local S3 POST, upload completion, CPU YOLO
  worker, persisted status, and signed annotated-image download. This does not satisfy the
  production-like database/service acceptance item below.
- [ ] Run migrations and API readiness against a provisioned production-like database.
- [ ] Provision and verify the production database, storage, Redis, OIDC, SMTP, DNS, and TLS.
- [ ] Run the HTTPS smoke command and authenticated workflow tests against staging/production.
- [ ] Configure external monitoring, alerting, backups, and release image pinning.

Do not treat the scaffold checks as evidence that a production service is deployed or ready to accept
public traffic.
