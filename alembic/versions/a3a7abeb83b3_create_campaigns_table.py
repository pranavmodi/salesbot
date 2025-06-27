"""create_campaigns_table

Revision ID: a3a7abeb83b3
Revises: 005e12e7f88b
Create Date: 2025-06-27 18:05:31.731450

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3a7abeb83b3'
down_revision: Union[str, None] = '005e12e7f88b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create campaigns table for storing email campaign information."""
    op.create_table(
        'campaigns',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )
    
    # Create indexes for better query performance
    op.create_index('idx_campaigns_name', 'campaigns', ['name'])
    op.create_index('idx_campaigns_status', 'campaigns', ['status'])
    op.create_index('idx_campaigns_created_at', 'campaigns', ['created_at'])


def downgrade() -> None:
    """Drop campaigns table."""
    op.drop_index('idx_campaigns_created_at')
    op.drop_index('idx_campaigns_status')
    op.drop_index('idx_campaigns_name')
    op.drop_table('campaigns')
