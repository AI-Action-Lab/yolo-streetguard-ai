from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import boto3
from botocore.config import Config

from streetguard.config import Settings

_S3_CLIENT_CONFIG = Config(signature_version="s3v4")


@dataclass(frozen=True)
class UploadGrant:
    url: str
    object_key: str
    fields: dict[str, str] | None = None


class ObjectStorage(Protocol):
    def presign_download(self, object_key: str) -> str: ...

    def download_bytes(self, object_key: str) -> bytes: ...

    def put_bytes(self, object_key: str, content: bytes, content_type: str) -> None: ...

    def presign_upload(self, object_key: str, content_type: str, max_bytes: int) -> UploadGrant: ...


class S3ObjectStorage:
    def __init__(self, settings: Settings) -> None:
        self._bucket = settings.storage_bucket
        self._signed_url_ttl = settings.storage_signed_url_ttl_seconds
        self._server_side_encryption = settings.storage_server_side_encryption
        self._client = boto3.client(
            "s3",
            endpoint_url=str(settings.storage_endpoint_url),
            region_name=settings.storage_region,
            aws_access_key_id=settings.storage_access_key,
            aws_secret_access_key=settings.storage_secret_key,
            use_ssl=settings.storage_use_ssl,
            config=_S3_CLIENT_CONFIG,
        )
        self._presign_client = self._client
        public_endpoint_url = settings.storage_public_endpoint_url
        if public_endpoint_url and str(public_endpoint_url).rstrip("/") != str(
            settings.storage_endpoint_url
        ).rstrip("/"):
            self._presign_client = boto3.client(
                "s3",
                endpoint_url=str(public_endpoint_url),
                region_name=settings.storage_region,
                aws_access_key_id=settings.storage_access_key,
                aws_secret_access_key=settings.storage_secret_key,
                use_ssl=settings.storage_use_ssl,
                config=_S3_CLIENT_CONFIG,
            )

    def presign_download(self, object_key: str) -> str:
        return str(
            self._presign_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": object_key},
                ExpiresIn=self._signed_url_ttl,
            )
        )

    def download_bytes(self, object_key: str) -> bytes:
        response = self._client.get_object(Bucket=self._bucket, Key=object_key)
        return bytes(response["Body"].read())

    def put_bytes(self, object_key: str, content: bytes, content_type: str) -> None:
        if self._server_side_encryption:
            self._client.put_object(
                Bucket=self._bucket,
                Key=object_key,
                Body=content,
                ContentType=content_type,
                ServerSideEncryption="AES256",
            )
        else:
            self._client.put_object(
                Bucket=self._bucket,
                Key=object_key,
                Body=content,
                ContentType=content_type,
            )

    def presign_upload(self, object_key: str, content_type: str, max_bytes: int) -> UploadGrant:
        response = self._presign_client.generate_presigned_post(
            Bucket=self._bucket,
            Key=object_key,
            Fields={"Content-Type": content_type},
            Conditions=[
                {"Content-Type": content_type},
                ["content-length-range", 1, max_bytes],
            ],
            ExpiresIn=self._signed_url_ttl,
        )
        return UploadGrant(
            url=str(response["url"]),
            object_key=object_key,
            fields={str(key): str(value) for key, value in response["fields"].items()},
        )
