"""rc2_performance_indexes

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-12

RC2 Production Hardening — critical performance indexes identified in the
RC1 audit.  These indexes eliminate sequential scans on the highest-frequency
query patterns across the user-facing API surface.

Tables affected:
  prediction_audit_logs — user_id, disease_model, created_at
  user_sessions         — user_id + composite (user_id, is_revoked, expires_at)
  login_history         — user_id
  security_events       — user_id
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── prediction_audit_logs ─────────────────────────────────────────────
    # user_id: all history / dashboard / export queries are scoped by user
    op.create_index(
        "ix_prediction_audit_logs_user_id",
        "prediction_audit_logs",
        ["user_id"],
        unique=False,
    )
    # disease_model: filtered history (?disease=diabetes etc.)
    op.create_index(
        "ix_prediction_audit_logs_disease_model",
        "prediction_audit_logs",
        ["disease_model"],
        unique=False,
    )
    # created_at DESC: all ORDER BY and date-range queries
    op.create_index(
        "ix_prediction_audit_logs_created_at",
        "prediction_audit_logs",
        ["created_at"],
        unique=False,
    )

    # ── user_sessions ─────────────────────────────────────────────────────
    # user_id: GET /auth/sessions and session look-ups in get_current_user
    op.create_index(
        "ix_user_sessions_user_id",
        "user_sessions",
        ["user_id"],
        unique=False,
    )
    # Composite: used in get_current_user for active-session validation
    # (user_id, is_revoked, expires_at)
    op.create_index(
        "ix_user_sessions_user_active",
        "user_sessions",
        ["user_id", "is_revoked", "expires_at"],
        unique=False,
    )

    # ── login_history ─────────────────────────────────────────────────────
    op.create_index(
        "ix_login_history_user_id",
        "login_history",
        ["user_id"],
        unique=False,
    )

    # ── security_events ───────────────────────────────────────────────────
    op.create_index(
        "ix_security_events_user_id",
        "security_events",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_security_events_user_id", table_name="security_events")
    op.drop_index("ix_login_history_user_id", table_name="login_history")
    op.drop_index("ix_user_sessions_user_active", table_name="user_sessions")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_index(
        "ix_prediction_audit_logs_created_at",
        table_name="prediction_audit_logs",
    )
    op.drop_index(
        "ix_prediction_audit_logs_disease_model",
        table_name="prediction_audit_logs",
    )
    op.drop_index(
        "ix_prediction_audit_logs_user_id", table_name="prediction_audit_logs"
    )
