"""create_email_history_table

Revision ID: aba854ab6f1f
Revises: 
Create Date: 2024-05-15 14:45:12.123456 # Placeholder, will be updated by Alembic

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aba854ab6f1f'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'email_history',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('date', sa.DateTime, nullable=False),
        sa.Column('to', sa.String, nullable=False),
        sa.Column('subject', sa.String, nullable=False),
        sa.Column('body', sa.Text, nullable=False),
        sa.Column('status', sa.String, nullable=False)
    )


def downgrade() -> None:
    op.drop_table('email_history')
