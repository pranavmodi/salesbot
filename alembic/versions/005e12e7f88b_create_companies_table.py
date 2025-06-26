"""create_companies_table

Revision ID: 005e12e7f88b
Revises: dcfd9b261ec6
Create Date: 2025-06-26 15:14:50.789359

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005e12e7f88b'
down_revision: Union[str, None] = 'dcfd9b261ec6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create companies table for storing company information."""
    op.create_table(
        'companies',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('company_name', sa.String(255), nullable=False),
        sa.Column('website_url', sa.String(500), nullable=True),
        sa.Column('company_research', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )
    
    # Create indexes for better query performance
    op.create_index('idx_companies_company_name', 'companies', ['company_name'])
    op.create_index('idx_companies_website_url', 'companies', ['website_url'])
    op.create_index('idx_companies_created_at', 'companies', ['created_at'])


def downgrade() -> None:
    """Drop companies table."""
    op.drop_index('idx_companies_created_at')
    op.drop_index('idx_companies_website_url')
    op.drop_index('idx_companies_company_name')
    op.drop_table('companies')
