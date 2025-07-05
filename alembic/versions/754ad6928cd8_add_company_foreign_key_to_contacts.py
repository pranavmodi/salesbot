"""add_company_foreign_key_to_contacts

Revision ID: 754ad6928cd8
Revises: 6e33c0b597cc
Create Date: 2025-07-05 14:07:39.487750

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import String, Integer, text


# revision identifiers, used by Alembic.
revision: str = '754ad6928cd8'
down_revision: Union[str, None] = '6e33c0b597cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add company_id foreign key to contacts table and migrate existing data."""
    
    # Step 1: Add company_id column (nullable initially)
    op.add_column('contacts', sa.Column('company_id', sa.Integer, nullable=True))
    
    # Step 2: Create companies for existing contacts that don't have them
    # First, get a connection to execute raw SQL
    connection = op.get_bind()
    
    # Insert missing companies from contacts table
    connection.execute(text("""
        INSERT INTO companies (company_name, website_url, created_at, updated_at)
        SELECT DISTINCT 
            c.company_name,
            CASE 
                WHEN c.company_domain IS NOT NULL AND c.company_domain != '' 
                THEN 'https://' || c.company_domain
                ELSE NULL
            END as website_url,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        FROM contacts c
        WHERE c.company_name IS NOT NULL 
            AND c.company_name != ''
            AND NOT EXISTS (
                SELECT 1 FROM companies comp 
                WHERE LOWER(comp.company_name) = LOWER(c.company_name)
            )
    """))
    
    # Step 3: Update contacts to reference company IDs
    connection.execute(text("""
        UPDATE contacts 
        SET company_id = companies.id
        FROM companies
        WHERE LOWER(contacts.company_name) = LOWER(companies.company_name)
            AND contacts.company_name IS NOT NULL
            AND contacts.company_name != ''
    """))
    
    # Step 4: Add foreign key constraint
    op.create_foreign_key(
        'fk_contacts_company_id',
        'contacts', 'companies',
        ['company_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Step 5: Create index for better performance
    op.create_index('idx_contacts_company_id', 'contacts', ['company_id'])


def downgrade() -> None:
    """Remove company_id foreign key from contacts table."""
    
    # Drop index
    op.drop_index('idx_contacts_company_id')
    
    # Drop foreign key constraint
    op.drop_constraint('fk_contacts_company_id', 'contacts', type_='foreignkey')
    
    # Drop company_id column
    op.drop_column('contacts', 'company_id')
