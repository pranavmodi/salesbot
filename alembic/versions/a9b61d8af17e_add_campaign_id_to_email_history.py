"""add_campaign_id_to_email_history

Revision ID: a9b61d8af17e
Revises: a3a7abeb83b3
Create Date: 2025-06-27 18:05:57.683145

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9b61d8af17e'
down_revision: Union[str, None] = 'a3a7abeb83b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add campaign_id column to email_history table."""
    # Add campaign_id column to email_history table
    op.add_column('email_history', sa.Column('campaign_id', sa.Integer, nullable=True))
    
    # Add foreign key constraint to campaigns table
    op.create_foreign_key(
        'fk_email_history_campaign_id',
        'email_history', 'campaigns',
        ['campaign_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Create index for better query performance
    op.create_index('idx_email_history_campaign_id', 'email_history', ['campaign_id'])


def downgrade() -> None:
    """Remove campaign_id column from email_history table."""
    op.drop_index('idx_email_history_campaign_id')
    op.drop_constraint('fk_email_history_campaign_id', 'email_history', type_='foreignkey')
    op.drop_column('email_history', 'campaign_id')
