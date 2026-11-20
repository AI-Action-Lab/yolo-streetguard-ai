# Phase 3 — India Map and Location Intelligence

## Objective

Make an interactive India map the dominant product surface while connecting viewport-limited report
data, Indian state/UT filters, search, explicit location selection and the existing upload/detection
pipeline.

## Architecture

```text
Next.js + MapLibre
  ├── /geography/countries + ISO subdivisions
  ├── /geography/search ----------------> Google Geocoding API
  ├── /locations/reverse
  ├── /locations/confirm --------------> PostgreSQL/PostGIS
  ├── /map/markers | clusters ----------> bounded PostGIS viewport queries
  └── /uploads -------------------------> Phase 2 private AI pipeline
```

Frontend deployment variables are public and limited to the API URL and licensed tile-style URLs.
The Google geocoding key remains server-side in `GOOGLE_MAPS_API_KEY`.

## Files created

- `apps/web/`: Next.js 16, React 19, TypeScript and MapLibre dashboard.
- `apps/web/components/map-dashboard.tsx`: India map, search, state/UT filters, layers, location and upload UX.
- `apps/web/app/globals.css`: responsive dark GIS interface.
- `apps/web/lib/api.ts`: typed API client.
- `src/streetguard/geography_catalog.py`: ISO-backed India scope and provider-defined state/UT subdivisions.
- `src/streetguard/geocoding.py`: India-biased Google address/reverse-geocoding adapter.
- `src/streetguard/api/geography.py`: active India catalogue and search API.
- `src/streetguard/api/locations.py`: reverse geocoding and explicit location confirmation.
- `src/streetguard/api/map.py`: marker and grid-cluster GeoJSON queries.
- `tests/test_geography.py`, `tests/test_locations.py`, `tests/test_map_api.py`.

## Dependencies

- `pycountry` supplies a maintained ISO catalogue; the active API exposes only India.
- MapLibre GL JS renders GPU-accelerated vector/raster map styles.
- Next.js/React/TypeScript provide the responsive frontend.
- Google Geocoding is optional at runtime. Without a key, manual coordinates and map-pin confirmation
  remain available and the API explicitly returns 503 for provider search/reverse geocoding.

## Configuration

Backend `.env`:

```dotenv
GOOGLE_MAPS_API_KEY=
GOOGLE_GEOCODING_BASE_URL=https://maps.googleapis.com/maps/api/geocode/json
GEOCODING_TIMEOUT_SECONDS=8
MAP_MAX_MARKERS=1000
MAP_MAX_SPAN_DEGREES=360
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Frontend `apps/web/.env.local`:

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_MAP_STYLE_URL=https://tiles.openfreemap.org/styles/liberty
NEXT_PUBLIC_MAP_SATELLITE_STYLE_URL=
NEXT_PUBLIC_MAP_TERRAIN_STYLE_URL=
```

The map defaults to OpenFreeMap's Liberty style; the in-map selector also offers Positron.
The attribution control displays the provider and OpenStreetMap/OpenMapTiles credits. Before
deployment, verify the hosted provider's current availability and usage terms for your expected
traffic, or configure a licensed alternative/self-hosted tiles with the required attribution and
caching behavior. OSM standard tiles are not an unlimited production CDN. Satellite and terrain
controls appear only when supported style URLs are configured.

## Location behavior

The application never silently tracks a user.

- **Use my location:** one browser permission request, then one `getCurrentPosition` call.
- **Map pin:** clicking the map creates an unconfirmed candidate.
- **Manual coordinates:** editable latitude/longitude fields mark source as manual.
- **Geocoding:** user-confirmed coordinates may be reverse-geocoded.
- **Missing provider/component:** displays unavailable; no address is invented.
- **Confirmation:** only an explicitly confirmed location is stored with source, accuracy and provider
  metadata.

Address-derived values are not independent confirmation of photograph capture location.

## Bounded map strategy

Marker requests receive west/south/east/north bounds and a bounded result limit. Low zoom requests use
PostGIS `ST_SnapToGrid` aggregation and return cluster counts; higher zoom requests return only the
current public-report viewport. Spatial intersection uses the Phase 1 geography index.

The frontend reloads on `moveend` with a short debounce rather than loading every national record.
Reports not marked public are excluded. Unverified results use an `awaiting_review` marker category
and are never labelled verified.

## Run locally

Backend/database:

```powershell
python -m pip install -r requirements-dev.txt
alembic upgrade head
uvicorn streetguard.main:app --reload
```

Frontend:

```powershell
cd apps/web
Copy-Item .env.example .env.local
npm ci
npm run dev
```

Full Compose stack:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Frontend: `http://localhost:3000`. API docs: `http://localhost:8000/docs`.

## Testing and builds

Backend:

```powershell
ruff check src/streetguard tests migrations src/detector/predict.py
mypy src/streetguard
pytest
alembic upgrade head --sql
```

Frontend:

```powershell
cd apps/web
npm ci
npm run lint
npm run build
```

Expected Phase 3 evidence:

- 42 backend tests pass.
- TypeScript checks and production Next.js build pass.
- OpenAPI exposes the active India scope, subdivisions, geocoding, location confirmation, markers and clusters.
- The browser renders the India map shell, state/UT filters, search and upload modal.

## Troubleshooting

### Geocoding says not configured

Set `GOOGLE_MAPS_API_KEY` in the API environment and restrict it to server-side Geocoding API usage.
Never copy it into `NEXT_PUBLIC_*`.

### No report markers

Phase 4 will create persisted public reports. Upload processing alone creates detection records, not
public reports. This prevents unverified AI detections from appearing as confirmed road defects.

### Default map style fails or is unsuitable for production

The included URL is a development demo style. Configure a production provider style and attribution.
The frontend will offer satellite or terrain only when those URLs are present.

### CORS error

Add the exact frontend origin to `CORS_ORIGINS` and restart the API. Do not use `*` with private
operations.

### Browser says location permission denied

This is expected and handled. Select a map pin, search an address, or enter manual coordinates.

### Country selected but map does not move

The India state/UT catalogue does not contain fabricated centroids. Movement uses geocoding and
requires a configured provider; subdivision selection and search continue to display provider errors
rather than inventing a coordinate.

## Phase completion checklist

- [x] Interactive India map with zoom, pan, fullscreen and MapLibre navigation.
- [x] India scope with all 28 states and 8 union territories.
- [x] Search and reverse-geocoding provider adapter.
- [x] Current-device location with explicit permission and one-shot request.
- [x] Map pin and manual-coordinate confirmation with provenance.
- [x] Missing geocoding/component states.
- [x] Marker, heatmap and server-cluster layers.
- [x] Bounded PostGIS queries and public/verification-safe response shape.
- [x] Responsive dark dashboard and report detail panel.
- [x] Upload/detection browser workflow connected.
- [x] Next.js type check and production build.
- [x] Local PostGIS analytics, marker, and cluster endpoints return India-scoped responses after
  migrations.
- [ ] Production geocoding/map-tile provider-backed integration smoke test.

Authority workflows, report creation, analytics, severity, public tracking and review permissions are
intentionally outside Phase 3.
