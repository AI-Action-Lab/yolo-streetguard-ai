"""phase 5 communication preferences and delivery purpose

Revision ID: 8d4a3f19c2e7
Revises: 3f7bd4c2c0a1
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8d4a3f19c2e7"
down_revision: str | None = "3f7bd4c2c0a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("email_verified", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "users",
        sa.Column(
            "email_status_notifications_enabled",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column("email_notifications_confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "email_delivery_logs",
        sa.Column(
            "purpose",
            sa.String(length=50),
            server_default="report_share",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("email_delivery_logs", "purpose")
    op.drop_column("users", "email_notifications_confirmed_at")
    op.drop_column("users", "email_status_notifications_enabled")
    op.drop_column("users", "email_verified")
