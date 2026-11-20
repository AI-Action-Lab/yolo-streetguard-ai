"""phase 7 authority memberships

Revision ID: a72ce90f1b34
Revises: 8d4a3f19c2e7
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a72ce90f1b34"
down_revision: str | None = "8d4a3f19c2e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "authority_memberships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("authority_id", sa.Uuid(), nullable=False),
        sa.Column("granted_by_id", sa.Uuid(), nullable=True),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["authority_id"],
            ["authorities.id"],
            ondelete="CASCADE",
            name="fk_authority_memberships_authority_id_authorities",
        ),
        sa.ForeignKeyConstraint(
            ["granted_by_id"],
            ["users.id"],
            ondelete="SET NULL",
            name="fk_authority_memberships_granted_by_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="fk_authority_memberships_user_id_users",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_authority_memberships"),
        sa.UniqueConstraint(
            "user_id",
            "authority_id",
            name="uq_authority_memberships_user_authority",
        ),
    )
    op.create_index(
        "ix_authority_memberships_user_id",
        "authority_memberships",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_authority_memberships_authority_id",
        "authority_memberships",
        ["authority_id"],
        unique=False,
    )
    op.create_index(
        "ix_authority_memberships_authority_active",
        "authority_memberships",
        ["authority_id", "active"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_authority_memberships_authority_active", table_name="authority_memberships")
    op.drop_index("ix_authority_memberships_authority_id", table_name="authority_memberships")
    op.drop_index("ix_authority_memberships_user_id", table_name="authority_memberships")
    op.drop_table("authority_memberships")
