from fastapi import APIRouter, Depends, HTTPException, Query

from streetguard.config import Settings, get_settings
from streetguard.domain.geography import CountryOption, GeocodingResult, SubdivisionOption
from streetguard.geocoding import (
    GeocodingNotConfiguredError,
    GeocodingProviderError,
    GoogleGeocoder,
)
from streetguard.geography_catalog import countries, subdivisions

router = APIRouter(prefix="/geography", tags=["geography"])


@router.get("/countries", response_model=list[CountryOption])
async def list_countries(
    settings: Settings = Depends(get_settings),
) -> list[CountryOption]:
    scope = settings.product_country_code.upper()
    return [country for country in countries() if country.code == scope]


@router.get("/countries/{country_code}/subdivisions", response_model=list[SubdivisionOption])
async def list_subdivisions(
    country_code: str,
    settings: Settings = Depends(get_settings),
) -> list[SubdivisionOption]:
    if country_code.upper() != settings.product_country_code.upper():
        raise HTTPException(status_code=404, detail="Country is outside the active product scope")
    values = subdivisions(country_code)
    if not values:
        raise HTTPException(
            status_code=404,
            detail="Country is unknown or has no published subdivision catalogue",
        )
    return values


@router.get("/search", response_model=list[GeocodingResult])
async def search_geography(
    query: str = Query(min_length=2, max_length=300),
    settings: Settings = Depends(get_settings),
) -> list[GeocodingResult]:
    try:
        return await GoogleGeocoder(settings).search(query)
    except GeocodingNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except GeocodingProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
