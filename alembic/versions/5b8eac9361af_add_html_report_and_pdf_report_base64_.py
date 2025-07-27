"""Add html_report and pdf_report_base64 columns to companies table

Revision ID: 5b8eac9361af
Revises: ac732760ed63
Create Date: 2025-07-27 13:52:45.651628

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5b8eac9361af'
down_revision: Union[str, None] = 'ac732760ed63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add html_report and pdf_report_base64 columns to companies table if they don't exist."""
    # Check if columns already exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('companies')]
    
    if 'html_report' not in columns:
        # Add html_report column to companies table
        op.add_column('companies', sa.Column('html_report', sa.Text, nullable=True))
        
    if 'pdf_report_base64' not in columns:
        # Add pdf_report_base64 column to companies table  
        op.add_column('companies', sa.Column('pdf_report_base64', sa.Text, nullable=True))


def downgrade() -> None:
    """Remove html_report and pdf_report_base64 columns from companies table."""
    # Remove columns from companies table
    op.drop_column('companies', 'pdf_report_base64')
    op.drop_column('companies', 'html_report')
