from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AuthorityAssignmentRequest(StrictRequest):
    authority_id: UUID
    notes: str | None = Field(default=None, max_length=2_000)
    confirmed: bool


class AuthorityAssignmentResponse(BaseModel):
    assignment_id: UUID
    public_id: str
    authority_id: UUID
    authority_name: str
    status: str
    assigned_at: datetime


class AdminReportItem(BaseModel):
    public_id: str
    status: str
    title: str | None
    severity: str | None
    submitted_at: datetime | None
    location_address: str | None


class AuthorityReportItem(BaseModel):
    assignment_id: UUID
    public_id: str
    status: str
    title: str | None
    description: str | None
    severity: str | None
    location_address: str | None
    latitude: float
    longitude: float
    assigned_at: datetime
    completed_at: datetime | None
    notes: str | None
    authority_name: str


class AuthorityReportStatusRequest(StrictRequest):
    status: Literal["in_progress", "resolved"]
    notes: str = Field(min_length=3, max_length=2_000)
    confirmed: bool


class AuthorityMemberCreateRequest(StrictRequest):
    user_subject: str = Field(min_length=1, max_length=255)
    confirmed: bool


class AuthorityMemberResponse(BaseModel):
    id: UUID
    user_id: UUID
    user_subject: str
    email: str | None
    active: bool
    created_at: datetime
    updated_at: datetime


class AuditLogItem(BaseModel):
    id: UUID
    actor_subject: str | None
    action: str
    target_type: str
    target_id: str
    created_at: datetime
