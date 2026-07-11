"""phase2_7_data_export

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-11 12:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # We rename file_path to storage_path and add the new columns.
    # Note: SQLite alter table support in Alembic is limited, but we are designing for Postgres.
    op.alter_column('data_exports', 'file_path', new_column_name='storage_path', existing_type=sa.String(length=500), nullable=True)
    
    op.add_column('data_exports', sa.Column('export_type', sa.String(length=100), server_default='full', nullable=False))
    op.add_column('data_exports', sa.Column('export_format', sa.String(length=50), server_default='json', nullable=False))
    op.add_column('data_exports', sa.Column('file_name', sa.String(length=255), nullable=True))
    op.add_column('data_exports', sa.Column('file_size', sa.Integer(), nullable=True))
    op.add_column('data_exports', sa.Column('checksum', sa.String(length=255), nullable=True))
    op.add_column('data_exports', sa.Column('started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('data_exports', sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('data_exports', sa.Column('downloaded_at', sa.DateTime(timezone=True), nullable=True))

def downgrade() -> None:
    op.drop_column('data_exports', 'downloaded_at')
    op.drop_column('data_exports', 'expires_at')
    op.drop_column('data_exports', 'started_at')
    op.drop_column('data_exports', 'checksum')
    op.drop_column('data_exports', 'file_size')
    op.drop_column('data_exports', 'file_name')
    op.drop_column('data_exports', 'export_format')
    op.drop_column('data_exports', 'export_type')
    
    op.alter_column('data_exports', 'storage_path', new_column_name='file_path', existing_type=sa.String(length=500), nullable=True)
