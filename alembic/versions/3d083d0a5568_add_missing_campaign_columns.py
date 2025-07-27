"""Add missing campaign columns

Revision ID: 3d083d0a5568
Revises: ca86acfc25c0
Create Date: 2025-07-27 14:28:11.845706

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3d083d0a5568'
down_revision: Union[str, None] = 'ca86acfc25c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing campaign columns if they don't exist."""
    print("🔧 Starting campaign columns migration...")
    
    # Check if columns already exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('campaigns')]
    
    print(f"📋 Current campaigns table columns: {columns}")
    
    # Add missing campaign columns
    missing_columns = {
        'email_template': sa.String(length=100),
        'priority': sa.String(length=50),
        'campaign_settings': sa.Text,
        'schedule_date': sa.DateTime,
        'followup_days': sa.Integer,
        'selection_criteria': sa.Text,
        'status': sa.String(length=50),
        'created_at': sa.DateTime,
        'updated_at': sa.DateTime
    }
    
    for col_name, col_type in missing_columns.items():
        if col_name not in columns:
            print(f"➕ Adding missing column: {col_name}")
            if col_name == 'email_template':
                # Add with default value
                op.add_column('campaigns', sa.Column(col_name, col_type, nullable=True, default='deep_research'))
                op.execute("UPDATE campaigns SET email_template = 'deep_research' WHERE email_template IS NULL")
            elif col_name == 'priority':
                # Add with default value
                op.add_column('campaigns', sa.Column(col_name, col_type, nullable=True, default='medium'))
                op.execute("UPDATE campaigns SET priority = 'medium' WHERE priority IS NULL")
            elif col_name == 'followup_days':
                # Add with default value
                op.add_column('campaigns', sa.Column(col_name, col_type, nullable=True, default=3))
                op.execute("UPDATE campaigns SET followup_days = 3 WHERE followup_days IS NULL")
            elif col_name == 'status':
                # Add with default value
                op.add_column('campaigns', sa.Column(col_name, col_type, nullable=True, default='draft'))
                op.execute("UPDATE campaigns SET status = 'draft' WHERE status IS NULL")
            elif col_name in ['campaign_settings', 'selection_criteria']:
                # Add with default empty JSON
                op.add_column('campaigns', sa.Column(col_name, col_type, nullable=True, default='{}'))
                op.execute(f"UPDATE campaigns SET {col_name} = '{{}}' WHERE {col_name} IS NULL")
            elif col_name in ['created_at', 'updated_at']:
                # Add with current timestamp
                op.add_column('campaigns', sa.Column(col_name, col_type, nullable=True, default=sa.func.current_timestamp()))
                op.execute(f"UPDATE campaigns SET {col_name} = CURRENT_TIMESTAMP WHERE {col_name} IS NULL")
            else:
                # Add without default
                op.add_column('campaigns', sa.Column(col_name, col_type, nullable=True))
        else:
            print(f"✅ Column {col_name} already exists")
    
    print("🎉 Campaign columns migration completed!")


def downgrade() -> None:
    """Remove added campaign columns."""
    columns_to_remove = [
        'email_template', 'priority', 'campaign_settings', 'schedule_date', 
        'followup_days', 'selection_criteria', 'status'
    ]
    
    for col_name in columns_to_remove:
        try:
            op.drop_column('campaigns', col_name)
        except:
            pass  # Column might not exist
