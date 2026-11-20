from typing import Any

from fastapi.testclient import TestClient

from streetguard.config import get_settings
from streetguard.database import get_session
from streetguard.main import create_app


class FakeSession:
    def __init__(self) -> None:
        self.added: list[Any] = []

    def add(self, value: Any) -> None:
        self.added.append(value)

    async def commit(self) -> None:
        return None


def test_location_confirmation_without_geocoder_preserves_manual_source(settings) -> None:
    session = FakeSession()
    app = create_app()

    async def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_settings] = lambda: settings

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/locations/confirm",
            json={
                "latitude": 23.0225,
                "longitude": 72.5714,
                "accuracy_meters": 15,
                "source": "manual_coordinates",
                "confirmed": True,
                "reverse_geocode": False,
            },
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["latitude"] == 23.0225
    assert payload["source"] == "manual_coordinates"
    assert payload["confirmed_by_user"] is True
    assert payload["address"] is None
    assert payload["provider"] is None
    assert len(session.added) == 1


def test_location_confirmation_requires_user_confirmation(settings) -> None:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/locations/confirm",
            json={
                "latitude": 23.0225,
                "longitude": 72.5714,
                "source": "map_pin",
                "confirmed": False,
                "reverse_geocode": False,
            },
        )

    assert response.status_code == 422
    assert "must be confirmed" in response.json()["detail"]


def test_location_confirmation_rejects_obvious_out_of_india_coordinates(settings) -> None:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/locations/confirm",
            json={
                "latitude": 51.5072,
                "longitude": -0.1276,
                "source": "manual_coordinates",
                "confirmed": True,
                "reverse_geocode": False,
            },
        )

    assert response.status_code == 422
    assert "outside the India" in response.json()["detail"]
