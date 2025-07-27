"""comprehensive_schema_fix_for_railway

Revision ID: 406030e6b390
Revises: 3d083d0a5568
Create Date: 2025-07-27 14:43:35.723846

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '406030e6b390'
down_revision: Union[str, None] = '3d083d0a5568'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Comprehensive schema fix for Railway deployment."""
    print("🚀 Starting comprehensive schema fix for Railway...")
    
    # Get database connection and inspector
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Check if tables exist
    table_names = inspector.get_table_names()
    print(f"📋 Available tables: {table_names}")
    
    # ===============================================
    # FIX CAMPAIGNS TABLE
    # ===============================================
    if 'campaigns' in table_names:
        print("🔧 Fixing campaigns table...")
        campaigns_columns = [col['name'] for col in inspector.get_columns('campaigns')]
        print(f"📋 Current campaigns columns: {campaigns_columns}")
        
        # Define all required columns for campaigns
        required_campaigns_columns = {
            'type': sa.String(length=100),
            'email_template': sa.String(length=100),
            'priority': sa.String(length=50),
            'campaign_settings': sa.Text,
            'schedule_date': sa.DateTime,
            'followup_days': sa.Integer,
            'selection_criteria': sa.Text,
            'status': sa.String(length=50),
            'html_report': sa.Text,
            'pdf_report_base64': sa.Text,
            'created_at': sa.DateTime,
            'updated_at': sa.DateTime
        }
        
        for col_name, col_type in required_campaigns_columns.items():
            if col_name not in campaigns_columns:
                print(f"➕ Adding campaigns.{col_name}")
                try:
                    if col_name == 'type':
                        op.add_column('campaigns', sa.Column(col_name, col_type, nullable=True, default='outbound'))
                        op.execute("UPDATE campaigns SET type = 'outbound' WHERE type IS NULL")
                    elif col_name == 'email_template':
                        op.add_column('campaigns', sa.Column(col_name, col_type, nullable=True, default='deep_research'))
                        op.execute("UPDATE campaigns SET email_template = 'deep_research' WHERE email_template IS NULL")
                    elif col_name == 'priority':
                        op.add_column('campaigns', sa.Column(col_name, col_type, nullable=True, default='medium'))
                        op.execute("UPDATE campaigns SET priority = 'medium' WHERE priority IS NULL")
                    elif col_name == 'followup_days':
                        op.add_column('campaigns', sa.Column(col_name, col_type, nullable=True, default=3))
                        op.execute("UPDATE campaigns SET followup_days = 3 WHERE followup_days IS NULL")
                    elif col_name == 'status':
                        op.add_column('campaigns', sa.Column(col_name, col_type, nullable=True, default='draft'))
                        op.execute("UPDATE campaigns SET status = 'draft' WHERE status IS NULL")
                    elif col_name in ['campaign_settings', 'selection_criteria']:
                        op.add_column('campaigns', sa.Column(col_name, col_type, nullable=True, default='{}'))
                        op.execute(f"UPDATE campaigns SET {col_name} = '{{}}' WHERE {col_name} IS NULL")
                    elif col_name in ['created_at', 'updated_at']:
                        op.add_column('campaigns', sa.Column(col_name, col_type, nullable=True, default=sa.func.current_timestamp()))
                        op.execute(f"UPDATE campaigns SET {col_name} = CURRENT_TIMESTAMP WHERE {col_name} IS NULL")
                    else:
                        op.add_column('campaigns', sa.Column(col_name, col_type, nullable=True))
                    print(f"✅ Added campaigns.{col_name}")
                except Exception as e:
                    print(f"❌ Failed to add campaigns.{col_name}: {e}")
            else:
                print(f"✅ campaigns.{col_name} already exists")
    else:
        print("❌ Campaigns table does not exist!")
    
    # ===============================================
    # FIX COMPANIES TABLE  
    # ===============================================
    if 'companies' in table_names:
        print("🔧 Fixing companies table...")
        companies_columns = [col['name'] for col in inspector.get_columns('companies')]
        print(f"📋 Current companies columns: {companies_columns}")
        
        # Define all required columns for companies
        required_companies_columns = {
            'company_research': sa.Text,
            'markdown_report': sa.Text,
            'html_report': sa.Text,
            'pdf_report_base64': sa.Text,
            'strategic_imperatives': sa.Text,
            'agent_recommendations': sa.Text,
            'research_status': sa.String(length=50),
            'research_step_1_basic': sa.Text,
            'research_step_2_strategic': sa.Text,
            'research_step_3_report': sa.Text,
            'research_started_at': sa.DateTime,
            'research_completed_at': sa.DateTime,
            'research_error': sa.Text,
            'created_at': sa.DateTime,
            'updated_at': sa.DateTime
        }
        
        for col_name, col_type in required_companies_columns.items():
            if col_name not in companies_columns:
                print(f"➕ Adding companies.{col_name}")
                try:
                    if col_name == 'research_status':
                        op.add_column('companies', sa.Column(col_name, col_type, nullable=True, default='pending'))
                        op.execute("UPDATE companies SET research_status = 'pending' WHERE research_status IS NULL")
                    elif col_name in ['created_at', 'updated_at']:
                        op.add_column('companies', sa.Column(col_name, col_type, nullable=True, default=sa.func.current_timestamp()))
                        op.execute(f"UPDATE companies SET {col_name} = CURRENT_TIMESTAMP WHERE {col_name} IS NULL")
                    else:
                        op.add_column('companies', sa.Column(col_name, col_type, nullable=True))
                    print(f"✅ Added companies.{col_name}")
                except Exception as e:
                    print(f"❌ Failed to add companies.{col_name}: {e}")
            else:
                print(f"✅ companies.{col_name} already exists")
    else:
        print("❌ Companies table does not exist!")
    
    print("🎉 Comprehensive schema fix completed!")


def downgrade() -> None:
    """Downgrade schema."""
    pass
