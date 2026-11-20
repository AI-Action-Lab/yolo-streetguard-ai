from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy.dialects import postgresql

from streetguard.api.map import list_clusters, marker_category, validate_bounds
from streetguard.config import Settings


class EmptyRows:
    def mappings(self) -> EmptyRows:
        return self

    def all(self) -> list[object]:
        return []


class CompileSession:
    async def execute(self, statement: object) -> EmptyRows:
        statement.compile(dialect=postgresql.dialect())
        return EmptyRows()


def test_map_marker_category_does_not_confirm_unverified_ai_results() -> None:
    assert marker_category("awaiting_verification", "unverified", "high") == "awaiting_review"
    assert marker_category("verified", "verified", "high") == "verified"
    assert marker_category("in_progress", "verified", "critical") == "critical"
    assert marker_category("resolved", "verified", None) == "resolved"


def test_map_bounds_reject_inverted_viewport() -> None:
    with pytest.raises(HTTPException) as error:
        validate_bounds(20, 20, 10, 10, Settings())

    assert error.value.status_code == 422


def test_map_bounds_allow_global_view_when_configured() -> None:
    validate_bounds(
        -180,
        -90,
        180,
        90,
        Settings(map_max_span_degrees=360, product_country_code="US"),
    )


def test_map_bounds_reject_viewports_outside_india() -> None:
    with pytest.raises(HTTPException, match="outside the India"):
        validate_bounds(-100, 20, -80, 40, Settings(product_country_code="IN"))


async def test_map_clusters_builds_a_compilable_postgis_query() -> None:
    result = await list_clusters(
        minimum_longitude=68,
        minimum_latitude=6,
        maximum_longitude=97.5,
        maximum_latitude=37.5,
        zoom=6,
        session=CompileSession(),
        settings=Settings(),
    )

    assert result.features == []
