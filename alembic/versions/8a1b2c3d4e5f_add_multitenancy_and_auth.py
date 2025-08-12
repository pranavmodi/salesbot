"""add_multitenancy_and_auth

Revision ID: 8a1b2c3d4e5f
Revises: 507ede199c3f
Create Date: 2025-08-10 10:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8a1b2c3d4e5f'
down_revision: Union[str, None] = '507ede199c3f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tenants table
    op.create_table(
        'tenants',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('slug', sa.String(100), nullable=False, unique=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('settings', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    # Users table (Google auth)
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('avatar_url', sa.String(512), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.UniqueConstraint('tenant_id', 'email', name='uq_users_tenant_email'),
    )

    # Add tenant_id to key tables
    tables = [
        'companies', 'contacts', 'campaigns', 'campaign_email_jobs', 'email_history', 'email_tracking', 'report_clicks'
    ]
    for table in tables:
        op.add_column(table, sa.Column('tenant_id', sa.UUID(as_uuid=True), nullable=True))
        op.create_index(f'ix_{table}_tenant_id', table, ['tenant_id'])

    # Backfill existing rows with a default tenant
    # Create default tenant
    op.execute("""
        INSERT INTO tenants (slug, name) VALUES ('default', 'Default Tenant')
        ON CONFLICT (slug) DO NOTHING
    """)
    # Assign default tenant to existing rows
    # Fetch default tenant id and assign per table (separate statements; some DBs don't keep CTE across statements)
    op.execute("""
        DO $$
        DECLARE tid uuid;
        BEGIN
          SELECT id INTO tid FROM tenants WHERE slug = 'default' LIMIT 1;
          UPDATE companies SET tenant_id = tid WHERE tenant_id IS NULL;
          UPDATE contacts SET tenant_id = tid WHERE tenant_id IS NULL;
          UPDATE campaigns SET tenant_id = tid WHERE tenant_id IS NULL;
          UPDATE campaign_email_jobs SET tenant_id = tid WHERE tenant_id IS NULL;
          UPDATE email_history SET tenant_id = tid WHERE tenant_id IS NULL;
          UPDATE email_tracking SET tenant_id = tid WHERE tenant_id IS NULL;
          UPDATE report_clicks SET tenant_id = tid WHERE tenant_id IS NULL;
        END $$;
    """)

    # Set NOT NULL after backfill
    for table in tables:
        op.alter_column(table, 'tenant_id', nullable=False)

    # Add example composite unique constraints where appropriate
    op.create_unique_constraint('uq_companies_tenant_name', 'companies', ['tenant_id', 'company_name'])


def downgrade() -> None:
    # Drop unique constraints and columns
    op.drop_constraint('uq_companies_tenant_name', 'companies', type_='unique')

    tables = [
        'companies', 'contacts', 'campaigns', 'campaign_email_jobs', 'email_history', 'email_tracking', 'report_clicks'
    ]
    for table in tables:
        op.drop_index(f'ix_{table}_tenant_id', table_name=table)
        op.drop_column(table, 'tenant_id')

    op.drop_table('users')
    op.drop_table('tenants')


