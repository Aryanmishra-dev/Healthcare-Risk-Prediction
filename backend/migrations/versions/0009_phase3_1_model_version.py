"""phase3_1_model_version

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-11 12:35:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create model_versions table
    op.create_table(
        "model_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column("disease", sa.String(length=100), nullable=False),
        sa.Column("framework", sa.String(length=50), nullable=False),
        sa.Column("algorithm", sa.String(length=100), nullable=False),
        sa.Column("training_dataset", sa.String(length=255), nullable=True),
        sa.Column("dataset_version", sa.String(length=50), nullable=True),
        sa.Column(
            "feature_schema_version", sa.String(length=50), nullable=True
        ),
        sa.Column("hyperparameters", sa.JSON(), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column("training_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deployed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("model_path", sa.String(length=500), nullable=True),
        sa.Column("mlflow_run_id", sa.String(length=100), nullable=True),
        sa.Column("mlflow_model_uri", sa.String(length=500), nullable=True),
        sa.Column("checksum", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_model_versions_model_name"),
        "model_versions",
        ["model_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_model_versions_disease"),
        "model_versions",
        ["disease"],
        unique=False,
    )
    op.create_index(
        op.f("ix_model_versions_status"),
        "model_versions",
        ["status"],
        unique=False,
    )

    # 2. Add fields to prediction_audit_logs for AB testing, drift, and calibration
    op.add_column(
        "prediction_audit_logs",
        sa.Column("model_version_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "prediction_audit_logs",
        sa.Column(
            "is_calibrated", sa.Boolean(), server_default="0", nullable=False
        ),
    )
    op.add_column(
        "prediction_audit_logs",
        sa.Column("ab_test_group", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "prediction_audit_logs",
        sa.Column(
            "drift_detected", sa.Boolean(), server_default="0", nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_column("prediction_audit_logs", "drift_detected")
    op.drop_column("prediction_audit_logs", "ab_test_group")
    op.drop_column("prediction_audit_logs", "is_calibrated")
    op.drop_column("prediction_audit_logs", "model_version_id")

    op.drop_index(
        op.f("ix_model_versions_status"), table_name="model_versions"
    )
    op.drop_index(
        op.f("ix_model_versions_disease"), table_name="model_versions"
    )
    op.drop_index(
        op.f("ix_model_versions_model_name"), table_name="model_versions"
    )
    op.drop_table("model_versions")
