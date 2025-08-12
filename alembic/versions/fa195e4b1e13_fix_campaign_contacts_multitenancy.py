"""fix_campaign_contacts_multitenancy

Revision ID: fa195e4b1e13
Revises: f9427872ebac
Create Date: 2025-08-12 20:04:36.784627

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fa195e4b1e13'
down_revision: Union[str, None] = 'f9427872ebac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Fix campaign_contacts for multi-tenancy."""
    # Add tenant_id column to campaign_contacts table
    op.add_column('campaign_contacts', sa.Column('tenant_id', sa.dialects.postgresql.UUID(), nullable=True))
    
    # Populate tenant_id for existing records by joining with campaigns table
    op.execute("""
        UPDATE campaign_contacts cc
        SET tenant_id = c.tenant_id
        FROM campaigns c
        WHERE cc.campaign_id = c.id
    """)
    
    # Make tenant_id NOT NULL after populating
    op.alter_column('campaign_contacts', 'tenant_id', nullable=False)
    
    # Drop the old unique constraint
    op.drop_constraint('uq_campaign_contacts_campaign_contact', 'campaign_contacts', type_='unique')
    
    # Create new unique constraint including tenant_id
    op.create_unique_constraint(
        'campaign_contacts_tenant_campaign_contact_key',
        'campaign_contacts',
        ['tenant_id', 'campaign_id', 'contact_email']
    )


def downgrade() -> None:
    """Downgrade schema - Remove tenant_id from campaign_contacts."""
    # Drop the new unique constraint
    op.drop_constraint('campaign_contacts_tenant_campaign_contact_key', 'campaign_contacts', type_='unique')
    
    # Recreate the old unique constraint
    op.create_unique_constraint(
        'uq_campaign_contacts_campaign_contact',
        'campaign_contacts',
        ['campaign_id', 'contact_email']
    )
    
    # Drop the tenant_id column
    op.drop_column('campaign_contacts', 'tenant_id')
