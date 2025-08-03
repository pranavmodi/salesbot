"""add_llm_research_fields_to_companies

Revision ID: 5ab16ca41301
Revises: 31c6874391f2
Create Date: 2025-08-03 08:40:41.409386

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5ab16ca41301'
down_revision: Union[str, None] = '31c6874391f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add LLM research fields to companies table."""
    # Add LLM research fields to support general deep research functionality
    op.add_column('companies', sa.Column('llm_research_prompt', sa.Text, nullable=True, comment='Research prompt for LLM deep research'))
    op.add_column('companies', sa.Column('llm_research_results', sa.Text, nullable=True, comment='Raw research results from LLM'))
    op.add_column('companies', sa.Column('llm_research_status', sa.String(50), nullable=True, comment='Status: not_started, prompt_ready, completed, failed'))
    op.add_column('companies', sa.Column('llm_research_method', sa.String(100), nullable=True, comment='Research method: claude_deep_research, openai_deep_research, etc.'))
    op.add_column('companies', sa.Column('llm_research_word_count', sa.Integer, nullable=True, comment='Word count of research results'))
    op.add_column('companies', sa.Column('llm_research_character_count', sa.Integer, nullable=True, comment='Character count of research results'))
    op.add_column('companies', sa.Column('llm_research_quality_score', sa.Integer, nullable=True, comment='Quality score from 0-100'))
    op.add_column('companies', sa.Column('llm_research_updated_at', sa.DateTime, nullable=True, comment='Last updated timestamp for LLM research'))


def downgrade() -> None:
    """Remove LLM research fields from companies table."""
    op.drop_column('companies', 'llm_research_updated_at')
    op.drop_column('companies', 'llm_research_quality_score')
    op.drop_column('companies', 'llm_research_character_count')
    op.drop_column('companies', 'llm_research_word_count')
    op.drop_column('companies', 'llm_research_method')
    op.drop_column('companies', 'llm_research_status')
    op.drop_column('companies', 'llm_research_results')
    op.drop_column('companies', 'llm_research_prompt')
