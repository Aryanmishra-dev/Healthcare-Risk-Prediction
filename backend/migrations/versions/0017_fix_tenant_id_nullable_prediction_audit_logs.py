"""Make tenant_id nullable in prediction_audit_logs

Revision ID: 0017
Revises: 0016
Create Date: 2026-07-19 12:00:00.000000
"""

from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "prediction_audit_logs",
        "tenant_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "prediction_audit_logs",
        "tenant_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
