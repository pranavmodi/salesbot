"""create_email_tracking_table

Revision ID: 7a58370001cc
Revises: 2857f2a9a178
Create Date: 2025-08-06 19:49:41.801683

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a58370001cc'
down_revision: Union[str, None] = '2857f2a9a178'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create email_tracking table
    op.create_table(
        'email_tracking',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tracking_id', sa.String(50), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=True),
        sa.Column('recipient_email', sa.String(255), nullable=False),
        sa.Column('campaign_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('opened_at', sa.DateTime(), nullable=True),
        sa.Column('tracking_data', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_tracking_id', 'tracking_id', unique=True),
        sa.Index('idx_recipient_email', 'recipient_email'),
        sa.Index('idx_campaign_id', 'campaign_id'),
        sa.Index('idx_company_id', 'company_id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('email_tracking')
