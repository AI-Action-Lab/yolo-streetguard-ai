from streetguard.config import Settings


def test_settings_load_environment_values(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://service:secret@database.example/streetguard"
    )
    monkeypatch.setenv("DATABASE_POOL_SIZE", "12")
    monkeypatch.setenv("STORAGE_SIGNED_URL_TTL_SECONDS", "120")
    monkeypatch.setenv("STORAGE_ACCESS_KEY", "production-access-key")
    monkeypatch.setenv("STORAGE_SECRET_KEY", "production-secret-key")
    monkeypatch.setenv("STORAGE_USE_SSL", "true")
    monkeypatch.setenv("STORAGE_SERVER_SIDE_ENCRYPTION", "true")
    monkeypatch.setenv("STORAGE_ENDPOINT_URL", "https://objects.example")
    monkeypatch.setenv("STORAGE_PUBLIC_ENDPOINT_URL", "https://objects.example")
    monkeypatch.setenv("OIDC_ISSUER_URL", "https://identity.example/realms/streetguard")
    monkeypatch.setenv("OIDC_JWKS_URL", "https://identity.example/realms/streetguard/certs")

    settings = Settings()

    assert settings.app_env == "production"
    assert settings.database_pool_size == 12
    assert settings.storage_signed_url_ttl_seconds == 120
    assert settings.is_production


def test_settings_loads_secret_files(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STORAGE_SECRET_KEY", raising=False)
    (tmp_path / "storage_secret_key").write_text("mounted-secret", encoding="utf-8")

    settings = Settings(_env_file=None, _secrets_dir=tmp_path)

    assert settings.storage_secret_key == "mounted-secret"


def test_settings_rejects_unsafe_signed_url_ttl(monkeypatch) -> None:
    monkeypatch.setenv("STORAGE_SIGNED_URL_TTL_SECONDS", "1")

    try:
        Settings()
    except ValueError:
        return

    raise AssertionError("A sub-minute signed URL TTL must be rejected")


def test_production_settings_reject_local_defaults(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")

    try:
        Settings()
    except ValueError as error:
        assert "localhost" in str(error)
        return

    raise AssertionError("Production must reject local development credentials")


def test_production_rejects_non_https_public_storage_endpoint(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://service:secret@database.example/streetguard"
    )
    monkeypatch.setenv("STORAGE_ENDPOINT_URL", "https://objects.example")
    monkeypatch.setenv("STORAGE_PUBLIC_ENDPOINT_URL", "http://localhost:9000")
    monkeypatch.setenv("STORAGE_ACCESS_KEY", "production-access-key")
    monkeypatch.setenv("STORAGE_SECRET_KEY", "production-secret-key")
    monkeypatch.setenv("STORAGE_USE_SSL", "true")
    monkeypatch.setenv("STORAGE_SERVER_SIDE_ENCRYPTION", "true")
    monkeypatch.setenv("OIDC_ISSUER_URL", "https://identity.example/realms/streetguard")
    monkeypatch.setenv("OIDC_JWKS_URL", "https://identity.example/realms/streetguard/certs")

    try:
        Settings()
    except ValueError as error:
        assert "public HTTPS" in str(error)
        return

    raise AssertionError("Production must reject a private or non-HTTPS browser endpoint")
