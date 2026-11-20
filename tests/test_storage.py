from typing import Any

from streetguard.config import Settings
from streetguard.storage import S3ObjectStorage


class FakeS3Client:
    def __init__(self) -> None:
        self.put_requests: list[dict[str, Any]] = []

    def generate_presigned_url(self, operation: str, **kwargs: Any) -> str:
        assert operation == "get_object"
        assert kwargs["Params"]["Key"] == "reports/SG-GLOBAL-test/original.webp"
        return "https://storage.example/download"

    def generate_presigned_post(self, **kwargs: Any) -> dict[str, Any]:
        assert kwargs["Bucket"] == "streetguard-private"
        assert kwargs["Key"].startswith("quarantine/")
        assert ["content-length-range", 1, 10_000_000] in kwargs["Conditions"]
        return {
            "url": "https://storage.example/upload",
            "fields": {"key": kwargs["Key"], "Content-Type": kwargs["Fields"]["Content-Type"]},
        }

    def put_object(self, **kwargs: Any) -> None:
        self.put_requests.append(kwargs)


def test_storage_presigns_bounded_upload(settings, monkeypatch) -> None:
    fake = FakeS3Client()

    def client_factory(*args: Any, **kwargs: Any) -> FakeS3Client:
        assert args == ("s3",)
        assert kwargs["aws_access_key_id"] == "test"
        return fake

    monkeypatch.setattr("streetguard.storage.boto3.client", client_factory)
    storage = S3ObjectStorage(settings)

    grant = storage.presign_upload(
        "quarantine/upload.webp",
        content_type="image/webp",
        max_bytes=10_000_000,
    )

    assert grant.url == "https://storage.example/upload"
    assert grant.object_key == "quarantine/upload.webp"
    assert grant.fields == {
        "key": "quarantine/upload.webp",
        "Content-Type": "image/webp",
    }


def test_storage_presigned_post_uses_sigv4(settings) -> None:
    grant = S3ObjectStorage(settings).presign_upload(
        "quarantine/upload.jpg",
        content_type="image/jpeg",
        max_bytes=10_000_000,
    )

    assert grant.fields is not None
    assert grant.fields["x-amz-algorithm"] == "AWS4-HMAC-SHA256"


def test_storage_presigns_private_download(settings, monkeypatch) -> None:
    def client_factory(*args: Any, **kwargs: Any) -> FakeS3Client:
        assert args == ("s3",)
        assert kwargs["region_name"] == "us-east-1"
        return FakeS3Client()

    monkeypatch.setattr("streetguard.storage.boto3.client", client_factory)
    storage = S3ObjectStorage(settings)

    assert (
        storage.presign_download("reports/SG-GLOBAL-test/original.webp")
        == "https://storage.example/download"
    )


def test_storage_uses_browser_endpoint_for_presigned_urls(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        storage_endpoint_url="http://storage:9000",
        storage_public_endpoint_url="http://localhost:9000",
        storage_access_key="test",
        storage_secret_key="test",
    )
    clients: list[FakeS3Client] = []
    endpoints: list[str] = []

    def client_factory(*args: Any, **kwargs: Any) -> FakeS3Client:
        assert args == ("s3",)
        endpoints.append(kwargs["endpoint_url"])
        client = FakeS3Client()
        clients.append(client)
        return client

    monkeypatch.setattr("streetguard.storage.boto3.client", client_factory)
    storage = S3ObjectStorage(settings)

    grant = storage.presign_upload(
        "quarantine/upload.webp",
        content_type="image/webp",
        max_bytes=10_000_000,
    )
    storage.put_bytes("derived/upload.jpg", b"image", "image/jpeg")

    assert [endpoint.rstrip("/") for endpoint in endpoints] == [
        "http://storage:9000",
        "http://localhost:9000",
    ]
    assert grant.url == "https://storage.example/upload"
    assert clients[0].put_requests == [
        {
            "Bucket": "streetguard-private",
            "Key": "derived/upload.jpg",
            "Body": b"image",
            "ContentType": "image/jpeg",
        }
    ]
    assert clients[1].put_requests == []


def test_storage_requests_server_side_encryption_when_enabled(settings, monkeypatch) -> None:
    settings.storage_server_side_encryption = True
    fake = FakeS3Client()
    monkeypatch.setattr("streetguard.storage.boto3.client", lambda *args, **kwargs: fake)

    S3ObjectStorage(settings).put_bytes("derived/upload.jpg", b"image", "image/jpeg")

    assert fake.put_requests[0]["ServerSideEncryption"] == "AES256"
