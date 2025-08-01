"""convert_agent_recommendations_to_json

Revision ID: 31c6874391f2
Revises: 406030e6b390
Create Date: 2025-08-01 12:52:47.181821

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '31c6874391f2'
down_revision: Union[str, None] = '406030e6b390'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add ai_agent_recommendations JSON field and migrate existing data."""
    # Add new JSON field for structured AI agent recommendations
    op.add_column('companies', sa.Column('ai_agent_recommendations', sa.JSON, nullable=True))
    
    # Migrate existing text data to JSON format (if any)
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE companies 
        SET ai_agent_recommendations = CASE 
            WHEN agent_recommendations IS NOT NULL AND agent_recommendations != '' 
            THEN jsonb_build_array(jsonb_build_object('recommendation', agent_recommendations))
            ELSE NULL 
        END
        WHERE ai_agent_recommendations IS NULL
    """))


def downgrade() -> None:
    """Remove ai_agent_recommendations JSON field."""
    op.drop_column('companies', 'ai_agent_recommendations')
