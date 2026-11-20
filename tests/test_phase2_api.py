from hashlib import sha256
from typing import Any

from fastapi.testclient import TestClient

from streetguard.database import get_session
from streetguard.main import create_app
from streetguard.storage import UploadGrant


def test_openapi_exposes_phase_two_upload_workflow() -> None:
    schema = create_app().openapi()

    assert "/api/v1/uploads" in schema["paths"]
    assert "/api/v1/uploads/{upload_id}/complete" in schema["paths"]
    assert "/api/v1/uploads/{upload_id}" in schema["paths"]


def test_phase_two_celery_task_is_registered() -> None:
    from streetguard.celery_app import celery_app
    from streetguard.workers import detection  # noqa: F401

    assert "streetguard.process_upload" in celery_app.tasks


class EmptyResult:
    def scalar_one_or_none(self) -> None:
        return None


class FakeSession:
    def __init__(self) -> None:
        self.added: list[Any] = []

    async def execute(self, statement: Any) -> EmptyResult:
        del statement
        return EmptyResult()

    def add(self, value: Any) -> None:
        self.added.append(value)

    async def commit(self) -> None:
        return None


def test_upload_endpoint_returns_bounded_signed_upload(monkeypatch, settings) -> None:
    session = FakeSession()
    app = create_app()

    async def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    from streetguard.config import get_settings

    app.dependency_overrides[get_settings] = lambda: settings
    monkeypatch.setattr(
        "streetguard.api.detections.S3ObjectStorage.presign_upload",
        lambda self, object_key, content_type, max_bytes: UploadGrant(
            url="https://storage.example/upload",
            object_key=object_key,
            fields={"key": object_key, "Content-Type": content_type},
        ),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/uploads",
            headers={"Idempotency-Key": "phase2-test-upload-0001"},
            json={
                "filename": "road.jpg",
                "content_type": "image/jpeg",
                "byte_size": 1024,
                "sha256": sha256(b"road").hexdigest(),
            },
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["object_key"].startswith("quarantine/")
    assert payload["upload_url"] == "https://storage.example/upload"
    assert payload["upload_fields"]["Content-Type"] == "image/jpeg"
    assert len(session.added) == 1


def test_upload_endpoint_rejects_oversized_claim(settings) -> None:
    app = create_app()
    from streetguard.config import get_settings

    app.dependency_overrides[get_settings] = lambda: settings

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/uploads",
            headers={"Idempotency-Key": "phase2-test-upload-0002"},
            json={
                "filename": "road.jpg",
                "content_type": "image/jpeg",
                "byte_size": settings.max_image_upload_bytes + 1,
                "sha256": sha256(b"road").hexdigest(),
            },
        )

    assert response.status_code == 413
