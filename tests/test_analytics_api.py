from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError

from streetguard.database import get_session
from streetguard.main import create_app


class FakeResult:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self._rows = rows

    def all(self) -> list[tuple[object, ...]]:
        return self._rows

    def tuples(self) -> "FakeResult":
        return self


class FakeSession:
    def __init__(self, results: list[list[tuple[object, ...]]]) -> None:
        self.results = results
        self.statements: list[object] = []

    async def execute(self, statement: object) -> FakeResult:
        self.statements.append(statement)
        return FakeResult(self.results[len(self.statements) - 1])


class FailedSession:
    async def execute(self, statement: object) -> FakeResult:
        raise SQLAlchemyError("database unavailable")


def client_for(session: FakeSession | FailedSession) -> TestClient:
    app = create_app()

    async def override_session() -> AsyncGenerator[object, None]:
        yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


def test_analytics_summary_uses_only_public_verified_india_reports() -> None:
    now = datetime.now(UTC)
    authority_id = uuid4()
    session = FakeSession(
        [
            [("verified", 3), ("in_progress", 2), ("resolved", 1)],
            [("low", 2), ("critical", 1), (None, 3)],
            [(now.replace(day=1, hour=0, minute=0, second=0, microsecond=0), 4)],
            [("Karnataka", 4, 1), ("Maharashtra", 2, 1)],
            [("Bengaluru", 3, 1), ("Mumbai", 2, 1)],
            [(0, 1)],
            [(3, 1, 24.5)],
            [(authority_id, "Bengaluru Roads", 2, 1, 24.5)],
        ]
    )

    with client_for(session) as client:
        response = client.get("/api/v1/analytics/summary")

    assert response.status_code == 200
    summary = response.json()
    assert summary["country_code"] == "IN"
    assert summary["total_verified_reports"] == 6
    assert summary["open_reports"] == 5
    assert summary["resolved_reports"] == 1
    assert summary["severity_distribution"] == {
        "low": 2,
        "moderate": 0,
        "high": 0,
        "critical": 1,
        "unknown": 3,
    }
    assert len(summary["monthly_submissions"]) == 6
    assert summary["monthly_submissions"][-1] == {
        "month": now.strftime("%Y-%m"),
        "count": 4,
    }
    assert summary["states"] == [
        {"name": "Karnataka", "report_count": 4, "resolved_count": 1},
        {"name": "Maharashtra", "report_count": 2, "resolved_count": 1},
    ]
    assert summary["cities"][0] == {
        "name": "Bengaluru",
        "report_count": 3,
        "resolved_count": 1,
    }
    assert summary["state_unclassified_reports"] == 0
    assert summary["city_unclassified_reports"] == 1
    assert summary["authority_response"] == {
        "assigned_count": 3,
        "completed_count": 1,
        "open_count": 2,
        "average_completion_hours": 24.5,
        "first_response_time_available": False,
        "by_authority": [
            {
                "authority_id": str(authority_id),
                "authority_name": "Bengaluru Roads",
                "assigned_count": 2,
                "completed_count": 1,
                "average_completion_hours": 24.5,
            }
        ],
    }

    for statement in session.statements:
        compiled = statement.compile(dialect=postgresql.dialect())
        sql = str(compiled)
        assert "visibility" in sql
        assert "verification_status" in sql
        assert "longitude" in sql
        assert "latitude" in sql
        assert {"public", "verified", 68.0, 6.0, 97.5, 37.5}.issubset(compiled.params.values())
    assert "provider_metadata" in str(session.statements[3].compile(dialect=postgresql.dialect()))
    assert "provider_metadata" in str(session.statements[4].compile(dialect=postgresql.dialect()))
    assert (
        "state_province"
        in session.statements[3].compile(dialect=postgresql.dialect()).params.values()
    )
    assert "city" in session.statements[4].compile(dialect=postgresql.dialect()).params.values()
    assert "EXTRACT(epoch FROM" in str(session.statements[6].compile(dialect=postgresql.dialect()))
    for statement in session.statements[6:]:
        sql = str(statement)
        assert "active" in sql
        assert "is_verified" in sql


def test_analytics_summary_reports_database_unavailability() -> None:
    with client_for(FailedSession()) as client:
        response = client.get("/api/v1/analytics/summary")

    assert response.status_code == 503
    assert response.json()["detail"] == "Analytics data store is unavailable"
