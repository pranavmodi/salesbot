"""fix_contacts_primary_key_for_multitenancy

Revision ID: f9427872ebac
Revises: 683c7101eeb3
Create Date: 2025-08-12 19:58:36.675816

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f9427872ebac'
down_revision: Union[str, None] = '683c7101eeb3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Fix contacts primary key for multi-tenancy."""
    # First, drop the foreign key constraint that depends on the primary key
    op.drop_constraint('fk_campaign_contacts_contact_email', 'campaign_contacts', type_='foreignkey')
    
    # Drop the existing primary key constraint
    op.drop_constraint('contacts_pkey', 'contacts', type_='primary')
    
    # Create a composite primary key on (email, tenant_id)
    op.create_primary_key('contacts_pkey', 'contacts', ['email', 'tenant_id'])
    
    # Recreate the foreign key constraint - now it needs to reference both columns
    # Note: This assumes campaign_contacts also has tenant_id column
    # For now, we'll skip recreating the FK and handle it in application logic


def downgrade() -> None:
    """Downgrade schema - Revert to single email primary key."""
    # Drop any foreign key constraints first
    try:
        op.drop_constraint('fk_campaign_contacts_contact_email', 'campaign_contacts', type_='foreignkey')
    except:
        pass  # May not exist
        
    # Drop the composite primary key
    op.drop_constraint('contacts_pkey', 'contacts', type_='primary')
    
    # Recreate the single email primary key (this may fail if duplicate emails exist)
    op.create_primary_key('contacts_pkey', 'contacts', ['email'])
    
    # Recreate the original foreign key constraint
    op.create_foreign_key(
        'fk_campaign_contacts_contact_email',
        'campaign_contacts', 'contacts',
        ['contact_email'], ['email']
    )
