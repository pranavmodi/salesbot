"""add_feedback_table

Revision ID: fdda8270b504
Revises: 71cdf1fbede5
Create Date: 2025-08-17 14:53:34.766577

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fdda8270b504'
down_revision: Union[str, None] = '71cdf1fbede5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('feedback',
        sa.Column('id', sa.String(36), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('user_email', sa.String(255), nullable=False),
        sa.Column('user_name', sa.String(255), nullable=False),
        sa.Column('tenant_id', sa.String(36), nullable=False),
        sa.Column('message', sa.Text, nullable=False),
        sa.Column('category', sa.String(50), nullable=False, default='general'),
        sa.Column('status', sa.String(20), nullable=False, default='new'),
        sa.Column('admin_notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.TIMESTAMP, nullable=False, default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP, nullable=True)
    )
    
    # Create indexes
    op.create_index('idx_feedback_user_id', 'feedback', ['user_id'])
    op.create_index('idx_feedback_tenant_id', 'feedback', ['tenant_id'])
    op.create_index('idx_feedback_status', 'feedback', ['status'])
    op.create_index('idx_feedback_created_at', 'feedback', ['created_at'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('feedback')
