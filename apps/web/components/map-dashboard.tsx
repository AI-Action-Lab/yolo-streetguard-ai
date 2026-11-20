"use client";

import {
  Activity,
  Bell,
  Building2,
  Check,
  ChevronRight,
  Crosshair,
  FileUp,
  Filter,
  Layers3,
  LocateFixed,
  Map as MapIcon,
  MapPin,
  Menu,
  Moon,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Upload,
  X,
} from "lucide-react";
import * as maplibregl from "maplibre-gl";
import type {
  Map as MapLibreMap,
  MapGeoJSONFeature,
  MapMouseEvent,
} from "maplibre-gl";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import {
  AnalyticsSummary,
  api,
  GeocodeResult,
  ReportFeature,
  Subdivision,
  UploadStatus,
} from "../lib/api";

maplibregl.setWorkerUrl("/maplibre-gl-worker.mjs");

const EMPTY_FEATURES: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };
const STYLES = {
  atlas:
    process.env.NEXT_PUBLIC_MAP_STYLE_URL ??
    "https://tiles.openfreemap.org/styles/liberty",
  daylight: "https://tiles.openfreemap.org/styles/positron",
  satellite: process.env.NEXT_PUBLIC_MAP_SATELLITE_STYLE_URL ?? "",
  terrain: process.env.NEXT_PUBLIC_MAP_TERRAIN_STYLE_URL ?? "",
};

type LocationDraft = {
  latitude: number;
  longitude: number;
  accuracy?: number;
  source: "device_gps" | "map_pin" | "manual_coordinates";
};

function messageFrom(error: unknown) {
  return error instanceof Error ? error.message : "An unexpected error occurred";
}

async function sha256(file: File) {
  const digest = await crypto.subtle.digest("SHA-256", await file.arrayBuffer());
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

export function MapDashboard() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const clustersRef = useRef(true);
  const moveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mapRequestRef = useRef(0);
  const [subdivisions, setSubdivisions] = useState<Subdivision[]>([]);
  const [subdivision, setSubdivision] = useState("");
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<GeocodeResult[]>([]);
  const [features, setFeatures] = useState<GeoJSON.FeatureCollection>(EMPTY_FEATURES);
  const [clusters, setClusters] = useState(true);
  const [heatmap, setHeatmap] = useState(false);
  const [style, setStyle] = useState<keyof typeof STYLES>("atlas");
  const [selected, setSelected] = useState<ReportFeature | null>(null);
  const [location, setLocation] = useState<LocationDraft | null>(null);
  const [locationAddress, setLocationAddress] = useState<string>("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(false);
  const [mapDataLoading, setMapDataLoading] = useState(false);
  const [mapDataError, setMapDataError] = useState("");
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<UploadStatus | null>(null);
  const [analyticsOpen, setAnalyticsOpen] = useState(false);
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [analyticsError, setAnalyticsError] = useState("");
  const [mobileMenu, setMobileMenu] = useState(false);
  const [highContrast, setHighContrast] = useState(false);

  const selectedStats = useMemo(() => {
    const reports = features.features.filter((feature) =>
      Boolean(feature.properties && "report_id" in feature.properties),
    ) as ReportFeature[];
    return {
      visible: reports.length,
      verified: reports.filter((item) => item.properties.verification_status === "verified").length,
      critical: reports.filter((item) => item.properties.severity === "critical").length,
    };
  }, [features]);

  const loadAnalytics = async () => {
    setAnalyticsOpen(true);
    setAnalyticsLoading(true);
    setAnalyticsError("");
    try {
      setAnalytics(await api.analyticsSummary());
    } catch (error) {
      setAnalyticsError(messageFrom(error));
    } finally {
      setAnalyticsLoading(false);
    }
  };

  const severityMaximum = analytics
    ? Math.max(1, ...Object.values(analytics.severity_distribution))
    : 1;
  const monthlyMaximum = analytics
    ? Math.max(1, ...analytics.monthly_submissions.map((item) => item.count))
    : 1;
  const geographyMaximum = analytics
    ? Math.max(
        1,
        ...analytics.states.map((item) => item.report_count),
        ...analytics.cities.map((item) => item.report_count),
      )
    : 1;

  const updateMapData = async (map: MapLibreMap) => {
    const requestId = ++mapRequestRef.current;
    const bounds = map.getBounds();
    const west = Math.max(-180, bounds.getWest());
    const east = Math.min(180, bounds.getEast());
    const viewport: [number, number, number, number] = [
      west < east ? west : -180,
      bounds.getSouth(),
      west < east ? east : 180,
      bounds.getNorth(),
    ];
    setMapDataLoading(true);
    try {
      const data = await api.mapData(viewport, map.getZoom(), clustersRef.current);
      if (requestId !== mapRequestRef.current) return;
      setFeatures(data);
      setMapDataError("");
      if (map.getSource("streetguard-data")) {
        (map.getSource("streetguard-data") as maplibregl.GeoJSONSource).setData(data);
      }
    } catch (error) {
      if (requestId === mapRequestRef.current) setMapDataError(messageFrom(error));
    } finally {
      if (requestId === mapRequestRef.current) setMapDataLoading(false);
    }
  };

  useEffect(() => {
    api
      .subdivisions("IN")
      .then(setSubdivisions)
      .catch((error) => setNotice(messageFrom(error)));
  }, []);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: STYLES.atlas,
      center: [79, 22],
      zoom: 4.2,
      attributionControl: false,
      minZoom: 3.5,
      maxBounds: [
        [67, 6],
        [98, 38],
      ],
    });
    mapRef.current = map;
    map.addControl(new maplibregl.NavigationControl(), "bottom-right");
    map.addControl(new maplibregl.FullscreenControl(), "bottom-right");
    map.addControl(
      new maplibregl.AttributionControl({
        compact: true,
        customAttribution: "StreetGuard",
      }),
      "bottom-left",
    );

    const bindSources = () => {
      if (!map.getSource("streetguard-data")) {
        map.addSource("streetguard-data", { type: "geojson", data: EMPTY_FEATURES });
      }
      if (!map.getLayer("streetguard-clusters")) {
        map.addLayer({
          id: "streetguard-clusters",
          type: "circle",
          source: "streetguard-data",
          filter: ["has", "point_count"],
          paint: {
            "circle-color": "#4dd7b5",
            "circle-radius": ["interpolate", ["linear"], ["get", "point_count"], 1, 17, 100, 34],
            "circle-stroke-color": "#07151c",
            "circle-stroke-width": 4,
            "circle-opacity": 0.88,
          },
        });
        map.addLayer({
          id: "streetguard-cluster-labels",
          type: "symbol",
          source: "streetguard-data",
          filter: ["has", "point_count"],
          layout: { "text-field": ["get", "point_count"], "text-size": 12 },
          paint: { "text-color": "#f7faf9" },
        });
      }
      if (!map.getLayer("streetguard-reports")) {
        map.addLayer({
          id: "streetguard-reports",
          type: "circle",
          source: "streetguard-data",
          filter: ["has", "report_id"],
          paint: {
            "circle-color": [
              "match",
              ["get", "marker_category"],
              "critical",
              "#ff5d6c",
              "resolved",
              "#4dd7b5",
              "verified",
              "#5c8dff",
              "#f6b95c",
            ],
            "circle-radius": 8,
            "circle-stroke-width": 2,
            "circle-stroke-color": "#eefaf7",
          },
        });
      }
      if (!map.getLayer("streetguard-heatmap")) {
        map.addLayer({
          id: "streetguard-heatmap",
          type: "heatmap",
          source: "streetguard-data",
          filter: ["has", "report_id"],
          layout: { visibility: "none" },
          paint: {
            "heatmap-intensity": 1.2,
            "heatmap-color": [
              "interpolate",
              ["linear"],
              ["heatmap-density"],
              0,
              "rgba(15,23,42,0)",
              0.3,
              "#2dd4bf",
              0.7,
              "#f6b95c",
              1,
              "#ff5d6c",
            ],
            "heatmap-radius": 24,
          },
        });
      }
      setMapLayerVisibility(map);
      void updateMapData(map);
    };

    map.on("load", bindSources);
    map.on("style.load", bindSources);
    map.on("moveend", () => {
      if (moveTimer.current) clearTimeout(moveTimer.current);
      moveTimer.current = setTimeout(() => void updateMapData(map), 180);
    });
    map.on("click", "streetguard-reports", (event: MapMouseEvent & { features?: MapGeoJSONFeature[] }) => {
      event.preventDefault();
      const feature = event.features?.[0] as unknown as ReportFeature | undefined;
      if (feature) setSelected(feature);
    });
    map.on("click", "streetguard-clusters", (event: MapMouseEvent & { features?: MapGeoJSONFeature[] }) => {
      event.preventDefault();
      const coordinates = (event.features?.[0].geometry as GeoJSON.Point).coordinates;
      map.easeTo({ center: coordinates as [number, number], zoom: Math.min(map.getZoom() + 2, 14) });
    });
    map.on("click", (event: MapMouseEvent) => {
      if (event.defaultPrevented) return;
      setLocation({
        latitude: event.lngLat.lat,
        longitude: event.lngLat.lng,
        source: "map_pin",
      });
      setLocationAddress("");
      void api
        .reverse(event.lngLat.lat, event.lngLat.lng)
        .then((results) => setLocationAddress(results[0]?.formatted_address ?? "Address unavailable"))
        .catch(() => setLocationAddress("Address unavailable; coordinates can still be used"));
    });
    return () => {
      mapRequestRef.current += 1;
      if (moveTimer.current) clearTimeout(moveTimer.current);
      map.remove();
      mapRef.current = null;
    };
  }, []);

  const setMapLayerVisibility = (map = mapRef.current) => {
    if (!map || !map.isStyleLoaded()) return;
    if (map.getLayer("streetguard-clusters")) {
      map.setLayoutProperty(
        "streetguard-clusters",
        "visibility",
        clusters ? "visible" : "none",
      );
      map.setLayoutProperty(
        "streetguard-cluster-labels",
        "visibility",
        clusters ? "visible" : "none",
      );
    }
    if (map.getLayer("streetguard-heatmap")) {
      map.setLayoutProperty("streetguard-heatmap", "visibility", heatmap ? "visible" : "none");
    }
  };

  useEffect(() => setMapLayerVisibility(), [clusters, heatmap]);
  useEffect(() => {
    clustersRef.current = clusters;
    const map = mapRef.current;
    if (map?.isStyleLoaded()) void updateMapData(map);
  }, [clusters]);

  useEffect(() => {
    const map = mapRef.current;
    const nextStyle = STYLES[style];
    if (map && nextStyle) map.setStyle(nextStyle);
  }, [style]);

  const changeSubdivision = async (code: string) => {
    setSubdivision(code);
    const item = subdivisions.find((value) => value.code === code);
    if (!item) return;
    try {
      const results = await api.search(`${item.name}, India`);
      if (results[0]) {
        mapRef.current?.flyTo({
          center: [results[0].longitude, results[0].latitude],
          zoom: 7,
        });
      }
    } catch (error) {
      setNotice(messageFrom(error));
    }
  };

  const search = async (event: FormEvent) => {
    event.preventDefault();
    if (query.trim().length < 2) return;
    setLoading(true);
    try {
      const results = await api.search(query);
      setSearchResults(results);
      if (results.length === 0) setNotice("No matching place was returned.");
    } catch (error) {
      setNotice(messageFrom(error));
    } finally {
      setLoading(false);
    }
  };

  const chooseResult = (result: GeocodeResult) => {
    mapRef.current?.flyTo({
      center: [result.longitude, result.latitude],
      zoom: result.components.road ? 16 : 9,
    });
    setSearchResults([]);
    setQuery(result.formatted_address);
    setLocation({
      latitude: result.latitude,
      longitude: result.longitude,
      source: "map_pin",
    });
    setLocationAddress(result.formatted_address);
  };

  const useCurrentLocation = () => {
    if (!navigator.geolocation) {
      setNotice("Device geolocation is unavailable. Select a point on the map instead.");
      return;
    }
    setLoading(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const draft: LocationDraft = {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
          source: "device_gps",
        };
        setLocation(draft);
        mapRef.current?.flyTo({
          center: [draft.longitude, draft.latitude],
          zoom: 15,
        });
        void api
          .reverse(draft.latitude, draft.longitude)
          .then((results) =>
            setLocationAddress(results[0]?.formatted_address ?? "Address unavailable"),
          )
          .catch(() => setLocationAddress("Address unavailable; coordinates can still be used"))
          .finally(() => setLoading(false));
      },
      (error) => {
        setLoading(false);
        setNotice(`Location permission was not granted or location failed (${error.message}).`);
      },
      { enableHighAccuracy: true, maximumAge: 0, timeout: 15_000 },
    );
  };

  const confirmLocation = async () => {
    if (!location) return;
    try {
      await api.confirmLocation({
        latitude: location.latitude,
        longitude: location.longitude,
        accuracy_meters: location.accuracy,
        source: location.source,
        confirmed: true,
      });
      setNotice("Location confirmed and saved. No report has been created yet.");
      setLocation(null);
    } catch (error) {
      setNotice(messageFrom(error));
    }
  };

  const uploadImage = async (file: File) => {
    setNotice("");
    setLoading(true);
    try {
      const digest = await sha256(file);
      const created = await api.createUpload({
        filename: file.name,
        content_type: file.type,
        byte_size: file.size,
        sha256: digest,
      });
      if (!created.duplicate) {
        const form = new FormData();
        Object.entries(created.upload_fields).forEach(([key, value]) => form.append(key, value));
        form.append("file", file);
        const uploadResponse = await fetch(created.upload_url, { method: "POST", body: form });
        if (!uploadResponse.ok) throw new Error("Private object-storage upload failed");
      }
      let status = await api.completeUpload(created.upload_id, created.object_key);
      setUploadStatus(status);
      while (["queued", "ai_processing"].includes(status.processing_status)) {
        await new Promise((resolve) => setTimeout(resolve, 1800));
        status = await api.uploadStatus(created.upload_id);
        setUploadStatus(status);
      }
      if (status.processing_status === "completed") {
        setNotice("Detection completed. Review the result before creating a report.");
      } else {
        setNotice(status.detection_run?.error_message ?? "Detection did not complete.");
      }
    } catch (error) {
      setNotice(messageFrom(error));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className={`dashboard-shell ${highContrast ? "high-contrast" : ""}`}>
      <header className="topbar">
        <button className="icon-button mobile-menu" onClick={() => setMobileMenu(!mobileMenu)}>
          <Menu size={20} />
        </button>
        <div className="brand">
          <span className="brand-mark"><ShieldCheck size={19} /></span>
          <span>STREETGUARD</span>
          <b>AI</b>
        </div>
        <form className="geo-search" onSubmit={search}>
          <Search size={16} />
          <input
            aria-label="Search state, city, postal code or address in India"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search Indian state, city, address or PIN code"
          />
          <span className="key-hint">↵</span>
        </form>
        <div className="top-actions">
          <button
            className="icon-button"
            aria-label="Toggle high-contrast interface"
            aria-pressed={highContrast}
            onClick={() => setHighContrast(!highContrast)}
          >
            <Moon size={18} />
          </button>
          <button
            className="icon-button notification"
            aria-label="Notifications"
            onClick={() => setNotice("No new notification records are available.")}
          >
            <Bell size={18} /><span />
          </button>
          <div className="avatar" aria-label="Public user">SG</div>
        </div>
      </header>

      <aside className={`sidebar ${mobileMenu ? "sidebar-open" : ""}`}>
        <div className="side-label">INTELLIGENCE</div>
        <nav>
          <button className="active"><MapIcon size={18} /><span>Live India map</span></button>
          <button onClick={() => setUploadOpen(true)}><Upload size={18} /><span>Upload & detect</span></button>
          <Link href="/track"><FileUp size={18} /><span>Track report</span></Link>
          <button onClick={() => void loadAnalytics()}><Activity size={18} /><span>Analytics</span></button>
        </nav>
        <div className="side-label">OPERATIONS</div>
        <nav>
          <Link href="/authorities"><ShieldCheck size={18} /><span>Authorities</span></Link>
          <Link href="/authority"><Building2 size={18} /><span>Authority portal</span></Link>
          <Link href="/admin"><SlidersHorizontal size={18} /><span>Administration</span></Link>
        </nav>
        <div className="side-status">
          <span className="status-dot" />
          <div><b>Detection service</b><small>Configured separately</small></div>
        </div>
      </aside>

      <section className="workspace">
        <div className="workspace-heading">
          <div>
            <p className="eyebrow">INDIA ROAD INTELLIGENCE</p>
            <h1>India road watch</h1>
            <p className="subtitle">Explore verified road reports across India. AI detections remain unverified until human review.</p>
          </div>
          <button className="primary-button" onClick={() => setUploadOpen(true)}>
            <Upload size={16} /> Upload road image
          </button>
        </div>

        <div className="filterbar">
          <label><Filter size={14} /> India geography</label>
          <span className="india-scope" aria-label="Active country scope">INDIA</span>
          <select
            aria-label="State or Union Territory"
            value={subdivision}
            onChange={(event) => void changeSubdivision(event.target.value)}
            disabled={subdivisions.length === 0}
          >
            <option value="">State / Union Territory</option>
            {subdivisions.map((item) => <option key={item.code} value={item.code}>{item.name} — {item.type}</option>)}
          </select>
          <button className="location-button" onClick={useCurrentLocation}>
            <LocateFixed size={15} /> Use my location
          </button>
          <button
            className="text-button"
            onClick={() => {
              setSubdivision("");
              mapRef.current?.flyTo({ center: [79, 22], zoom: 4.2 });
            }}
          >
            Reset
          </button>
        </div>

        <div className="map-layout">
          <section className="map-card" aria-label="Interactive India map">
            <div ref={containerRef} className="map-canvas" />
            <div className="map-stats" aria-label="Visible report summary" aria-live="polite">
              <span className="map-stat-total"><small>Visible</small><b>{selectedStats.visible}</b></span>
              <span className="map-stat-verified"><small>Verified</small><b>{selectedStats.verified}</b></span>
              <span className="map-stat-critical"><small>Critical</small><b>{selectedStats.critical}</b></span>
            </div>
            <div className="map-tools">
              <label><Layers3 size={15} /> Map style
                <select value={style} onChange={(event) => setStyle(event.target.value as keyof typeof STYLES)}>
                  <option value="atlas">Atlas</option>
                  <option value="daylight">Daylight</option>
                  {STYLES.satellite && <option value="satellite">Satellite</option>}
                  {STYLES.terrain && <option value="terrain">Terrain</option>}
                </select>
              </label>
              <button
                type="button"
                className={heatmap ? "tool-active" : ""}
                aria-pressed={heatmap}
                onClick={() => setHeatmap(!heatmap)}
              >
                Heatmap
              </button>
              <button
                type="button"
                className={clusters ? "tool-active" : ""}
                aria-pressed={clusters}
                onClick={() => setClusters(!clusters)}
              >
                Clusters
              </button>
            </div>
            <div className="map-legend" role="group" aria-label="Report status legend">
              <span><i className="legend-awaiting" /> Awaiting review</span>
              <span><i className="legend-verified" /> Verified</span>
              <span><i className="legend-critical" /> Critical</span>
              <span><i className="legend-resolved" /> Resolved</span>
            </div>
            {mapDataLoading && <div className="map-loading">Loading reports…</div>}
          </section>

          <aside className="intel-panel">
            <div className="panel-header">
              <div><p className="eyebrow">MAP INTELLIGENCE</p><h2>{selected ? "Report details" : location ? "Confirm location" : "India overview"}</h2></div>
              <MapPin size={19} />
            </div>
            {location ? (
              <div className="location-card">
                <span className="pin-icon"><Crosshair size={22} /></span>
                <h3>Confirm this location</h3>
                <p>{locationAddress || "Reverse geocoding may be unavailable. Coordinates remain valid."}</p>
                <code>{location.latitude.toFixed(6)}, {location.longitude.toFixed(6)}</code>
                <small>Source: {location.source.replace("_", " ")}{location.accuracy ? ` · ±${Math.round(location.accuracy)} m` : ""}</small>
                <div className="manual-coordinates">
                  <label>Latitude<input type="number" value={location.latitude} step="0.000001" onChange={(event) => setLocation({ ...location, latitude: Number(event.target.value), source: "manual_coordinates" })} /></label>
                  <label>Longitude<input type="number" value={location.longitude} step="0.000001" onChange={(event) => setLocation({ ...location, longitude: Number(event.target.value), source: "manual_coordinates" })} /></label>
                </div>
                <button className="primary-button full-button" onClick={() => void confirmLocation()}><Check size={16} /> Confirm location</button>
                <button className="text-button full-button" onClick={() => setLocation(null)}>Cancel</button>
              </div>
            ) : selected ? (
              <div className="report-detail">
                <span className={`report-badge ${selected.properties.marker_category}`}>{selected.properties.marker_category.replace("_", " ")}</span>
                <h3>{selected.properties.report_id}</h3>
                <p className="muted">Public report metadata only</p>
                <dl>
                  <div><dt>Status</dt><dd>{selected.properties.status}</dd></div>
                  <div><dt>Verification</dt><dd>{selected.properties.verification_status}</dd></div>
                  <div><dt>Severity</dt><dd>{selected.properties.severity ?? "Unavailable"}</dd></div>
                  <div><dt>Detections</dt><dd>{selected.properties.detection_count}</dd></div>
                </dl>
                <Link className="primary-button full-button" href={`/track/${encodeURIComponent(selected.properties.report_id)}`}>Track public report</Link>
                <button className="secondary-button full-button" onClick={() => setSelected(null)}>Back to overview</button>
              </div>
            ) : (
              <div className="overview-list">
                <div className="overview-callout"><Activity size={18} /><div><b>India data only</b><p>The map loads bounded reports for the current Indian viewport. No demonstration statistics are displayed.</p></div></div>
                <h3>Map activity</h3>
                {mapDataError ? (
                  <div className="empty-state empty-state-error" role="alert">
                    <span className="empty-state-icon"><Activity size={20} /></span>
                    <b>Live report data is unavailable</b>
                    <p>The map is still available, but reports could not be loaded. {mapDataError}</p>
                    <button
                      type="button"
                      className="secondary-button"
                      onClick={() => {
                        if (mapRef.current) void updateMapData(mapRef.current);
                      }}
                    >
                      Try again
                    </button>
                  </div>
                ) : features.features.length === 0 ? (
                  <div className="empty-state">
                    <span className="empty-state-icon"><MapIcon size={20} /></span>
                    <b>No reports in this view</b>
                    <p>Pan or zoom to explore another area, or use your location to focus the map.</p>
                  </div>
                ) : (
                  features.features.slice(0, 8).map((feature, index) => (
                    <button key={index} onClick={() => "report_id" in (feature.properties ?? {}) && setSelected(feature as ReportFeature)}>
                      <span className="activity-icon"><MapPin size={14} /></span>
                      <span><b>{"report_id" in (feature.properties ?? {}) ? String((feature.properties as Record<string, unknown>).report_id) : `${String((feature.properties as Record<string, unknown>)?.point_count ?? 0)} clustered reports`}</b><small>{"report_id" in (feature.properties ?? {}) ? String((feature.properties as Record<string, unknown>).status) : "Zoom to inspect"}</small></span>
                      <ChevronRight size={15} />
                    </button>
                  ))
                )}
                <button className="location-prompt" onClick={useCurrentLocation}><LocateFixed size={16} /> Select or use a location</button>
              </div>
            )}
          </aside>
        </div>
      </section>

      {notice && <button className="toast" onClick={() => setNotice("")}><span>{notice}</span><X size={15} /></button>}

      {analyticsOpen && (
        <div className="modal-backdrop" role="presentation" onClick={() => setAnalyticsOpen(false)}>
          <section
            className="analytics-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="analytics-title"
            onClick={(event) => event.stopPropagation()}
          >
            <button
              className="modal-close"
              onClick={() => setAnalyticsOpen(false)}
              aria-label="Close analytics"
            >
              <X size={18} />
            </button>
            <p className="eyebrow">INDIA ROAD INTELLIGENCE</p>
            <h2 id="analytics-title">Verified India report analytics</h2>
            <p className="analytics-intro">
              Aggregates include only public, human-verified India reports.
            </p>
            {analyticsLoading ? (
              <p className="analytics-message">Loading verified report data…</p>
            ) : analyticsError ? (
              <div className="analytics-message analytics-error">
                <p>{analyticsError}</p>
                <button className="secondary-button" onClick={() => void loadAnalytics()}>
                  Retry
                </button>
              </div>
            ) : analytics ? (
              <>
                <div className="analytics-stat-grid">
                  <article><span>Verified reports</span><b>{analytics.total_verified_reports}</b></article>
                  <article><span>Open reports</span><b>{analytics.open_reports}</b></article>
                  <article><span>Resolved reports</span><b>{analytics.resolved_reports}</b></article>
                </div>
                {analytics.total_verified_reports === 0 ? (
                  <div className="analytics-empty">
                    <b>No verified public reports yet</b>
                    <span>Reviewed India reports will appear here when available.</span>
                  </div>
                ) : null}
                <div className="analytics-chart-grid">
                    <section className="analytics-chart">
                      <h3>Severity distribution</h3>
                      {Object.entries(analytics.severity_distribution).map(([category, count]) => (
                        <div className="severity-row" key={category}>
                          <span>{category}</span>
                          <div className="severity-track">
                            <i
                              className={`severity-fill severity-${category}`}
                              style={{ width: `${(count / severityMaximum) * 100}%` }}
                            />
                          </div>
                          <b>{count}</b>
                        </div>
                      ))}
                    </section>
                    <section className="analytics-chart">
                      <h3>Monthly report trend</h3>
                      <div className="monthly-chart">
                        {analytics.monthly_submissions.map((item) => (
                          <div className="monthly-column" key={item.month}>
                            <b>{item.count}</b>
                            <i
                              style={{
                                height: `${item.count === 0 ? 2 : Math.max(8, (item.count / monthlyMaximum) * 100)}%`,
                              }}
                            />
                            <span>{item.month.slice(5)}</span>
                          </div>
                        ))}
                      </div>
                    </section>
                    <section className="analytics-chart">
                      <h3>Reports by state / union territory</h3>
                      {analytics.states.length === 0 ? (
                        <p className="analytics-chart-empty">No verified state labels are available.</p>
                      ) : (
                        <div className="geography-list">
                          {analytics.states.map((item) => (
                            <div className="geography-row" key={item.name}>
                              <span>{item.name}</span>
                              <div className="severity-track">
                                <i
                                  className="severity-fill"
                                  style={{ width: `${(item.report_count / geographyMaximum) * 100}%` }}
                                />
                              </div>
                              <b>{item.report_count}</b>
                              <small>{item.resolved_count} resolved</small>
                            </div>
                          ))}
                        </div>
                      )}
                      <p className="analytics-chart-note">
                        {analytics.state_unclassified_reports} reports have no recorded state label.
                      </p>
                    </section>
                    <section className="analytics-chart">
                      <h3>Top cities</h3>
                      {analytics.cities.length === 0 ? (
                        <p className="analytics-chart-empty">No verified city labels are available.</p>
                      ) : (
                        <div className="geography-list">
                          {analytics.cities.map((item) => (
                            <div className="geography-row" key={item.name}>
                              <span>{item.name}</span>
                              <div className="severity-track">
                                <i
                                  className="severity-fill"
                                  style={{ width: `${(item.report_count / geographyMaximum) * 100}%` }}
                                />
                              </div>
                              <b>{item.report_count}</b>
                              <small>{item.resolved_count} resolved</small>
                            </div>
                          ))}
                        </div>
                      )}
                      <p className="analytics-chart-note">
                        Top 10 cities; {analytics.city_unclassified_reports} reports have no city label.
                      </p>
                    </section>
                    <section className="analytics-chart">
                      <h3>Authority response and case closure</h3>
                      {analytics.authority_response.assigned_count === 0 ? (
                        <p className="analytics-chart-empty">
                          No eligible verified-report authority assignments are recorded yet.
                        </p>
                      ) : (
                        <>
                          <div className="authority-analytics-stats">
                            <span><b>{analytics.authority_response.assigned_count}</b> assigned</span>
                            <span><b>{analytics.authority_response.open_count}</b> open</span>
                            <span><b>{analytics.authority_response.completed_count}</b> completed</span>
                          </div>
                          <div className="geography-list">
                            {analytics.authority_response.by_authority.map((item) => (
                              <div className="authority-analytics-row" key={item.authority_id}>
                                <span>{item.authority_name}</span>
                                <b>{item.completed_count}/{item.assigned_count} closed</b>
                                <small>
                                  {item.average_completion_hours === null
                                    ? "Closure time unavailable"
                                    : `${item.average_completion_hours.toFixed(1)} h avg. to close`}
                                </small>
                              </div>
                            ))}
                          </div>
                        </>
                      )}
                      <p className="analytics-chart-note">
                        Assignment-to-completion time is a closure metric, not first-response time.
                        First-response timestamps are not captured yet.
                      </p>
                    </section>
                  </div>
                <p className="analytics-disclaimer">
                  Severity is the visual-box-v1 estimate, not a measurement of depth or road risk.
                  State and city groupings use available geocoded labels; unmatched records remain
                  unclassified.
                </p>
              </>
            ) : null}
          </section>
        </div>
      )}

      {searchResults.length > 0 && (
        <div className="search-results">
          <div className="search-results-title"><b>Location results</b><button onClick={() => setSearchResults([])}><X size={15} /></button></div>
          {searchResults.map((result, index) => (
            <button key={`${result.place_id ?? result.formatted_address}-${index}`} onClick={() => chooseResult(result)}>
              <MapPin size={15} /><span><b>{result.formatted_address}</b><small>{result.components.city || result.components.state_province || result.components.country || "Location"}</small></span>
            </button>
          ))}
        </div>
      )}

      {uploadOpen && (
        <div className="modal-backdrop" role="presentation">
          <section className="upload-modal" role="dialog" aria-modal="true" aria-labelledby="upload-title">
            <button className="modal-close" onClick={() => setUploadOpen(false)} aria-label="Close upload dialog"><X size={18} /></button>
            <span className="upload-icon"><Upload size={25} /></span>
            <p className="eyebrow">AI DETECTION PIPELINE</p>
            <h2 id="upload-title">Upload a road photograph</h2>
            <p>JPG, PNG, WEBP, BMP and TIFF. The original remains private and EXIF GPS is used only when present.</p>
            <label className="dropzone">
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp,image/bmp,image/tiff"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) void uploadImage(file);
                }}
              />
              <Upload size={22} />
              <b>{loading ? "Processing securely…" : "Choose an image"}</b>
              <span>Your file is uploaded directly to private storage.</span>
            </label>
            {uploadStatus && (
              <div className="upload-result">
                <div><span>Status</span><b>{uploadStatus.processing_status.replace("_", " ")}</b></div>
                <div><span>Scan</span><b>{uploadStatus.scan_status}</b></div>
                {uploadStatus.detection_run?.processing_ms != null && <div><span>Processing</span><b>{uploadStatus.detection_run.processing_ms} ms</b></div>}
                {uploadStatus.detection_run?.detections && <div><span>Potholes</span><b>{uploadStatus.detection_run.detections.length}</b></div>}
                {uploadStatus.detection_run?.annotated_download_url && <a href={uploadStatus.detection_run.annotated_download_url} target="_blank" rel="noreferrer">Download annotated image</a>}
              </div>
            )}
          </section>
        </div>
      )}
    </main>
  );
}
