"""add_click_tracking_columns

Revision ID: ca064c3f7aba
Revises: df4ea3b00352
Create Date: 2025-08-14 14:48:31.179899

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ca064c3f7aba'
down_revision: Union[str, None] = 'df4ea3b00352'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add click tracking columns to link_tracking table."""
    op.add_column('link_tracking', sa.Column('click_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('link_tracking', sa.Column('last_clicked_at', sa.DateTime(), nullable=True))
    op.add_column('link_tracking', sa.Column('last_user_agent', sa.String(500), nullable=True))
    op.add_column('link_tracking', sa.Column('last_ip_address', sa.String(50), nullable=True))
    op.add_column('link_tracking', sa.Column('last_referer', sa.String(500), nullable=True))


def downgrade() -> None:
    """Remove click tracking columns from link_tracking table."""
    op.drop_column('link_tracking', 'last_referer')
    op.drop_column('link_tracking', 'last_ip_address')
    op.drop_column('link_tracking', 'last_user_agent')
    op.drop_column('link_tracking', 'last_clicked_at')
    op.drop_column('link_tracking', 'click_count')
