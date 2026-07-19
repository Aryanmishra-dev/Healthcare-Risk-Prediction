"""phase2_6_security

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-11 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Update user_sessions table
    op.add_column(
        "user_sessions",
        sa.Column("device_name", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "user_sessions",
        sa.Column("browser", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "user_sessions",
        sa.Column("operating_system", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "user_sessions",
        sa.Column("country", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "user_sessions",
        sa.Column("city", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "user_sessions",
        sa.Column(
            "login_method",
            sa.String(length=50),
            server_default="password",
            nullable=False,
        ),
    )
    op.add_column(
        "user_sessions",
        sa.Column(
            "last_activity",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "user_sessions",
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 2. Create login_history table
    op.create_table(
        "login_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("ip_address", sa.String(length=255), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("device_name", sa.String(length=100), nullable=True),
        sa.Column("browser", sa.String(length=100), nullable=True),
        sa.Column("operating_system", sa.String(length=100), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("login_method", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("login_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 3. Create security_events table
    op.create_table(
        "security_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=255), nullable=False),
        sa.Column("severity", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("metadata_payload", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("security_events")
    op.drop_table("login_history")
    op.drop_column("user_sessions", "revoked_at")
    op.drop_column("user_sessions", "last_activity")
    op.drop_column("user_sessions", "login_method")
    op.drop_column("user_sessions", "city")
    op.drop_column("user_sessions", "country")
    op.drop_column("user_sessions", "operating_system")
    op.drop_column("user_sessions", "browser")
    op.drop_column("user_sessions", "device_name")
