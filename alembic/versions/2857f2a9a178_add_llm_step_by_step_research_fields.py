"""add_llm_step_by_step_research_fields

Revision ID: 2857f2a9a178
Revises: 5ab16ca41301
Create Date: 2025-08-03 09:10:21.830008

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2857f2a9a178'
down_revision: Union[str, None] = '5ab16ca41301'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add LLM step-by-step research fields to companies table."""
    # Add LLM step-by-step research fields
    op.add_column('companies', sa.Column('llm_research_step_1_basic', sa.Text, nullable=True, comment='LLM basic research step results'))
    op.add_column('companies', sa.Column('llm_research_step_2_strategic', sa.Text, nullable=True, comment='LLM strategic analysis step results'))
    op.add_column('companies', sa.Column('llm_research_step_3_report', sa.Text, nullable=True, comment='LLM final report step results'))
    op.add_column('companies', sa.Column('llm_markdown_report', sa.Text, nullable=True, comment='LLM generated markdown report'))
    op.add_column('companies', sa.Column('llm_html_report', sa.Text, nullable=True, comment='LLM generated HTML report'))
    op.add_column('companies', sa.Column('llm_research_step_status', sa.String(50), nullable=True, comment='Current LLM research step: step_1, step_2, step_3, completed'))
    op.add_column('companies', sa.Column('llm_research_provider', sa.String(50), nullable=True, comment='LLM provider used: claude, openai, etc.'))
    op.add_column('companies', sa.Column('llm_research_started_at', sa.DateTime, nullable=True, comment='LLM research start timestamp'))
    op.add_column('companies', sa.Column('llm_research_completed_at', sa.DateTime, nullable=True, comment='LLM research completion timestamp'))


def downgrade() -> None:
    """Remove LLM step-by-step research fields from companies table."""
    op.drop_column('companies', 'llm_research_completed_at')
    op.drop_column('companies', 'llm_research_started_at')
    op.drop_column('companies', 'llm_research_provider')
    op.drop_column('companies', 'llm_research_step_status')
    op.drop_column('companies', 'llm_html_report')
    op.drop_column('companies', 'llm_markdown_report')
    op.drop_column('companies', 'llm_research_step_3_report')
    op.drop_column('companies', 'llm_research_step_2_strategic')
    op.drop_column('companies', 'llm_research_step_1_basic')
