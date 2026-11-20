from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql import func

from streetguard.domain.reports import country_code_from_metadata, create_public_report_id
from streetguard.domain.severity import assess_visual_severity
from streetguard.domain.statuses import ReportStatus, can_transition
from streetguard.models.core import (
    DetectionRun,
    DuplicateReportLink,
    Location,
    PotholeDetection,
    Report,
    ReportStatusHistory,
    SeverityAssessment,
    Upload,
    User,
)
from streetguard.security.principal import Principal


class ReportingError(ValueError):
    pass


def duplicate_similarity(distance_meters: float, radius_meters: float) -> float:
    return max(0.0, min(1.0, 1 - max(0.0, distance_meters) / max(radius_meters, 1)))


async def get_or_create_user(session: AsyncSession, principal: Principal) -> User:
    user = (
        await session.scalars(select(User).where(User.subject == principal.subject).limit(1))
    ).first()
    if user is not None:
        if principal.email is not None:
            user.email = principal.email
        user.email_verified = principal.email_verified
        if not principal.email_verified:
            user.email_status_notifications_enabled = False
            user.email_notifications_confirmed_at = None
        return user
    user = User(
        id=uuid4(),
        subject=principal.subject,
        email=principal.email,
        email_verified=principal.email_verified,
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


async def latest_completed_run(session: AsyncSession, upload_id: UUID) -> DetectionRun | None:
    return (
        await session.scalars(
            select(DetectionRun)
            .where(
                DetectionRun.upload_id == upload_id,
                DetectionRun.status == "completed",
            )
            .order_by(DetectionRun.completed_at.desc())
            .limit(1)
        )
    ).first()


def append_status(
    report: Report,
    target: ReportStatus,
    *,
    actor_id: UUID | None,
    reason: str | None,
    metadata: dict[str, object] | None = None,
) -> ReportStatusHistory:
    current = ReportStatus(report.status)
    if not can_transition(current, target):
        raise ReportingError(f"Cannot transition report from {current.value} to {target.value}")
    report.status = target.value
    return ReportStatusHistory(
        id=uuid4(),
        report_id=report.id,
        actor_id=actor_id,
        from_status=current.value,
        to_status=target.value,
        reason=reason,
        event_metadata=metadata or {},
        occurred_at=datetime.now(UTC),
    )


async def find_duplicate_candidates(
    session: AsyncSession,
    report: Report,
    location: Location,
    *,
    radius_meters: float = 50,
) -> list[DuplicateReportLink]:
    candidate_location = aliased(Location)
    source_point = func.ST_GeogFromText(
        f"SRID=4326;POINT({location.longitude} {location.latitude})"
    )
    distance = func.ST_Distance(candidate_location.coordinates, source_point)
    rows = (
        await session.execute(
            select(
                Report.id,
                Report.public_id,
                distance.label("distance_meters"),
            )
            .join(candidate_location, Report.location_id == candidate_location.id)
            .where(
                Report.id != report.id,
                Report.status.not_in(
                    (
                        ReportStatus.RESOLVED.value,
                        ReportStatus.REJECTED.value,
                        ReportStatus.DUPLICATE.value,
                    )
                ),
                func.ST_DWithin(
                    candidate_location.coordinates,
                    source_point,
                    radius_meters,
                ),
            )
            .order_by(distance)
            .limit(20)
        )
    ).all()

    candidates: list[DuplicateReportLink] = []
    for candidate_id, candidate_public_id, distance_meters in rows:
        distance_value = max(0.0, float(cast(float, distance_meters)))
        similarity = duplicate_similarity(distance_value, radius_meters)
        link = DuplicateReportLink(
            id=uuid4(),
            source_report_id=report.id,
            candidate_report_id=candidate_id,
            similarity_score=similarity,
            algorithm_version="nearby-geo-v1",
            factors={
                "distance_meters": distance_value,
                "candidate_public_id": candidate_public_id,
                "radius_meters": radius_meters,
                "source_type": "spatial_only",
            },
        )
        session.add(link)
        candidates.append(link)
    return candidates


async def create_draft_report(
    session: AsyncSession,
    principal: Principal,
    *,
    upload_id: UUID,
    location_id: UUID,
    title: str | None,
    description: str | None,
    default_country_code: str = "IN",
) -> tuple[Report, list[DuplicateReportLink]]:
    user = await get_or_create_user(session, principal)
    upload = await session.get(Upload, upload_id)
    location = await session.get(Location, location_id)
    if upload is None:
        raise ReportingError("Upload not found")
    if location is None or not location.confirmed_by_user:
        raise ReportingError("A confirmed location is required")
    if upload.processing_status != "completed":
        raise ReportingError("Upload must complete AI processing before report creation")
    if upload.owner_id is not None and upload.owner_id != user.id:
        raise ReportingError("Upload belongs to another reporter")

    existing = (
        await session.scalars(select(Report).where(Report.upload_id == upload.id).limit(1))
    ).first()
    if existing is not None:
        raise ReportingError(f"Upload already belongs to report {existing.public_id}")

    run = await latest_completed_run(session, upload.id)
    if run is None:
        raise ReportingError("Completed detection run not found")
    detections = (
        await session.scalars(
            select(PotholeDetection).where(PotholeDetection.detection_run_id == run.id)
        )
    ).all()
    severity = assess_visual_severity(list(detections))

    if upload.owner_id is None:
        upload.owner_id = user.id
    report = Report(
        id=uuid4(),
        public_id=create_public_report_id(
            country_code_from_metadata(location.provider_metadata) or default_country_code
        ),
        reporter_id=user.id,
        upload_id=upload.id,
        location_id=location.id,
        title=title,
        description=description,
        status=ReportStatus.DRAFT.value,
        verification_status="unverified",
        visibility="private",
        detection_count=len(detections),
        severity=severity.category,
    )
    session.add(report)
    await session.flush()
    session.add(
        ReportStatusHistory(
            id=uuid4(),
            report_id=report.id,
            actor_id=user.id,
            from_status=None,
            to_status=ReportStatus.DRAFT.value,
            reason="Report draft created",
            event_metadata={"source": "citizen_report"},
            occurred_at=datetime.now(UTC),
        )
    )
    session.add(
        SeverityAssessment(
            id=uuid4(),
            report_id=report.id,
            method_version=str(severity.factor_snapshot["method_version"]),
            category=severity.category,
            factor_snapshot=severity.factor_snapshot,
        )
    )
    duplicates = await find_duplicate_candidates(session, report, location)
    return report, duplicates
