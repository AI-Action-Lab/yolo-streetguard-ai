"""phase 2 model registry

Revision ID: 3f7bd4c2c0a1
Revises: fcbf15d159d4
"""

from collections.abc import Sequence
from uuid import NAMESPACE_URL, uuid5

from alembic import op

revision: str = "3f7bd4c2c0a1"
down_revision: str | None = "fcbf15d159d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_model_versions_single_active")
    op.execute(
        "CREATE UNIQUE INDEX ix_model_versions_single_active "
        "ON model_versions (is_active) WHERE is_active = true"
    )
    model_id = uuid5(NAMESPACE_URL, "streetguard:model:yolo11n:2026-10-25")
    op.execute(
        "INSERT INTO model_versions "
        "(id, name, version, model_family, artifact_object_key, artifact_sha256, "
        "confidence_threshold, image_size, class_names, evaluation_metrics, is_active) "
        f"VALUES ('{model_id}', 'streetguard-pothole', 'yolo11n-2026-10-25', "
        "'YOLO11n', 'models/pothole/best.pt', "
        "'d4ec8035e55e7db185e82cbfdf97f402264e40024b2d7e6d0e335bce5d321543', "
        "0.25, 640, json_build_object('0', 'pothole'), "
        "json_build_object('precision', 0.7870117184533936, "
        "'recall', 0.6521739130434783, 'map50', 0.7693320121909515, "
        "'map50_95', 0.49589763876619664), true)"
    )


def downgrade() -> None:
    op.execute("DELETE FROM model_versions WHERE id = '22619930-554d-5945-8fcd-ef4388ca5ec4'")
    op.execute("DROP INDEX IF EXISTS ix_model_versions_single_active")
