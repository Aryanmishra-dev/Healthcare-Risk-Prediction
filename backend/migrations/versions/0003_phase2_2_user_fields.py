"""Phase 2.2 User Fields

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-11 11:20:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_profiles", sa.Column("avatar_url", sa.String(length=500), nullable=True)
    )
    op.add_column(
        "user_profiles",
        sa.Column(
            "timezone", sa.String(length=50), server_default="UTC", nullable=True
        ),
    )

    op.add_column(
        "user_settings",
        sa.Column(
            "marketing_emails",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "user_settings",
        sa.Column(
            "prediction_alerts",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("user_settings", "prediction_alerts")
    op.drop_column("user_settings", "marketing_emails")
    op.drop_column("user_profiles", "timezone")
    op.drop_column("user_profiles", "avatar_url")
