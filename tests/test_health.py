from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from streetguard.api import health


def test_liveness_does_not_require_database(client: TestClient) -> None:
    response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_documents_health_api(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    assert "/api/v1/health/live" in schema["paths"]
    assert "/api/v1/health/ready" in schema["paths"]


def test_readiness_reports_database_unavailable(client: TestClient, monkeypatch) -> None:
    class UnavailableSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            del exc_type, exc, traceback
            return None

        async def execute(self, statement):
            assert str(statement) == "SELECT 1"
            raise SQLAlchemyError("database offline")

    monkeypatch.setattr(health, "SessionFactory", UnavailableSession)

    response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database is not ready"}
