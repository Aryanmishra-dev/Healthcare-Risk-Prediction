"""Phase 2.5 Notifications

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-11 11:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0006'
down_revision: Union[str, None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename `type` to `notification_type`
    op.alter_column('notifications', 'type', new_column_name='notification_type', existing_type=sa.String(length=50), nullable=False)
    
    # Add new Notification fields
    op.add_column('notifications', sa.Column('category', sa.String(length=50), server_default="General", nullable=False))
    op.add_column('notifications', sa.Column('priority', sa.String(length=20), server_default="NORMAL", nullable=False))
    op.add_column('notifications', sa.Column('status', sa.String(length=20), server_default="pending", nullable=False))
    op.add_column('notifications', sa.Column('channel', sa.String(length=20), server_default="in_app", nullable=False))
    op.add_column('notifications', sa.Column('read_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('notifications', sa.Column('metadata_payload', sa.JSON(), nullable=True))
    op.add_column('notifications', sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True))
    
    # Add new UserSettings fields
    op.add_column('user_settings', sa.Column('security_alerts', sa.Boolean(), server_default=sa.text("true"), nullable=False))
    op.add_column('user_settings', sa.Column('system_notifications', sa.Boolean(), server_default=sa.text("true"), nullable=False))


def downgrade() -> None:
    op.drop_column('user_settings', 'system_notifications')
    op.drop_column('user_settings', 'security_alerts')
    
    op.drop_column('notifications', 'expires_at')
    op.drop_column('notifications', 'metadata_payload')
    op.drop_column('notifications', 'read_at')
    op.drop_column('notifications', 'channel')
    op.drop_column('notifications', 'status')
    op.drop_column('notifications', 'priority')
    op.drop_column('notifications', 'category')
    
    op.alter_column('notifications', 'notification_type', new_column_name='type', existing_type=sa.String(length=50), nullable=False)
