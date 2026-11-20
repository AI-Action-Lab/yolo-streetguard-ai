from enum import StrEnum


class ReportStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    AI_PROCESSING = "ai_processing"
    AWAITING_VERIFICATION = "awaiting_verification"
    VERIFIED = "verified"
    ASSIGNED_TO_AUTHORITY = "assigned_to_authority"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    REJECTED = "rejected"
    DUPLICATE = "duplicate"


ALLOWED_REPORT_TRANSITIONS: dict[ReportStatus, frozenset[ReportStatus]] = {
    ReportStatus.DRAFT: frozenset({ReportStatus.SUBMITTED}),
    ReportStatus.SUBMITTED: frozenset({ReportStatus.AI_PROCESSING}),
    ReportStatus.AI_PROCESSING: frozenset({ReportStatus.AWAITING_VERIFICATION}),
    ReportStatus.AWAITING_VERIFICATION: frozenset(
        {
            ReportStatus.VERIFIED,
            ReportStatus.REJECTED,
            ReportStatus.DUPLICATE,
        }
    ),
    ReportStatus.VERIFIED: frozenset({ReportStatus.ASSIGNED_TO_AUTHORITY}),
    ReportStatus.ASSIGNED_TO_AUTHORITY: frozenset({ReportStatus.IN_PROGRESS}),
    ReportStatus.IN_PROGRESS: frozenset({ReportStatus.RESOLVED}),
    ReportStatus.RESOLVED: frozenset(),
    ReportStatus.REJECTED: frozenset(),
    ReportStatus.DUPLICATE: frozenset(),
}


def can_transition(current: ReportStatus, target: ReportStatus) -> bool:
    return target in ALLOWED_REPORT_TRANSITIONS[current]
