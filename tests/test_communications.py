from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from email.message import EmailMessage
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import Select

from streetguard.api.communications import (
    record_report_status_notification,
    send_report_email,
)
from streetguard.api.communications_schemas import ReportEmailRequest
from streetguard.communications import (
    EmailProviderNotConfigured,
    report_email_content,
    send_smtp_email,
    valid_email_address,
)
from streetguard.config import Settings
from streetguard.database import get_session
from streetguard.main import create_app
from streetguard.models.core import (
    AuditLog,
    Authority,
    EmailDeliveryLog,
    Location,
    Notification,
    Report,
    User,
)
from streetguard.reporting import get_or_create_user
from streetguard.security.oidc import get_current_principal
from streetguard.security.principal import Principal
from streetguard.security.rbac import Role


class FakeSMTP:
    instances: list["FakeSMTP"] = []

    def __init__(self, host: str, port: int, *, timeout: float) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.logged_in = False
        self.message: EmailMessage | None = None
        self.instances.append(self)

    def __enter__(self) -> "FakeSMTP":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def starttls(self, *, context: object) -> None:
        self.started_tls = context is not None

    def login(self, username: str, password: str) -> None:
        self.logged_in = username == "streetguard" and password == "smtp-secret"

    def send_message(self, message: EmailMessage) -> None:
        self.message = message


class FakeResult:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self._rows = rows

    def all(self) -> list[tuple[object, ...]]:
        return self._rows


class AuthorityUserResult:
    def __init__(self, user: User | None) -> None:
        self.user = user

    def first(self) -> User | None:
        return self.user


class AuthoritySession:
    def __init__(
        self,
        rows: list[tuple[object, ...]] | None = None,
        *,
        user: User | None = None,
    ) -> None:
        self.rows = rows or []
        self.user = user
        self.added: list[object] = []
        self.statement: object | None = None

    async def scalars(self, _: Select[tuple[User]]) -> AuthorityUserResult:
        return AuthorityUserResult(self.user)

    async def execute(self, statement: Select[tuple[Authority, str | None]]) -> FakeResult:
        self.statement = statement
        return FakeResult(self.rows)

    async def get(self, *_: object) -> None:
        return None

    def add(self, item: object) -> None:
        self.added.append(item)

    async def commit(self) -> None:
        return None

    async def refresh(self, _: object) -> None:
        return None


class StatusNotificationSession:
    def __init__(self, user: User, location: Location) -> None:
        self.user = user
        self.location = location
        self.added: list[object] = []
        self.commit_count = 0

    async def get(self, model: type[object], _: object) -> User | Location | None:
        if model is User:
            return self.user
        if model is Location:
            return self.location
        return None

    def add(self, item: object) -> None:
        self.added.append(item)

    async def commit(self) -> None:
        self.commit_count += 1


class UserLookupResult:
    def __init__(self, user: User | None) -> None:
        self.user = user

    def first(self) -> User | None:
        return self.user


class UserLookupSession:
    def __init__(self, user: User | None) -> None:
        self.user = user

    async def scalars(self, _: object) -> UserLookupResult:
        return UserLookupResult(self.user)

    def add(self, _: object) -> None:
        return None

    async def flush(self) -> None:
        return None


class ReportEmailResults:
    def __init__(self, value: object | None) -> None:
        self.value = value

    def first(self) -> object | None:
        return self.value


class ReportEmailSession:
    def __init__(
        self,
        report: Report,
        user: User,
        location: Location,
        *,
        recent_attempts: int = 0,
    ) -> None:
        self.report = report
        self.user = user
        self.location = location
        self.recent_attempts = recent_attempts
        self.added: list[object] = []
        self.commit_count = 0

    async def scalars(self, statement: Select[tuple[object]]) -> ReportEmailResults:
        entity = statement.column_descriptions[0]["entity"]
        if entity is Report:
            return ReportEmailResults(self.report)
        if entity is User:
            return ReportEmailResults(self.user)
        return ReportEmailResults(None)

    async def scalar(self, _: object) -> int:
        return self.recent_attempts

    async def get(self, model: type[object], _: object) -> object | None:
        if model is Location:
            return self.location
        return None

    def add(self, item: object) -> None:
        self.added.append(item)

    async def commit(self) -> None:
        self.commit_count += 1

    async def refresh(self, item: object) -> None:
        if isinstance(item, EmailDeliveryLog):
            item.id = uuid4()
            item.created_at = datetime.now(UTC)

    async def rollback(self) -> None:
        return None


def client_for_authority_session(
    session: AuthoritySession,
    *,
    principal: Principal | None = None,
) -> TestClient:
    app = create_app()

    async def override_session() -> AsyncGenerator[AuthoritySession, None]:
        yield session

    app.dependency_overrides[get_session] = override_session
    if principal is not None:
        app.dependency_overrides[get_current_principal] = lambda: principal
    return TestClient(app)


def test_email_address_validation_rejects_header_injection() -> None:
    assert valid_email_address("reports@example.org")
    assert not valid_email_address("reports@example.org\r\nBcc: other@example.org")
    assert not valid_email_address("not-an-address")


def test_report_email_contains_public_link_and_no_coordinates() -> None:
    settings = Settings(app_env="test", public_base_url="https://streetguard.example")
    report = Report(
        id=uuid4(),
        public_id="SG-IN-ABC123",
        status="verified",
        visibility="public",
        title="Pothole on Main Road",
        severity="high",
    )
    location = Location(
        formatted_address="Main Road, Bengaluru",
        latitude=12.9716,
        longitude=77.5946,
    )

    subject, body = report_email_content(report, location, settings)

    assert subject == "Road damage report: SG-IN-ABC123"
    assert "Main Road, Bengaluru" in body
    assert "https://streetguard.example/track/SG-IN-ABC123" in body
    assert "12.9716" not in body
    assert "77.5946" not in body


def test_private_status_email_does_not_link_to_public_tracker() -> None:
    settings = Settings(app_env="test", public_base_url="https://streetguard.example")
    report = Report(
        id=uuid4(),
        public_id="SG-IN-ABC123",
        status="awaiting_verification",
        visibility="private",
    )
    location = Location(
        formatted_address="Main Road, Bengaluru",
        latitude=12.9716,
        longitude=77.5946,
    )

    _, body = report_email_content(report, location, settings, status_update=True)

    assert "https://streetguard.example/track/SG-IN-ABC123" not in body
    assert "not publicly visible" in body


@pytest.mark.asyncio
async def test_smtp_sender_uses_starttls_auth_and_plain_report_content(monkeypatch) -> None:
    FakeSMTP.instances.clear()
    monkeypatch.setattr("streetguard.communications.smtplib.SMTP", FakeSMTP)
    settings = Settings(
        app_env="test",
        smtp_host="smtp.example.org",
        smtp_username="streetguard",
        smtp_password="smtp-secret",
        smtp_from_email="reports@example.org",
        smtp_starttls=True,
    )

    message_id = await send_smtp_email(
        settings,
        "authority@example.org",
        "Report: SG-IN-ABC123",
        "View report: https://streetguard.example/track/SG-IN-ABC123",
    )

    smtp = FakeSMTP.instances[0]
    assert smtp.started_tls
    assert smtp.logged_in
    assert smtp.message is not None
    assert smtp.message["To"] == "authority@example.org"
    assert smtp.message["Message-ID"] == message_id
    assert "View report:" in smtp.message.get_content()


@pytest.mark.asyncio
async def test_smtp_sender_fails_explicitly_when_not_configured() -> None:
    with pytest.raises(EmailProviderNotConfigured):
        await send_smtp_email(
            Settings(app_env="test"),
            "authority@example.org",
            "Report",
            "Report body",
        )


def test_communications_mutations_require_authentication() -> None:
    with TestClient(create_app()) as client:
        authority = client.post(
            "/api/v1/authorities",
            json={"name": "City Roads", "category": "municipal"},
        )
        report_email = client.post(
            "/api/v1/reports/SG-IN-ABC123/email",
            json={"recipient_email": "authority@example.org", "confirmed": True},
        )
        preferences = client.put(
            "/api/v1/notifications/preferences",
            json={"email_status_notifications_enabled": True, "confirmed": True},
        )

    assert authority.status_code == 401
    assert report_email.status_code == 401
    assert preferences.status_code == 401


def test_public_authority_directory_only_queries_verified_active_records() -> None:
    authority = Authority(
        id=uuid4(),
        name="Bengaluru Road Authority",
        category="municipal",
        contact_email="roads@example.org",
        jurisdiction_region_id=uuid4(),
        is_verified=True,
        active=True,
    )
    session = AuthoritySession([(authority, "Bengaluru")])

    with client_for_authority_session(session) as client:
        response = client.get("/api/v1/authorities")

    assert response.status_code == 200
    assert response.json()[0]["name"] == "Bengaluru Road Authority"
    assert response.json()[0]["jurisdiction_name"] == "Bengaluru"
    assert "is_verified" in str(session.statement)
    assert "active" in str(session.statement)


def test_authority_creation_is_unverified_and_audited() -> None:
    session = AuthoritySession()
    principal = Principal(subject="global-admin", roles=frozenset({Role.GLOBAL_ADMINISTRATOR}))

    with client_for_authority_session(session, principal=principal) as client:
        response = client.post(
            "/api/v1/authorities",
            json={
                "name": "Bengaluru Road Authority",
                "category": "municipal",
                "contact_email": "roads@example.org",
            },
        )

    assert response.status_code == 201
    assert response.json()["is_verified"] is False
    audit = next(item for item in session.added if isinstance(item, AuditLog))
    assert audit.action == "authority.created"
    assert audit.after_state is not None
    assert audit.after_state["is_verified"] is False


def test_inactive_global_admin_cannot_mutate_authorities() -> None:
    admin = User(id=uuid4(), subject="global-admin", is_active=False)
    session = AuthoritySession(user=admin)
    principal = Principal(subject=admin.subject, roles=frozenset({Role.GLOBAL_ADMINISTRATOR}))
    authority_id = uuid4()
    requests = [
        (
            "POST",
            "/api/v1/authorities",
            {"name": "Bengaluru Roads", "category": "municipal"},
        ),
        (
            "PUT",
            f"/api/v1/authorities/{authority_id}",
            {"name": "Bengaluru Roads", "category": "municipal", "active": True},
        ),
        (
            "POST",
            f"/api/v1/authorities/{authority_id}/verify",
            {"evidence_url": "https://example.org/evidence", "confirmed": True},
        ),
    ]

    with client_for_authority_session(session, principal=principal) as client:
        responses = [
            client.request(method, path, json=payload) for method, path, payload in requests
        ]

    assert [response.status_code for response in responses] == [403, 403, 403]
    assert session.added == []


def test_authority_creation_cannot_set_verified_from_request() -> None:
    session = AuthoritySession()
    principal = Principal(subject="global-admin", roles=frozenset({Role.GLOBAL_ADMINISTRATOR}))

    with client_for_authority_session(session, principal=principal) as client:
        response = client.post(
            "/api/v1/authorities",
            json={
                "name": "Bengaluru Road Authority",
                "category": "municipal",
                "is_verified": True,
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_user_sync_requires_verified_oidc_email_for_notification_consent() -> None:
    user = User(
        id=uuid4(),
        subject="reporter",
        email="old@example.org",
        email_verified=True,
        email_status_notifications_enabled=True,
    )
    session = UserLookupSession(user)

    result = await get_or_create_user(
        session, Principal(subject="reporter", email="new@example.org", email_verified=False)
    )

    assert result.email == "new@example.org"
    assert result.email_verified is False
    assert result.email_status_notifications_enabled is False
    assert result.email_notifications_confirmed_at is None


@pytest.mark.asyncio
async def test_status_email_is_only_sent_for_verified_opted_in_user(monkeypatch) -> None:
    user = User(
        id=uuid4(),
        subject="reporter",
        email="reporter@example.org",
        email_verified=False,
        email_status_notifications_enabled=True,
    )
    location = Location(
        id=uuid4(),
        formatted_address="Main Road, Bengaluru",
        latitude=12.9716,
        longitude=77.5946,
    )
    report = Report(
        id=uuid4(),
        public_id="SG-IN-ABC123",
        status="verified",
        title="Pothole on Main Road",
        severity="high",
        location_id=location.id,
    )
    session = StatusNotificationSession(user, location)
    settings = Settings(
        app_env="test",
        public_base_url="https://streetguard.example",
        smtp_host="smtp.example.org",
        smtp_from_email="reports@example.org",
    )
    sent: list[str] = []

    async def fake_send_email(*args: object) -> str:
        sent.append(str(args[1]))
        return "<message@example.org>"

    monkeypatch.setattr("streetguard.api.communications.send_smtp_email", fake_send_email)

    await record_report_status_notification(session, report, user.id, settings)

    assert sent == []
    assert any(isinstance(item, Notification) for item in session.added)
    assert not any(isinstance(item, EmailDeliveryLog) for item in session.added)

    user.email_verified = True
    session.added.clear()
    await record_report_status_notification(session, report, user.id, settings)

    delivery = next(item for item in session.added if isinstance(item, EmailDeliveryLog))
    assert sent == ["reporter@example.org"]
    assert delivery.purpose == "status_update"
    assert delivery.delivery_status == "accepted"


def report_email_fixture() -> tuple[Report, User, Location]:
    user_id = uuid4()
    location = Location(
        id=uuid4(),
        formatted_address="Main Road, Bengaluru",
        latitude=12.9716,
        longitude=77.5946,
    )
    user = User(id=user_id, subject="reporter", email="reporter@example.org")
    report = Report(
        id=uuid4(),
        public_id="SG-IN-ABC123",
        status="verified",
        verification_status="verified",
        visibility="public",
        reporter_id=user_id,
        location_id=location.id,
        title="Pothole on Main Road",
        severity="high",
    )
    return report, user, location


@pytest.mark.asyncio
async def test_report_email_is_owner_only_and_records_relay_acceptance(monkeypatch) -> None:
    report, user, location = report_email_fixture()
    session = ReportEmailSession(report, user, location)
    settings = Settings(
        app_env="test",
        smtp_host="smtp.example.org",
        smtp_from_email="reports@example.org",
    )
    recipients: list[str] = []

    async def fake_send_email(
        _: Settings,
        recipient: str,
        __: str,
        ___: str,
    ) -> str:
        recipients.append(recipient)
        return "<message@example.org>"

    monkeypatch.setattr("streetguard.api.communications.send_smtp_email", fake_send_email)
    response = await send_report_email(
        report.public_id,
        ReportEmailRequest(recipient_email="authority@example.org", confirmed=True),
        session,  # type: ignore[arg-type]
        Principal(subject="reporter"),
        settings,
    )

    delivery = next(item for item in session.added if isinstance(item, EmailDeliveryLog))
    assert response.delivery_status == "accepted"
    assert recipients == ["authority@example.org"]
    assert delivery.delivery_status == "accepted"
    assert delivery.purpose == "report_share"

    report.reporter_id = uuid4()
    with pytest.raises(HTTPException) as error:
        await send_report_email(
            report.public_id,
            ReportEmailRequest(recipient_email="authority@example.org", confirmed=True),
            session,  # type: ignore[arg-type]
            Principal(subject="reporter"),
            settings,
        )
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_report_email_rate_limit_prevents_delivery(monkeypatch) -> None:
    report, user, location = report_email_fixture()
    session = ReportEmailSession(report, user, location, recent_attempts=5)

    async def unexpected_send(*_: object) -> str:
        pytest.fail("The SMTP sender must not run after the rate limit is reached")

    monkeypatch.setattr("streetguard.api.communications.send_smtp_email", unexpected_send)

    with pytest.raises(HTTPException) as error:
        await send_report_email(
            report.public_id,
            ReportEmailRequest(recipient_email="authority@example.org", confirmed=True),
            session,  # type: ignore[arg-type]
            Principal(subject="reporter"),
            Settings(
                app_env="test",
                smtp_host="smtp.example.org",
                smtp_from_email="reports@example.org",
            ),
        )

    assert error.value.status_code == 429
