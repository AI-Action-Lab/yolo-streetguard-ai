# Phase 5 — Communications and Authority Directory

## Status

The communications API, audit trail, SMTP adapter, and public India authority directory are
implemented. Live relay delivery and the population of verified authority records require
environment-specific operations and are not represented as complete by this code.

## Authority directory

`GET /api/v1/authorities` returns only active, verified records. An optional `region_id` query
filters by the configured jurisdiction. The public web directory at `/authorities` consumes this
endpoint and intentionally shows an empty state until verified records exist.

Creation, update, and verification require the global-administrator role:

- `POST /api/v1/authorities` creates an active but unverified record.
- `PUT /api/v1/authorities/{authority_id}` updates its details. Changing contact or jurisdiction
  details clears verification and evidence.
- `POST /api/v1/authorities/{authority_id}/verify` requires an evidence URL and explicit
  confirmation. Creation, edits, and verification are audited.

The API does not infer a responsible agency from a report location. Administrators must check
jurisdiction and contact information against authoritative sources before verification. Never add
sample or guessed public agency records.

## Report email and status notifications

- `POST /api/v1/reports/{public_id}/email` is restricted to the authenticated report owner and a
  public, human-verified report. The request must explicitly confirm sending and specify exactly one
  verified authority or manually entered recipient. The API limits attempts to five per owner per
  hour.
- `GET /api/v1/reports/{public_id}/emails` returns the report owner's delivery log.
- `GET` and `PUT /api/v1/notifications/preferences` read and update email status-notification
  consent. Enabling email requires explicit consent, a verified OIDC identity email, and configured
  SMTP. Consent is disabled if the identity provider no longer verifies the email.
- `GET /api/v1/notifications/mine` lists in-app status notifications, and
  `POST /api/v1/notifications/{notification_id}/read` marks an owned notification read.

Status changes create an in-app notification. Email is attempted only for a verified identity email
with current opt-in consent. A report-share endpoint requires an authenticated client; the web app
does not bypass that requirement. Existing user-initiated external email/WhatsApp drafts remain
separate from server-side SMTP.

Email log states `pending`, `accepted`, and `failed` record the application's interaction with the
SMTP relay. `accepted` means the relay accepted the message, not that it reached or was read by the
recipient. Report-share SMTP errors are returned to the caller; status-update email failures are
retained in the delivery log and do not roll back a report status change.

Messages include a public tracking URL and issue/address summary; exact coordinates are omitted.
Severity is labelled as an image-based estimate, not a physical measurement.

## SMTP configuration

Configure these values in the API environment; never commit credentials:

```dotenv
PUBLIC_BASE_URL=https://your-public-web-host
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=
SMTP_USE_SSL=false
SMTP_STARTTLS=true
SMTP_TIMEOUT_SECONDS=10
```

Set either implicit SSL (`SMTP_USE_SSL=true`) or STARTTLS, not both. SMTP username and password
must be supplied together. Production SMTP requires a valid TLS mode and sender address. Leave the
host blank to disable delivery; the API records/returns an explicit unconfigured-provider error
rather than claiming success.

## Database and validation

Apply the Phase 5 migration with the normal Alembic deployment procedure. It adds identity email
verification state, opt-in preference/consent fields, and a purpose field on delivery logs. No
authority data is inserted by the migration.

Focused validation:

```powershell
python -m pytest -q tests\test_communications.py tests\test_schema.py tests\test_settings.py
ruff check src\streetguard tests migrations
ruff format --check src\streetguard tests migrations
mypy src\streetguard
alembic upgrade head --sql
```

Automated SMTP tests use a fake relay. Before launch, configure the production provider, run the
database-backed integration checks, send a controlled end-to-end message, verify relay/provider
logs, and populate only evidence-reviewed authority records.
