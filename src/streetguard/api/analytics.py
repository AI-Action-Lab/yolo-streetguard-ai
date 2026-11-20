from datetime import UTC, datetime
from decimal import Decimal
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from streetguard.config import Settings, get_settings
from streetguard.database import get_session
from streetguard.models.core import Authority, AuthorityAssignment, Location, Report

router = APIRouter(prefix="/analytics", tags=["analytics"])

SEVERITY_CATEGORIES = ("low", "moderate", "high", "critical", "unknown")
OPEN_STATUSES = frozenset({"verified", "assigned_to_authority", "in_progress"})
INDIA_BOUNDS = (68.0, 6.0, 97.5, 37.5)


class MonthlySubmission(BaseModel):
    month: str
    count: int


class GeographicBreakdown(BaseModel):
    name: str
    report_count: int
    resolved_count: int


class AuthorityCompletion(BaseModel):
    authority_id: UUID
    authority_name: str
    assigned_count: int
    completed_count: int
    average_completion_hours: float | None


class AuthorityResponseSummary(BaseModel):
    assigned_count: int
    completed_count: int
    open_count: int
    average_completion_hours: float | None
    first_response_time_available: bool
    by_authority: list[AuthorityCompletion]


class AnalyticsSummary(BaseModel):
    country_code: str
    total_verified_reports: int
    open_reports: int
    resolved_reports: int
    severity_distribution: dict[str, int]
    monthly_submissions: list[MonthlySubmission]
    states: list[GeographicBreakdown]
    cities: list[GeographicBreakdown]
    state_unclassified_reports: int
    city_unclassified_reports: int
    authority_response: AuthorityResponseSummary


def _month_start(now: datetime, months_ago: int) -> datetime:
    month_index = now.year * 12 + now.month - 1 - months_ago
    year, month = divmod(month_index, 12)
    return datetime(year, month + 1, 1, tzinfo=UTC)


@router.get("/summary", response_model=AnalyticsSummary)
async def analytics_summary(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AnalyticsSummary:
    filters = [
        Report.visibility == "public",
        Report.verification_status == "verified",
    ]
    if settings.product_country_code.upper() == "IN":
        minimum_longitude, minimum_latitude, maximum_longitude, maximum_latitude = INDIA_BOUNDS
        filters.extend(
            [
                Location.longitude.between(minimum_longitude, maximum_longitude),
                Location.latitude.between(minimum_latitude, maximum_latitude),
            ]
        )

    join = (Location, Report.location_id == Location.id)
    status_query = (
        select(Report.status, func.count()).join(*join).where(*filters).group_by(Report.status)
    )
    severity_query = (
        select(Report.severity, func.count()).join(*join).where(*filters).group_by(Report.severity)
    )
    now = datetime.now(UTC)
    first_month = _month_start(now, 5)
    next_month = _month_start(now, -1)
    month = func.date_trunc("month", Report.submitted_at)
    monthly_query = (
        select(month.label("month"), func.count())
        .join(*join)
        .where(
            *filters,
            Report.submitted_at.is_not(None),
            Report.submitted_at >= first_month,
            Report.submitted_at < next_month,
        )
        .group_by(month)
        .order_by(month)
    )
    state_name = func.nullif(
        func.trim(Location.provider_metadata["state_province"].as_string()),
        "",
    )
    city_name = func.nullif(
        func.trim(Location.provider_metadata["city"].as_string()),
        "",
    )
    resolved_count = func.sum(case((Report.status == "resolved", 1), else_=0))
    state_query = (
        select(state_name.label("name"), func.count(Report.id), resolved_count)
        .join(*join)
        .where(*filters, state_name.is_not(None))
        .group_by(state_name)
        .order_by(func.count(Report.id).desc(), state_name)
    )
    city_query = (
        select(city_name.label("name"), func.count(Report.id), resolved_count)
        .join(*join)
        .where(*filters, city_name.is_not(None))
        .group_by(city_name)
        .order_by(func.count(Report.id).desc(), city_name)
        .limit(10)
    )
    geography_coverage_query = (
        select(
            func.count(case((state_name.is_(None), Report.id))),
            func.count(case((city_name.is_(None), Report.id))),
        )
        .join(*join)
        .where(*filters)
    )
    completion_hours = (
        func.extract(
            "epoch",
            AuthorityAssignment.completed_at - AuthorityAssignment.assigned_at,
        )
        / 3600
    )
    valid_completion_hours = case(
        (AuthorityAssignment.completed_at >= AuthorityAssignment.assigned_at, completion_hours),
        else_=None,
    )
    authority_filters = [
        *filters,
        Authority.active.is_(True),
        Authority.is_verified.is_(True),
    ]
    authority_totals_query = (
        select(
            func.count(AuthorityAssignment.id),
            func.count(AuthorityAssignment.completed_at),
            func.avg(valid_completion_hours),
        )
        .join(Report, AuthorityAssignment.report_id == Report.id)
        .join(*join)
        .join(Authority, AuthorityAssignment.authority_id == Authority.id)
        .where(*authority_filters)
    )
    authority_breakdown_query = (
        select(
            Authority.id,
            Authority.name,
            func.count(AuthorityAssignment.id),
            func.count(AuthorityAssignment.completed_at),
            func.avg(valid_completion_hours),
        )
        .join(AuthorityAssignment, AuthorityAssignment.authority_id == Authority.id)
        .join(Report, AuthorityAssignment.report_id == Report.id)
        .join(*join)
        .where(*authority_filters)
        .group_by(Authority.id, Authority.name)
        .order_by(func.count(AuthorityAssignment.id).desc(), Authority.name)
        .limit(10)
    )

    try:
        status_rows = cast(list[tuple[str, int]], (await session.execute(status_query)).all())
        severity_rows = cast(
            list[tuple[str | None, int]],
            (await session.execute(severity_query)).all(),
        )
        monthly_rows = cast(
            list[tuple[datetime, int]],
            (await session.execute(monthly_query)).tuples().all(),
        )
        state_rows = cast(
            list[tuple[str, int, int]],
            (await session.execute(state_query)).all(),
        )
        city_rows = cast(
            list[tuple[str, int, int]],
            (await session.execute(city_query)).all(),
        )
        geography_coverage = cast(
            tuple[int, int],
            (await session.execute(geography_coverage_query)).all()[0],
        )
        authority_totals = cast(
            tuple[int, int, Decimal | float | None],
            (await session.execute(authority_totals_query)).all()[0],
        )
        authority_rows = cast(
            list[tuple[UUID, str, int, int, Decimal | float | None]],
            (await session.execute(authority_breakdown_query)).all(),
        )
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Analytics data store is unavailable",
        ) from exc

    status_counts = {str(status): int(count) for status, count in status_rows}
    severity_counts = dict.fromkeys(SEVERITY_CATEGORIES, 0)
    for category, count in severity_rows:
        key = str(category) if category in SEVERITY_CATEGORIES[:-1] else "unknown"
        severity_counts[key] += int(count)

    monthly_counts = {
        month_value.strftime("%Y-%m"): int(count) for month_value, count in monthly_rows
    }
    monthly_submissions = [
        MonthlySubmission(month=_month_start(now, offset).strftime("%Y-%m"), count=0)
        for offset in range(5, -1, -1)
    ]
    monthly_submissions = [
        item.model_copy(update={"count": monthly_counts.get(item.month, 0)})
        for item in monthly_submissions
    ]
    states = [
        GeographicBreakdown(
            name=str(name),
            report_count=int(count),
            resolved_count=int(resolved),
        )
        for name, count, resolved in state_rows
    ]
    cities = [
        GeographicBreakdown(
            name=str(name),
            report_count=int(count),
            resolved_count=int(resolved),
        )
        for name, count, resolved in city_rows
    ]
    assigned_count, completed_count, average_completion = authority_totals
    assigned_count = int(assigned_count or 0)
    completed_count = int(completed_count or 0)
    authority_response = AuthorityResponseSummary(
        assigned_count=assigned_count,
        completed_count=completed_count,
        open_count=max(0, assigned_count - completed_count),
        average_completion_hours=(
            float(average_completion) if average_completion is not None else None
        ),
        first_response_time_available=False,
        by_authority=[
            AuthorityCompletion(
                authority_id=authority_id,
                authority_name=str(authority_name),
                assigned_count=int(count),
                completed_count=int(completed),
                average_completion_hours=float(average) if average is not None else None,
            )
            for authority_id, authority_name, count, completed, average in authority_rows
        ],
    )

    return AnalyticsSummary(
        country_code=settings.product_country_code.upper(),
        total_verified_reports=sum(status_counts.values()),
        open_reports=sum(status_counts.get(status, 0) for status in OPEN_STATUSES),
        resolved_reports=status_counts.get("resolved", 0),
        severity_distribution=severity_counts,
        monthly_submissions=monthly_submissions,
        states=states,
        cities=cities,
        state_unclassified_reports=int(geography_coverage[0]),
        city_unclassified_reports=int(geography_coverage[1]),
        authority_response=authority_response,
    )
