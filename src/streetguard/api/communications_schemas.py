from datetime import datetime
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator, model_validator

from streetguard.communications import valid_email_address


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AuthorityCreateRequest(StrictRequest):
    name: str = Field(min_length=2, max_length=240)
    category: str = Field(min_length=2, max_length=100)
    contact_email: str | None = Field(default=None, max_length=320)
    website_url: AnyHttpUrl | None = None
    jurisdiction_region_id: UUID | None = None

    @field_validator("contact_email")
    @classmethod
    def validate_contact_email(cls, value: str | None) -> str | None:
        if value is not None and not valid_email_address(value):
            raise ValueError("A valid contact email address is required")
        return value


class AuthorityUpdateRequest(AuthorityCreateRequest):
    active: bool


class AuthorityVerificationRequest(StrictRequest):
    evidence_url: AnyHttpUrl
    confirmed: bool


class AuthorityResponse(BaseModel):
    id: UUID
    name: str
    category: str
    contact_email: str | None
    website_url: str | None
    jurisdiction_region_id: UUID | None
    jurisdiction_name: str | None
    is_verified: bool
    active: bool


class ReportEmailRequest(StrictRequest):
    recipient_email: str | None = Field(default=None, max_length=320)
    authority_id: UUID | None = None
    confirmed: bool

    @field_validator("recipient_email")
    @classmethod
    def validate_recipient_email(cls, value: str | None) -> str | None:
        if value is not None and not valid_email_address(value):
            raise ValueError("A valid recipient email address is required")
        return value

    @model_validator(mode="after")
    def validate_recipient(self) -> "ReportEmailRequest":
        if (self.recipient_email is None) == (self.authority_id is None):
            raise ValueError("Specify exactly one authority or manual recipient email")
        return self


class EmailDeliveryResponse(BaseModel):
    id: UUID
    purpose: str
    delivery_status: str
    provider_message_id: str | None
    created_at: datetime


class NotificationPreferenceRequest(StrictRequest):
    email_status_notifications_enabled: bool
    confirmed: bool = False


class NotificationPreferenceResponse(BaseModel):
    email_status_notifications_enabled: bool
    email: str | None


class NotificationItem(BaseModel):
    id: UUID
    report_id: UUID | None
    notification_type: str
    subject: str
    body: str
    created_at: datetime
    read_at: datetime | None
