# India-First Product Scope

## Decision

StreetGuard is now presented and operated as an India-first product. The worldwide dashboard and
country selector are removed from the frontend. The API exposes India as the active country and only
Indian states/union territories. Report IDs generated in this deployment default to `SG-IN-*`.

Reusable database and coordinate primitives remain country-neutral internally so a future expansion
would be configuration/data work rather than a destructive rewrite. This is an engineering
boundary, not a worldwide product claim.

## Active scope

- India-wide interactive map centered on India and bounded to an Indian service viewport.
- 28 states and 8 union territories from the maintained ISO subdivision catalogue.
- Search, PIN code/address and reverse geocoding biased and filtered to India.
- Manual coordinates outside the broad India service envelope rejected.
- Human-confirmed map/device coordinates retain explicit provenance.
- Indian road and authority terminology.
- Public report tracking for `SG-IN-*` reports.
- Verified authorities and jurisdiction data added only after evidence is checked.

The bounding envelope is an operational routing guard, not a legal boundary dataset. Exact country
membership must come from a configured geocoding/boundary provider when strict scope is enabled.

## Authority rollout

Authority routing is intentionally conservative. The platform must not infer a responsible agency
from a pin alone. Supported categories can include municipal corporations/ULBs, panchayats, public
works departments, state highway authorities, NHAI and special road jurisdictions, but only verified
records may receive a report.

Until a jurisdiction has a reviewed authority record:

> Authority not identified

The citizen can select a recipient manually and explicitly confirm any email action. A report remains
valid for tracking even when an authority is not yet configured.

## Pilot recommendation

Start with one state or two to three pilot cities selected by the product owner, while retaining
India-wide public map/search browsing. This controls authority verification, model error review,
geocoding cost and support load. The software does not pretend that a pilot already exists until the
jurisdictions are explicitly configured and reviewed.

## Configuration

```dotenv
PRODUCT_COUNTRY_CODE=IN
PRODUCT_COUNTRY_NAME=India
STRICT_COUNTRY_SCOPE=false
GOOGLE_MAPS_API_KEY=
```

Set `STRICT_COUNTRY_SCOPE=true` for a production environment once an Indian geocoding provider is
configured. With strict scope enabled, production refuses to start without the provider key and
manual coordinates require an in-India provider result before confirmation.

## What was removed from the product

- Worldwide country selector.
- World-centred default map.
- Worldwide launch wording.
- Global report-ID fallback for normal India reports.
- Out-of-country map browsing and geocoding results.

## What remains internally reusable

- PostgreSQL/PostGIS coordinate and region types.
- Generic OIDC/RBAC and workflow rules.
- UUID-backed records and bounded viewport queries.
- Provider adapters with an active country filter.
- Configurable storage and AI processing.

These fields are not exposed as worldwide product options. A later world launch would require a new
explicit scope decision, provider/boundary review, authorities, privacy work, QA and cost approval.
