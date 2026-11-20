# Phase 2 — AI Detection Backend

## Objective

Turn the existing local YOLO11n script into a reusable, asynchronous detection backend while
preserving the checkpoint, one-class model behavior, confidence threshold, image size, local command
line workflow, and existing baseline evaluation evidence.

## Architecture

```text
client
  |
  +-- POST /api/v1/uploads ----------------> PostgreSQL upload row
  |                                           |
  |  signed POST request                      v
  +------------------------------------> private S3 quarantine/
  |
  +-- POST /api/v1/uploads/{id}/complete -> Celery job on Redis
                                               |
                                               v
                                      async detection worker
                                      1. download original
                                      2. verify size and SHA-256
                                      3. validate/read image
                                      4. extract EXIF/GPS
                                      5. verify model checksum
                                      6. run YOLO11n
                                      7. upload annotated JPEG
                                      8. persist boxes/status
```

The worker—not the web process—loads and runs the model. A process keeps one verified model instance
and rejects a checkpoint or active database model whose checksum does not match configuration.

## Files added and modified

### Added

- `src/streetguard/detection.py`
- `src/streetguard/images.py`
- `src/streetguard/domain/detections.py`
- `src/streetguard/api/schemas.py`
- `src/streetguard/api/detections.py`
- `src/streetguard/celery_app.py`
- `src/streetguard/workers/detection.py`
- `migrations/versions/3f7bd4c2c0a1_phase_2_model_registry.py`
- `tests/test_images.py`
- `tests/test_detection.py`
- `tests/test_phase2_api.py`

### Modified

- `src/detector/predict.py`: uses the shared detector while retaining terminal output.
- `src/streetguard/storage.py`: private byte download/derived upload.
- `src/streetguard/config.py`: model, limit and Redis settings.
- `src/streetguard/main.py`: upload routes.
- `Dockerfile` and `docker-compose.yml`: API, migration, Redis and Celery worker.
- `.env.example`, `pyproject.toml`, `README.md` and documentation.

The checkpoint and training notebook were not modified.

## Dependency rationale

- **Celery/Redis:** decouples request latency from model and validation work, provides retries and one
  worker task at a time during the first deployment.
- **Pillow:** verifies decodable images and extracts EXIF/GPS using local bytes.
- **Ultralytics/PyTorch:** the existing YOLO11n detector, introduced through the existing `model`
  optional dependency group rather than replaced.

## Configuration

Add the new values from `.env.example`:

```dotenv
REDIS_URL=redis://localhost:6379/0
MAX_IMAGE_UPLOAD_BYTES=20000000
MAX_IMAGE_PIXELS=50000000
DETECTION_CONFIDENCE_THRESHOLD=0.25
DETECTION_IMAGE_SIZE=640
DETECTION_DEVICE=cpu
MODEL_PATH=models/pothole/best.pt
MODEL_CHECKSUM=d4ec8035e55e7db185e82cbfdf97f402264e40024b2d7e6d0e335bce5d321543
```

Production limits must be chosen from measured latency and abuse requirements. The confidence value
remains a model score, not a probability of failure or severity.

## Installation and startup

```powershell
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
docker compose up --build
```

Compose starts PostGIS, a pinned local-only S3-compatible test service, Redis, a one-shot Alembic
migration, the API, and a Celery worker. The trained checkpoint is mounted read-only at
`/models/pothole/best.pt`; it is not copied into the container image. The test service is not for
production and does not provide production encryption at rest.

For browser uploads in Compose, `STORAGE_ENDPOINT_URL` uses the internal `storage` service name and
`STORAGE_PUBLIC_ENDPOINT_URL` uses the browser-reachable `http://localhost:9000`. The bucket/provider
must allow the frontend origin to perform signed `POST` uploads and signed `GET` downloads. In
production, configure the provider's CORS allowlist for the exact app origin; never use `*` with
credentials or expose the original-object bucket publicly.

Start local processes separately when containers are unavailable:

```powershell
alembic upgrade head
redis-server
celery -A streetguard.celery_app:celery_app worker --loglevel=INFO --queues=detection --concurrency=1
uvicorn streetguard.main:app --reload
```

## API workflow

### 1. Request a signed upload

`POST /api/v1/uploads` with `Idempotency-Key` (minimum 16 characters):

```json
{
  "filename": "road.jpg",
  "content_type": "image/jpeg",
  "byte_size": 20480,
  "sha256": "64-character-lowercase-file-hash"
}
```

The response includes a UUID, exact quarantine object key, signed form fields, URL, and expiry. A
duplicate byte size/MIME/hash receives a `duplicate: true` response without a new signed form.

### 2. Upload directly to private object storage

POST every returned `upload_fields` value as multipart form data to `upload_url`, followed by the
file field named by the S3 policy. The signed policy enforces the declared content type and byte
limit. The browser never receives bucket credentials.

### 3. Complete the upload

`POST /api/v1/uploads/{upload_id}/complete`:

```json
{
  "object_key": "quarantine/<upload-id>.jpg"
}
```

Expected response: HTTP 202 and `processing_status: "queued"`.

### 4. Poll status

`GET /api/v1/uploads/{upload_id}` returns:

- Original/scan processing state.
- Dimensions and available capture time.
- Sanitized EXIF summary and GPS object when present.
- Model threshold/image size and processing duration.
- Normalized detection boxes and confidence scores.
- A short-lived annotated download URL after completion.
- Worker error text after failure.

When no EXIF GPS exists, `location_message` is:

> Location information is not available in this photograph. Please select the location manually.

This value does not assign a location. Location confirmation, map pin selection, device permission
and reverse geocoding are deferred to Phase 3.

## Detection response semantics

Boxes are normalized against the original decoded image:

- `x_center` and `y_center`: `[0,1]`.
- `box_width` and `box_height`: `(0,1]`.
- `confidence`: YOLO score in `[0,1]`.

The annotated object is separate from the original. Original EXIF remains private in quarantine;
derived output is generated by Ultralytics and must not be treated as verified road evidence.

## Validation commands

```powershell
ruff check src/streetguard src/detector/predict.py tests migrations
ruff format --check src/streetguard src/detector/predict.py tests migrations
mypy src/streetguard
pytest
alembic upgrade head --sql
```

Real inference:

```powershell
python src/detector/predict.py
```

The refactored command retains the same interactive path prompt, text box output and
`outputs/detections/*_detected.jpg` destination.

## Expected test evidence

- 31 tests pass for Phase 1 and Phase 2.
- Ruff and mypy pass.
- Alembic emits both migration revisions, a single-active-model index and the known model seed.
- The local checkpoint produces one 81.41% detection on the audit sample through the new detector
  service, without writing a persistent service scratch image.
- No API request bypasses the configured 20 MB claim limit.

## Troubleshooting

### Upload completion stays queued

Check `celery -A streetguard.celery_app:celery_app inspect ping`, Redis connectivity, worker logs, and
that the worker subscribes to the `detection` queue.

### `Uploaded file checksum does not match`

The client sent different bytes than the SHA-256 submitted during upload creation. Calculate the hash
over the exact bytes and request a new upload.

### `Declared MIME type ... does not match`

The filename, HTTP content type, or file bytes disagree. Do not rename an extension to bypass
validation.

### Worker rejects the active model

Compare the `MODEL_CHECKSUM` value with:

```powershell
Get-FileHash .\models\pothole\best.pt -Algorithm SHA256
```

The database model seed and worker configuration must match exactly. This is intentional supply-chain
protection.

### No GPS appears

This is valid. The system does not fabricate coordinates. Phase 3 will provide user-selected,
device-authorized, and manually entered location options.

### Celery repeatedly retries

Malformed files, checksum/model mismatches and non-image values are marked failed without retry.
Storage, database, or model runtime failures are retried up to the task limit.

## Phase completion checklist

- [x] Existing CLI behavior preserved through the shared detector.
- [x] Original model and metrics preserved and checksum-pinned.
- [x] Signed, bounded uploads and private object references implemented.
- [x] Image decode, MIME, pixel, byte and hash validation implemented.
- [x] EXIF capture/camera metadata and optional GPS extraction implemented.
- [x] Missing GPS explicitly remains unlocated.
- [x] Structured multi-detection output and annotated object implemented.
- [x] Celery processing state and failure responses implemented.
- [x] Model registry migration, API, tests and runbook implemented.
- [x] Loopback-only PostGIS/local-S3/Redis/API/worker smoke: signed upload, CPU inference, persisted
  completion status, and signed annotated-image download.

Video processing, geocoding, reports, frontend UI, verification, severity and communication are not
part of Phase 2.

## Git commit recommendation

```text
feat: add asynchronous pothole detection backend

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
```
