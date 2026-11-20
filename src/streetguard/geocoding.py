from __future__ import annotations

from typing import Any

import httpx

from streetguard.config import Settings
from streetguard.domain.geography import AddressComponents, GeocodingResult


class GeocodingNotConfiguredError(RuntimeError):
    pass


class GeocodingProviderError(RuntimeError):
    pass


def parse_address_components(raw: list[dict[str, Any]]) -> AddressComponents:
    by_type: dict[str, dict[str, Any]] = {}
    for component in raw:
        for component_type in component.get("types", []):
            by_type.setdefault(str(component_type), component)

    def value(component_type: str) -> str | None:
        component = by_type.get(component_type)
        raw_value = component.get("long_name") if component else None
        return str(raw_value) if raw_value is not None else None

    country = by_type.get("country")
    country_code = country.get("short_name") if country else None
    return AddressComponents(
        country=value("country"),
        country_code=str(country_code).upper() if country_code else None,
        state_province=value("administrative_area_level_1"),
        district=value("administrative_area_level_2") or value("administrative_area_level_3"),
        city=value("locality") or value("postal_town"),
        locality=value("sublocality") or value("neighborhood"),
        postal_code=value("postal_code"),
        road=value("route"),
    )


class GoogleGeocoder:
    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.google_maps_api_key
        self._base_url = str(settings.google_geocoding_base_url)
        self._timeout = settings.geocoding_timeout_seconds
        self._country_scope = settings.product_country_code.lower()

    async def search(self, query: str) -> list[GeocodingResult]:
        if not query.strip():
            return []
        return await self._request(
            {
                "address": query.strip(),
                "region": self._country_scope,
                "components": f"country:{self._country_scope}",
            }
        )

    async def reverse(self, latitude: float, longitude: float) -> list[GeocodingResult]:
        return await self._request({"latlng": f"{latitude},{longitude}"})

    async def _request(self, query_params: dict[str, str]) -> list[GeocodingResult]:
        if not self._api_key:
            raise GeocodingNotConfiguredError(
                "Google geocoding is not configured; use a manual map pin or coordinates"
            )
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(
                    self._base_url,
                    params={**query_params, "key": self._api_key},
                )
                response.raise_for_status()
                payload: dict[str, Any] = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise GeocodingProviderError("Google geocoding request failed") from exc

        provider_status = str(payload.get("status", "UNKNOWN_ERROR"))
        if provider_status == "ZERO_RESULTS":
            return []
        if provider_status != "OK":
            error = str(payload.get("error_message") or provider_status)
            raise GeocodingProviderError(f"Google geocoding returned {error}")
        results = payload.get("results")
        if not isinstance(results, list):
            raise GeocodingProviderError("Google geocoding response is malformed")
        parsed = [self._parse_result(result) for result in results if isinstance(result, dict)]
        return [
            result
            for result in parsed
            if result.components.country_code == self._country_scope.upper()
        ]

    @staticmethod
    def _parse_result(raw: dict[str, Any]) -> GeocodingResult:
        geometry = raw.get("geometry")
        location = geometry.get("location") if isinstance(geometry, dict) else None
        components = raw.get("address_components")
        if (
            not isinstance(location, dict)
            or not isinstance(location.get("lat"), (float, int))
            or not isinstance(location.get("lng"), (float, int))
            or not isinstance(components, list)
        ):
            raise GeocodingProviderError("Google geocoding result is missing required fields")
        formatted_address = raw.get("formatted_address")
        return GeocodingResult(
            formatted_address=str(formatted_address or "Address unavailable"),
            latitude=float(location["lat"]),
            longitude=float(location["lng"]),
            place_id=str(raw.get("place_id")) if raw.get("place_id") else None,
            components=parse_address_components(components),
        )
