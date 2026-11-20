import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class UploadCreateRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: Literal["image/jpeg", "image/png", "image/webp", "image/bmp", "image/tiff"]
    byte_size: int = Field(gt=0)
    sha256: str

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, value: str) -> str:
        if value != value.replace("/", "").replace("\\", ""):
            raise ValueError("Filename must not contain path separators")
        return value

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        normalized = value.lower()
        if not SHA256_PATTERN.fullmatch(normalized):
            raise ValueError("sha256 must contain 64 lowercase hexadecimal characters")
        return normalized


class UploadCreateResponse(BaseModel):
    upload_id: UUID
    object_key: str
    upload_url: str
    upload_fields: dict[str, str]
    expires_in_seconds: int
    duplicate: bool = False


class UploadCompleteRequest(BaseModel):
    object_key: str = Field(min_length=1, max_length=1024)


class DetectionItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    class_name: str
    confidence: float
    x_center: float
    y_center: float
    box_width: float
    box_height: float


class DetectionRunResponse(BaseModel):
    id: UUID
    upload_id: UUID
    status: str
    confidence_threshold: float
    image_size: int
    processing_ms: int | None
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    annotated_download_url: str | None = None
    detections: list[DetectionItem] = Field(default_factory=list)


class UploadStatusResponse(BaseModel):
    id: UUID
    processing_status: str
    scan_status: str
    byte_size: int
    mime_type: str
    pixel_width: int | None
    pixel_height: int | None
    capture_time: datetime | None
    exif_summary: dict[str, object]
    detection_run: DetectionRunResponse | None = None
