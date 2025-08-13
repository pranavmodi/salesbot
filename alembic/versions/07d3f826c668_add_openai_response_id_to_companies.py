"""add_openai_response_id_to_companies

Revision ID: 07d3f826c668
Revises: 039363f66853
Create Date: 2025-08-13 15:08:59.392487

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '07d3f826c668'
down_revision: Union[str, None] = '039363f66853'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add openai_response_id column to companies table."""
    # Check if companies table exists and if column doesn't exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'companies' in inspector.get_table_names():
        companies_columns = [col['name'] for col in inspector.get_columns('companies')]
        
        if 'openai_response_id' not in companies_columns:
            print("➕ Adding openai_response_id to companies table")
            op.add_column('companies', sa.Column('openai_response_id', sa.String(length=255), nullable=True))
            print("✅ Added openai_response_id to companies table")
        else:
            print("✅ openai_response_id already exists in companies table")
    else:
        print("❌ Companies table does not exist!")


def downgrade() -> None:
    """Remove openai_response_id column from companies table."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'companies' in inspector.get_table_names():
        companies_columns = [col['name'] for col in inspector.get_columns('companies')]
        
        if 'openai_response_id' in companies_columns:
            print("➖ Removing openai_response_id from companies table")
            op.drop_column('companies', 'openai_response_id')
            print("✅ Removed openai_response_id from companies table")
