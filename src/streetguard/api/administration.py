from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from streetguard.api.administration_schemas import (
    AdminReportItem,
    AuditLogItem,
    AuthorityAssignmentRequest,
    AuthorityAssignmentResponse,
    AuthorityMemberCreateRequest,
    AuthorityMemberResponse,
    AuthorityReportItem,
    AuthorityReportStatusRequest,
)
from streetguard.api.communications import record_report_status_notification
from streetguard.config import Settings, get_settings
from streetguard.database import get_session
from streetguard.domain.statuses import ReportStatus
from streetguard.models.core import (
    AuditLog,
    Authority,
    AuthorityAssignment,
    AuthorityMembership,
    Location,
    Report,
    User,
)
from streetguard.reporting import ReportingError, append_status, get_or_create_user
from streetguard.security.oidc import require_permission
from streetguard.security.principal import Principal
from streetguard.security.rbac import Permission, Role

administration_router = APIRouter(prefix="/administration", tags=["administration"])
authority_portal_router = APIRouter(prefix="/authority", tags=["authority portal"])

require_manage_authorities = require_permission(Permission.MANAGE_AUTHORITIES)
require_view_audit_logs = require_permission(Permission.VIEW_AUDIT_LOGS)
require_update_assigned_reports = require_permission(Permission.UPDATE_ASSIGNED_REPORTS)


async def require_global_authority_admin(
    principal: Principal = Depends(require_manage_authorities),
    session: AsyncSession = Depends(get_session),
) -> Principal:
    if Role.GLOBAL_ADMINISTRATOR not in principal.roles:
        raise HTTPException(
            status_code=403,
            detail=(
                "Global administrator role is required until regional admin scopes are configured"
            ),
        )
    user = (
        await session.scalars(select(User).where(User.subject == principal.subject).limit(1))
    ).first()
    if user is not None and not user.is_active:
        raise HTTPException(
            status_code=403, detail="Inactive accounts cannot administer authorities"
        )
    return principal


async def require_global_audit_admin(
    principal: Principal = Depends(require_view_audit_logs),
    session: AsyncSession = Depends(get_session),
) -> Principal:
    if Role.GLOBAL_ADMINISTRATOR not in principal.roles:
        raise HTTPException(
            status_code=403,
            detail="Global administrator role is required to view cross-region audit logs",
        )
    user = (
        await session.scalars(select(User).where(User.subject == principal.subject).limit(1))
    ).first()
    if user is not None and not user.is_active:
        raise HTTPException(status_code=403, detail="Inactive accounts cannot view audit logs")
    return principal


async def commit_or_unavailable(session: AsyncSession, detail: str) -> None:
    try:
        await session.commit()
    except SQLAlchemyError as exc:
        await session.rollback()
        raise HTTPException(status_code=503, detail=detail) from exc


def audit_entry(
    principal: Principal,
    actor: User,
    *,
    action: str,
    target_type: str,
    target_id: str,
    before: dict[str, object] | None = None,
    after: dict[str, object] | None = None,
) -> AuditLog:
    return AuditLog(
        actor_subject=principal.subject,
        actor_user_id=actor.id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        before_state=before,
        after_state=after,
    )


def authority_member_response(
    membership: AuthorityMembership,
    user: User,
) -> AuthorityMemberResponse:
    return AuthorityMemberResponse(
        id=membership.id,
        user_id=user.id,
        user_subject=user.subject,
        email=user.email,
        active=membership.active,
        created_at=membership.created_at,
        updated_at=membership.updated_at,
    )


async def get_active_authority_ids(session: AsyncSession, user_id: UUID) -> list[UUID]:
    result = await session.scalars(
        select(AuthorityMembership.authority_id)
        .join(Authority, AuthorityMembership.authority_id == Authority.id)
        .where(
            AuthorityMembership.user_id == user_id,
            AuthorityMembership.active.is_(True),
            Authority.active.is_(True),
            Authority.is_verified.is_(True),
        )
    )
    return list(result.all())


async def get_assignment_report(
    session: AsyncSession,
    public_id: str,
    authority_ids: list[UUID],
) -> tuple[Report, AuthorityAssignment, Authority, Location]:
    if not authority_ids:
        raise HTTPException(status_code=404, detail="Assigned report not found")
    row = (
        await session.execute(
            select(Report, AuthorityAssignment, Authority, Location)
            .join(AuthorityAssignment, AuthorityAssignment.report_id == Report.id)
            .join(Authority, AuthorityAssignment.authority_id == Authority.id)
            .join(Location, Report.location_id == Location.id)
            .where(
                Report.public_id == public_id,
                Report.visibility == "public",
                Report.verification_status == "verified",
                AuthorityAssignment.authority_id.in_(authority_ids),
            )
            .limit(1)
            .with_for_update()
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Assigned report not found")
    report, assignment, authority, location = row
    return report, assignment, authority, location


def authority_report_response(
    report: Report,
    assignment: AuthorityAssignment,
    authority: Authority,
    location: Location,
) -> AuthorityReportItem:
    return AuthorityReportItem(
        assignment_id=assignment.id,
        public_id=report.public_id,
        status=report.status,
        title=report.title,
        description=report.description,
        severity=report.severity,
        location_address=location.formatted_address,
        latitude=location.latitude,
        longitude=location.longitude,
        assigned_at=assignment.assigned_at,
        completed_at=assignment.completed_at,
        notes=assignment.notes,
        authority_name=authority.name,
    )


@administration_router.get("/reports", response_model=list[AdminReportItem])
async def list_reports_ready_for_assignment(
    session: AsyncSession = Depends(get_session),
    _principal: Principal = Depends(require_global_authority_admin),
) -> list[AdminReportItem]:
    prior_assignment = select(AuthorityAssignment.id).where(
        AuthorityAssignment.report_id == Report.id
    )
    rows = (
        await session.execute(
            select(Report, Location.formatted_address)
            .join(Location, Report.location_id == Location.id)
            .where(
                Report.status == ReportStatus.VERIFIED.value,
                Report.visibility == "public",
                Report.verification_status == "verified",
                ~prior_assignment.exists(),
            )
            .order_by(Report.submitted_at, Report.created_at)
            .limit(100)
        )
    ).all()
    return [
        AdminReportItem(
            public_id=report.public_id,
            status=report.status,
            title=report.title,
            severity=report.severity,
            submitted_at=report.submitted_at,
            location_address=address,
        )
        for report, address in rows
    ]


@administration_router.post(
    "/reports/{public_id}/assign",
    response_model=AuthorityAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_report_to_authority(
    public_id: str,
    payload: AuthorityAssignmentRequest,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_global_authority_admin),
    settings: Settings = Depends(get_settings),
) -> AuthorityAssignmentResponse:
    if not payload.confirmed:
        raise HTTPException(status_code=400, detail="Authority assignment must be confirmed")

    report = (
        await session.scalars(
            select(Report).where(Report.public_id == public_id).limit(1).with_for_update()
        )
    ).first()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    if (
        report.status != ReportStatus.VERIFIED.value
        or report.visibility != "public"
        or report.verification_status != "verified"
    ):
        raise HTTPException(status_code=409, detail="Only public verified reports can be assigned")

    authority = await session.get(Authority, payload.authority_id)
    if authority is None or not authority.active or not authority.is_verified:
        raise HTTPException(status_code=404, detail="Active verified authority not found")
    if report.location_id is None or await session.get(Location, report.location_id) is None:
        raise HTTPException(status_code=409, detail="Report location is unavailable")

    prior_assignment = (
        await session.scalars(
            select(AuthorityAssignment).where(AuthorityAssignment.report_id == report.id).limit(1)
        )
    ).first()
    if prior_assignment is not None:
        raise HTTPException(status_code=409, detail="Report already has an authority assignment")

    actor = await get_or_create_user(session, principal)
    now = datetime.now(UTC)
    assignment = AuthorityAssignment(
        id=uuid4(),
        report_id=report.id,
        authority_id=authority.id,
        assigned_by_id=actor.id,
        assigned_at=now,
        notes=payload.notes.strip() if payload.notes else None,
    )
    try:
        history = append_status(
            report,
            ReportStatus.ASSIGNED_TO_AUTHORITY,
            actor_id=actor.id,
            reason="Assigned to verified authority",
            metadata={"authority_id": str(authority.id)},
        )
    except ReportingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    session.add(assignment)
    session.add(history)
    session.add(
        audit_entry(
            principal,
            actor,
            action="report.authority_assigned",
            target_type="report",
            target_id=report.public_id,
            after={
                "status": report.status,
                "authority_id": str(authority.id),
                "assignment_id": str(assignment.id),
            },
        )
    )
    await commit_or_unavailable(session, "Could not save authority assignment")
    if report.reporter_id is not None:
        await record_report_status_notification(session, report, report.reporter_id, settings)
    return AuthorityAssignmentResponse(
        assignment_id=assignment.id,
        public_id=report.public_id,
        authority_id=authority.id,
        authority_name=authority.name,
        status=report.status,
        assigned_at=assignment.assigned_at,
    )


@administration_router.get(
    "/authorities/{authority_id}/members", response_model=list[AuthorityMemberResponse]
)
async def list_authority_members(
    authority_id: UUID,
    session: AsyncSession = Depends(get_session),
    _principal: Principal = Depends(require_global_authority_admin),
) -> list[AuthorityMemberResponse]:
    authority = await session.get(Authority, authority_id)
    if authority is None:
        raise HTTPException(status_code=404, detail="Authority not found")
    rows = (
        await session.execute(
            select(AuthorityMembership, User)
            .join(User, AuthorityMembership.user_id == User.id)
            .where(AuthorityMembership.authority_id == authority_id)
            .order_by(User.subject)
        )
    ).all()
    return [authority_member_response(membership, user) for membership, user in rows]


@administration_router.post(
    "/authorities/{authority_id}/members",
    response_model=AuthorityMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_authority_member(
    authority_id: UUID,
    payload: AuthorityMemberCreateRequest,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_global_authority_admin),
) -> AuthorityMemberResponse:
    if not payload.confirmed:
        raise HTTPException(status_code=400, detail="Authority membership must be confirmed")
    authority = await session.get(Authority, authority_id)
    if authority is None or not authority.active or not authority.is_verified:
        raise HTTPException(status_code=404, detail="Active verified authority not found")
    user = (
        await session.scalars(select(User).where(User.subject == payload.user_subject).limit(1))
    ).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=404, detail="Active user account not found")
    membership = (
        await session.scalars(
            select(AuthorityMembership)
            .where(
                AuthorityMembership.authority_id == authority_id,
                AuthorityMembership.user_id == user.id,
            )
            .limit(1)
        )
    ).first()
    if membership is not None and membership.active:
        raise HTTPException(status_code=409, detail="User is already an authority member")

    actor = await get_or_create_user(session, principal)
    before: dict[str, object] | None = {"active": False} if membership is not None else None
    if membership is None:
        membership = AuthorityMembership(
            id=uuid4(),
            authority_id=authority.id,
            user_id=user.id,
            granted_by_id=actor.id,
            active=True,
        )
        session.add(membership)
    else:
        membership.active = True
        membership.granted_by_id = actor.id
    session.add(
        audit_entry(
            principal,
            actor,
            action="authority.member_added",
            target_type="authority_membership",
            target_id=str(membership.id),
            before=before,
            after={
                "authority_id": str(authority.id),
                "user_id": str(user.id),
                "active": True,
            },
        )
    )
    await commit_or_unavailable(session, "Could not save authority membership")
    return authority_member_response(membership, user)


@administration_router.delete(
    "/authorities/{authority_id}/members/{user_id}",
    response_model=AuthorityMemberResponse,
)
async def remove_authority_member(
    authority_id: UUID,
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_global_authority_admin),
) -> AuthorityMemberResponse:
    membership = (
        await session.scalars(
            select(AuthorityMembership)
            .where(
                AuthorityMembership.authority_id == authority_id,
                AuthorityMembership.user_id == user_id,
            )
            .limit(1)
        )
    ).first()
    if membership is None:
        raise HTTPException(status_code=404, detail="Authority membership not found")
    user = await session.get(User, membership.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User account not found")
    if membership.active:
        actor = await get_or_create_user(session, principal)
        membership.active = False
        session.add(
            audit_entry(
                principal,
                actor,
                action="authority.member_removed",
                target_type="authority_membership",
                target_id=str(membership.id),
                before={
                    "authority_id": str(authority_id),
                    "user_id": str(user_id),
                    "active": True,
                },
                after={"active": False},
            )
        )
        await commit_or_unavailable(session, "Could not remove authority membership")
    return authority_member_response(membership, user)


@administration_router.get("/audit-logs", response_model=list[AuditLogItem])
async def list_audit_logs(
    limit: int = Query(default=50, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _principal: Principal = Depends(require_global_audit_admin),
) -> list[AuditLogItem]:
    rows = (
        await session.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit))
    ).all()
    return [
        AuditLogItem(
            id=entry.id,
            actor_subject=entry.actor_subject,
            action=entry.action,
            target_type=entry.target_type,
            target_id=entry.target_id,
            created_at=entry.created_at,
        )
        for entry in rows
    ]


@authority_portal_router.get("/reports", response_model=list[AuthorityReportItem])
async def list_assigned_reports(
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_update_assigned_reports),
) -> list[AuthorityReportItem]:
    user = await get_or_create_user(session, principal)
    if not user.is_active:
        raise HTTPException(
            status_code=403, detail="Inactive accounts cannot access authority reports"
        )
    await session.commit()
    authority_ids = await get_active_authority_ids(session, user.id)
    if not authority_ids:
        return []
    rows = (
        await session.execute(
            select(Report, AuthorityAssignment, Authority, Location)
            .join(AuthorityAssignment, AuthorityAssignment.report_id == Report.id)
            .join(Authority, AuthorityAssignment.authority_id == Authority.id)
            .join(Location, Report.location_id == Location.id)
            .where(
                AuthorityAssignment.authority_id.in_(authority_ids),
                Report.visibility == "public",
                Report.verification_status == "verified",
            )
            .order_by(AuthorityAssignment.assigned_at.desc())
            .limit(100)
        )
    ).all()
    return [
        authority_report_response(report, assignment, authority, location)
        for report, assignment, authority, location in rows
    ]


@authority_portal_router.post(
    "/reports/{public_id}/status",
    response_model=AuthorityReportItem,
)
async def update_assigned_report_status(
    public_id: str,
    payload: AuthorityReportStatusRequest,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_update_assigned_reports),
    settings: Settings = Depends(get_settings),
) -> AuthorityReportItem:
    if not payload.confirmed:
        raise HTTPException(status_code=400, detail="Authority status change must be confirmed")
    user = await get_or_create_user(session, principal)
    if not user.is_active:
        raise HTTPException(
            status_code=403, detail="Inactive accounts cannot update authority reports"
        )
    await session.commit()
    authority_ids = await get_active_authority_ids(session, user.id)
    report, assignment, authority, location = await get_assignment_report(
        session,
        public_id,
        authority_ids,
    )
    if assignment.completed_at is not None:
        raise HTTPException(status_code=409, detail="Assignment is already completed")

    target = ReportStatus(payload.status)
    previous_status = report.status
    try:
        history = append_status(
            report,
            target,
            actor_id=user.id,
            reason=payload.notes.strip(),
            metadata={
                "source": "authority_portal",
                "authority_id": str(authority.id),
                "assignment_id": str(assignment.id),
            },
        )
    except ReportingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    now = datetime.now(UTC)
    assignment.notes = payload.notes.strip()
    if target == ReportStatus.RESOLVED:
        assignment.completed_at = now
        report.resolved_at = now
    session.add(history)
    session.add(
        audit_entry(
            principal,
            user,
            action="report.authority_status_changed",
            target_type="report",
            target_id=report.public_id,
            before={"status": previous_status},
            after={
                "status": report.status,
                "authority_id": str(authority.id),
                "assignment_id": str(assignment.id),
            },
        )
    )
    await commit_or_unavailable(session, "Could not save authority report status")
    if report.reporter_id is not None:
        await record_report_status_notification(session, report, report.reporter_id, settings)
    return authority_report_response(report, assignment, authority, location)
