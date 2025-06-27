"""create_campaign_contacts_junction_table

Revision ID: 43c31049fc87
Revises: a9b61d8af17e
Create Date: 2025-06-27 18:10:00.626583

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '43c31049fc87'
down_revision: Union[str, None] = 'a9b61d8af17e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create campaign_contacts junction table for many-to-many relationship."""
    op.create_table(
        'campaign_contacts',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('campaign_id', sa.Integer, nullable=False),
        sa.Column('contact_email', sa.String(255), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),  # active, paused, completed, removed
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )
    
    # Add foreign key constraints
    op.create_foreign_key(
        'fk_campaign_contacts_campaign_id',
        'campaign_contacts', 'campaigns',
        ['campaign_id'], ['id'],
        ondelete='CASCADE'
    )
    
    op.create_foreign_key(
        'fk_campaign_contacts_contact_email',
        'campaign_contacts', 'contacts',
        ['contact_email'], ['email'],
        ondelete='CASCADE'
    )
    
    # Create unique constraint to prevent duplicate campaign-contact pairs
    op.create_unique_constraint(
        'uq_campaign_contacts_campaign_contact',
        'campaign_contacts',
        ['campaign_id', 'contact_email']
    )
    
    # Create indexes for better query performance
    op.create_index('idx_campaign_contacts_campaign_id', 'campaign_contacts', ['campaign_id'])
    op.create_index('idx_campaign_contacts_contact_email', 'campaign_contacts', ['contact_email'])
    op.create_index('idx_campaign_contacts_status', 'campaign_contacts', ['status'])
    op.create_index('idx_campaign_contacts_added_at', 'campaign_contacts', ['added_at'])


def downgrade() -> None:
    """Drop campaign_contacts junction table."""
    op.drop_index('idx_campaign_contacts_added_at')
    op.drop_index('idx_campaign_contacts_status')
    op.drop_index('idx_campaign_contacts_contact_email')
    op.drop_index('idx_campaign_contacts_campaign_id')
    op.drop_constraint('uq_campaign_contacts_campaign_contact', 'campaign_contacts')
    op.drop_constraint('fk_campaign_contacts_contact_email', 'campaign_contacts', type_='foreignkey')
    op.drop_constraint('fk_campaign_contacts_campaign_id', 'campaign_contacts', type_='foreignkey')
    op.drop_table('campaign_contacts')
