"""add_research_steps_to_companies

Revision ID: 6e33c0b597cc
Revises: 58e517818d4d
Create Date: 2025-06-29 13:15:43.572265

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6e33c0b597cc'
down_revision: Union[str, None] = '58e517818d4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add step-by-step research tracking fields to companies table."""
    # Add research step fields
    op.add_column('companies', sa.Column('research_status', sa.String(50), nullable=True, default='pending'))
    op.add_column('companies', sa.Column('research_step_1_basic', sa.Text, nullable=True))
    op.add_column('companies', sa.Column('research_step_2_strategic', sa.Text, nullable=True))
    op.add_column('companies', sa.Column('research_step_3_report', sa.Text, nullable=True))
    op.add_column('companies', sa.Column('research_started_at', sa.DateTime, nullable=True))
    op.add_column('companies', sa.Column('research_completed_at', sa.DateTime, nullable=True))
    op.add_column('companies', sa.Column('research_error', sa.Text, nullable=True))


def downgrade() -> None:
    """Remove step-by-step research tracking fields from companies table."""
    op.drop_column('companies', 'research_status')
    op.drop_column('companies', 'research_step_1_basic')
    op.drop_column('companies', 'research_step_2_strategic')
    op.drop_column('companies', 'research_step_3_report')
    op.drop_column('companies', 'research_started_at')
    op.drop_column('companies', 'research_completed_at')
    op.drop_column('companies', 'research_error')
