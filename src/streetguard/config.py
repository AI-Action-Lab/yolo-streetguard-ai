from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_CONTAINER_SECRETS_DIR = Path("/run/secrets")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        secrets_dir=_CONTAINER_SECRETS_DIR if _CONTAINER_SECRETS_DIR.is_dir() else None,
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    app_name: str = "YOLO StreetGuard AI"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    public_base_url: AnyHttpUrl = AnyHttpUrl("http://localhost:3000")

    database_url: str = "postgresql+psycopg://streetguard:streetguard@localhost:5432/streetguard"
    database_pool_size: int = Field(default=5, ge=1, le=100)
    database_max_overflow: int = Field(default=10, ge=0, le=100)

    oidc_issuer_url: AnyHttpUrl = AnyHttpUrl("http://localhost:8080/realms/streetguard")
    oidc_audience: str = "streetguard-api"
    oidc_jwks_url: AnyHttpUrl = AnyHttpUrl(
        "http://localhost:8080/realms/streetguard/protocol/openid-connect/certs"
    )

    storage_endpoint_url: AnyHttpUrl = AnyHttpUrl("http://localhost:9000")
    storage_public_endpoint_url: AnyHttpUrl | None = None
    storage_region: str = "us-east-1"
    storage_bucket: str = "streetguard-private"
    storage_access_key: str = "streetguard"
    storage_secret_key: str = "streetguard"
    storage_use_ssl: bool = False
    storage_server_side_encryption: bool = False
    storage_signed_url_ttl_seconds: int = Field(default=900, ge=60, le=86_400)

    redis_url: str = "redis://localhost:6379/0"
    max_image_upload_bytes: int = Field(default=20_000_000, ge=1, le=100_000_000)
    max_image_pixels: int = Field(default=50_000_000, ge=1, le=200_000_000)
    detection_confidence_threshold: float = Field(default=0.25, ge=0.0, le=1.0)
    detection_image_size: int = Field(default=640, ge=320, le=2048, multiple_of=32)
    detection_device: str = "cpu"
    model_path: Path = Path("models/pothole/best.pt")
    model_checksum: str = Field(
        default="d4ec8035e55e7db185e82cbfdf97f402264e40024b2d7e6d0e335bce5d321543",
        min_length=64,
        max_length=64,
    )

    google_maps_api_key: str = ""
    google_geocoding_base_url: AnyHttpUrl = AnyHttpUrl(
        "https://maps.googleapis.com/maps/api/geocode/json"
    )
    geocoding_timeout_seconds: float = Field(default=8, ge=1, le=30)
    smtp_host: str = ""
    smtp_port: int = Field(default=587, ge=1, le=65_535)
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_from_email: str = ""
    smtp_use_ssl: bool = False
    smtp_starttls: bool = True
    smtp_timeout_seconds: float = Field(default=10, ge=1, le=60)
    map_max_markers: int = Field(default=1_000, ge=100, le=5_000)
    map_max_span_degrees: float = Field(default=360, ge=1, le=360)
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    product_country_code: str = Field(default="IN", min_length=2, max_length=2)
    product_country_name: str = "India"
    strict_country_scope: bool = False

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def allowed_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host.strip() and self.smtp_from_email.strip())

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if bool(self.smtp_username) != bool(self.smtp_password.get_secret_value()):
            raise ValueError("SMTP username and password must be configured together")
        if self.smtp_use_ssl and self.smtp_starttls:
            raise ValueError("SMTP implicit SSL and STARTTLS cannot both be enabled")

        if not self.is_production:
            return self

        if "localhost" in self.database_url or "127.0.0.1" in self.database_url:
            raise ValueError("Production DATABASE_URL cannot target localhost")
        if (
            self.storage_access_key == "streetguard"
            or self.storage_secret_key == "streetguard"
            or not self.storage_use_ssl
            or self.storage_endpoint_url.scheme != "https"
            or not self.storage_server_side_encryption
        ):
            raise ValueError(
                "Production object storage requires unique credentials, TLS, and encryption"
            )
        if self.storage_public_endpoint_url and (
            self.storage_public_endpoint_url.scheme != "https"
            or self.storage_public_endpoint_url.host in {"localhost", "127.0.0.1", "::1"}
        ):
            raise ValueError("Production public object-storage endpoint must use public HTTPS")
        if self.oidc_issuer_url.scheme != "https" or self.oidc_jwks_url.scheme != "https":
            raise ValueError("Production OIDC endpoints must use HTTPS")
        if self.smtp_host and (
            not self.smtp_from_email or not (self.smtp_use_ssl or self.smtp_starttls)
        ):
            raise ValueError("Production SMTP requires a sender address and TLS")
        if (
            self.product_country_code == "IN"
            and self.strict_country_scope
            and not self.google_maps_api_key
        ):
            raise ValueError("Strict India scope requires configured geocoding")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
