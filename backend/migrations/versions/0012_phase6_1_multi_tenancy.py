"""phase6_1_multi_tenancy

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-12 12:00:00.000000

"""

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create tables
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f("ix_tenants_slug"), "tenants", ["slug"], unique=True)

    op.create_table(
        "workspaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE"
        ),
    )

    op.create_table(
        "teams",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE"
        ),
    )

    op.create_table(
        "memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_role", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    # 2. Insert Default Tenant
    default_tenant_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    op.execute(
        f"INSERT INTO tenants (id, name, slug, is_active, "
        f"created_at, updated_at) "
        f"VALUES ("
        f"'{default_tenant_id}', "
        f"'Default Organization', 'default-org', true, "
        f"'{now}', '{now}'"
        f")"
    )

    # 3. Add nullable=True tenant_id to existing tables
    tables = [
        "prediction_audit_logs",
        "user_reports",
        "data_exports",
        "notifications",
        "model_versions",
        "admin_actions",
        "audit_logs",
        "security_events",
    ]

    for table in tables:
        op.add_column(
            table,
            sa.Column(
                "tenant_id", postgresql.UUID(as_uuid=True), nullable=True
            ),
        )
        op.execute(f"UPDATE {table} SET tenant_id = '{default_tenant_id}'")

    # 4. Create Memberships for existing users
    op.execute(
        f"INSERT INTO memberships (id, tenant_id, user_id, "
        f"org_role, created_at, updated_at) "
        f"SELECT gen_random_uuid(), "
        f"'{default_tenant_id}', id, 'MEMBER', "
        f"'{now}', '{now}' FROM users"
    )

    # 5. Alter columns to nullable=False (except audit_logs,
    # security_events, admin_actions where some can be null)
    non_null_tables = [
        "prediction_audit_logs",
        "user_reports",
        "data_exports",
        "notifications",
        "model_versions",
    ]
    for table in non_null_tables:
        op.alter_column(
            table,
            "tenant_id",
            existing_type=postgresql.UUID(as_uuid=True),
            nullable=False,
        )
        op.create_foreign_key(
            f"fk_{table}_tenant_id",
            table,
            "tenants",
            ["tenant_id"],
            ["id"],
            ondelete="CASCADE",
        )

    # Foreign keys for nullable tables
    nullable_tables = ["admin_actions", "audit_logs", "security_events"]
    for table in nullable_tables:
        op.create_foreign_key(
            f"fk_{table}_tenant_id",
            table,
            "tenants",
            ["tenant_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    tables = [
        "prediction_audit_logs",
        "user_reports",
        "data_exports",
        "notifications",
        "model_versions",
        "admin_actions",
        "audit_logs",
        "security_events",
    ]
    for table in tables:
        op.drop_constraint(f"fk_{table}_tenant_id", table, type_="foreignkey")
        op.drop_column(table, "tenant_id")

    op.drop_table("memberships")
    op.drop_table("teams")
    op.drop_table("workspaces")
    op.drop_index(op.f("ix_tenants_slug"), table_name="tenants")
    op.drop_table("tenants")
