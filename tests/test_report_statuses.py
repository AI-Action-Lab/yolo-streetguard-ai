from itertools import pairwise

from streetguard.domain.statuses import ReportStatus, can_transition


def test_normal_report_workflow_transitions_are_allowed() -> None:
    workflow = (
        ReportStatus.DRAFT,
        ReportStatus.SUBMITTED,
        ReportStatus.AI_PROCESSING,
        ReportStatus.AWAITING_VERIFICATION,
        ReportStatus.VERIFIED,
        ReportStatus.ASSIGNED_TO_AUTHORITY,
        ReportStatus.IN_PROGRESS,
        ReportStatus.RESOLVED,
    )

    assert all(can_transition(current, target) for current, target in pairwise(workflow))


def test_ai_cannot_verify_a_report() -> None:
    assert not can_transition(ReportStatus.AWAITING_VERIFICATION, ReportStatus.RESOLVED)
    assert not can_transition(ReportStatus.AI_PROCESSING, ReportStatus.VERIFIED)


def test_terminal_states_cannot_transition() -> None:
    for status in (
        ReportStatus.RESOLVED,
        ReportStatus.REJECTED,
        ReportStatus.DUPLICATE,
    ):
        assert not can_transition(status, ReportStatus.IN_PROGRESS)
