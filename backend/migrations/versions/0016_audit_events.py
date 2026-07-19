"""audit_events_and_retention_policies

Revision ID: 0016
Revises: 0015
Create Date: 2026-07-19 17:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: Union[str, None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("actor_email", sa.String(length=255), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_id", sa.String(length=255), nullable=True),
        sa.Column("before_snapshot", sa.JSON(), nullable=True),
        sa.Column("after_snapshot", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("request_id", sa.String(length=255), nullable=True),
        sa.Column("metadata_payload", sa.JSON(), nullable=True),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("outcome", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_audit_events_id"), "audit_events", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_audit_events_tenant_id"),
        "audit_events",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_events_actor_id"),
        "audit_events",
        ["actor_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_events_action"),
        "audit_events",
        ["action"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_events_resource_type"),
        "audit_events",
        ["resource_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_events_resource_id"),
        "audit_events",
        ["resource_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_events_severity"),
        "audit_events",
        ["severity"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_events_outcome"),
        "audit_events",
        ["outcome"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_events_created_at"),
        "audit_events",
        ["created_at"],
        unique=False,
    )

    op.create_table(
        "audit_retention_policies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("action_pattern", sa.String(length=100), nullable=False),
        sa.Column("retention_days", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("action_pattern"),
    )
    op.create_index(
        op.f("ix_audit_retention_policies_id"),
        "audit_retention_policies",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_audit_retention_policies_id"),
        table_name="audit_retention_policies",
    )
    op.drop_table("audit_retention_policies")
    op.drop_index(
        op.f("ix_audit_events_created_at"), table_name="audit_events"
    )
    op.drop_index(op.f("ix_audit_events_outcome"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_severity"), table_name="audit_events")
    op.drop_index(
        op.f("ix_audit_events_resource_id"), table_name="audit_events"
    )
    op.drop_index(
        op.f("ix_audit_events_resource_type"), table_name="audit_events"
    )
    op.drop_index(op.f("ix_audit_events_action"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_actor_id"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_tenant_id"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_id"), table_name="audit_events")
    op.drop_table("audit_events")
