"""Add type column to campaigns table

Revision ID: ac732760ed63
Revises: 9e96bd2040b2
Create Date: 2025-07-27 13:44:19.463442

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ac732760ed63'
down_revision: Union[str, None] = '9e96bd2040b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add type column to campaigns table if it doesn't exist."""
    # Check if type column already exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('campaigns')]
    
    if 'type' not in columns:
        # Add type column to campaigns table
        op.add_column('campaigns', sa.Column('type', sa.String(length=50), nullable=True))
        
    # Set default value for existing campaigns that don't have type set
    op.execute("UPDATE campaigns SET type = 'cold_outreach' WHERE type IS NULL")


def downgrade() -> None:
    """Remove type column from campaigns table."""
    # Remove type column from campaigns table
    op.drop_column('campaigns', 'type')
