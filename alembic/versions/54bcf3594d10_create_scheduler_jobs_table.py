"""create_scheduler_jobs_table

Revision ID: 54bcf3594d10
Revises: 43c31049fc87
Create Date: 2025-06-28 09:33:45.389763

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '54bcf3594d10'
down_revision: Union[str, None] = '43c31049fc87'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create scheduler_jobs table for APScheduler."""
    op.create_table(
        'scheduler_jobs',
        sa.Column('id', sa.String(191), primary_key=True),
        sa.Column('next_run_time', sa.Float(25), nullable=True, index=True),
        sa.Column('job_state', sa.LargeBinary, nullable=False)
    )


def downgrade() -> None:
    """Drop scheduler_jobs table."""
    op.drop_table('scheduler_jobs')
