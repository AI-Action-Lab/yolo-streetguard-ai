from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from geoalchemy2 import Geometry
from pydantic import BaseModel, ConfigDict
from sqlalchemy import cast, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from streetguard.config import Settings, get_settings
from streetguard.database import get_session
from streetguard.models.core import Location, Report

router = APIRouter(prefix="/map", tags=["map"])


class MarkerProperties(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_id: str
    status: str
    verification_status: str
    severity: str | None
    detection_count: int
    marker_category: str


class GeoJsonFeature(BaseModel):
    type: str = "Feature"
    geometry: dict[str, Any]
    properties: MarkerProperties


class MarkerCollection(BaseModel):
    type: str = "FeatureCollection"
    features: list[GeoJsonFeature]


class ClusterFeature(BaseModel):
    type: str = "Feature"
    geometry: dict[str, Any]
    properties: dict[str, int]


class ClusterCollection(BaseModel):
    type: str = "FeatureCollection"
    features: list[ClusterFeature]


def validate_bounds(
    minimum_longitude: float,
    minimum_latitude: float,
    maximum_longitude: float,
    maximum_latitude: float,
    settings: Settings,
) -> None:
    if minimum_longitude >= maximum_longitude or minimum_latitude >= maximum_latitude:
        raise HTTPException(
            status_code=422,
            detail="Minimum map bounds must be below maximum bounds",
        )
    longitude_span = maximum_longitude - minimum_longitude
    latitude_span = maximum_latitude - minimum_latitude
    if max(longitude_span, latitude_span) > settings.map_max_span_degrees:
        raise HTTPException(
            status_code=422,
            detail=f"Map viewport exceeds the {settings.map_max_span_degrees}-degree limit",
        )
    if settings.product_country_code == "IN" and (
        maximum_longitude < 68.0
        or minimum_longitude > 97.5
        or maximum_latitude < 6.0
        or minimum_latitude > 37.5
    ):
        raise HTTPException(status_code=422, detail="Viewport is outside the India product scope")


def marker_category(status: str, verification_status: str, severity: str | None) -> str:
    if status in {"resolved", "rejected", "duplicate"}:
        return status
    if severity == "critical":
        return "critical"
    if verification_status == "verified":
        return "verified"
    return "awaiting_review"


@router.get("/markers", response_model=MarkerCollection)
async def list_markers(
    minimum_longitude: float = Query(ge=-180, le=180),
    minimum_latitude: float = Query(ge=-90, le=90),
    maximum_longitude: float = Query(ge=-180, le=180),
    maximum_latitude: float = Query(ge=-90, le=90),
    limit: int = Query(default=500, ge=1, le=1_000),
    status: str | None = Query(default=None, max_length=50),
    severity: str | None = Query(default=None, max_length=30),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> MarkerCollection:
    validate_bounds(
        minimum_longitude,
        minimum_latitude,
        maximum_longitude,
        maximum_latitude,
        settings,
    )
    limit = min(limit, settings.map_max_markers)
    point = cast(Location.coordinates, Geometry(geometry_type="POINT", srid=4326))
    envelope = func.ST_MakeEnvelope(
        minimum_longitude,
        minimum_latitude,
        maximum_longitude,
        maximum_latitude,
        4326,
    )
    statement = (
        select(
            Report.public_id,
            Report.status,
            Report.verification_status,
            Report.severity,
            Report.detection_count,
            func.ST_X(point).label("longitude"),
            func.ST_Y(point).label("latitude"),
        )
        .join(Location, Report.location_id == Location.id)
        .where(
            Report.visibility == "public",
            func.ST_Intersects(point, envelope),
            *(
                [
                    Location.longitude.between(68.0, 97.5),
                    Location.latitude.between(6.0, 37.5),
                ]
                if settings.product_country_code == "IN"
                else []
            ),
        )
        .order_by(Report.created_at.desc())
        .limit(limit)
    )
    if status:
        statement = statement.where(Report.status == status)
    if severity:
        statement = statement.where(Report.severity == severity)

    try:
        rows = (await session.execute(statement)).mappings().all()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Map data store is unavailable",
        ) from exc
    features = [
        GeoJsonFeature(
            geometry={
                "type": "Point",
                "coordinates": [float(row["longitude"]), float(row["latitude"])],
            },
            properties=MarkerProperties(
                report_id=str(row["public_id"]),
                status=str(row["status"]),
                verification_status=str(row["verification_status"]),
                severity=row["severity"],
                detection_count=int(row["detection_count"]),
                marker_category=marker_category(
                    str(row["status"]),
                    str(row["verification_status"]),
                    row["severity"],
                ),
            ),
        )
        for row in rows
    ]
    return MarkerCollection(features=features)


@router.get("/clusters", response_model=ClusterCollection)
async def list_clusters(
    minimum_longitude: float = Query(ge=-180, le=180),
    minimum_latitude: float = Query(ge=-90, le=90),
    maximum_longitude: float = Query(ge=-180, le=180),
    maximum_latitude: float = Query(ge=-90, le=90),
    zoom: int = Query(ge=0, le=22),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ClusterCollection:
    validate_bounds(
        minimum_longitude,
        minimum_latitude,
        maximum_longitude,
        maximum_latitude,
        settings,
    )
    point = cast(Location.coordinates, Geometry(geometry_type="POINT", srid=4326))
    envelope = func.ST_MakeEnvelope(
        minimum_longitude,
        minimum_latitude,
        maximum_longitude,
        maximum_latitude,
        4326,
    )
    grid_size = max(0.0005, 180 / (2**zoom) / 4)
    grid = func.ST_SnapToGrid(point, grid_size)
    collection = func.ST_Collect(point)
    statement = (
        select(
            func.count().label("count"),
            func.ST_X(func.ST_Centroid(collection)).label("longitude"),
            func.ST_Y(func.ST_Centroid(collection)).label("latitude"),
        )
        .select_from(Report)
        .join(Location, Report.location_id == Location.id)
        .where(
            Report.visibility == "public",
            func.ST_Intersects(point, envelope),
            *(
                [
                    Location.longitude.between(68.0, 97.5),
                    Location.latitude.between(6.0, 37.5),
                ]
                if settings.product_country_code == "IN"
                else []
            ),
        )
        .group_by(grid)
        .limit(settings.map_max_markers)
    )
    try:
        rows = (await session.execute(statement)).mappings().all()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Map data store is unavailable",
        ) from exc
    return ClusterCollection(
        features=[
            ClusterFeature(
                geometry={
                    "type": "Point",
                    "coordinates": [float(row["longitude"]), float(row["latitude"])],
                },
                properties={"point_count": int(row["count"])},
            )
            for row in rows
        ]
    )
