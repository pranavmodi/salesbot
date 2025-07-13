"""create_report_clicks_table

Revision ID: ce4ca1c074f5
Revises: 936332f868ca
Create Date: 2025-07-13 07:43:11.889355

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ce4ca1c074f5'
down_revision: Union[str, None] = '936332f868ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create report_clicks table for tracking click analytics
    op.create_table(
        'report_clicks',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('company_id', sa.Integer, sa.ForeignKey('companies.id'), nullable=True),
        sa.Column('campaign_id', sa.Integer, sa.ForeignKey('campaigns.id'), nullable=True),
        sa.Column('email_history_id', sa.Integer, sa.ForeignKey('email_history.id'), nullable=True),
        sa.Column('recipient_email', sa.String(255), nullable=True),
        sa.Column('company_slug', sa.String(255), nullable=True),
        sa.Column('tracking_id', sa.String(100), nullable=True),
        sa.Column('click_timestamp', sa.DateTime, nullable=False, default=sa.func.current_timestamp()),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.Column('referer', sa.Text, nullable=True),
        sa.Column('utm_source', sa.String(100), nullable=True),
        sa.Column('utm_medium', sa.String(100), nullable=True),
        sa.Column('utm_campaign', sa.String(100), nullable=True),
        sa.Column('utm_content', sa.String(100), nullable=True),
        sa.Column('utm_term', sa.String(100), nullable=True),
        sa.Column('device_type', sa.String(50), nullable=True),
        sa.Column('browser', sa.String(100), nullable=True),
        sa.Column('operating_system', sa.String(100), nullable=True),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('session_id', sa.String(255), nullable=True),
        sa.Column('custom_data', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime, nullable=False, default=sa.func.current_timestamp(), onupdate=sa.func.current_timestamp())
    )
    
    # Create indexes for better query performance
    op.create_index('idx_report_clicks_company_id', 'report_clicks', ['company_id'])
    op.create_index('idx_report_clicks_campaign_id', 'report_clicks', ['campaign_id'])
    op.create_index('idx_report_clicks_recipient_email', 'report_clicks', ['recipient_email'])
    op.create_index('idx_report_clicks_tracking_id', 'report_clicks', ['tracking_id'])
    op.create_index('idx_report_clicks_click_timestamp', 'report_clicks', ['click_timestamp'])
    op.create_index('idx_report_clicks_utm_campaign', 'report_clicks', ['utm_campaign'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes first
    op.drop_index('idx_report_clicks_utm_campaign', 'report_clicks')
    op.drop_index('idx_report_clicks_click_timestamp', 'report_clicks')
    op.drop_index('idx_report_clicks_tracking_id', 'report_clicks')
    op.drop_index('idx_report_clicks_recipient_email', 'report_clicks')
    op.drop_index('idx_report_clicks_campaign_id', 'report_clicks')
    op.drop_index('idx_report_clicks_company_id', 'report_clicks')
    
    # Drop table
    op.drop_table('report_clicks')
