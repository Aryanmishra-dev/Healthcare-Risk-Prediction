"""webhooks

Revision ID: 0015
Revises: 0014
Create Date: 2026-07-19 16:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "webhooks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("url", sa.String(length=1024), nullable=False),
        sa.Column("secret", sa.String(length=255), nullable=False),
        sa.Column("events", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column(
            "last_triggered_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_webhooks_id"), "webhooks", ["id"], unique=False)
    op.create_index(
        op.f("ix_webhooks_tenant_id"), "webhooks", ["tenant_id"], unique=False
    )

    op.create_table(
        "webhook_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("webhook_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("request_url", sa.String(length=1024), nullable=False),
        sa.Column("request_headers", sa.JSON(), nullable=False),
        sa.Column("response_status_code", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["webhook_id"], ["webhooks.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_webhook_events_id"), "webhook_events", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_webhook_events_webhook_id"),
        "webhook_events",
        ["webhook_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_webhook_events_status"),
        "webhook_events",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_webhook_events_next_retry_at"),
        "webhook_events",
        ["next_retry_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_webhook_events_next_retry_at"), table_name="webhook_events"
    )
    op.drop_index(
        op.f("ix_webhook_events_status"), table_name="webhook_events"
    )
    op.drop_index(
        op.f("ix_webhook_events_webhook_id"), table_name="webhook_events"
    )
    op.drop_index(op.f("ix_webhook_events_id"), table_name="webhook_events")
    op.drop_table("webhook_events")
    op.drop_index(op.f("ix_webhooks_tenant_id"), table_name="webhooks")
    op.drop_index(op.f("ix_webhooks_id"), table_name="webhooks")
    op.drop_table("webhooks")
