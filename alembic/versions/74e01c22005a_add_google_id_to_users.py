"""add_google_id_to_users

Revision ID: 74e01c22005a
Revises: 8a1b2c3d4e5f
Create Date: 2025-08-12 15:31:41.139500

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '74e01c22005a'
down_revision: Union[str, None] = '8a1b2c3d4e5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add google_id column to users table
    op.add_column('users', sa.Column('google_id', sa.String(255), nullable=True))
    
    # Add index for google_id for faster lookups
    op.create_index('ix_users_google_id', 'users', ['google_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove index and column
    op.drop_index('ix_users_google_id', 'users')
    op.drop_column('users', 'google_id')
