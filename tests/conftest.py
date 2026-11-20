from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from streetguard.config import Settings, get_settings
from streetguard.main import create_app


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_env="test",
        database_url="postgresql+psycopg://test:test@localhost:5432/test",
        storage_access_key="test",
        storage_secret_key="test",
    )


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture(autouse=True)
def clear_cached_settings() -> Generator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
