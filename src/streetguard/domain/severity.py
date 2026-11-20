from dataclasses import dataclass
from typing import Literal, Protocol

Severity = Literal["low", "moderate", "high", "critical"]

VISUAL_SEVERITY_METHOD_VERSION = "visual-box-v1"
VISUAL_SEVERITY_DISCLAIMER = (
    "Estimated visual severity from image-relative box area and count; "
    "not a measurement of pothole depth, vehicle risk, or road failure."
)


class BoxLike(Protocol):
    box_width: float
    box_height: float


@dataclass(frozen=True)
class SeverityResult:
    category: Severity
    factor_snapshot: dict[str, object]


def assess_visual_severity(boxes: list[BoxLike]) -> SeverityResult:
    if not boxes:
        return SeverityResult(
            category="low",
            factor_snapshot={
                "method_version": VISUAL_SEVERITY_METHOD_VERSION,
                "max_box_area_ratio": 0.0,
                "total_box_area_ratio": 0.0,
                "detection_count": 0,
                "score": 0.0,
                "disclaimer": VISUAL_SEVERITY_DISCLAIMER,
            },
        )

    areas = [max(0.0, box.box_width * box.box_height) for box in boxes]
    max_area = max(areas)
    total_area = sum(areas)
    count_factor = min(max(len(boxes) - 1, 0), 4) * 0.04
    score = min(1.0, round(max_area * 5 + count_factor, 6))

    if score >= 0.75:
        category: Severity = "critical"
    elif score >= 0.45:
        category = "high"
    elif score >= 0.2:
        category = "moderate"
    else:
        category = "low"

    return SeverityResult(
        category=category,
        factor_snapshot={
            "method_version": VISUAL_SEVERITY_METHOD_VERSION,
            "max_box_area_ratio": max_area,
            "total_box_area_ratio": total_area,
            "detection_count": len(boxes),
            "count_factor": count_factor,
            "score": score,
            "disclaimer": VISUAL_SEVERITY_DISCLAIMER,
        },
    )
