"""create_campaign_email_jobs_table

Revision ID: 9e96bd2040b2
Revises: fa8fffa563c9
Create Date: 2025-07-22 09:37:44.916607

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9e96bd2040b2'
down_revision: Union[str, None] = 'fa8fffa563c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create campaign_email_jobs table for persistent email scheduling."""
    op.create_table('campaign_email_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('campaign_id', sa.Integer(), nullable=False),
        sa.Column('contact_email', sa.String(255), nullable=False),
        sa.Column('contact_data', sa.Text(), nullable=False),  # JSON string
        sa.Column('campaign_settings', sa.Text(), nullable=False),  # JSON string
        sa.Column('scheduled_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, default='pending'),  # pending, executed, failed
        sa.Column('attempts', sa.Integer(), nullable=False, default=0),
        sa.Column('last_attempt', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='CASCADE'),
        sa.Index('idx_campaign_email_jobs_status_time', 'status', 'scheduled_time'),
        sa.Index('idx_campaign_email_jobs_campaign', 'campaign_id')
    )


def downgrade() -> None:
    """Drop campaign_email_jobs table."""
    op.drop_table('campaign_email_jobs')
