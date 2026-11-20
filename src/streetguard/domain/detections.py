from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GpsCoordinates(BaseModel):
    model_config = ConfigDict(frozen=True)

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class ImageMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    mime_type: str
    byte_size: int = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    captured_at: datetime | None = None
    camera_make: str | None = None
    camera_model: str | None = None
    gps: GpsCoordinates | None = None
    exif_summary: dict[str, Any] = Field(default_factory=dict)


class DetectionBox(BaseModel):
    model_config = ConfigDict(frozen=True)

    class_name: str = "pothole"
    confidence: float = Field(ge=0, le=1)
    x_center: float = Field(ge=0, le=1)
    y_center: float = Field(ge=0, le=1)
    box_width: float = Field(gt=0, le=1)
    box_height: float = Field(gt=0, le=1)


@dataclass(frozen=True)
class DetectionResult:
    boxes: tuple[DetectionBox, ...]
    annotated_bytes: bytes
    processing_ms: int
    model_version: str
    completed_at: datetime


def utc_now() -> datetime:
    return datetime.now(UTC)
