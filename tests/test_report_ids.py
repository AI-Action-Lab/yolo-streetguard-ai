import re

from streetguard.domain.reports import (
    country_code_from_metadata,
    create_public_report_id,
)
from streetguard.reporting import duplicate_similarity


def test_report_ids_are_unique_and_country_safe() -> None:
    first = create_public_report_id("IN")
    second = create_public_report_id("IN")

    assert first != second
    assert re.fullmatch(r"SG-IN-[0-9A-F]{20}", first)
    assert create_public_report_id(None).startswith("SG-GLOBAL-")
    assert create_public_report_id("invented").startswith("SG-GLOBAL-")


def test_country_code_comes_only_from_provider_metadata() -> None:
    assert country_code_from_metadata({"country_code": "ca"}) == "CA"
    assert country_code_from_metadata({"country_code": "Canada"}) is None
    assert country_code_from_metadata(None) is None


def test_duplicate_score_is_bounded_and_distance_based() -> None:
    assert duplicate_similarity(0, 50) == 1
    assert duplicate_similarity(25, 50) == 0.5
    assert duplicate_similarity(100, 50) == 0
    assert duplicate_similarity(-5, 50) == 1
