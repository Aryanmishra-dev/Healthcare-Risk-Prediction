"""usage_records_and_tenant_quotas

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-12 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0014'
down_revision: Union[str, None] = '0013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'usage_records',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('api_key_id', sa.UUID(), nullable=True),
        sa.Column('endpoint', sa.String(length=255), nullable=False),
        sa.Column('method', sa.String(length=10), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['api_key_id'], ['api_keys.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_usage_records_id'), 'usage_records', ['id'], unique=False)
    op.create_index(op.f('ix_usage_records_tenant_id'), 'usage_records', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_usage_records_api_key_id'), 'usage_records', ['api_key_id'], unique=False)
    op.create_index(op.f('ix_usage_records_recorded_at'), 'usage_records', ['recorded_at'], unique=False)

    op.create_table(
        'tenant_quotas',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('rate_limit_per_minute', sa.Integer(), nullable=False),
        sa.Column('monthly_quota', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id'),
    )
    op.create_index(op.f('ix_tenant_quotas_id'), 'tenant_quotas', ['id'], unique=False)
    op.create_index(op.f('ix_tenant_quotas_tenant_id'), 'tenant_quotas', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_tenant_quotas_tenant_id'), table_name='tenant_quotas')
    op.drop_index(op.f('ix_tenant_quotas_id'), table_name='tenant_quotas')
    op.drop_table('tenant_quotas')
    op.drop_index(op.f('ix_usage_records_recorded_at'), table_name='usage_records')
    op.drop_index(op.f('ix_usage_records_api_key_id'), table_name='usage_records')
    op.drop_index(op.f('ix_usage_records_tenant_id'), table_name='usage_records')
    op.drop_index(op.f('ix_usage_records_id'), table_name='usage_records')
    op.drop_table('usage_records')
