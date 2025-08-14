"""add_link_tracking_table

Revision ID: df4ea3b00352
Revises: d939f6cf7aa3
Create Date: 2025-08-14 14:45:38.066160

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'df4ea3b00352'
down_revision: Union[str, None] = 'd939f6cf7aa3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create link_tracking table
    op.create_table('link_tracking',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tracking_id', sa.String(255), nullable=False, unique=True),
        sa.Column('original_url', sa.Text(), nullable=False),
        sa.Column('campaign_id', sa.Integer(), nullable=True),
        sa.Column('company_id', sa.Integer(), nullable=True),
        sa.Column('contact_email', sa.String(255), nullable=True),
        sa.Column('tenant_id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index on tracking_id for fast lookups
    op.create_index('idx_link_tracking_tracking_id', 'link_tracking', ['tracking_id'])
    op.create_index('idx_link_tracking_tenant_id', 'link_tracking', ['tenant_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_link_tracking_tenant_id', table_name='link_tracking')
    op.drop_index('idx_link_tracking_tracking_id', table_name='link_tracking')
    op.drop_table('link_tracking')
