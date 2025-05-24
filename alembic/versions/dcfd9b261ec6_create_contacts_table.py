"""create_contacts_table

Revision ID: dcfd9b261ec6
Revises: aba854ab6f1f
Create Date: 2025-05-24 18:30:59.352528

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'dcfd9b261ec6'
down_revision: Union[str, None] = 'aba854ab6f1f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create contacts table for sales automation system."""
    op.create_table(
        'contacts',
        sa.Column('email', sa.String(255), primary_key=True, nullable=False),
        sa.Column('first_name', sa.String(100), nullable=True),
        sa.Column('last_name', sa.String(100), nullable=True),
        sa.Column('full_name', sa.String(200), nullable=True),
        sa.Column('job_title', sa.String(200), nullable=True),
        sa.Column('company_name', sa.String(200), nullable=True),
        sa.Column('company_domain', sa.String(100), nullable=True),
        sa.Column('linkedin_profile', sa.String(500), nullable=True),
        sa.Column('location', sa.String(200), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('linkedin_message', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('source_files', postgresql.JSONB, nullable=True),  # JSON array of source files
        sa.Column('all_data', postgresql.JSONB, nullable=True),      # JSON object with all original data
    )
    
    # Create indexes for better query performance
    op.create_index('idx_contacts_company_name', 'contacts', ['company_name'])
    op.create_index('idx_contacts_job_title', 'contacts', ['job_title'])
    op.create_index('idx_contacts_full_name', 'contacts', ['first_name', 'last_name'])
    op.create_index('idx_contacts_created_at', 'contacts', ['created_at'])
    
    # Create additional tables for metadata tracking
    op.create_table(
        'file_metadata',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('filename', sa.String(255), unique=True, nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('total_rows', sa.Integer, nullable=False),
        sa.Column('successful_inserts', sa.Integer, nullable=False),
        sa.Column('errors', sa.Integer, nullable=False),
        sa.Column('column_mapping', postgresql.JSONB, nullable=True),  # JSON mapping of columns found
    )
    
    op.create_table(
        'column_mappings',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('source_column', sa.String(255), nullable=False),
        sa.Column('standard_column', sa.String(255), nullable=False),
        sa.Column('confidence_score', sa.Float, nullable=False, default=1.0),
        sa.Column('file_source', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )
    
    # Add indexes for metadata tables
    op.create_index('idx_file_metadata_filename', 'file_metadata', ['filename'])
    op.create_index('idx_column_mappings_source', 'column_mappings', ['source_column'])


def downgrade() -> None:
    """Drop contacts table and related metadata tables."""
    op.drop_index('idx_column_mappings_source')
    op.drop_index('idx_file_metadata_filename')
    op.drop_index('idx_contacts_created_at')
    op.drop_index('idx_contacts_full_name')
    op.drop_index('idx_contacts_job_title')
    op.drop_index('idx_contacts_company_name')
    
    op.drop_table('column_mappings')
    op.drop_table('file_metadata')
    op.drop_table('contacts')
