"""add_clicked_at_column_to_report_clicks

Revision ID: 71cdf1fbede5
Revises: ca064c3f7aba
Create Date: 2025-08-15 17:06:19.947084

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '71cdf1fbede5'
down_revision: Union[str, None] = 'ca064c3f7aba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add clicked_at column to report_clicks table."""
    # Add clicked_at column with default value of current timestamp
    op.add_column('report_clicks', sa.Column('clicked_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')))


def downgrade() -> None:
    """Remove clicked_at column from report_clicks table."""
    op.drop_column('report_clicks', 'clicked_at')
