from dataclasses import dataclass

import pytest

from streetguard.domain.severity import (
    VISUAL_SEVERITY_METHOD_VERSION,
    assess_visual_severity,
)


@dataclass
class Box:
    box_width: float
    box_height: float


def test_severity_does_not_use_detection_confidence() -> None:
    assessment = assess_visual_severity([Box(0.2, 0.2)])

    assert assessment.category == "moderate"
    assert "confidence" not in assessment.factor_snapshot
    assert assessment.factor_snapshot["method_version"] == VISUAL_SEVERITY_METHOD_VERSION
    assert "not a measurement" in str(assessment.factor_snapshot["disclaimer"])


@pytest.mark.parametrize(
    ("boxes", "category"),
    [
        ([Box(0.02, 0.02)], "low"),
        ([Box(0.2, 0.2)], "moderate"),
        ([Box(0.3, 0.3)], "high"),
        ([Box(0.5, 0.4)], "critical"),
    ],
)
def test_visual_severity_thresholds_are_deterministic(boxes: list[Box], category: str) -> None:
    assert assess_visual_severity(boxes).category == category


def test_empty_detection_result_is_low_with_explicit_factors() -> None:
    result = assess_visual_severity([])

    assert result.category == "low"
    assert result.factor_snapshot["detection_count"] == 0
    assert result.factor_snapshot["total_box_area_ratio"] == 0.0
