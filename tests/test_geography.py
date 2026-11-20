import pytest
from fastapi.testclient import TestClient

from streetguard.config import Settings
from streetguard.geocoding import (
    GeocodingNotConfiguredError,
    GoogleGeocoder,
    parse_address_components,
)
from streetguard.geography_catalog import countries, subdivisions
from streetguard.main import create_app


def test_global_catalogue_is_not_hardcoded_to_one_country() -> None:
    catalogue = countries()

    assert len(catalogue) == 249
    assert "IN" in {country.code for country in catalogue}
    assert "US" in {country.code for country in catalogue}
    assert "BR" in {country.code for country in catalogue}


def test_subdivisions_use_source_defined_global_types() -> None:
    india = subdivisions("IN")
    united_states = subdivisions("US")

    assert any(item.code == "IN-GJ" for item in india)
    assert any(item.code == "US-CA" and item.type == "State" for item in united_states)
    assert subdivisions("ZZ") == []


def test_address_components_preserve_unknown_values_as_none() -> None:
    components = parse_address_components(
        [
            {"long_name": "Canada", "short_name": "CA", "types": ["country"]},
            {
                "long_name": "Ontario",
                "short_name": "ON",
                "types": ["administrative_area_level_1"],
            },
            {"long_name": "M5V 3L9", "short_name": "M5V 3L9", "types": ["postal_code"]},
        ]
    )

    assert components.country == "Canada"
    assert components.country_code == "CA"
    assert components.state_province == "Ontario"
    assert components.city is None
    assert components.road is None


@pytest.mark.asyncio
async def test_geocoder_reports_missing_provider_configuration() -> None:
    geocoder = GoogleGeocoder(Settings(google_maps_api_key=""))

    with pytest.raises(GeocodingNotConfiguredError, match="not configured"):
        await geocoder.search("Ahmedabad")


def test_geography_routes_expose_global_catalogue_and_safe_error(client: TestClient) -> None:
    countries_response = client.get("/api/v1/geography/countries")
    search_response = client.get("/api/v1/geography/search", params={"query": "Ahmedabad"})

    assert countries_response.status_code == 200
    assert [country["code"] for country in countries_response.json()] == ["IN"]
    assert search_response.status_code == 503
    assert "manual map pin" in search_response.json()["detail"]


def test_geography_api_rejects_non_india_subdivisions(client: TestClient) -> None:
    response = client.get("/api/v1/geography/countries/US/subdivisions")

    assert response.status_code == 404
    assert "outside" in response.json()["detail"]


def test_cors_allows_configured_frontend_origin() -> None:
    settings = Settings(cors_origins="http://localhost:3000,https://streetguard.example")
    assert settings.allowed_cors_origins == [
        "http://localhost:3000",
        "https://streetguard.example",
    ]

    app = create_app()
    response = TestClient(app).options(
        "/api/v1/geography/countries",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
