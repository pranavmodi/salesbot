"""Add missing company research columns

Revision ID: ca86acfc25c0
Revises: 5b8eac9361af
Create Date: 2025-07-27 14:23:14.736819

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ca86acfc25c0'
down_revision: Union[str, None] = '5b8eac9361af'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing company research columns if they don't exist."""
    # Check if columns already exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('companies')]
    
    # Add missing text/research columns
    missing_text_columns = [
        'company_research', 'markdown_report', 'strategic_imperatives', 
        'agent_recommendations', 'research_step_1_basic', 'research_step_2_strategic', 
        'research_step_3_report', 'research_error'
    ]
    
    for col_name in missing_text_columns:
        if col_name not in columns:
            op.add_column('companies', sa.Column(col_name, sa.Text, nullable=True))
    
    # Add research_status column with default
    if 'research_status' not in columns:
        op.add_column('companies', sa.Column('research_status', sa.String(length=50), nullable=True, default='pending'))
        # Set default value for existing companies
        op.execute("UPDATE companies SET research_status = 'pending' WHERE research_status IS NULL")
    
    # Add timestamp columns
    if 'research_started_at' not in columns:
        op.add_column('companies', sa.Column('research_started_at', sa.DateTime, nullable=True))
    
    if 'research_completed_at' not in columns:
        op.add_column('companies', sa.Column('research_completed_at', sa.DateTime, nullable=True))
        
    # Add created_at and updated_at if missing
    if 'created_at' not in columns:
        op.add_column('companies', sa.Column('created_at', sa.DateTime, nullable=True, default=sa.func.current_timestamp()))
        op.execute("UPDATE companies SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
        
    if 'updated_at' not in columns:
        op.add_column('companies', sa.Column('updated_at', sa.DateTime, nullable=True, default=sa.func.current_timestamp()))
        op.execute("UPDATE companies SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")


def downgrade() -> None:
    """Remove added company research columns."""
    # Remove the columns we added
    columns_to_remove = [
        'company_research', 'markdown_report', 'strategic_imperatives', 
        'agent_recommendations', 'research_step_1_basic', 'research_step_2_strategic', 
        'research_step_3_report', 'research_error', 'research_status',
        'research_started_at', 'research_completed_at'
    ]
    
    for col_name in columns_to_remove:
        try:
            op.drop_column('companies', col_name)
        except:
            pass  # Column might not exist
