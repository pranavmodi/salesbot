"""add_email_status_standardization

Revision ID: 936332f868ca
Revises: 754ad6928cd8
Create Date: 2025-07-06 10:37:21.651013

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '936332f868ca'
down_revision: Union[str, None] = '754ad6928cd8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add new columns for standardized email status tracking
    op.add_column('email_history', sa.Column('sent_via', sa.String(255), nullable=True))
    op.add_column('email_history', sa.Column('email_type', sa.String(50), nullable=True, default='campaign'))
    op.add_column('email_history', sa.Column('error_details', sa.Text(), nullable=True))
    
    # Standardize existing status values and populate new fields
    # Convert old status format to new standardized format
    op.execute("""
        UPDATE email_history 
        SET 
            status = CASE 
                WHEN status LIKE 'Success%' THEN 'sent'
                WHEN status LIKE 'Failed%' THEN 'failed'
                WHEN status = 'Success' THEN 'sent'
                WHEN status = 'Failed' THEN 'failed'
                ELSE 'unknown'
            END,
            sent_via = CASE 
                WHEN status LIKE '%via %' THEN 
                    SUBSTRING(status FROM 'via ([^)]+)')
                ELSE NULL
            END,
            email_type = CASE 
                WHEN status LIKE '%Test Email%' THEN 'test'
                WHEN campaign_id IS NOT NULL THEN 'campaign'
                ELSE 'manual'
            END
        WHERE status IS NOT NULL;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove the new columns
    op.drop_column('email_history', 'error_details')
    op.drop_column('email_history', 'email_type')
    op.drop_column('email_history', 'sent_via')
    
    # Restore old status format (best effort)
    op.execute("""
        UPDATE email_history 
        SET status = CASE 
            WHEN status = 'sent' AND sent_via IS NOT NULL THEN 'Success (via ' || sent_via || ')'
            WHEN status = 'sent' THEN 'Success'
            WHEN status = 'failed' AND sent_via IS NOT NULL THEN 'Failed (via ' || sent_via || ')'
            WHEN status = 'failed' THEN 'Failed'
            ELSE status
        END;
    """)
