from __future__ import annotations

from sqlalchemy.exc import SQLAlchemyError

from streetguard import wait_for_database


class FakeConnection:
    def __init__(self, error: SQLAlchemyError | None) -> None:
        self.error = error

    def __enter__(self) -> FakeConnection:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, statement: object) -> None:
        assert str(statement) == "SELECT PostGIS_Version()"
        if self.error is not None:
            raise self.error


class FakeEngine:
    def __init__(self, outcomes: list[SQLAlchemyError | None]) -> None:
        self.outcomes = outcomes
        self.disposed = False

    def connect(self) -> FakeConnection:
        return FakeConnection(self.outcomes.pop(0))

    def dispose(self) -> None:
        self.disposed = True


def test_wait_for_postgis_requires_two_consecutive_successes(monkeypatch) -> None:
    engine = FakeEngine([None, SQLAlchemyError("database restarting"), None, None])
    sleeps: list[float] = []
    monkeypatch.setattr(wait_for_database, "create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(wait_for_database.time, "sleep", sleeps.append)

    wait_for_database.wait_for_postgis("postgresql+psycopg://user:pass@db/test")

    assert len(engine.outcomes) == 0
    assert sleeps == [5, 5, 5]
    assert engine.disposed
