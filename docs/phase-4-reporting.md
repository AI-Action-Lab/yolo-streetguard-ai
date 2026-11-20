# Phase 4 — Report Creation, Verification and Public Tracking

## Objective

Connect completed AI detections with user-confirmed locations and produce uniquely identified,
auditable reports without allowing AI results to self-verify, publish, assign, repair or resolve road
damage.

## Security and authorization

Report mutations use OIDC bearer authentication:

- The API verifies signature, supported algorithm, issuer, audience and expiry from the configured
  JWKS endpoint.
- Known StreetGuard roles are read from top-level `roles` and Keycloak-style `realm_access.roles`.
- Unknown provider roles are ignored.
- `registered_citizen` may create and submit owned reports.
- `verified_reviewer` may verify/reject/duplicate reports and review candidates.
- `global_administrator` receives every permission through the Phase 1 role model.

The API never accepts a user ID from request JSON as authority. A local `users` record is created from
the verified JWT subject. Configure `OIDC_ISSUER_URL`, `OIDC_AUDIENCE`, and `OIDC_JWKS_URL`.

## Report creation

`POST /api/v1/reports` requires:

- a completed upload owned by the authenticated reporter,
- a location whose `confirmed_by_user` flag is true,
- a completed detection run,
- a non-reused upload.

The service generates a public ID in `SG-<country>-<20 uppercase hex>` format. It uses a valid
two-letter provider country code when available, otherwise the deployment's configured product
country. The India product defaults to `IN`, so normal report creation does not produce a global
fallback ID. UUID entropy prevents sequential-code collisions without assuming a common state/city
naming scheme.

The report begins `draft`, private, and unverified. Creation writes an initial append-only status
history event and visual severity v1 assessment.

## Status workflow

Submission is idempotent while the report is in the processing portion of the workflow:

```text
draft
  -> submitted
  -> ai_processing
  -> awaiting_verification
  -> verified | rejected | duplicate
```

The existing completed YOLO run is attached before human review. A reviewer—not AI—chooses verify,
reject or duplicate. A report remains private unless the human decision is `verified`; only then does
it become public and eligible for the India map.

Every report state change records old/new status, actor, reason, event metadata and time.

## Public aggregate analytics

`GET /api/v1/analytics/summary` returns counts for public, human-verified reports in the active
product scope. For India, report locations are restricted to the same operational envelope used by
the map. The response includes open and resolved totals, severity categories, and six months of
submission counts; it excludes private reports and reporter information. Severity remains the
visual-box-v1 estimate and is not a physical damage measurement. Phase 6 extends this summary with
available state/city labels and authority assignment closure aggregates; see the
[Phase 6 runbook](phase-6-analytics.md) for their definitions and data-quality limits.

## Visual severity v1

Method version: `visual-box-v1`.

The score uses only normalized detection-box area and nearby-box count represented in the same image:

```text
score = min(1, max_box_area_ratio * 5 + min(box_count - 1, 4) * 0.04)
```

Categories:

| Score | Category |
|---:|---|
| `< 0.20` | Low |
| `0.20–0.44` | Moderate |
| `0.45–0.74` | High |
| `>= 0.75` | Critical |

Confidence is intentionally absent. The saved factor snapshot states:

> Estimated visual severity from image-relative box area and count; not a measurement of pothole
> depth, vehicle risk, or road failure.

Authorized reviewers can append a `human-review-v1` assessment with a reason; earlier assessments
remain preserved.

## Duplicate identification

Report creation runs a PostGIS `ST_DWithin` query with a 50 m radius against open reports. The
`nearby-geo-v1` candidate includes distance and a bounded proximity score. It is presented to
reviewers and cannot delete or merge a report automatically.

Reviewers can:

- mark a candidate `linked`,
- mark it `dismissed`, or
- explicitly set the source report status to `duplicate` with the candidate public ID.

Spatial proximity is not proof of duplication.

## Public tracking and privacy

`GET /api/v1/reports/{public_id}` returns only reports with public visibility after human
verification. It exposes:

- public report ID and workflow state,
- coarse/precise report location depending on current privacy policy,
- visual severity and method disclaimer,
- detection boxes and model scores,
- a signed annotated-image URL,
- public status history.

It does not expose reporter identity, email, internal user IDs, the original upload key, or the
original private image URL. Provider geocoding components can be displayed as returned but unknown
components remain unavailable.

Frontend pages:

- `/track`: searchable public tracking.
- `/track/{public_id}`: shareable deep link.

The public tracking page offers user-initiated WhatsApp and email draft links containing only the
public report ID and tracking URL. StreetGuard does not send messages through these links; the user
reviews and sends them in the external application. Authority routing and provider delivery remain
unconfigured.

## API examples

Create draft:

```http
POST /api/v1/reports
Authorization: Bearer <registered-citizen-token>
Content-Type: application/json

{
  "upload_id": "uuid",
  "location_id": "uuid",
  "title": "Pothole near road crossing",
  "description": "User-provided observation"
}
```

Submit:

```http
POST /api/v1/reports/SG-IN-.../submit
Authorization: Bearer <same-reporter-token>
```

Verify with optional human severity override:

```http
POST /api/v1/reports/SG-IN-.../verification
Authorization: Bearer <verified-reviewer-token>
Content-Type: application/json

{
  "decision": "verified",
  "reason": "Photograph and map pin reviewed",
  "severity_override": "high"
}
```

## Tests and commands

```powershell
python -m pip install -r requirements-dev.txt
ruff check src/streetguard tests migrations src/detector/predict.py
ruff format --check src/streetguard tests migrations src/detector/predict.py
mypy src/streetguard
pytest

cd apps/web
npm ci
npm run lint
npm run build
```

Expected: backend and frontend acceptance passes, including permission rejection, severity
determinism, ID collision resistance, privacy schema and public tracking route builds.

## Completion checklist

- [x] OIDC JWT and JWKS verification.
- [x] Role-based report mutation permissions.
- [x] Unique IDs with `IN` product default.
- [x] Completed detection + confirmed location prerequisites.
- [x] Append-only report status history.
- [x] Transparent visual severity v1.
- [x] Nearby duplicate candidates without automatic deletion.
- [x] Reviewer link/dismiss and duplicate status.
- [x] Human-only publication.
- [x] Privacy-safe annotated tracking response.
- [x] Public tracking UI and CI build.
- [ ] Live OIDC/JWKS, PostGIS and public tracking smoke test.

## Troubleshooting

### 401 bearer token required

Report mutations intentionally require a verified OIDC token. Public tracking does not.

### 403 permission missing

The identity lacks the expected StreetGuard role claim. Do not grant a role client-side.

### 409 upload completed/ownership error

A report requires a completed upload not already claimed by another reporter or report.

### Duplicate candidate absent

The report must be within 50 m of another open report with a location. The absence of a candidate is
not proof the reports are unique.

### Public tracking returns 404

Draft, submitted, rejected and duplicate reports remain private. Only human-verified reports are
published.
