"""Phase 2.4 Report Storage

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-11 11:45:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # We are dropping file_name, file_path, extracted_metadata and replacing with the new schema fields.
    # Note: SQLite compatibility might throw issues with dropping columns, but the user said PostgreSQL ONLY.

    op.drop_column("user_reports", "file_name")
    op.drop_column("user_reports", "file_path")
    op.drop_column("user_reports", "extracted_metadata")

    op.add_column(
        "user_reports",
        sa.Column(
            "filename",
            sa.String(length=255),
            nullable=False,
            server_default="legacy.pdf",
        ),
    )
    op.add_column(
        "user_reports",
        sa.Column(
            "original_filename",
            sa.String(length=255),
            nullable=False,
            server_default="legacy.pdf",
        ),
    )
    op.add_column(
        "user_reports", sa.Column("extension", sa.String(length=20), nullable=True)
    )
    op.add_column(
        "user_reports",
        sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
    )

    op.add_column(
        "user_reports",
        sa.Column(
            "storage_path", sa.String(length=500), nullable=False, server_default=""
        ),
    )
    op.add_column(
        "user_reports",
        sa.Column("checksum", sa.String(length=64), nullable=False, server_default=""),
    )

    op.add_column(
        "user_reports",
        sa.Column(
            "upload_status",
            sa.String(length=50),
            nullable=False,
            server_default="uploaded",
        ),
    )
    op.add_column(
        "user_reports",
        sa.Column(
            "processing_status",
            sa.String(length=50),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "user_reports",
        sa.Column(
            "parser_version", sa.String(length=50), nullable=False, server_default="1.0"
        ),
    )

    op.add_column(
        "user_reports", sa.Column("extracted_entities", sa.JSON(), nullable=True)
    )
    op.add_column(
        "user_reports",
        sa.Column("prediction_count", sa.Integer(), nullable=False, server_default="0"),
    )

    op.add_column(
        "user_reports",
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.add_column(
        "user_reports",
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "user_reports",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index(
        op.f("ix_user_reports_checksum"), "user_reports", ["checksum"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_user_reports_checksum"), table_name="user_reports")

    op.drop_column("user_reports", "deleted_at")
    op.drop_column("user_reports", "processed_at")
    op.drop_column("user_reports", "uploaded_at")

    op.drop_column("user_reports", "prediction_count")
    op.drop_column("user_reports", "extracted_entities")

    op.drop_column("user_reports", "parser_version")
    op.drop_column("user_reports", "processing_status")
    op.drop_column("user_reports", "upload_status")

    op.drop_column("user_reports", "checksum")
    op.drop_column("user_reports", "storage_path")

    op.drop_column("user_reports", "file_size")
    op.drop_column("user_reports", "extension")
    op.drop_column("user_reports", "original_filename")
    op.drop_column("user_reports", "filename")

    op.add_column(
        "user_reports", sa.Column("extracted_metadata", sa.JSON(), nullable=True)
    )
    op.add_column(
        "user_reports",
        sa.Column(
            "file_path", sa.String(length=500), nullable=False, server_default=""
        ),
    )
    op.add_column(
        "user_reports",
        sa.Column(
            "file_name", sa.String(length=255), nullable=False, server_default=""
        ),
    )
