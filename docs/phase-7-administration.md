# Phase 7 — Administration and Authority Operations

## Status and scope

The global-administrator and authority operations APIs, dashboard portals, audit events, and
authority-membership migration are implemented. The work provides the operational building blocks
for assignment and resolution, but does not establish regional administrator scopes or production
readiness. Use only evidence-reviewed authority records and jurisdiction data.

## Administrator operations

The `/admin` portal links to these protected API operations:

- `GET /api/v1/administration/reports` lists at most 100 unassigned public, human-verified reports.
- `POST /api/v1/administration/reports/{public_id}/assign` requires explicit confirmation, an active
  verified authority, and an eligible report. Assignment and report status history are saved
  together; the report row is locked during assignment to prevent concurrent assignment races.
- `GET /api/v1/administration/authorities/{authority_id}/members` lists membership records.
- `POST /api/v1/administration/authorities/{authority_id}/members` adds or reactivates an existing
  active user. `DELETE /api/v1/administration/authorities/{authority_id}/members/{user_id}` deactivates
  that membership and retains its audit history.
- `GET /api/v1/administration/audit-logs` returns a bounded, newest-first audit list (default 50,
  maximum 100).

All cross-region administrator operations currently require the global-administrator role as well
as the relevant permission. Regional administrators are not given broad access because regional
scope membership has not been modeled. Adding an authority membership does not grant an OIDC role;
the identity provider must separately issue the `municipal_authority` role.

## Authority workflow

The `/authority` portal calls `GET /api/v1/authority/reports` and
`POST /api/v1/authority/reports/{public_id}/status`. Access requires the municipal-authority
permission and an active membership to an active, verified authority. Reports must be public and
human-verified. Status transitions are ordered: `assigned_to_authority` to `in_progress`, then
`resolved`. Each change requires a work note, writes report status history and an audit event, and
resolution stamps both the report and assignment completion times.

The API returns only reports assigned to the caller's active verified memberships. Cross-authority
report lookup returns not found. The dashboard shows an empty report list when the caller has no
active verified authority memberships.

## Portal authentication and privacy

The existing web application does not yet include an OIDC sign-in client. Both operations portals
therefore accept a short-lived OIDC **access token** manually; they never accept an ID token. The
token is held in React component memory only and is cleared on disconnect or page reload. Integrate
the portal with the deployed OIDC sign-in before operational launch, and do not use long-lived tokens.

## Migration and validation

The Phase 7 migration creates `authority_memberships` with active-state, grantor, foreign-key,
uniqueness, and lookup-index constraints. Apply it through the normal Alembic deployment process.
No authority or membership data is seeded.

Focused validation:

```powershell
python -m pytest -q tests\test_administration_api.py tests\test_schema.py
ruff check src\streetguard tests migrations
ruff format --check src\streetguard tests migrations
mypy src\streetguard
alembic upgrade head --sql
```

The authority-membership migration was applied during fresh local PostGIS startup. The API test
suite uses isolated fake sessions and does not verify PostgreSQL locking or the authority workflow.
Before launch, verify permission claims and OIDC integration, then exercise assignment, member
access, audit logging, and both resolution transitions using reviewed authority data.
