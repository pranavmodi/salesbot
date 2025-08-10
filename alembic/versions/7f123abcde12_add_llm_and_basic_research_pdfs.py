"""add_llm_and_basic_research_pdfs

Revision ID: 7f123abcde12
Revises: 2857f2a9a178
Create Date: 2025-08-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f123abcde12'
down_revision: Union[str, None] = '2857f2a9a178'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add PDF storage columns for LLM final report and basic research."""
    with op.batch_alter_table('companies') as batch_op:
        # Final LLM report PDF (base64)
        batch_op.add_column(sa.Column('llm_pdf_report_base64', sa.Text, nullable=True, comment='LLM generated final report PDF (base64)'))
        # Basic research PDF (base64)
        batch_op.add_column(sa.Column('basic_research_pdf_base64', sa.Text, nullable=True, comment='Basic research (step 1) PDF (base64)'))


def downgrade() -> None:
    """Remove added PDF columns."""
    with op.batch_alter_table('companies') as batch_op:
        batch_op.drop_column('basic_research_pdf_base64')
        batch_op.drop_column('llm_pdf_report_base64')


