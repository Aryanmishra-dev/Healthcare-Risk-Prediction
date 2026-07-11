"""Phase 2.3 Prediction History

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-11 11:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Adding Phase 2.3 fields to prediction_audit_logs
    op.add_column('prediction_audit_logs', sa.Column('report_id', sa.Uuid(), nullable=True))
    op.add_column('prediction_audit_logs', sa.Column('confidence_score', sa.Float(), server_default="0.0", nullable=False))
    op.add_column('prediction_audit_logs', sa.Column('model_version', sa.String(length=50), server_default="local", nullable=False))
    op.add_column('prediction_audit_logs', sa.Column('shap_values', sa.JSON(), nullable=True))
    op.add_column('prediction_audit_logs', sa.Column('processing_time_ms', sa.Integer(), server_default="0", nullable=False))
    op.add_column('prediction_audit_logs', sa.Column('prediction_status', sa.String(length=50), server_default="success", nullable=False))
    op.add_column('prediction_audit_logs', sa.Column('favorite', sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column('prediction_audit_logs', sa.Column('archived', sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column('prediction_audit_logs', sa.Column('notes', sa.String(length=1000), nullable=True))
    
    # Add foreign key constraint for report_id
    op.create_foreign_key(
        'fk_prediction_audit_logs_report_id_user_reports',
        'prediction_audit_logs', 'user_reports',
        ['report_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_prediction_audit_logs_report_id_user_reports', 'prediction_audit_logs', type_='foreignkey')
    
    op.drop_column('prediction_audit_logs', 'notes')
    op.drop_column('prediction_audit_logs', 'archived')
    op.drop_column('prediction_audit_logs', 'favorite')
    op.drop_column('prediction_audit_logs', 'prediction_status')
    op.drop_column('prediction_audit_logs', 'processing_time_ms')
    op.drop_column('prediction_audit_logs', 'shap_values')
    op.drop_column('prediction_audit_logs', 'model_version')
    op.drop_column('prediction_audit_logs', 'confidence_score')
    op.drop_column('prediction_audit_logs', 'report_id')
