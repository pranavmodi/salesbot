"""create_email_template_configuration_tables

Revision ID: ef4fa7b86584
Revises: 7e999ce7afc9
Create Date: 2025-09-06 14:36:54.405578

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ef4fa7b86584'
down_revision: Union[str, None] = '7e999ce7afc9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create email_templates table
    op.create_table('email_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('is_default', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('message_framework', sa.Enum('AIDA', 'PAS', 'PROBLEM_SOLUTION', 'STORYTELLING', 'DIRECT', 'CONSULTATIVE', name='messageframework'), nullable=True),
        sa.Column('tone_level', sa.Enum('FORMAL', 'SEMI_FORMAL', 'CASUAL', 'CONVERSATIONAL', name='tonelevel'), nullable=True),
        sa.Column('email_length', sa.Enum('SHORT', 'MEDIUM', 'LONG', name='emaillength'), nullable=True),
        sa.Column('subject_templates', sa.JSON(), nullable=True),
        sa.Column('subject_ab_test', sa.Boolean(), nullable=True, default=False),
        sa.Column('opening_style', sa.String(50), nullable=True, default='personal'),
        sa.Column('opening_templates', sa.JSON(), nullable=True),
        sa.Column('use_personal_connection', sa.Boolean(), nullable=True, default=True),
        sa.Column('reference_company_research', sa.Boolean(), nullable=True, default=True),
        sa.Column('value_propositions', sa.JSON(), nullable=True),
        sa.Column('pain_points', sa.JSON(), nullable=True),
        sa.Column('social_proof_elements', sa.JSON(), nullable=True),
        sa.Column('product_details', sa.JSON(), nullable=True),
        sa.Column('personalization_fields', sa.JSON(), nullable=True),
        sa.Column('industry_customization', sa.JSON(), nullable=True),
        sa.Column('role_customization', sa.JSON(), nullable=True),
        sa.Column('cta_type', sa.Enum('MEETING', 'DEMO', 'CALL', 'TRIAL', 'DOWNLOAD', 'WEBSITE', 'REPLY', name='ctatype'), nullable=True),
        sa.Column('cta_templates', sa.JSON(), nullable=True),
        sa.Column('meeting_duration_options', sa.JSON(), nullable=True),
        sa.Column('calendar_booking_url', sa.String(500), nullable=True),
        sa.Column('urgency_elements', sa.JSON(), nullable=True),
        sa.Column('closing_templates', sa.JSON(), nullable=True),
        sa.Column('signature_template', sa.Text(), nullable=True),
        sa.Column('include_unsubscribe', sa.Boolean(), nullable=True, default=True),
        sa.Column('gdpr_compliance_text', sa.Text(), nullable=True),
        sa.Column('legal_disclaimers', sa.JSON(), nullable=True),
        sa.Column('industry_compliance', sa.JSON(), nullable=True),
        sa.Column('sender_name', sa.String(255), nullable=True),
        sa.Column('sender_title', sa.String(255), nullable=True),
        sa.Column('sender_company', sa.String(255), nullable=True),
        sa.Column('sender_contact_info', sa.JSON(), nullable=True),
        sa.Column('sender_personal_touch', sa.Text(), nullable=True),
        sa.Column('enable_ab_testing', sa.Boolean(), nullable=True, default=False),
        sa.Column('ab_test_elements', sa.JSON(), nullable=True),
        sa.Column('follow_up_sequence', sa.JSON(), nullable=True),
        sa.Column('max_follow_ups', sa.Integer(), nullable=True, default=3),
        sa.Column('follow_up_intervals', sa.JSON(), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=True, default=0),
        sa.Column('success_metrics', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_email_templates_tenant_id', 'email_templates', ['tenant_id'])

    # Create email_template_usage table
    op.create_table('email_template_usage',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('contact_email', sa.String(255), nullable=False),
        sa.Column('generated_subject', sa.String(500), nullable=True),
        sa.Column('generated_body', sa.Text(), nullable=True),
        sa.Column('personalization_data', sa.JSON(), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('opened_at', sa.DateTime(), nullable=True),
        sa.Column('clicked_at', sa.DateTime(), nullable=True),
        sa.Column('replied_at', sa.DateTime(), nullable=True),
        sa.Column('bounced_at', sa.DateTime(), nullable=True),
        sa.Column('ab_test_variant', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['template_id'], ['email_templates.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_email_template_usage_tenant_id', 'email_template_usage', ['tenant_id'])

    # Create industry_templates table
    op.create_table('industry_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('industry_name', sa.String(255), nullable=False),
        sa.Column('pain_points', sa.JSON(), nullable=True),
        sa.Column('value_props', sa.JSON(), nullable=True),
        sa.Column('case_studies', sa.JSON(), nullable=True),
        sa.Column('compliance_requirements', sa.JSON(), nullable=True),
        sa.Column('terminology', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_industry_templates_tenant_id', 'industry_templates', ['tenant_id'])

    # Create role_templates table
    op.create_table('role_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('role_name', sa.String(255), nullable=False),
        sa.Column('role_level', sa.String(50), nullable=True),
        sa.Column('pain_points', sa.JSON(), nullable=True),
        sa.Column('motivations', sa.JSON(), nullable=True),
        sa.Column('preferred_tone', sa.Enum('FORMAL', 'SEMI_FORMAL', 'CASUAL', 'CONVERSATIONAL', name='tonelevel'), nullable=True),
        sa.Column('preferred_length', sa.Enum('SHORT', 'MEDIUM', 'LONG', name='emaillength'), nullable=True),
        sa.Column('best_cta_types', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_role_templates_tenant_id', 'role_templates', ['tenant_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_role_templates_tenant_id', table_name='role_templates')
    op.drop_table('role_templates')
    op.drop_index('ix_industry_templates_tenant_id', table_name='industry_templates')
    op.drop_table('industry_templates')
    op.drop_index('ix_email_template_usage_tenant_id', table_name='email_template_usage')
    op.drop_table('email_template_usage')
    op.drop_index('ix_email_templates_tenant_id', table_name='email_templates')
    op.drop_table('email_templates')
