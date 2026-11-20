# Phase 6 — Dashboard and Analytics

## Status and scope

The analytics API and dashboard present India-only aggregates. The roadmap's “global dashboard”
wording is not enabled: the established product scope remains India-first. The summary describes
public, human-verified reports only and excludes reporter identity and private report details.

`GET /api/v1/analytics/summary` returns the India country code, verified/open/resolved totals,
severity counts, the six latest calendar months of submissions, state/UT counts, top 10 city counts,
geography coverage counts, and verified-authority assignment/closure aggregates.

## Geography breakdowns

State and city names are grouped from `locations.provider_metadata.state_province` and
`locations.provider_metadata.city`, which are populated when reverse geocoding provides those
fields. The API does not infer a state or city from coordinates, text, or administrative boundaries.
Reports missing a state or city label are separately counted as unclassified. City results show the
top 10 named cities; this display limit is not included in the unclassified count.

Provider labels are not a canonical geographic catalogue. Variations can split one place across
multiple rows, and reverse-geocoding coverage may be sparse. Validate/canonicalize a reviewed data
set before using these figures for funding, ranking, or agency performance decisions.

## Trends and severity

The monthly trend groups eligible reports by `submitted_at` for the current month and five preceding
calendar months; missing months are returned as zero. Severity distribution uses the saved report
severity categories, including `unknown`. Visual-box-v1 is an image-relative estimate and does not
measure depth, road risk, or repair cost.

## Authority assignment analytics

Authority rows include only active, verified authorities assigned to public, human-verified reports.
Summary counts describe assignment records, not unique citizens or all incoming reports. The
dashboard reports assigned, open, and completed assignments, plus assignment-to-completion hours
where timestamps are valid. This is a closure metric, not first-response time. The schema does not
yet store a dedicated first-response timestamp, so `first_response_time_available` is false and the
UI says so explicitly.

No example authority records or synthetic performance data are seeded. Until Phase 7 assignment and
resolution workflows populate reviewed records, the dashboard displays an empty state.

## Validation and live-data prerequisites

Focused checks:

```powershell
python -m pytest -q tests\test_analytics_api.py
ruff check src\streetguard\api\analytics.py tests\test_analytics_api.py
mypy src\streetguard
```

The SQL tests verify the public/verified and India-envelope constraints and compile the JSON and
elapsed-time expressions using the PostgreSQL dialect. A loopback-only PostGIS smoke returned the
expected zero-count India analytics summary and empty marker/cluster collections. This validates
query execution against an empty local database, not data quality; production database acceptance
and reviewed geocoding/authority data remain required before relying on operational analytics.
