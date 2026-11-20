from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from streetguard.api.communications import record_report_status_notification
from streetguard.api.report_schemas import (
    DuplicateCandidateResponse,
    DuplicateDecisionRequest,
    ReportCreateRequest,
    ReportHistoryItem,
    ReportListItem,
    ReportLocationResponse,
    ReportResponse,
    ReportSeverityResponse,
    VerificationRequest,
)
from streetguard.config import Settings, get_settings
from streetguard.database import get_session
from streetguard.domain.geography import AddressComponents
from streetguard.domain.severity import VISUAL_SEVERITY_DISCLAIMER
from streetguard.domain.statuses import ReportStatus
from streetguard.models.core import (
    DuplicateReportLink,
    Location,
    PotholeDetection,
    Report,
    ReportStatusHistory,
    SeverityAssessment,
    Upload,
)
from streetguard.reporting import (
    ReportingError,
    append_status,
    create_draft_report,
    get_or_create_user,
    latest_completed_run,
)
from streetguard.security.oidc import require_permission
from streetguard.security.principal import Principal
from streetguard.security.rbac import Permission
from streetguard.storage import S3ObjectStorage

router = APIRouter(prefix="/reports", tags=["reports"])
require_create_report = require_permission(Permission.CREATE_REPORT)
require_review_report = require_permission(Permission.REVIEW_REPORTS)
require_view_own = require_permission(Permission.VIEW_OWN_REPORTS)


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    payload: ReportCreateRequest,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_create_report),
    settings: Settings = Depends(get_settings),
) -> ReportResponse:
    try:
        report, _ = await create_draft_report(
            session,
            principal,
            upload_id=payload.upload_id,
            location_id=payload.location_id,
            title=payload.title,
            description=payload.description,
            default_country_code=settings.product_country_code,
        )
        await session.commit()
    except ReportingError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return await build_report_response(session, report, settings, include_duplicates=True)


@router.get("/mine", response_model=list[ReportListItem])
async def list_my_reports(
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_view_own),
) -> list[ReportListItem]:
    user = await get_or_create_user(session, principal)
    reports = (
        await session.scalars(
            select(Report).where(Report.reporter_id == user.id).order_by(Report.created_at.desc())
        )
    ).all()
    return [
        ReportListItem(
            public_id=report.public_id,
            status=report.status,
            verification_status=report.verification_status,
            severity=report.severity,
            created_at=report.created_at,
            submitted_at=report.submitted_at,
        )
        for report in reports
    ]


@router.post("/{public_id}/submit", response_model=ReportResponse)
async def submit_report(
    public_id: str,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_create_report),
    settings: Settings = Depends(get_settings),
) -> ReportResponse:
    report = await report_by_public_id(session, public_id)
    user = await get_or_create_user(session, principal)
    if report.reporter_id != user.id:
        raise HTTPException(status_code=403, detail="Report belongs to another user")

    current = ReportStatus(report.status)
    if current == ReportStatus.DRAFT:
        run = await latest_completed_run(session, report.upload_id)
        if run is None:
            raise HTTPException(status_code=409, detail="Detection result is not complete")
        report.submitted_at = datetime.now(UTC)
        histories = [
            append_status(
                report,
                ReportStatus.SUBMITTED,
                actor_id=user.id,
                reason="Reporter submitted road damage report",
            ),
            append_status(
                report,
                ReportStatus.AI_PROCESSING,
                actor_id=user.id,
                reason="Completed detection attached",
                metadata={"detection_run_id": str(run.id)},
            ),
            append_status(
                report,
                ReportStatus.AWAITING_VERIFICATION,
                actor_id=user.id,
                reason="AI processing complete; human review required",
            ),
        ]
        session.add_all(histories)
        await session.commit()
        await record_report_status_notification(session, report, user.id, settings)
    elif current not in {
        ReportStatus.SUBMITTED,
        ReportStatus.AI_PROCESSING,
        ReportStatus.AWAITING_VERIFICATION,
    }:
        raise HTTPException(status_code=409, detail="Report can no longer be submitted")
    return await build_report_response(session, report, settings, include_duplicates=True)


@router.post("/{public_id}/verification", response_model=ReportResponse)
async def verify_report(
    public_id: str,
    payload: VerificationRequest,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_review_report),
    settings: Settings = Depends(get_settings),
) -> ReportResponse:
    report = await report_by_public_id(session, public_id)
    if report.status != ReportStatus.AWAITING_VERIFICATION.value:
        raise HTTPException(status_code=409, detail="Report is not awaiting verification")
    reviewer = await get_or_create_user(session, principal)
    target = ReportStatus(payload.decision)

    if target == ReportStatus.DUPLICATE and not payload.duplicate_target_report_id:
        raise HTTPException(status_code=422, detail="A duplicate target report ID is required")
    if payload.duplicate_target_report_id:
        candidate = await report_by_public_id(session, payload.duplicate_target_report_id)
        link = (
            await session.scalars(
                select(DuplicateReportLink)
                .where(
                    DuplicateReportLink.source_report_id == report.id,
                    DuplicateReportLink.candidate_report_id == candidate.id,
                )
                .limit(1)
            )
        ).first()
        if link is None:
            raise HTTPException(status_code=422, detail="The duplicate target is not a candidate")
        link.review_status = "linked"
        link.reviewed_by_id = reviewer.id
        link.factors = {**link.factors, "review_reason": payload.reason}

    if payload.severity_override:
        existing = (
            await session.scalars(
                select(SeverityAssessment)
                .where(SeverityAssessment.report_id == report.id)
                .order_by(SeverityAssessment.created_at.desc())
                .limit(1)
            )
        ).first()
        session.add(
            SeverityAssessment(
                report_id=report.id,
                method_version="human-review-v1",
                category=payload.severity_override,
                factor_snapshot={
                    "previous_category": existing.category if existing else None,
                    "disclaimer": VISUAL_SEVERITY_DISCLAIMER,
                },
                human_overridden=True,
                override_reason=payload.reason,
                reviewer_id=reviewer.id,
            )
        )
        report.severity = payload.severity_override

    history = append_status(
        report,
        target,
        actor_id=reviewer.id,
        reason=payload.reason,
        metadata={"source": "human_reviewer"},
    )
    session.add(history)
    report.verification_status = "verified" if target == ReportStatus.VERIFIED else target.value
    report.visibility = "public" if target == ReportStatus.VERIFIED else "private"
    await session.commit()
    if report.reporter_id is not None:
        await record_report_status_notification(
            session,
            report,
            report.reporter_id,
            settings,
        )
    return await build_report_response(session, report, settings, include_duplicates=True)


@router.get("/{public_id}", response_model=ReportResponse)
async def track_public_report(
    public_id: str,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ReportResponse:
    report = await report_by_public_id(session, public_id)
    if report.visibility != "public":
        raise HTTPException(status_code=404, detail="Public report not found")
    return await build_report_response(
        session,
        report,
        settings,
        include_duplicates=False,
        include_private_notes=False,
    )


@router.get("/{public_id}/duplicates", response_model=list[DuplicateCandidateResponse])
async def list_duplicate_candidates(
    public_id: str,
    session: AsyncSession = Depends(get_session),
    _principal: Principal = Depends(require_review_report),
) -> list[DuplicateCandidateResponse]:
    report = await report_by_public_id(session, public_id)
    links = (
        await session.scalars(
            select(DuplicateReportLink).where(DuplicateReportLink.source_report_id == report.id)
        )
    ).all()
    reports = {
        candidate.id: candidate.public_id
        for candidate in (
            await session.scalars(
                select(Report).where(Report.id.in_([link.candidate_report_id for link in links]))
            )
        ).all()
    }
    return duplicate_responses(links, reports)


@router.post("/{public_id}/duplicates/{candidate_public_id}", status_code=204)
async def decide_duplicate_candidate(
    public_id: str,
    candidate_public_id: str,
    payload: DuplicateDecisionRequest,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_review_report),
) -> None:
    report = await report_by_public_id(session, public_id)
    candidate = await report_by_public_id(session, candidate_public_id)
    link = (
        await session.scalars(
            select(DuplicateReportLink)
            .where(
                DuplicateReportLink.source_report_id == report.id,
                DuplicateReportLink.candidate_report_id == candidate.id,
            )
            .limit(1)
        )
    ).first()
    if link is None:
        raise HTTPException(status_code=404, detail="Duplicate candidate not found")
    reviewer = await get_or_create_user(session, principal)
    link.review_status = payload.decision
    link.reviewed_by_id = reviewer.id
    link.factors = {**link.factors, "review_reason": payload.reason}
    await session.commit()


async def report_by_public_id(session: AsyncSession, public_id: str) -> Report:
    report = (
        await session.scalars(select(Report).where(Report.public_id == public_id).limit(1))
    ).first()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


def duplicate_responses(
    links: Sequence[DuplicateReportLink],
    reports: dict[UUID, str],
) -> list[DuplicateCandidateResponse]:
    return [
        DuplicateCandidateResponse(
            candidate_report_id=reports[link.candidate_report_id],
            similarity_score=link.similarity_score,
            distance_meters=(
                float(link.factors["distance_meters"])
                if link.factors.get("distance_meters") is not None
                else None
            ),
            review_status=link.review_status,
            algorithm_version=link.algorithm_version,
        )
        for link in links
    ]


async def build_report_response(
    session: AsyncSession,
    report: Report,
    settings: Settings,
    *,
    include_duplicates: bool,
    include_private_notes: bool = True,
) -> ReportResponse:
    upload = await session.get(Upload, report.upload_id)
    location = await session.get(Location, report.location_id)
    if upload is None or location is None:
        raise HTTPException(status_code=500, detail="Report data is incomplete")

    severity = (
        await session.scalars(
            select(SeverityAssessment)
            .where(SeverityAssessment.report_id == report.id)
            .order_by(SeverityAssessment.created_at.desc())
            .limit(1)
        )
    ).first()
    if severity is None:
        raise HTTPException(status_code=500, detail="Report severity assessment is missing")

    run = await latest_completed_run(session, upload.id)
    detections = (
        (
            await session.scalars(
                select(PotholeDetection)
                .where(PotholeDetection.detection_run_id == run.id)
                .order_by(PotholeDetection.created_at)
            )
        ).all()
        if run
        else []
    )
    history = (
        await session.scalars(
            select(ReportStatusHistory)
            .where(ReportStatusHistory.report_id == report.id)
            .order_by(ReportStatusHistory.occurred_at)
        )
    ).all()
    annotated_url = (
        S3ObjectStorage(settings).presign_download(upload.annotated_object_key)
        if upload.annotated_object_key
        else None
    )
    duplicate_values: list[DuplicateCandidateResponse] = []
    if include_duplicates:
        links = (
            await session.scalars(
                select(DuplicateReportLink).where(DuplicateReportLink.source_report_id == report.id)
            )
        ).all()
        candidates = (
            await session.scalars(
                select(Report).where(Report.id.in_([link.candidate_report_id for link in links]))
            )
        ).all()
        duplicate_values = duplicate_responses(
            links, {candidate.id: candidate.public_id for candidate in candidates}
        )

    return ReportResponse(
        id=report.id,
        public_id=report.public_id,
        status=report.status,
        verification_status=report.verification_status,
        visibility=report.visibility,
        created_at=report.created_at,
        submitted_at=report.submitted_at,
        detection_count=report.detection_count,
        title=report.title,
        description=report.description,
        location=ReportLocationResponse(
            latitude=location.latitude,
            longitude=location.longitude,
            accuracy_meters=location.accuracy_meters,
            source=location.source,
            formatted_address=location.formatted_address,
            components=AddressComponents.model_validate(location.provider_metadata),
        ),
        severity=ReportSeverityResponse(
            category=severity.category,
            method_version=severity.method_version,
            factor_snapshot=severity.factor_snapshot,
            human_overridden=severity.human_overridden,
            disclaimer=VISUAL_SEVERITY_DISCLAIMER,
        ),
        detections=list(detections),
        annotated_image_url=annotated_url,
        history=[
            ReportHistoryItem(
                from_status=item.from_status,
                to_status=item.to_status,
                reason=item.reason if include_private_notes else None,
                occurred_at=item.occurred_at,
            )
            for item in history
        ],
        duplicate_candidates=duplicate_values,
    )
