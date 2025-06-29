"""add_markdown_report_to_companies

Revision ID: 58e517818d4d
Revises: 54bcf3594d10
Create Date: 2025-06-29 13:15:43.572265

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '58e517818d4d'
down_revision: Union[str, None] = '54bcf3594d10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add markdown_report column to companies table."""
    op.add_column('companies', sa.Column('markdown_report', sa.Text, nullable=True))


def downgrade() -> None:
    """Remove markdown_report column from companies table."""
    op.drop_column('companies', 'markdown_report')
