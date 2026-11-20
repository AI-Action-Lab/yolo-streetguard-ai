from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from streetguard.api.schemas import DetectionItem
from streetguard.domain.geography import AddressComponents


class ReportCreateRequest(BaseModel):
    upload_id: UUID
    location_id: UUID
    title: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=10_000)


class DuplicateCandidateResponse(BaseModel):
    candidate_report_id: str
    similarity_score: float
    distance_meters: float | None
    review_status: str
    algorithm_version: str


class ReportHistoryItem(BaseModel):
    from_status: str | None
    to_status: str
    reason: str | None
    occurred_at: datetime


class ReportSeverityResponse(BaseModel):
    category: str
    method_version: str
    factor_snapshot: dict[str, object]
    human_overridden: bool
    disclaimer: str


class ReportLocationResponse(BaseModel):
    latitude: float
    longitude: float
    accuracy_meters: float | None
    source: str
    formatted_address: str | None
    components: AddressComponents


class ReportResponse(BaseModel):
    id: UUID
    public_id: str
    status: str
    verification_status: str
    visibility: str
    created_at: datetime
    submitted_at: datetime | None
    detection_count: int
    title: str | None
    description: str | None
    location: ReportLocationResponse
    severity: ReportSeverityResponse
    detections: list[DetectionItem]
    annotated_image_url: str | None
    history: list[ReportHistoryItem]
    duplicate_candidates: list[DuplicateCandidateResponse] = Field(default_factory=list)


class ReportListItem(BaseModel):
    public_id: str
    status: str
    verification_status: str
    severity: str | None
    created_at: datetime
    submitted_at: datetime | None


class VerificationRequest(BaseModel):
    decision: Literal["verified", "rejected", "duplicate"]
    reason: str = Field(min_length=3, max_length=2_000)
    severity_override: Literal["low", "moderate", "high", "critical"] | None = None
    duplicate_target_report_id: str | None = None


class DuplicateDecisionRequest(BaseModel):
    decision: Literal["linked", "dismissed"]
    reason: str = Field(min_length=3, max_length=2_000)
