"""fix_file_metadata_multitenancy

Revision ID: 039363f66853
Revises: fa195e4b1e13
Create Date: 2025-08-12 20:05:36.782231

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '039363f66853'
down_revision: Union[str, None] = 'fa195e4b1e13'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Fix file_metadata for multi-tenancy."""
    # Add tenant_id column to file_metadata table
    op.add_column('file_metadata', sa.Column('tenant_id', sa.dialects.postgresql.UUID(), nullable=True))
    
    # For existing records, we'll set them to a default tenant
    # This assumes there's a default tenant in the system
    op.execute("""
        UPDATE file_metadata 
        SET tenant_id = (
            SELECT id FROM tenants 
            WHERE slug = 'default' 
            LIMIT 1
        )
        WHERE tenant_id IS NULL
    """)
    
    # Make tenant_id NOT NULL after populating
    op.alter_column('file_metadata', 'tenant_id', nullable=False)
    
    # Drop the old unique constraint on filename
    op.drop_constraint('file_metadata_filename_key', 'file_metadata', type_='unique')
    
    # Create new unique constraint including tenant_id
    op.create_unique_constraint(
        'file_metadata_tenant_filename_key',
        'file_metadata',
        ['tenant_id', 'filename']
    )


def downgrade() -> None:
    """Downgrade schema - Remove tenant_id from file_metadata."""
    # Drop the new unique constraint
    op.drop_constraint('file_metadata_tenant_filename_key', 'file_metadata', type_='unique')
    
    # Recreate the old unique constraint (may fail if duplicate filenames exist)
    op.create_unique_constraint(
        'file_metadata_filename_key',
        'file_metadata',
        ['filename']
    )
    
    # Drop the tenant_id column
    op.drop_column('file_metadata', 'tenant_id')
