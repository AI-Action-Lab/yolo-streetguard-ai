from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from geoalchemy2 import Geography, Geometry
from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from streetguard.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


def utc_now() -> datetime:
    return datetime.now(UTC)


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    subject: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    email: Mapped[str | None] = mapped_column(String(320))
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    display_name: Mapped[str | None] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    email_status_notifications_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    email_notifications_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Role(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")


class Permission(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "permissions"

    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    granted_by_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )


class Upload(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "uploads"
    __table_args__ = (
        CheckConstraint("byte_size > 0", name="positive_byte_size"),
        CheckConstraint("pixel_width IS NULL OR pixel_width > 0", name="positive_pixel_width"),
        CheckConstraint("pixel_height IS NULL OR pixel_height > 0", name="positive_pixel_height"),
    )

    owner_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    original_object_key: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    annotated_object_key: Mapped[str | None] = mapped_column(String(1024))
    thumbnail_object_key: Mapped[str | None] = mapped_column(String(1024))
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    pixel_width: Mapped[int | None] = mapped_column(Integer)
    pixel_height: Mapped[int | None] = mapped_column(Integer)
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    capture_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    exif_summary: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    scan_status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    processing_status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    visibility: Mapped[str] = mapped_column(String(30), nullable=False, default="private")


class ModelVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "model_versions"
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_model_versions_name_version"),
        CheckConstraint(
            "confidence_threshold >= 0 AND confidence_threshold <= 1",
            name="confidence_range",
        ),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(100), nullable=False)
    model_family: Mapped[str] = mapped_column(String(100), nullable=False, default="YOLO11n")
    artifact_object_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    artifact_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.25)
    image_size: Mapped[int] = mapped_column(Integer, nullable=False, default=640)
    class_names: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    evaluation_metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class DetectionRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "detection_runs"

    upload_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_version_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("model_versions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="queued")
    confidence_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    image_size: Mapped[int] = mapped_column(Integer, nullable=False)
    worker_version: Mapped[str | None] = mapped_column(String(100))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processing_ms: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    settings_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class PotholeDetection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "pothole_detections"
    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
        CheckConstraint("x_center >= 0 AND x_center <= 1", name="x_center_range"),
        CheckConstraint("y_center >= 0 AND y_center <= 1", name="y_center_range"),
        CheckConstraint("box_width > 0 AND box_width <= 1", name="box_width_range"),
        CheckConstraint("box_height > 0 AND box_height <= 1", name="box_height_range"),
        CheckConstraint(
            "x_center - box_width / 2 >= 0 AND x_center + box_width / 2 <= 1",
            name="x_bounds",
        ),
        CheckConstraint(
            "y_center - box_height / 2 >= 0 AND y_center + box_height / 2 <= 1",
            name="y_bounds",
        ),
    )

    detection_run_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("detection_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    class_name: Mapped[str] = mapped_column(String(80), nullable=False, default="pothole")
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    x_center: Mapped[float] = mapped_column(Float, nullable=False)
    y_center: Mapped[float] = mapped_column(Float, nullable=False)
    box_width: Mapped[float] = mapped_column(Float, nullable=False)
    box_height: Mapped[float] = mapped_column(Float, nullable=False)


class GeographicalRegion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "geographical_regions"
    __table_args__ = (
        UniqueConstraint("source_name", "source_code", name="uq_geographical_regions_source"),
        Index("ix_geographical_regions_type_name", "region_type", "name"),
        Index("ix_geographical_regions_boundary", "boundary", postgresql_using="gist"),
    )

    parent_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("geographical_regions.id", ondelete="SET NULL"), index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    local_name: Mapped[str | None] = mapped_column(String(200))
    region_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    source_code: Mapped[str] = mapped_column(String(150), nullable=False)
    iso_code: Mapped[str | None] = mapped_column(String(20), index=True)
    boundary = mapped_column(Geometry("MULTIPOLYGON", srid=4326, spatial_index=False))
    source_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class Location(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "locations"
    __table_args__ = (
        CheckConstraint(
            "accuracy_meters IS NULL OR accuracy_meters >= 0",
            name="accuracy_nonnegative",
        ),
        Index("ix_locations_geography", "coordinates", postgresql_using="gist"),
    )

    coordinates = mapped_column(
        Geography("POINT", srid=4326, spatial_index=False),
        nullable=False,
    )
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    accuracy_meters: Mapped[float | None] = mapped_column(Float)
    confirmed_by_user: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    formatted_address: Mapped[str | None] = mapped_column(Text)
    country_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("geographical_regions.id", ondelete="SET NULL")
    )
    region_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("geographical_regions.id", ondelete="SET NULL")
    )
    city_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("geographical_regions.id", ondelete="SET NULL")
    )
    locality_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("geographical_regions.id", ondelete="SET NULL")
    )
    provider: Mapped[str | None] = mapped_column(String(100))
    provider_place_id: Mapped[str | None] = mapped_column(String(255))
    provider_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    geocoded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Report(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reports"
    __table_args__ = (
        CheckConstraint("detection_count >= 0", name="nonnegative_detection_count"),
        Index("ix_reports_status_created_at", "status", "created_at"),
        Index("ix_reports_visibility_status", "visibility", "status"),
    )

    public_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    reporter_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    upload_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("uploads.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    location_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("locations.id", ondelete="SET NULL"), unique=True
    )
    title: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft", index=True)
    verification_status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="unverified"
    )
    visibility: Mapped[str] = mapped_column(String(30), nullable=False, default="private")
    detection_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    severity: Mapped[str | None] = mapped_column(String(30), index=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SeverityAssessment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "severity_assessments"
    __table_args__ = (
        CheckConstraint(
            "human_overridden = false OR override_reason IS NOT NULL",
            name="override_reason",
        ),
    )

    report_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    detection_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("pothole_detections.id", ondelete="CASCADE")
    )
    method_version: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    factor_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    human_overridden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    override_reason: Mapped[str | None] = mapped_column(Text)
    reviewer_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )


class Authority(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "authorities"

    name: Mapped[str] = mapped_column(String(240), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(320))
    website_url: Mapped[str | None] = mapped_column(String(500))
    contact_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    jurisdiction_region_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("geographical_regions.id", ondelete="SET NULL"), index=True
    )
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class AuthorityMembership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "authority_memberships"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "authority_id",
            name="uq_authority_memberships_user_authority",
        ),
        Index("ix_authority_memberships_authority_active", "authority_id", "active"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    authority_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("authorities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    granted_by_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class AuthorityAssignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "authority_assignments"
    __table_args__ = (
        UniqueConstraint(
            "report_id",
            "authority_id",
            name="uq_authority_assignment_report_authority",
        ),
    )

    report_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    authority_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("authorities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    assigned_by_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)


class ReportStatusHistory(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "report_status_history"

    report_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    from_status: Mapped[str | None] = mapped_column(String(50))
    to_status: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    event_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class DuplicateReportLink(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "duplicate_report_links"
    __table_args__ = (
        UniqueConstraint("source_report_id", "candidate_report_id", name="uq_duplicate_pair"),
        CheckConstraint(
            "source_report_id != candidate_report_id",
            name="distinct_duplicate_reports",
        ),
        CheckConstraint("similarity_score >= 0 AND similarity_score <= 1", name="similarity_range"),
    )

    source_report_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_report_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(100), nullable=False)
    factors: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    review_status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    reviewed_by_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    report_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("reports.id", ondelete="CASCADE"), index=True
    )
    notification_type: Mapped[str] = mapped_column(String(100), nullable=False)
    subject: Mapped[str] = mapped_column(String(240), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EmailDeliveryLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "email_delivery_logs"

    purpose: Mapped[str] = mapped_column(String(50), nullable=False, default="report_share")
    report_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requested_by_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    recipient: Mapped[str] = mapped_column(String(320), nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(255))
    delivery_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text)
    confirmed_by_user_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WhatsappShareLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "whatsapp_share_logs"

    report_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requested_by_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    mode: Mapped[str] = mapped_column(String(40), nullable=False, default="user_initiated")
    share_url: Mapped[str] = mapped_column(Text, nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(255))
    delivery_status: Mapped[str] = mapped_column(String(50), nullable=False, default="opened")
    confirmed_by_user_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_actor_created_at", "actor_subject", "created_at"),)

    actor_subject: Mapped[str | None] = mapped_column(String(255), index=True)
    actor_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(String(160), nullable=False)
    target_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[str] = mapped_column(String(255), nullable=False)
    before_state: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    after_state: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    request_id: Mapped[str | None] = mapped_column(String(100), index=True)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )


class SystemSetting(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    updated_by_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
