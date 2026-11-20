from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from streetguard.config import Settings, get_settings
from streetguard.database import get_session
from streetguard.domain.geography import AddressComponents, GeocodingResult, LocationSource
from streetguard.geocoding import (
    GeocodingNotConfiguredError,
    GeocodingProviderError,
    GoogleGeocoder,
)
from streetguard.models.core import Location

router = APIRouter(prefix="/locations", tags=["locations"])


class LocationConfirmationRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_meters: float | None = Field(default=None, ge=0)
    source: LocationSource
    confirmed: bool
    reverse_geocode: bool = True


class LocationConfirmationResponse(BaseModel):
    id: str
    latitude: float
    longitude: float
    source: LocationSource
    confirmed_by_user: bool
    address: AddressComponents | None
    formatted_address: str | None
    provider: str | None
    place_id: str | None


@router.get("/reverse", response_model=list[GeocodingResult])
async def reverse_geocode(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    settings: Settings = Depends(get_settings),
) -> list[GeocodingResult]:
    try:
        return await GoogleGeocoder(settings).reverse(latitude, longitude)
    except GeocodingNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except GeocodingProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/confirm", response_model=LocationConfirmationResponse, status_code=201)
async def confirm_location(
    payload: LocationConfirmationRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> LocationConfirmationResponse:
    if not payload.confirmed:
        raise HTTPException(status_code=422, detail="The selected location must be confirmed")

    geocoded: GeocodingResult | None = None
    if payload.reverse_geocode:
        try:
            results = await GoogleGeocoder(settings).reverse(payload.latitude, payload.longitude)
            geocoded = results[0] if results else None
        except GeocodingNotConfiguredError:
            geocoded = None
        except GeocodingProviderError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    if settings.product_country_code == "IN" and not (
        6.0 <= payload.latitude <= 37.5 and 68.0 <= payload.longitude <= 97.5
    ):
        raise HTTPException(
            status_code=422,
            detail="Selected coordinates are outside the India product scope",
        )
    if (
        settings.product_country_code == "IN"
        and settings.strict_country_scope
        and (geocoded is None or geocoded.components.country_code != settings.product_country_code)
    ):
        raise HTTPException(
            status_code=422,
            detail="Selected coordinates could not be verified within India",
        )

    location_id = uuid4()
    location = Location(
        id=location_id,
        coordinates=func.ST_GeogFromText(
            f"SRID=4326;POINT({payload.longitude} {payload.latitude})"
        ),
        longitude=payload.longitude,
        latitude=payload.latitude,
        source=payload.source,
        accuracy_meters=payload.accuracy_meters,
        confirmed_by_user=True,
        formatted_address=geocoded.formatted_address if geocoded else None,
        provider=geocoded.provider if geocoded else None,
        provider_place_id=geocoded.place_id if geocoded else None,
        provider_metadata=(geocoded.components.model_dump(exclude_none=True) if geocoded else {}),
    )
    session.add(location)
    await session.commit()
    return LocationConfirmationResponse(
        id=str(location_id),
        latitude=payload.latitude,
        longitude=payload.longitude,
        source=payload.source,
        confirmed_by_user=True,
        address=geocoded.components if geocoded else None,
        formatted_address=geocoded.formatted_address if geocoded else None,
        provider=geocoded.provider if geocoded else None,
        place_id=geocoded.place_id if geocoded else None,
    )
