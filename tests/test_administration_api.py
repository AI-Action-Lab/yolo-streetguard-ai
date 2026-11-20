from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from streetguard.database import get_session
from streetguard.main import create_app
from streetguard.models.core import (
    AuditLog,
    Authority,
    AuthorityAssignment,
    AuthorityMembership,
    Location,
    Report,
    ReportStatusHistory,
    User,
)
from streetguard.security.oidc import get_current_principal
from streetguard.security.principal import Principal
from streetguard.security.rbac import Role


class FakeScalarResult:
    def __init__(self, values: list[object]) -> None:
        self.values = values

    def first(self) -> object | None:
        return self.values[0] if self.values else None

    def all(self) -> list[object]:
        return self.values


class FakeRows:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self.rows = rows

    def first(self) -> tuple[object, ...] | None:
        return self.rows[0] if self.rows else None

    def all(self) -> list[tuple[object, ...]]:
        return self.rows


class FakeSession:
    def __init__(self) -> None:
        self.user = User(
            id=uuid4(),
            subject="operator",
            email="operator@example.org",
            is_active=True,
        )
        self.authority = Authority(
            id=uuid4(),
            name="Verified Roads Authority",
            category="municipal",
            is_verified=True,
            active=True,
        )
        self.location = Location(
            id=uuid4(),
            formatted_address="Main Road, Bengaluru",
            latitude=12.9716,
            longitude=77.5946,
        )
        self.report = Report(
            id=uuid4(),
            public_id="SG-IN-ABC123",
            status="verified",
            verification_status="verified",
            visibility="public",
            reporter_id=None,
            location_id=self.location.id,
            title="Pothole on Main Road",
            description="Road surface damage",
            severity="high",
        )
        self.assignment = AuthorityAssignment(
            id=uuid4(),
            report_id=self.report.id,
            authority_id=self.authority.id,
            assigned_by_id=self.user.id,
            assigned_at=datetime.now(UTC),
        )
        self.authority_ids = [self.authority.id]
        self.added: list[object] = []
        self.statements: list[object] = []

    async def scalars(self, statement: object) -> FakeScalarResult:
        entity = statement.column_descriptions[0]["entity"]  # type: ignore[attr-defined]
        if entity is User:
            return FakeScalarResult([self.user])
        if entity is Report:
            return FakeScalarResult([self.report])
        if entity is AuthorityAssignment:
            return FakeScalarResult([self.assignment] if self.assignment is not None else [])
        if entity is AuthorityMembership:
            name = statement.column_descriptions[0]["name"]  # type: ignore[attr-defined]
            return FakeScalarResult(self.authority_ids if name == "authority_id" else [])
        if entity is AuditLog:
            return FakeScalarResult([])
        return FakeScalarResult([])

    async def execute(self, statement: object) -> FakeRows:
        self.statements.append(statement)
        return FakeRows([(self.report, self.assignment, self.authority, self.location)])

    async def get(self, model: type[object], _: object) -> object | None:
        if model is User:
            return self.user
        if model is Authority:
            return self.authority
        if model is Location:
            return self.location
        if model is Report:
            return self.report
        return None

    def add(self, item: object) -> None:
        self.added.append(item)

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


def client_for(session: FakeSession, principal: Principal) -> TestClient:
    app = create_app()

    async def override_session() -> AsyncGenerator[FakeSession, None]:
        yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_principal] = lambda: principal
    return TestClient(app)


def test_admin_portal_requires_global_admin_role() -> None:
    session = FakeSession()
    principal = Principal(subject="regional-admin", roles=frozenset({Role.REGIONAL_ADMINISTRATOR}))

    with client_for(session, principal) as client:
        response = client.get("/api/v1/administration/audit-logs")

    assert response.status_code == 403


def test_admin_assigns_only_verified_reports_to_verified_authorities() -> None:
    session = FakeSession()
    session.assignment = None
    principal = Principal(subject="global-admin", roles=frozenset({Role.GLOBAL_ADMINISTRATOR}))

    with client_for(session, principal) as client:
        response = client.post(
            f"/api/v1/administration/reports/{session.report.public_id}/assign",
            json={
                "authority_id": str(session.authority.id),
                "notes": "Assigned to the verified jurisdiction",
                "confirmed": True,
            },
        )

    assert response.status_code == 201
    assert session.report.status == "assigned_to_authority"
    assignment = next(item for item in session.added if isinstance(item, AuthorityAssignment))
    history = next(item for item in session.added if isinstance(item, ReportStatusHistory))
    audit = next(item for item in session.added if isinstance(item, AuditLog))
    assert assignment.authority_id == session.authority.id
    assert history.to_status == "assigned_to_authority"
    assert audit.action == "report.authority_assigned"


def test_authority_portal_requires_membership_and_enforces_resolution_order() -> None:
    session = FakeSession()
    principal = Principal(
        subject=session.user.subject,
        roles=frozenset({Role.MUNICIPAL_AUTHORITY}),
    )

    with client_for(session, principal) as client:
        invalid_initial_transition = client.post(
            f"/api/v1/authority/reports/{session.report.public_id}/status",
            json={"status": "in_progress", "notes": "Started repair work", "confirmed": True},
        )
        session.report.status = "assigned_to_authority"
        invalid_order = client.post(
            f"/api/v1/authority/reports/{session.report.public_id}/status",
            json={"status": "resolved", "notes": "Road repaired", "confirmed": True},
        )
        started = client.post(
            f"/api/v1/authority/reports/{session.report.public_id}/status",
            json={"status": "in_progress", "notes": "Repair work started", "confirmed": True},
        )
        resolved = client.post(
            f"/api/v1/authority/reports/{session.report.public_id}/status",
            json={"status": "resolved", "notes": "Road repair completed", "confirmed": True},
        )

    assert invalid_initial_transition.status_code == 409
    assert invalid_order.status_code == 409
    assert started.status_code == 200
    assert started.json()["status"] == "in_progress"
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"
    assert session.assignment.completed_at is not None
    assert session.report.resolved_at is not None
    assert any(
        isinstance(item, AuditLog) and item.action == "report.authority_status_changed"
        for item in session.added
    )


def test_authority_user_without_membership_cannot_read_assigned_reports() -> None:
    session = FakeSession()
    session.authority_ids = []
    principal = Principal(
        subject=session.user.subject,
        roles=frozenset({Role.MUNICIPAL_AUTHORITY}),
    )

    with client_for(session, principal) as client:
        response = client.get("/api/v1/authority/reports")

    assert response.status_code == 200
    assert response.json() == []


def test_authorization_header_is_allowed_by_api_cors() -> None:
    with TestClient(create_app()) as client:
        response = client.options(
            "/api/v1/authority/reports",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        )

    assert response.status_code == 200
    assert "authorization" in response.headers["access-control-allow-headers"].lower()
