import smtplib
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from streetguard.api.communications_schemas import (
    AuthorityCreateRequest,
    AuthorityResponse,
    AuthorityUpdateRequest,
    AuthorityVerificationRequest,
    EmailDeliveryResponse,
    NotificationItem,
    NotificationPreferenceRequest,
    NotificationPreferenceResponse,
    ReportEmailRequest,
)
from streetguard.communications import (
    EmailProviderNotConfigured,
    public_report_url,
    report_email_content,
    send_smtp_email,
    valid_email_address,
)
from streetguard.config import Settings, get_settings
from streetguard.database import get_session
from streetguard.models.core import (
    AuditLog,
    Authority,
    EmailDeliveryLog,
    GeographicalRegion,
    Location,
    Notification,
    Report,
    User,
)
from streetguard.reporting import get_or_create_user
from streetguard.security.oidc import get_current_principal, require_permission
from streetguard.security.principal import Principal
from streetguard.security.rbac import Permission, Role

authority_router = APIRouter(prefix="/authorities", tags=["authorities"])
report_email_router = APIRouter(prefix="/reports", tags=["communications"])
notification_router = APIRouter(prefix="/notifications", tags=["notifications"])

require_report_create = require_permission(Permission.CREATE_REPORT)
require_view_own = require_permission(Permission.VIEW_OWN_REPORTS)


async def require_global_administrator(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> Principal:
    if Role.GLOBAL_ADMINISTRATOR not in principal.roles:
        raise HTTPException(status_code=403, detail="Global administrator role is required")
    user = (
        await session.scalars(select(User).where(User.subject == principal.subject).limit(1))
    ).first()
    if user is not None and not user.is_active:
        raise HTTPException(
            status_code=403, detail="Inactive accounts cannot administer authorities"
        )
    return principal


def authority_snapshot(authority: Authority) -> dict[str, object]:
    return {
        "name": authority.name,
        "category": authority.category,
        "contact_email": authority.contact_email,
        "website_url": authority.website_url,
        "jurisdiction_region_id": (
            str(authority.jurisdiction_region_id) if authority.jurisdiction_region_id else None
        ),
        "is_verified": authority.is_verified,
        "active": authority.active,
    }


def authority_response(
    authority: Authority,
    jurisdiction_name: str | None,
) -> AuthorityResponse:
    return AuthorityResponse(
        id=authority.id,
        name=authority.name,
        category=authority.category,
        contact_email=authority.contact_email,
        website_url=authority.website_url,
        jurisdiction_region_id=authority.jurisdiction_region_id,
        jurisdiction_name=jurisdiction_name,
        is_verified=authority.is_verified,
        active=authority.active,
    )


def audit_authority_change(
    principal: Principal,
    authority: Authority,
    action: str,
    *,
    before: dict[str, object] | None = None,
) -> AuditLog:
    return AuditLog(
        actor_subject=principal.subject,
        actor_user_id=principal.user_id,
        action=action,
        target_type="authority",
        target_id=str(authority.id),
        before_state=before,
        after_state=authority_snapshot(authority),
    )


async def ensure_region_exists(
    session: AsyncSession,
    region_id: UUID | None,
) -> GeographicalRegion | None:
    if region_id is None:
        return None
    region = await session.get(GeographicalRegion, region_id)
    if region is None:
        raise HTTPException(status_code=404, detail="Jurisdiction region not found")
    return region


@authority_router.get("", response_model=list[AuthorityResponse])
async def list_verified_authorities(
    region_id: UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> list[AuthorityResponse]:
    statement = (
        select(Authority, GeographicalRegion.name)
        .outerjoin(GeographicalRegion, Authority.jurisdiction_region_id == GeographicalRegion.id)
        .where(Authority.active.is_(True), Authority.is_verified.is_(True))
        .order_by(Authority.name)
    )
    if region_id is not None:
        statement = statement.where(Authority.jurisdiction_region_id == region_id)
    try:
        rows = (await session.execute(statement)).all()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Authority directory is unavailable") from exc
    return [authority_response(authority, region_name) for authority, region_name in rows]


@authority_router.post("", response_model=AuthorityResponse, status_code=status.HTTP_201_CREATED)
async def create_authority(
    payload: AuthorityCreateRequest,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_global_administrator),
) -> AuthorityResponse:
    region = await ensure_region_exists(session, payload.jurisdiction_region_id)
    authority = Authority(
        id=uuid4(),
        name=payload.name.strip(),
        category=payload.category.strip(),
        contact_email=payload.contact_email,
        website_url=str(payload.website_url) if payload.website_url else None,
        jurisdiction_region_id=payload.jurisdiction_region_id,
        contact_metadata={},
        is_verified=False,
        active=True,
    )
    session.add(authority)
    session.add(audit_authority_change(principal, authority, "authority.created"))
    try:
        await session.commit()
        await session.refresh(authority)
    except SQLAlchemyError as exc:
        await session.rollback()
        raise HTTPException(status_code=503, detail="Authority directory is unavailable") from exc
    return authority_response(authority, region.name if region else None)


@authority_router.put("/{authority_id}", response_model=AuthorityResponse)
async def update_authority(
    authority_id: UUID,
    payload: AuthorityUpdateRequest,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_global_administrator),
) -> AuthorityResponse:
    authority = await session.get(Authority, authority_id)
    if authority is None:
        raise HTTPException(status_code=404, detail="Authority not found")
    region = await ensure_region_exists(session, payload.jurisdiction_region_id)
    before = authority_snapshot(authority)
    contact_changed = (
        authority.name != payload.name.strip()
        or authority.category != payload.category.strip()
        or authority.contact_email != payload.contact_email
        or authority.website_url != (str(payload.website_url) if payload.website_url else None)
        or authority.jurisdiction_region_id != payload.jurisdiction_region_id
    )
    authority.name = payload.name.strip()
    authority.category = payload.category.strip()
    authority.contact_email = payload.contact_email
    authority.website_url = str(payload.website_url) if payload.website_url else None
    authority.jurisdiction_region_id = payload.jurisdiction_region_id
    authority.active = payload.active
    if contact_changed:
        authority.is_verified = False
        authority.contact_metadata = {}
    session.add(audit_authority_change(principal, authority, "authority.updated", before=before))
    try:
        await session.commit()
        await session.refresh(authority)
    except SQLAlchemyError as exc:
        await session.rollback()
        raise HTTPException(status_code=503, detail="Authority directory is unavailable") from exc
    return authority_response(authority, region.name if region else None)


@authority_router.post("/{authority_id}/verify", response_model=AuthorityResponse)
async def verify_authority(
    authority_id: UUID,
    payload: AuthorityVerificationRequest,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_global_administrator),
) -> AuthorityResponse:
    if not payload.confirmed:
        raise HTTPException(status_code=400, detail="Authority verification must be confirmed")
    authority = await session.get(Authority, authority_id)
    if authority is None:
        raise HTTPException(status_code=404, detail="Authority not found")
    if not authority.active:
        raise HTTPException(status_code=409, detail="Inactive authorities cannot be verified")

    before = authority_snapshot(authority)
    verified_at = datetime.now(UTC)
    authority.is_verified = True
    authority.contact_metadata = {
        **authority.contact_metadata,
        "verification_evidence_url": str(payload.evidence_url),
        "verified_at": verified_at.isoformat(),
        "verified_by": principal.subject,
    }
    session.add(audit_authority_change(principal, authority, "authority.verified", before=before))
    region = await ensure_region_exists(session, authority.jurisdiction_region_id)
    try:
        await session.commit()
        await session.refresh(authority)
    except SQLAlchemyError as exc:
        await session.rollback()
        raise HTTPException(status_code=503, detail="Authority directory is unavailable") from exc
    return authority_response(authority, region.name if region else None)


@report_email_router.post(
    "/{public_id}/email",
    response_model=EmailDeliveryResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def send_report_email(
    public_id: str,
    payload: ReportEmailRequest,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_report_create),
    settings: Settings = Depends(get_settings),
) -> EmailDeliveryResponse:
    if not payload.confirmed:
        raise HTTPException(status_code=400, detail="Email sending requires user confirmation")
    if not settings.smtp_configured or not valid_email_address(settings.smtp_from_email):
        raise HTTPException(status_code=503, detail="Email provider is not configured")

    report = (
        await session.scalars(select(Report).where(Report.public_id == public_id).limit(1))
    ).first()
    if report is None or report.visibility != "public":
        raise HTTPException(status_code=404, detail="Public report not found")
    if report.verification_status != "verified":
        raise HTTPException(status_code=409, detail="Only verified reports can be emailed")
    reporter = await get_or_create_user(session, principal)
    if report.reporter_id != reporter.id:
        raise HTTPException(status_code=403, detail="Only the report owner can send this report")

    if payload.authority_id is not None:
        authority = await session.get(Authority, payload.authority_id)
        if authority is None or not authority.active or not authority.is_verified:
            raise HTTPException(status_code=404, detail="Verified authority not found")
        if not authority.contact_email:
            raise HTTPException(status_code=409, detail="Authority has no verified contact email")
        recipient = authority.contact_email
    else:
        manual_recipient = payload.recipient_email
        if manual_recipient is None:
            raise HTTPException(status_code=422, detail="A recipient email address is required")
        recipient = manual_recipient

    now = datetime.now(UTC)
    recent_attempts = await session.scalar(
        select(func.count(EmailDeliveryLog.id)).where(
            EmailDeliveryLog.requested_by_id == reporter.id,
            EmailDeliveryLog.created_at >= now - timedelta(hours=1),
        )
    )
    if int(recent_attempts or 0) >= 5:
        raise HTTPException(status_code=429, detail="Email share limit reached; try again later")

    location = await session.get(Location, report.location_id)
    if location is None:
        raise HTTPException(status_code=500, detail="Report location is unavailable")
    subject, body = report_email_content(report, location, settings)
    delivery = EmailDeliveryLog(
        purpose="report_share",
        report_id=report.id,
        requested_by_id=reporter.id,
        recipient=recipient,
        provider="smtp",
        delivery_status="pending",
        confirmed_by_user_at=now,
    )
    session.add(delivery)
    try:
        await session.commit()
        await session.refresh(delivery)
    except SQLAlchemyError as exc:
        await session.rollback()
        raise HTTPException(status_code=503, detail="Email delivery log is unavailable") from exc

    try:
        delivery.provider_message_id = await send_smtp_email(settings, recipient, subject, body)
        delivery.delivery_status = "accepted"
    except (EmailProviderNotConfigured, OSError, smtplib.SMTPException) as exc:
        delivery.delivery_status = "failed"
        delivery.error_message = type(exc).__name__
        await session.commit()
        raise HTTPException(
            status_code=502, detail="Email provider could not accept the report"
        ) from exc

    await session.commit()
    return EmailDeliveryResponse(
        id=delivery.id,
        purpose=delivery.purpose,
        delivery_status=delivery.delivery_status,
        provider_message_id=delivery.provider_message_id,
        created_at=delivery.created_at,
    )


@report_email_router.get("/{public_id}/emails", response_model=list[EmailDeliveryResponse])
async def list_report_email_deliveries(
    public_id: str,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_view_own),
) -> list[EmailDeliveryResponse]:
    report = (
        await session.scalars(select(Report).where(Report.public_id == public_id).limit(1))
    ).first()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    reporter = await get_or_create_user(session, principal)
    if report.reporter_id != reporter.id:
        raise HTTPException(status_code=403, detail="Report belongs to another reporter")
    deliveries = (
        await session.scalars(
            select(EmailDeliveryLog)
            .where(EmailDeliveryLog.report_id == report.id)
            .order_by(EmailDeliveryLog.created_at.desc())
            .limit(50)
        )
    ).all()
    return [
        EmailDeliveryResponse(
            id=delivery.id,
            purpose=delivery.purpose,
            delivery_status=delivery.delivery_status,
            provider_message_id=delivery.provider_message_id,
            created_at=delivery.created_at,
        )
        for delivery in deliveries
    ]


@notification_router.get("/preferences", response_model=NotificationPreferenceResponse)
async def get_notification_preferences(
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_view_own),
) -> NotificationPreferenceResponse:
    user = await get_or_create_user(session, principal)
    await session.commit()
    return NotificationPreferenceResponse(
        email_status_notifications_enabled=user.email_status_notifications_enabled,
        email=user.email,
    )


@notification_router.put("/preferences", response_model=NotificationPreferenceResponse)
async def update_notification_preferences(
    payload: NotificationPreferenceRequest,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_view_own),
    settings: Settings = Depends(get_settings),
) -> NotificationPreferenceResponse:
    user = await get_or_create_user(session, principal)
    if payload.email_status_notifications_enabled:
        if not payload.confirmed:
            raise HTTPException(status_code=400, detail="Email notifications require consent")
        if not user.email_verified or not user.email or not valid_email_address(user.email):
            raise HTTPException(
                status_code=422, detail="A verified identity email address is required"
            )
        if not settings.smtp_configured or not valid_email_address(settings.smtp_from_email):
            raise HTTPException(status_code=503, detail="Email provider is not configured")
        user.email_notifications_confirmed_at = datetime.now(UTC)
    else:
        user.email_notifications_confirmed_at = None
    user.email_status_notifications_enabled = payload.email_status_notifications_enabled
    await session.commit()
    return NotificationPreferenceResponse(
        email_status_notifications_enabled=user.email_status_notifications_enabled,
        email=user.email,
    )


@notification_router.get("/mine", response_model=list[NotificationItem])
async def list_my_notifications(
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_view_own),
) -> list[NotificationItem]:
    user = await get_or_create_user(session, principal)
    notifications = (
        await session.scalars(
            select(Notification)
            .where(Notification.user_id == user.id)
            .order_by(Notification.created_at.desc())
            .limit(50)
        )
    ).all()
    return [
        NotificationItem(
            id=notification.id,
            report_id=notification.report_id,
            notification_type=notification.notification_type,
            subject=notification.subject,
            body=notification.body,
            created_at=notification.created_at,
            read_at=notification.read_at,
        )
        for notification in notifications
    ]


@notification_router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_notification_read(
    notification_id: UUID,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_view_own),
) -> None:
    user = await get_or_create_user(session, principal)
    notification = await session.get(Notification, notification_id)
    if notification is None or notification.user_id != user.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.read_at = datetime.now(UTC)
    await session.commit()


async def record_report_status_notification(
    session: AsyncSession,
    report: Report,
    user_id: UUID,
    settings: Settings,
) -> None:
    subject = f"Report {report.public_id} status updated"
    body = f"Report status: {report.status.replace('_', ' ')}"
    if report.visibility == "public":
        body += f"\nView report: {public_report_url(settings, report.public_id)}"
    else:
        body += "\nThis report is not publicly visible while it is under review."
    notification = Notification(
        id=uuid4(),
        user_id=user_id,
        report_id=report.id,
        notification_type="report_status_update",
        subject=subject,
        body=body,
    )
    session.add(notification)
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=500, detail="Report owner is unavailable")

    delivery: EmailDeliveryLog | None = None
    recipient_email: str | None = None
    if user.email_verified and user.email_status_notifications_enabled and user.email:
        recipient_email = user.email
        delivery = EmailDeliveryLog(
            purpose="status_update",
            report_id=report.id,
            requested_by_id=user.id,
            recipient=recipient_email,
            provider="smtp",
            delivery_status="pending",
            confirmed_by_user_at=(user.email_notifications_confirmed_at or datetime.now(UTC)),
        )
        session.add(delivery)
    await session.commit()

    if delivery is None or recipient_email is None:
        return
    location = await session.get(Location, report.location_id)
    if location is None:
        delivery.delivery_status = "failed"
        delivery.error_message = "LocationUnavailable"
        await session.commit()
        return
    email_subject, email_body = report_email_content(
        report,
        location,
        settings,
        status_update=True,
    )
    if not settings.smtp_configured or not valid_email_address(settings.smtp_from_email):
        delivery.delivery_status = "failed"
        delivery.error_message = "EmailProviderNotConfigured"
        await session.commit()
        return
    try:
        delivery.provider_message_id = await send_smtp_email(
            settings,
            recipient_email,
            email_subject,
            email_body,
        )
        delivery.delivery_status = "accepted"
    except (EmailProviderNotConfigured, OSError, smtplib.SMTPException) as exc:
        delivery.delivery_status = "failed"
        delivery.error_message = type(exc).__name__
    await session.commit()
