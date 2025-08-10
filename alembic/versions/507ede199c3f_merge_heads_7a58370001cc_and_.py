"""merge heads 7a58370001cc and 7f123abcde12

Revision ID: 507ede199c3f
Revises: 7a58370001cc, 7f123abcde12
Create Date: 2025-08-10 08:45:25.703590

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '507ede199c3f'
down_revision: Union[str, None] = ('7a58370001cc', '7f123abcde12')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
