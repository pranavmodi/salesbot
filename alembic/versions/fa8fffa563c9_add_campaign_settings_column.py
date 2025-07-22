"""add_campaign_settings_column

Revision ID: fa8fffa563c9
Revises: ce4ca1c074f5
Create Date: 2025-07-22 09:18:12.787579

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fa8fffa563c9'
down_revision: Union[str, None] = 'ce4ca1c074f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add campaign_settings column to campaigns table."""
    op.add_column('campaigns', sa.Column('campaign_settings', sa.Text(), nullable=True, default='{}'))


def downgrade() -> None:
    """Remove campaign_settings column from campaigns table."""
    op.drop_column('campaigns', 'campaign_settings')
