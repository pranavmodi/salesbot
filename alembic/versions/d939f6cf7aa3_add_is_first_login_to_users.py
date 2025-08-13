"""add_is_first_login_to_users

Revision ID: d939f6cf7aa3
Revises: 07d3f826c668
Create Date: 2025-08-13 21:53:51.123819

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd939f6cf7aa3'
down_revision: Union[str, None] = '07d3f826c668'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_first_login field to users table."""
    # Check if users table exists and if column doesn't exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'users' in inspector.get_table_names():
        users_columns = [col['name'] for col in inspector.get_columns('users')]
        
        if 'is_first_login' not in users_columns:
            print("➕ Adding is_first_login to users table")
            op.add_column('users', sa.Column('is_first_login', sa.Boolean, nullable=True, default=True))
            # Set existing users to false (they've already logged in)
            op.execute("UPDATE users SET is_first_login = false WHERE is_first_login IS NULL")
            print("✅ Added is_first_login to users table")
        else:
            print("✅ is_first_login already exists in users table")
    else:
        print("❌ Users table does not exist!")


def downgrade() -> None:
    """Remove is_first_login field from users table."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'users' in inspector.get_table_names():
        users_columns = [col['name'] for col in inspector.get_columns('users')]
        
        if 'is_first_login' in users_columns:
            print("➖ Removing is_first_login from users table")
            op.drop_column('users', 'is_first_login')
            print("✅ Removed is_first_login from users table")
