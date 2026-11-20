from __future__ import annotations

import logging
import time

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from streetguard.config import get_settings

logger = logging.getLogger(__name__)


def wait_for_postgis(
    database_url: str,
    *,
    timeout_seconds: float = 180,
    check_interval_seconds: float = 5,
) -> None:
    engine = create_engine(database_url, pool_pre_ping=True)
    deadline = time.monotonic() + timeout_seconds
    consecutive_successes = 0
    last_error: SQLAlchemyError | None = None
    logger.info("Waiting for a stable PostGIS connection")

    try:
        while time.monotonic() < deadline:
            try:
                with engine.connect() as connection:
                    connection.execute(text("SELECT PostGIS_Version()"))
            except SQLAlchemyError as error:
                last_error = error
                consecutive_successes = 0
            else:
                consecutive_successes += 1
                if consecutive_successes == 2:
                    return

            time.sleep(check_interval_seconds)

        raise TimeoutError(
            "PostGIS did not become stable before the startup timeout"
        ) from last_error
    finally:
        engine.dispose()


def main() -> None:
    wait_for_postgis(get_settings().database_url)


if __name__ == "__main__":
    main()
