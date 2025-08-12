"""create_tenant_settings_table

Revision ID: 683c7101eeb3
Revises: 74e01c22005a
Create Date: 2025-08-12 15:50:11.770195

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '683c7101eeb3'
down_revision: Union[str, None] = '74e01c22005a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create tenant_settings table
    op.create_table('tenant_settings',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.dialects.postgresql.UUID, nullable=False),
        
        # Email Configuration (encrypted)
        sa.Column('email_configs_encrypted', sa.Text, nullable=True),
        
        # API Keys (encrypted)
        sa.Column('openai_api_key_encrypted', sa.Text, nullable=True),
        sa.Column('anthropic_api_key_encrypted', sa.Text, nullable=True),
        sa.Column('perplexity_api_key_encrypted', sa.Text, nullable=True),
        
        # Other settings (JSON)
        sa.Column('other_settings', sa.JSON, nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        
        # Foreign key constraint
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        
        # Indexes
        sa.Index('ix_tenant_settings_tenant_id', 'tenant_id', unique=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('tenant_settings')
