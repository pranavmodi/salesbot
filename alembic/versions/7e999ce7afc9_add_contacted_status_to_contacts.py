"""add_contacted_status_to_contacts

Revision ID: 7e999ce7afc9
Revises: cad7507811f6
Create Date: 2025-09-04 14:06:04.703522

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7e999ce7afc9'
down_revision: Union[str, None] = 'cad7507811f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add contacted column to contacts table
    op.add_column('contacts', sa.Column('contacted', sa.Boolean(), nullable=True, default=False))
    
    # Update existing records to set contacted=False by default
    op.execute("UPDATE contacts SET contacted = FALSE WHERE contacted IS NULL")
    
    # Set NOT NULL constraint after updating existing records
    op.alter_column('contacts', 'contacted', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove contacted column
    op.drop_column('contacts', 'contacted')
