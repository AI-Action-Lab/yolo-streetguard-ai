# YOLO StreetGuard AI 🚧

### India-First AI Pothole Detection and Road Safety Platform

YOLO StreetGuard AI is a computer vision project designed to detect potholes in road images using a custom-trained YOLO object detection model.

The current product goal is an India-first road monitoring platform that combines pothole detection
with location tracking, reporting, and interactive analytics. The implementation keeps reusable
data-layer primitives country-neutral internally, but the visible scope, workflows, and launch
decisions are for India.

> **Current status:** The existing YOLO11n model remains functional. Phases 1–9 provide a typed
> FastAPI foundation, AI processing, an India map and reporting workflow, communications, analytics,
> administrator/authority operations, and a production deployment scaffold. A public production
> launch still requires a provider, domain, secrets, and service-enabled smoke testing. The product is
> configured for India and does not present a worldwide launch.

---

## 📌 Table of Contents

- [Project Overview](#-project-overview)
- [Problem Statement](#-problem-statement)
- [Project Objectives](#-project-objectives)
- [Current Features](#-current-features)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure)
- [Dataset and Preparation](#-dataset-and-preparation)
- [Model Training and Evaluation](#-model-training-and-evaluation)
- [Installation](#-installation)
- [Running Pothole Detection](#-running-pothole-detection)
- [Output](#-output)
- [Development Roadmap](#-development-roadmap)
- [Limitations](#-limitations)
- [Contributing](#-contributing)
- [License and Dataset Attribution](#-license-and-dataset-attribution)

---

## 📖 Project Overview

Potholes can damage vehicles, create traffic hazards, and increase the risk of road accidents.

Traditional road inspection often depends on manual observation and reporting. Computer vision provides an opportunity to automate part of this process by identifying potential potholes from images.

YOLO StreetGuard AI uses a custom-trained YOLO model to locate potholes in road images and generate annotated images containing bounding boxes and confidence scores.

The India-first platform builds on this detection pipeline with confirmed locations, report review and
tracking, and an interactive map.

### Intended workflow

1. Provide an image containing a road.
2. Run the trained YOLO model.
3. Identify potential potholes.
4. Display bounding boxes and confidence scores.
5. Save the annotated image.
6. Optionally confirm a location and create a report for human review.
7. Publish reports to the India map only after human verification.

---

## 🎯 Problem Statement

Road damage can be difficult to monitor consistently across large road networks. Manual inspections can require substantial time and resources, while reports from road users may lack precise location information or supporting evidence.

This project explores how AI-based object detection can help identify potholes from images and provide a foundation for a more structured road monitoring and maintenance workflow.

The model's predictions are intended to assist inspection. They do not replace professional road assessments or establish the actual severity of road damage.

---

## 🚀 Project Objectives

- Develop a custom-trained YOLO model for pothole detection.
- Convert annotated road images into YOLO-compatible training labels.
- Validate dataset structure and annotation integrity.
- Train and evaluate the model using Google Colab with GPU acceleration.
- Run trained-model inference locally on Windows.
- Generate annotated images with detection confidence scores.
- Provide a transparent visual severity indicator and evaluate it against ground truth.
- Associate reports with explicitly confirmed, provenance-bearing locations.
- Support report creation, human verification, and public status tracking.
- Provide an India-focused map for reviewing verified road reports.

---

## ✨ Current Features

### Implemented

- Pothole dataset preparation.
- Pascal VOC XML to YOLO annotation conversion.
- Training, validation, and test dataset organization.
- Dataset integrity validation.
- YOLO model training in Google Colab.
- Evaluation using precision, recall, and mean average precision.
- Reusable YOLO11n inference with upload validation, EXIF extraction, and annotated outputs.
- Asynchronous image processing with model checksum verification and persisted results.
- India-scoped map, state/UT filters, location confirmation, and bounded PostGIS map queries.
- OIDC/RBAC report creation, human verification, status history, and duplicate review.
- Public report tracking with privacy-filtered data and annotated-image links.
- User-initiated WhatsApp and email draft links containing only a public report ID and link.
- India dashboard analytics for public, human-verified reports, severity, monthly trends, available
  state/city labels, and authority assignment closure.
- Global-admin report assignment, authority membership management, bounded audit-log access, and
  member-scoped authority report resolution workflows.
- Backend tests, frontend type checking/build, and database migration tooling.

### Remaining work

- Validate severity indicators against representative, labeled road data.
- Configure and smoke-test production-like database, storage, worker, OIDC, geocoding, map-tile,
  and SMTP providers.
- Integrate portal sign-in with the OIDC client; the current operations portals accept a short-lived
  access token in memory only.
- Add evidence-reviewed India authority/jurisdiction data before operational routing.
- Configure transactional email delivery and notifications; current email and WhatsApp actions only open user-controlled drafts.
- Validate geocoded state/city labels before using their breakdowns for operational decisions;
  first-response timestamps are not yet captured.
- Provision the Phase 9 production host and managed services, configure real secrets/domains, and run
  the production smoke checks before accepting traffic.

---

## 🛠 Technology Stack

| Technology | Purpose |
|---|---|
| Python | Primary programming language |
| Ultralytics YOLO | Object detection and model training |
| PyTorch | Deep learning framework |
| OpenCV | Computer vision and image processing |
| Google Colab | Cloud-based model training |
| CUDA-enabled GPU | Accelerated training in Colab |
| FastAPI | Versioned application API |
| PostgreSQL + PostGIS | Relational and geospatial data |
| SQLAlchemy + Alembic | Models and database migrations |
| Redis + Celery | Asynchronous AI processing |
| S3-compatible storage | Private original and derived images |
| Next.js, React, TypeScript | Web dashboard and report tracking |
| MapLibre GL JS | India map rendering |
| Google Geocoding API | Optional server-side address search and reverse geocoding |
| OIDC provider | User authentication and role claims |
| VS Code | Local development |
| Anaconda | Python environment management |
| Git and GitHub | Version control and project collaboration |

Production provider configuration and live infrastructure validation remain outstanding.

---

## 📁 Project Structure

```text
yolo-streetguard-ai/
│
├── configs/                    # Project and model configurations
├── apps/
│   └── web/                    # Next.js and MapLibre India dashboard
├── migrations/                 # Alembic PostgreSQL/PostGIS migrations
├── .github/workflows/          # Phase 1 quality automation
│
├── data/
│   ├── raw/                    # Original dataset and annotations
│   └── processed/
│       └── potholes/           # YOLO-formatted dataset
│           ├── images/
│           │   ├── train/
│           │   ├── val/
│           │   └── test/
│           ├── labels/
│           │   ├── train/
│           │   ├── val/
│           │   └── test/
│           └── data.yaml
│
├── models/
│   └── pothole/
│       └── best.pt             # Trained model checkpoint
│
├── notebooks/
│   └── YOLO_StreetGuard_Training.ipynb
│
├── outputs/
│   └── detections/             # Locally generated predictions
│
├── src/
│   ├── streetguard/            # FastAPI, database, RBAC, and storage foundation
│   ├── data_processing/        # Dataset conversion and validation
│   ├── detector/               # Pothole inference
│   ├── severity/               # Legacy placeholder; platform v1 is in streetguard/domain/
│   ├── location/               # Legacy placeholder; platform APIs are in streetguard/api/
│   ├── reporting/              # Legacy placeholder; platform workflow is in streetguard/
│   ├── database/               # Legacy placeholder; models are in streetguard/models/
│   └── analytics/              # Aggregate India analytics API
│
├── pages/                      # Legacy placeholder; the dashboard is in apps/web/
├── tests/                      # Automated tests
├── docs/                       # Additional documentation
├── .gitignore
└── README.md
```

Platform functionality lives in `src/streetguard/` and `apps/web/`; older top-level module folders
remain placeholders for now.

---

## 🗂 Dataset and Preparation

The project uses an annotated pothole dataset sourced from Kaggle.

The original annotations use Pascal VOC XML format. A preprocessing script converts valid bounding boxes into normalized YOLO format.

### Dataset source

[Annotated Potholes Dataset — Kaggle](https://www.kaggle.com/datasets/chitholian/annotated-potholes-dataset)

Review the original dataset's license and redistribution conditions before sharing the dataset or its images.

### Processed dataset summary

| Split | Images | Bounding boxes |
|---|---:|---:|
| Training | 479 | 1,310 |
| Validation | 52 | 128 |
| Testing | 133 | 299 |
| **Total** | **664** | **1,737** |

One invalid source annotation was excluded because its bounding box had zero width.

The processed dataset was checked for structural and label-format issues. The validation script reported zero issues.

### Dataset configuration

The YOLO dataset configuration defines:

- Training images.
- Validation images.
- Test images.
- One object class: `pothole`.

The raw dataset is kept separate from generated files. Dataset files should not be committed to GitHub unless their licensing, size, and redistribution permissions have been checked.

---

## 🧠 Model Training and Evaluation

The initial model was trained using Ultralytics YOLO11n in Google Colab with a Tesla T4 GPU.

### Training configuration

| Parameter | Value |
|---|---|
| Model | YOLO11n |
| Training epochs | 30 |
| Image size | 640 pixels |
| Batch size | 8 |
| Training environment | Google Colab |
| GPU | NVIDIA Tesla T4 |
| Detection class | Pothole |

### Initial test-set results

| Metric | Result |
|---|---:|
| Precision | 78.70% |
| Recall | 65.22% |
| mAP@50 | 76.93% |
| mAP@50–95 | 49.59% |

These results are the baseline evaluation from the current experiment.

**Metric interpretation:**

- **Precision:** Measures how many predicted detections were correct under the evaluation criteria.
- **Recall:** Measures how many annotated potholes the model successfully detected.
- **mAP@50:** Measures detection performance at an intersection-over-union threshold of 0.50.
- **mAP@50–95:** Evaluates detection performance across multiple intersection-over-union thresholds.

Performance may vary on unfamiliar images, including roads with different lighting, weather, surface textures, and camera angles.

The test results should not be treated as a guarantee of real-world performance.

---

## 💻 Installation

### Prerequisites

- Windows, macOS, or Linux.
- Python environment with compatible dependencies.
- Git.
- A local copy of this repository.
- The trained model checkpoint, `best.pt`.

The current local development environment uses Windows and an Anaconda environment named `streetguard`.

### 1. Clone the repository

```bash
git clone https://github.com/AI-Action-Lab/yolo-streetguard-ai.git
cd yolo-streetguard-ai
```

### 2. Install dependencies

Install the existing detector and application dependencies from the project metadata:

```bash
pip install -r requirements-dev.txt
```

For an application/model runtime without development tools:

```bash
pip install -r requirements.txt
```

The project metadata is the source of truth. The historical `requirments.txt` filename is retained
only as a compatibility pointer. The model has been tested with Ultralytics 8.4.189.

### 3. Add the trained model

Place the trained checkpoint at:

```text
models/pothole/best.pt
```

The checkpoint is not necessarily included in the GitHub repository. Obtain it from the project's training artifacts or the authorized model-storage location.

---

## 🔍 Running Pothole Detection

The current inference script is:

```text
src/detector/predict.py
```

It loads the trained model, runs inference on a user-provided image, prints the detected bounding boxes and confidence scores, and saves the annotated image.

### Run the script

From the repository root, run:

```bash
python src/detector/predict.py
```

If you are using a specific Python environment, invoke the Python executable from that environment.

When prompted, enter the full path to an image:

```text
Enter the full path to a road image:
```

For example:

```text
C:\Images\road_test.jpg
```

The current script uses:

- Confidence threshold: `0.25`
- Inference image size: `640`
- Device: CPU

### Output location

The annotated image is saved in:

```text
outputs/detections/
```

The output filename is based on the input image name and ends with `_detected.jpg`.

---

## 📊 Output

The inference script reports:

- Input image name.
- Number of detected potholes.
- Confidence threshold.
- Confidence score for each detection.
- Bounding-box coordinates.
- Output image location.

Detection confidence is a model score, not a calibrated probability that a pothole exists.

Predictions should be reviewed visually, particularly when the model is applied to images outside the training distribution.

---

## 🗺 Development Roadmap

### Phase 1 — Dataset Preparation
**Status: Completed**

- [x] Organize the source dataset.
- [x] Convert Pascal VOC annotations to YOLO format.
- [x] Prepare training, validation, and test splits.
- [x] Validate the processed dataset.

### Phase 2 — Model Training
**Status: Completed — Initial Baseline**

- [x] Train YOLO11n in Google Colab.
- [x] Evaluate the trained model.
- [x] Download the trained checkpoint.
- [x] Verify local model loading.

### Phase 3 — Local Detection
**Status: Completed — Initial Implementation**

- [x] Implement local inference.
- [x] Generate bounding boxes.
- [x] Print confidence scores.
- [x] Save annotated images.
- [ ] Conduct broader real-world error analysis.
- [ ] Evaluate duplicate detections and missed potholes.

### Phase 1 platform foundation
**Status: Implemented — pending deployment smoke test**

- [x] Add reproducible Python project metadata.
- [x] Add FastAPI health endpoints and typed configuration.
- [x] Define PostgreSQL/PostGIS entities and GiST indexes.
- [x] Add an Alembic schema and RBAC seed migration.
- [x] Define report state-transition and role-permission rules.
- [x] Add private S3-compatible signed URL abstraction.
- [x] Add Docker Compose services for PostGIS and a local-only S3-compatible store.
- [x] Add Ruff, mypy, pytest, and GitHub Actions quality checks.
- [x] Apply local PostGIS migrations and verify API readiness in Docker Compose.

See [the Phase 1 runbook](docs/phase-1-foundation.md) for installation, configuration, commands,
expected outputs, troubleshooting, and the phase acceptance checklist.

### Phase 2 — AI detection backend
**Status: Implemented — loopback-only end-to-end container smoke verified; external provider checks pending**

- [x] Extract the YOLO11n detector into a reusable, checksum-verified service.
- [x] Preserve the existing command-line detection workflow.
- [x] Add content-length-bounded private signed uploads.
- [x] Validate MIME type, readability, byte size, pixel count, and SHA-256.
- [x] Extract available EXIF capture, camera, and GPS metadata without inventing locations.
- [x] Add Redis/Celery asynchronous processing and persisted processing state.
- [x] Persist structured detections and a separate annotated image.
- [x] Expose upload, completion, and status OpenAPI endpoints.
- [x] Register and seed the current YOLO11n checkpoint in the model registry.
- [x] Exercise the API/worker/PostGIS/local-S3/Redis flow with signed upload, inference, and download.

See [the Phase 2 runbook](docs/phase-2-detection-backend.md) for the complete API sequence,
configuration, expected responses, commands, troubleshooting, and checklist.

### Phase 3 — India map and location intelligence
**Status: Implemented — local PostGIS map smoke verified; live geocoding and tile-provider checks pending**

- [x] Add an India-only country scope with all 28 states and 8 union territories.
- [x] Add server-side Google geocoding and reverse-geocoding adapter.
- [x] Add explicit location pin/device/manual confirmation with provenance.
- [x] Add bounded PostGIS marker and grid-cluster GeoJSON APIs.
- [x] Distinguish awaiting-review, verified, critical, resolved, duplicate, and rejected markers.
- [x] Build a responsive map-first Next.js/MapLibre dashboard.
- [x] Connect India search, state/UT filters, layer controls, heatmap, fullscreen and location flows.
- [x] Connect the Phase 2 signed upload and detection workflow from the browser.
- [x] Add Next.js type checking and production build to CI.
- [x] Run local PostGIS-backed analytics, marker, and cluster requests against the migrated schema.
- [ ] Configure production geocoding/map-tile providers and run provider-backed smoke tests.

See [the Phase 3 runbook](docs/phase-3-india-map.md).

### Phase 4 — Reports, verification and tracking
**Status: Implemented — OIDC/provider/database integration smoke test pending**

- [x] Verify OIDC bearer tokens and enforce report RBAC permissions.
- [x] Create scalable unique public IDs from completed upload and confirmed location records.
- [x] Persist transparent visual severity v1 independently of confidence.
- [x] Add draft, submit, AI-processing and awaiting-verification audit transitions.
- [x] Require verified-reviewer action for verification, rejection and duplicate status.
- [x] Find nearby open-report duplicate candidates without automatic deletion.
- [x] Support reviewer link/dismiss decisions and human severity override.
- [x] Publish only human-verified reports to the public map and tracking API.
- [x] Expose privacy-safe public status history and annotated image URLs.
- [x] Add responsive public report tracking pages.
- [ ] Exercise OIDC, PostGIS duplicate queries and public tracking against live services.

See [the Phase 4 runbook](docs/phase-4-reporting.md).

### Phase 5 — Communications and authority directory
**Status: Implemented — authority data and live SMTP delivery pending**

- [x] Add an India-focused public directory that displays only active, verified authorities.
- [x] Restrict authority creation, changes, and evidence-backed verification to global administrators; audit each change.
- [x] Add owner-only, explicitly confirmed email sharing for public, human-verified reports with rate limiting and delivery logs.
- [x] Add consent-based in-app status notifications and optional email after identity email verification.
- [x] Send via configurable SMTP and record relay acceptance/failure without claiming final recipient delivery.
- [ ] Configure and smoke-test the production SMTP relay and database-backed delivery paths.
- [ ] Add evidence-reviewed authority and jurisdiction records; no agency contacts are pre-populated.

See [the Phase 5 runbook](docs/phase-5-communications.md).

### Phase 6 — Dashboard and analytics
**Status: Implemented — local database smoke verified; reviewed data quality and production validation pending**

- [x] Extend the India summary with state/UT and top-city counts from available reverse-geocoded labels.
- [x] Show severity distribution and six-month report submission trends.
- [x] Add public, verified-report authority assignment and closure aggregates.
- [x] Keep missing geography labels visible as unclassified instead of guessing locations.
- [x] Label assignment-to-completion as closure time; first-response timestamps are not yet recorded.
- [x] Exercise empty India-scoped analytics results against the local PostGIS database.
- [ ] Validate state/city labels and authority assignment data against a live, reviewed dataset.

See [the Phase 6 runbook](docs/phase-6-analytics.md).

### Phase 7 — Administration and authority operations
**Status: Implemented — migrations run locally; regional scoping, OIDC sign-in, and reviewed workflow validation pending**

- [x] Add a global-admin assignment queue for public, human-verified reports and active verified authorities.
- [x] Add authority membership management without granting identity-provider roles.
- [x] Restrict authority report access to active memberships and support ordered in-progress/resolved updates.
- [x] Record report assignments, membership changes, authority status changes, and report status history.
- [x] Add bounded global-admin audit-log access and dashboard links to both operations portals.
- [ ] Configure regional administrator scopes and integrate the portals with the deployed OIDC sign-in.
- [x] Apply the authority-membership migration during fresh local PostGIS startup.
- [ ] Exercise assignment/resolution with OIDC and evidence-reviewed authority records.

See [the Phase 7 runbook](docs/phase-7-administration.md).

### Phase 8 — Testing and security
**Status: Automated checks, local integration, and security review completed; live provider testing pending**

- [x] Run the complete backend suite, static checks, frontend checks, and offline migration generation.
- [x] Review authorization and reject authority mutations by locally inactive global administrators.
- [x] Exercise location accuracy, map bounds, upload limits, and communications through automated tests.
- [x] Smoke-test the map at mobile width; no horizontal overflow was observed.
- [ ] Run production database/OIDC, email-provider, WhatsApp, and map-load tests with configured services.

See [the Phase 8 runbook](docs/phase-8-testing-security.md) for results and limits.

### Phase 9 — Production deployment
**Status: Deployment scaffold and local end-to-end acceptance validated; public rollout pending**

- [x] Package the API, migration runner, Celery inference worker, and standalone frontend as
  non-root containers.
- [x] Add an external-service production Compose stack, file-mounted secrets, health checks, bounded
  logs, and Caddy-managed HTTPS.
- [x] Add a post-deployment HTTPS and database-readiness smoke command.
- [x] Verify a fresh local Compose migration/startup and synthetic signed-upload-to-inference-to-download flow.
- [ ] Provision the production host, managed PostGIS/Redis/object storage, OIDC, DNS, SMTP, and
  monitoring; apply migrations and run live smoke tests.

See [the Phase 9 deployment runbook](docs/phase-9-production-deployment.md). No public deployment
has been performed from this workspace.

### Severity validation
**Status: Visual severity v1 implemented; field validation pending**

- [x] Add a transparent visual severity indicator independent of model confidence.
- [ ] Determine which additional measurements and labels are needed for validated severity.
- [ ] Evaluate severity estimates against appropriate ground truth.

### India rollout and analytics
**Status: Product foundation implemented; live rollout pending**

- [x] Confirm locations explicitly and retain provenance.
- [x] Create, review, and track reports with audited status transitions.
- [x] Visualize eligible verified reports on the India map.
- [x] Add India country, state/UT, city, severity, trend, and authority-closure analytics for public,
  human-verified reports.
- [x] Run local database, storage, worker, map-marker/cluster, and analytics integration smoke tests.
- [ ] Run OIDC, production map-tile, and geocoding provider smoke tests.
- [ ] Configure evidence-reviewed authority records and review geocoded geography labels.

---

## ⚠️ Limitations

The current implementation is an image-based pothole detector, not a complete road safety monitoring system.

- It processes images rather than continuously monitoring roads.
- It does not currently calculate actual pothole depth.
- Visual severity v1 is a geometric proxy, not a validated physical damage assessment.
- EXIF GPS is retained as provenance when present; missing GPS still requires a later explicit
  user-confirmed location step.
- Reports are persisted, but verified authority routing and repair confirmation are not configured.
- Predictions may be affected by lighting, shadows, standing water, image quality, and unfamiliar road surfaces.
- A high-confidence detection can still be incorrect.
- Model performance requires further testing on diverse real-world road images.

These limitations will guide future development and evaluation.

---

## 🤝 Contributing

Contributions, suggestions, and constructive feedback are welcome.

For proposed changes:

1. Explain the issue or feature.
2. Describe the proposed implementation.
3. Test changes before submitting them.
4. Avoid committing raw datasets, large model artifacts, credentials, or generated outputs unless explicitly intended.
5. Document new functionality and dependencies.

---

## 📄 License and Dataset Attribution

The repository's software license and the source dataset's license are separate matters.

Before publishing a license for the complete project:

- Verify the dataset's license and redistribution conditions.
- Confirm the terms applicable to pretrained model weights and dependencies.
- Decide which license applies to the project's original source code.
- Document the attribution required by the dataset provider.

Do not assume that permission to download or use a dataset automatically permits redistribution.

---

## 👨‍💻 Project

**YOLO StreetGuard AI**

Repository: [AI-Action-Lab/yolo-streetguard-ai](https://github.com/AI-Action-Lab/yolo-streetguard-ai)

An evolving computer vision project exploring AI-assisted pothole detection and intelligent road monitoring.