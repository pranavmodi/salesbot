"""Add leadgen tables for lead generation functionality

Revision ID: cad7507811f6
Revises: fdda8270b504
Create Date: 2025-09-04 11:27:57.932120

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cad7507811f6'
down_revision: Union[str, None] = 'fdda8270b504'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create leadgen_companies table
    op.create_table('leadgen_companies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('domain', sa.String(length=255), nullable=True),
        sa.Column('industry', sa.String(length=255), nullable=True),
        sa.Column('employee_count', sa.Integer(), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('founded_year', sa.Integer(), nullable=True),
        sa.Column('technology_stack', sa.JSON(), nullable=True),
        sa.Column('linkedin_url', sa.String(length=500), nullable=True),
        sa.Column('source', sa.String(length=100), nullable=False, server_default='unknown'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('ats_scraped', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('ats_scraped_at', sa.DateTime(), nullable=True),
        sa.Column('last_scrape_status', sa.String(length=50), nullable=True),
        sa.Column('support_roles_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sales_roles_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ai_roles_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('lead_score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_qualified_lead', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('support_intensity_score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('digital_presence_score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('growth_signals_score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('implementation_feasibility_score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('lead_scoring_data', sa.JSON(), nullable=True),
        sa.Column('lead_scored_at', sa.DateTime(), nullable=True),
        sa.Column('tenant_id', sa.String(length=255), nullable=True),
        sa.Column('tenant_created_at', sa.DateTime(), nullable=True),
        sa.Column('salesbot_tenant_id', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_leadgen_companies_domain'), 'leadgen_companies', ['domain'], unique=False)
    op.create_index(op.f('ix_leadgen_companies_employee_count'), 'leadgen_companies', ['employee_count'], unique=False)
    op.create_index(op.f('ix_leadgen_companies_id'), 'leadgen_companies', ['id'], unique=False)
    op.create_index(op.f('ix_leadgen_companies_industry'), 'leadgen_companies', ['industry'], unique=False)
    op.create_index(op.f('ix_leadgen_companies_name'), 'leadgen_companies', ['name'], unique=False)
    op.create_index(op.f('ix_leadgen_companies_salesbot_tenant_id'), 'leadgen_companies', ['salesbot_tenant_id'], unique=False)
    op.create_index(op.f('ix_leadgen_companies_source'), 'leadgen_companies', ['source'], unique=False)

    # Create leadgen_seeding_sessions table
    op.create_table('leadgen_seeding_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(length=255), nullable=False),
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='in_progress'),
        sa.Column('companies_found', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('companies_imported', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('salesbot_tenant_id', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id')
    )
    op.create_index(op.f('ix_leadgen_seeding_sessions_id'), 'leadgen_seeding_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_leadgen_seeding_sessions_salesbot_tenant_id'), 'leadgen_seeding_sessions', ['salesbot_tenant_id'], unique=False)
    op.create_index(op.f('ix_leadgen_seeding_sessions_session_id'), 'leadgen_seeding_sessions', ['session_id'], unique=False)

    # Create leadgen_job_postings table
    op.create_table('leadgen_job_postings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('external_id', sa.String(length=255), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('department', sa.String(length=255), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('requirements', sa.Text(), nullable=True),
        sa.Column('job_url', sa.String(length=1000), nullable=True),
        sa.Column('role_category', sa.String(length=100), nullable=True),
        sa.Column('seniority_level', sa.String(length=100), nullable=True),
        sa.Column('ats_source', sa.String(length=100), nullable=False),
        sa.Column('posted_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('salesbot_tenant_id', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['leadgen_companies.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_leadgen_job_postings_ats_source'), 'leadgen_job_postings', ['ats_source'], unique=False)
    op.create_index(op.f('ix_leadgen_job_postings_department'), 'leadgen_job_postings', ['department'], unique=False)
    op.create_index(op.f('ix_leadgen_job_postings_external_id'), 'leadgen_job_postings', ['external_id'], unique=False)
    op.create_index(op.f('ix_leadgen_job_postings_id'), 'leadgen_job_postings', ['id'], unique=False)
    op.create_index(op.f('ix_leadgen_job_postings_role_category'), 'leadgen_job_postings', ['role_category'], unique=False)
    op.create_index(op.f('ix_leadgen_job_postings_salesbot_tenant_id'), 'leadgen_job_postings', ['salesbot_tenant_id'], unique=False)

    # Create leadgen_scraping_logs table
    op.create_table('leadgen_scraping_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.String(length=255), nullable=True),
        sa.Column('ats_source', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('jobs_found', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('scraping_metadata', sa.JSON(), nullable=True),
        sa.Column('salesbot_tenant_id', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['leadgen_companies.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_leadgen_scraping_logs_id'), 'leadgen_scraping_logs', ['id'], unique=False)
    op.create_index(op.f('ix_leadgen_scraping_logs_salesbot_tenant_id'), 'leadgen_scraping_logs', ['salesbot_tenant_id'], unique=False)
    op.create_index(op.f('ix_leadgen_scraping_logs_status'), 'leadgen_scraping_logs', ['status'], unique=False)
    op.create_index(op.f('ix_leadgen_scraping_logs_task_id'), 'leadgen_scraping_logs', ['task_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop tables in reverse order (child tables first due to foreign keys)
    op.drop_table('leadgen_scraping_logs')
    op.drop_table('leadgen_job_postings')
    op.drop_table('leadgen_seeding_sessions')
    op.drop_table('leadgen_companies')
