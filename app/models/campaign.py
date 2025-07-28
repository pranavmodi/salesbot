from datetime import datetime
from typing import List, Dict, Optional
from flask import current_app
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import os
import logging
import json

class Campaign:
    """Campaign model for managing email campaign data."""
    
    def __init__(self, name=None, type=None, description='', email_template=None, 
                 priority='medium', schedule_date=None, followup_days=3, 
                 selection_criteria=None, campaign_settings=None, **kwargs):
        # Handle both dict-style and keyword initialization
        if isinstance(name, dict):
            data = name
            self.id = data.get('id')
            self.name = data.get('name', '')
            self.type = data.get('type', '')
            self.description = data.get('description', '')
            self.email_template = data.get('email_template', '')
            self.priority = data.get('priority', 'medium')
            self.schedule_date = data.get('schedule_date')
            self.followup_days = data.get('followup_days', 3)
            self.selection_criteria = data.get('selection_criteria', '{}')
            self.campaign_settings = data.get('campaign_settings', '{}')
            self.status = data.get('status', 'draft')  # draft, active, paused, completed
            self.created_at = data.get('created_at')
            self.updated_at = data.get('updated_at')
        else:
            # Direct parameter initialization
            self.id = kwargs.get('id')
            self.name = name or ''
            self.type = type or ''
            self.description = description
            self.email_template = email_template or ''
            self.priority = priority
            self.schedule_date = schedule_date
            self.followup_days = followup_days
            self.selection_criteria = selection_criteria or '{}'
            self.campaign_settings = campaign_settings or '{}'
            self.status = kwargs.get('status', 'draft')
            self.created_at = kwargs.get('created_at')
            self.updated_at = kwargs.get('updated_at')
    
    @property
    def selection_criteria_dict(self):
        """Parse selection criteria JSON string to dict."""
        try:
            if isinstance(self.selection_criteria, str):
                return json.loads(self.selection_criteria)
            return self.selection_criteria or {}
        except (json.JSONDecodeError, TypeError):
            return {}

    @staticmethod
    def _get_db_engine():
        """Get database engine from environment."""
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            current_app.logger.error("DATABASE_URL not configured.")
            return None
        try:
            return create_engine(
                database_url,
                pool_size=1,          # Reduced: Maximum number of permanent connections
                max_overflow=2,       # Reduced: Maximum number of overflow connections  
                pool_pre_ping=True,   # Verify connections before use
                pool_recycle=1800     # Recycle connections every 30 minutes
            )
        except Exception as e:
            current_app.logger.error(f"Error creating database engine: {e}")
            return None

    @classmethod
    def load_all(cls) -> List['Campaign']:
        """Load all campaigns from PostgreSQL database."""
        campaigns = []
        engine = cls._get_db_engine()
        if not engine:
            current_app.logger.error("No database engine available")
            return campaigns
            
        try:
            with engine.connect() as conn:
                current_app.logger.info("Loading campaigns with full schema...")
                result = conn.execute(text("""
                    SELECT id, name, type, description, email_template, priority, 
                           schedule_date, followup_days, selection_criteria, campaign_settings, 
                           status, created_at, updated_at
                    FROM campaigns 
                    ORDER BY created_at DESC
                """))
                
                row_count = 0
                for row in result:
                    row_count += 1
                    campaign_data = dict(row._mapping)
                    current_app.logger.info(f"Processing campaign row {row_count}: {campaign_data}")
                    campaigns.append(cls(campaign_data))
                
                current_app.logger.info(f"Loaded {len(campaigns)} campaigns successfully")
                    
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error loading campaigns from database: {e}")
        except Exception as e:
            current_app.logger.error(f"Unexpected error loading campaigns: {e}")
            
        return campaigns

    @classmethod
    def get_active_campaigns(cls) -> List['Campaign']:
        """Load only active campaigns."""
        campaigns = []
        engine = cls._get_db_engine()
        if not engine:
            return campaigns
            
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, name, type, description, email_template, priority, 
                           schedule_date, followup_days, selection_criteria, status, 
                           created_at, updated_at
                    FROM campaigns 
                    WHERE status = 'active'
                    ORDER BY created_at DESC
                """))
                
                for row in result:
                    campaign_data = dict(row._mapping)
                    campaigns.append(cls(campaign_data))
                    
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error loading active campaigns: {e}")
        except Exception as e:
            current_app.logger.error(f"Unexpected error loading active campaigns: {e}")
            
        return campaigns

    @classmethod
    def get_by_id(cls, campaign_id: int) -> Optional['Campaign']:
        """Get a campaign by ID."""
        engine = cls._get_db_engine()
        if not engine:
            return None
            
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, name, type, description, email_template, priority, 
                           schedule_date, followup_days, selection_criteria, status, 
                           created_at, updated_at
                    FROM campaigns 
                    WHERE id = :id
                """), {"id": campaign_id})
                
                row = result.fetchone()
                if row:
                    campaign_data = dict(row._mapping)
                    return cls(campaign_data)
                    
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error getting campaign by ID: {e}")
        except Exception as e:
            current_app.logger.error(f"Unexpected error getting campaign by ID: {e}")
            
        return None

    @classmethod
    def save(cls, campaign_data: Dict) -> bool:
        """Save a new campaign to the database."""
        engine = cls._get_db_engine()
        if not engine:
            current_app.logger.error("Failed to save campaign: Database engine not available.")
            return False

        try:
            with engine.connect() as conn:
                with conn.begin():
                    insert_query = text("""
                        INSERT INTO campaigns (name, type, description, email_template, 
                                             priority, schedule_date, followup_days, 
                                             selection_criteria, status) 
                        VALUES (:name, :type, :description, :email_template, 
                               :priority, :schedule_date, :followup_days, 
                               :selection_criteria, :status)
                    """)
                    conn.execute(insert_query, {
                        'name': campaign_data['name'],
                        'type': campaign_data.get('type', 'cold_outreach'),
                        'description': campaign_data.get('description', ''),
                        'email_template': campaign_data.get('email_template', 'deep_research'),
                        'priority': campaign_data.get('priority', 'medium'),
                        'schedule_date': campaign_data.get('schedule_date'),
                        'followup_days': campaign_data.get('followup_days', 3),
                        'selection_criteria': campaign_data.get('selection_criteria', '{}'),
                        'status': campaign_data.get('status', 'draft')
                    })
            current_app.logger.info(f"Successfully saved campaign: {campaign_data['name']}")
            return True
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error saving campaign: {e}")
            return False
        except Exception as e:
            current_app.logger.error(f"Unexpected error saving campaign: {e}")
            return False

    @classmethod
    def update(cls, campaign_id: int, campaign_data: Dict) -> bool:
        """Update an existing campaign in the database."""
        engine = cls._get_db_engine()
        if not engine:
            current_app.logger.error("Failed to update campaign: Database engine not available.")
            return False

        try:
            with engine.connect() as conn:
                with conn.begin():
                    update_query = text("""
                        UPDATE campaigns 
                        SET name = :name, 
                            type = :type,
                            description = :description, 
                            email_template = :email_template,
                            priority = :priority,
                            schedule_date = :schedule_date,
                            followup_days = :followup_days,
                            selection_criteria = :selection_criteria,
                            status = :status,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :id
                    """)
                    result = conn.execute(update_query, {
                        'id': campaign_id,
                        'name': campaign_data['name'],
                        'type': campaign_data.get('type', ''),
                        'description': campaign_data.get('description', ''),
                        'email_template': campaign_data.get('email_template', ''),
                        'priority': campaign_data.get('priority', 'medium'),
                        'schedule_date': campaign_data.get('schedule_date'),
                        'followup_days': campaign_data.get('followup_days', 3),
                        'selection_criteria': campaign_data.get('selection_criteria', '{}'),
                        'status': campaign_data.get('status', 'active')
                    })
                    
                    if result.rowcount > 0:
                        current_app.logger.info(f"Successfully updated campaign ID: {campaign_id}")
                        return True
                    else:
                        current_app.logger.warning(f"No campaign found with ID: {campaign_id}")
                        return False
                        
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error updating campaign: {e}")
            return False
        except Exception as e:
            current_app.logger.error(f"Unexpected error updating campaign: {e}")
            return False

    @classmethod
    def delete(cls, campaign_id: int) -> bool:
        """Delete a campaign from the database."""
        engine = cls._get_db_engine()
        if not engine:
            current_app.logger.error("Failed to delete campaign: Database engine not available.")
            return False

        try:
            with engine.connect() as conn:
                with conn.begin():
                    delete_query = text("DELETE FROM campaigns WHERE id = :id")
                    result = conn.execute(delete_query, {"id": campaign_id})
                    
                    if result.rowcount > 0:
                        current_app.logger.info(f"Successfully deleted campaign ID: {campaign_id}")
                        return True
                    else:
                        current_app.logger.warning(f"No campaign found with ID: {campaign_id}")
                        return False
                        
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error deleting campaign: {e}")
            return False
        except Exception as e:
            current_app.logger.error(f"Unexpected error deleting campaign: {e}")
            return False

    @classmethod
    def get_campaign_stats(cls, campaign_id: int) -> Dict:
        """Get statistics for a specific campaign."""
        engine = cls._get_db_engine()
        if not engine:
            return {}
            
        try:
            with engine.connect() as conn:
                # Get email stats with standardized status values
                email_result = conn.execute(text("""
                    SELECT 
                        COUNT(*) as total_emails,
                        COUNT(CASE WHEN status = 'sent' THEN 1 END) as sent_emails,
                        COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_emails,
                        COUNT(DISTINCT "to") as unique_recipients,
                        MIN(date) as first_email_date,
                        MAX(date) as last_email_date
                    FROM email_history 
                    WHERE campaign_id = :campaign_id
                """), {"campaign_id": campaign_id})
                
                # Get contact stats
                contact_result = conn.execute(text("""
                    SELECT 
                        COUNT(*) as total_contacts,
                        COUNT(CASE WHEN status = 'active' THEN 1 END) as active_contacts,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_contacts,
                        COUNT(CASE WHEN status = 'paused' THEN 1 END) as paused_contacts
                    FROM campaign_contacts 
                    WHERE campaign_id = :campaign_id
                """), {"campaign_id": campaign_id})
                
                email_row = email_result.fetchone()
                contact_row = contact_result.fetchone()
                
                stats = {
                    'total_emails': email_row.total_emails or 0 if email_row else 0,
                    'sent_emails': email_row.sent_emails or 0 if email_row else 0,
                    'failed_emails': email_row.failed_emails or 0 if email_row else 0,
                    'unique_recipients': email_row.unique_recipients or 0 if email_row else 0,
                    'first_email_date': email_row.first_email_date if email_row else None,
                    'last_email_date': email_row.last_email_date if email_row else None,
                    'total_contacts': contact_row.total_contacts or 0 if contact_row else 0,
                    'active_contacts': contact_row.active_contacts or 0 if contact_row else 0,
                    'completed_contacts': contact_row.completed_contacts or 0 if contact_row else 0,
                    'paused_contacts': contact_row.paused_contacts or 0 if contact_row else 0
                }
                
                # Calculate success rate
                if stats['total_emails'] > 0:
                    stats['success_rate'] = round((stats['sent_emails'] / stats['total_emails'] * 100), 2)
                else:
                    stats['success_rate'] = 0
                    
                return stats
                    
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error getting campaign stats: {e}")
        except Exception as e:
            current_app.logger.error(f"Unexpected error getting campaign stats: {e}")
            
        return {}

    @classmethod
    def add_contact_to_campaign(cls, campaign_id: int, contact_email: str, status: str = 'active') -> bool:
        """Add a contact to a campaign."""
        engine = cls._get_db_engine()
        if not engine:
            current_app.logger.error("Failed to add contact to campaign: Database engine not available.")
            return False

        try:
            with engine.connect() as conn:
                with conn.begin():
                    insert_query = text("""
                        INSERT INTO campaign_contacts (campaign_id, contact_email, status) 
                        VALUES (:campaign_id, :contact_email, :status)
                        ON CONFLICT (campaign_id, contact_email) 
                        DO UPDATE SET 
                            status = :status,
                            updated_at = CURRENT_TIMESTAMP
                    """)
                    conn.execute(insert_query, {
                        'campaign_id': campaign_id,
                        'contact_email': contact_email,
                        'status': status
                    })
            current_app.logger.info(f"Successfully added contact {contact_email} to campaign {campaign_id}")
            return True
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error adding contact to campaign: {e}")
            return False
        except Exception as e:
            current_app.logger.error(f"Unexpected error adding contact to campaign: {e}")
            return False

    @classmethod
    def remove_contact_from_campaign(cls, campaign_id: int, contact_email: str) -> bool:
        """Remove a contact from a campaign."""
        engine = cls._get_db_engine()
        if not engine:
            current_app.logger.error("Failed to remove contact from campaign: Database engine not available.")
            return False

        try:
            with engine.connect() as conn:
                with conn.begin():
                    delete_query = text("""
                        DELETE FROM campaign_contacts 
                        WHERE campaign_id = :campaign_id AND contact_email = :contact_email
                    """)
                    result = conn.execute(delete_query, {
                        'campaign_id': campaign_id,
                        'contact_email': contact_email
                    })
                    
                    if result.rowcount > 0:
                        current_app.logger.info(f"Successfully removed contact {contact_email} from campaign {campaign_id}")
                        return True
                    else:
                        current_app.logger.warning(f"Contact {contact_email} not found in campaign {campaign_id}")
                        return False
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error removing contact from campaign: {e}")
            return False
        except Exception as e:
            current_app.logger.error(f"Unexpected error removing contact from campaign: {e}")
            return False

    @classmethod
    def get_campaign_contacts(cls, campaign_id: int, status: str = None) -> List[Dict]:
        """Get all contacts in a campaign, optionally filtered by status."""
        engine = cls._get_db_engine()
        if not engine:
            return []
            
        try:
            with engine.connect() as conn:
                if status:
                    query = text("""
                        SELECT c.*, cc.status as campaign_status, cc.added_at, cc.updated_at as status_updated_at
                        FROM contacts c
                        JOIN campaign_contacts cc ON c.email = cc.contact_email
                        WHERE cc.campaign_id = :campaign_id AND cc.status = :status
                        ORDER BY cc.added_at DESC
                    """)
                    result = conn.execute(query, {"campaign_id": campaign_id, "status": status})
                else:
                    query = text("""
                        SELECT c.*, cc.status as campaign_status, cc.added_at, cc.updated_at as status_updated_at
                        FROM contacts c
                        JOIN campaign_contacts cc ON c.email = cc.contact_email
                        WHERE cc.campaign_id = :campaign_id
                        ORDER BY cc.added_at DESC
                    """)
                    result = conn.execute(query, {"campaign_id": campaign_id})
                
                contacts = []
                for row in result:
                    contact_data = dict(row._mapping)
                    contacts.append(contact_data)
                
                return contacts
                    
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error getting campaign contacts: {e}")
        except Exception as e:
            current_app.logger.error(f"Unexpected error getting campaign contacts: {e}")
            
        return []

    @classmethod
    def update_contact_status_in_campaign(cls, campaign_id: int, contact_email: str, status: str) -> bool:
        """Update a contact's status in a campaign."""
        engine = cls._get_db_engine()
        if not engine:
            current_app.logger.error("Failed to update contact status: Database engine not available.")
            return False

        try:
            with engine.connect() as conn:
                with conn.begin():
                    update_query = text("""
                        UPDATE campaign_contacts 
                        SET status = :status, updated_at = CURRENT_TIMESTAMP
                        WHERE campaign_id = :campaign_id AND contact_email = :contact_email
                    """)
                    result = conn.execute(update_query, {
                        'campaign_id': campaign_id,
                        'contact_email': contact_email,
                        'status': status
                    })
                    
                    if result.rowcount > 0:
                        current_app.logger.info(f"Successfully updated contact {contact_email} status to {status} in campaign {campaign_id}")
                        return True
                    else:
                        current_app.logger.warning(f"Contact {contact_email} not found in campaign {campaign_id}")
                        return False
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error updating contact status: {e}")
            return False
        except Exception as e:
            current_app.logger.error(f"Unexpected error updating contact status: {e}")
            return False

    @classmethod
    def bulk_add_contacts_to_campaign(cls, campaign_id: int, contact_emails: List[str], status: str = 'active') -> Dict:
        """Add multiple contacts to a campaign in bulk."""
        engine = cls._get_db_engine()
        if not engine:
            current_app.logger.error("Failed to bulk add contacts: Database engine not available.")
            return {'success': 0, 'failed': 0, 'errors': []}

        success_count = 0
        failed_count = 0
        errors = []

        try:
            with engine.connect() as conn:
                with conn.begin():
                    for contact_email in contact_emails:
                        try:
                            insert_query = text("""
                                INSERT INTO campaign_contacts (campaign_id, contact_email, status) 
                                VALUES (:campaign_id, :contact_email, :status)
                                ON CONFLICT (campaign_id, contact_email) 
                                DO UPDATE SET 
                                    status = :status,
                                    updated_at = CURRENT_TIMESTAMP
                            """)
                            conn.execute(insert_query, {
                                'campaign_id': campaign_id,
                                'contact_email': contact_email,
                                'status': status
                            })
                            success_count += 1
                        except Exception as e:
                            failed_count += 1
                            errors.append(f"Contact {contact_email}: {str(e)}")
            
            current_app.logger.info(f"Bulk add completed: {success_count} successful, {failed_count} failed")
            return {
                'success': success_count,
                'failed': failed_count,
                'errors': errors
            }
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error in bulk add: {e}")
            return {'success': 0, 'failed': len(contact_emails), 'errors': [str(e)]}
        except Exception as e:
            current_app.logger.error(f"Unexpected error in bulk add: {e}")
            return {'success': 0, 'failed': len(contact_emails), 'errors': [str(e)]}

    @classmethod
    def update_status(cls, campaign_id: int, status: str) -> bool:
        """Update campaign status."""
        engine = cls._get_db_engine()
        if not engine:
            current_app.logger.error("Failed to update campaign status: Database engine not available.")
            return False

        try:
            with engine.connect() as conn:
                with conn.begin():
                    update_query = text("""
                        UPDATE campaigns 
                        SET status = :status, updated_at = CURRENT_TIMESTAMP
                        WHERE id = :id
                    """)
                    result = conn.execute(update_query, {
                        'id': campaign_id,
                        'status': status
                    })
                    
                    if result.rowcount > 0:
                        current_app.logger.info(f"Successfully updated campaign {campaign_id} status to {status}")
                        return True
                    else:
                        current_app.logger.warning(f"No campaign found with ID: {campaign_id}")
                        return False
                        
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error updating campaign status: {e}")
            return False
        except Exception as e:
            current_app.logger.error(f"Unexpected error updating campaign status: {e}")
            return False

    @classmethod
    def get_campaign_settings(cls, campaign_id: int) -> Dict:
        """Get campaign settings, merging any stored settings with defaults."""
        engine = cls._get_db_engine()
        if not engine:
            return cls._get_default_settings()
            
        try:
            with engine.connect() as conn:
                # Get both the campaign_settings JSON and the email_template column
                result = conn.execute(text("""
                    SELECT campaign_settings, email_template
                    FROM campaigns 
                    WHERE id = :campaign_id
                """), {"campaign_id": campaign_id})
                
                row = result.fetchone()
                
                # Start with default settings
                default_settings = cls._get_default_settings()
                
                if row:
                    # Update email_template from the database column if available
                    if row[1]:  # email_template column
                        default_settings['email_template'] = row[1]
                    
                    # Update with stored JSON settings if available
                    if row[0]:  # campaign_settings column
                        try:
                            stored_settings = json.loads(row[0])
                            default_settings.update(stored_settings)
                        except (json.JSONDecodeError, TypeError):
                            current_app.logger.warning(f"Invalid JSON in campaign_settings for campaign {campaign_id}")
                
                return default_settings
                    
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error getting campaign settings: {e}")
            return cls._get_default_settings()
        except Exception as e:
            current_app.logger.error(f"Unexpected error getting campaign settings: {e}")
            return cls._get_default_settings()

    @classmethod
    def _get_default_settings(cls) -> Dict:
        """Get default campaign settings."""
        return {
            'email_template': 'deep_research',  # Changed default to deep_research
            'email_frequency': {'value': 30, 'unit': 'minutes'},
            'random_delay': {'min_minutes': 1, 'max_minutes': 5},
            'timezone': 'America/Los_Angeles',
            'daily_email_limit': 50,
            'respect_business_hours': True,
            'business_hours': {
                'start_time': '09:00',
                'end_time': '17:00',
                'days': {
                    'monday': True, 'tuesday': True, 'wednesday': True,
                    'thursday': True, 'friday': True, 'saturday': False, 'sunday': False
                }
            },
            'enable_spam_check': True,
            'enable_unsubscribe_link': True,
            'enable_tracking': True,
            'enable_personalization': True
        }

    @classmethod
    def create_campaign_with_settings(cls, campaign_data: Dict, settings: Dict, contacts: List[str]) -> Optional[int]:
        """Create a campaign with settings and contacts."""
        engine = cls._get_db_engine()
        if not engine:
            current_app.logger.error("Failed to create campaign: Database engine not available.")
            return None

        try:
            with engine.connect() as conn:
                with conn.begin():
                    # Insert campaign
                    insert_query = text("""
                        INSERT INTO campaigns (name, type, description, email_template, 
                                             priority, schedule_date, followup_days, 
                                             selection_criteria, status) 
                        VALUES (:name, :type, :description, :email_template, 
                               :priority, :schedule_date, :followup_days, 
                               :selection_criteria, :status)
                        RETURNING id
                    """)
                    result = conn.execute(insert_query, {
                        'name': campaign_data['name'],
                        'type': campaign_data.get('type', ''),
                        'description': campaign_data.get('description', ''),
                        'email_template': campaign_data.get('email_template', ''),
                        'priority': campaign_data.get('priority', 'medium'),
                        'schedule_date': campaign_data.get('schedule_date'),
                        'followup_days': campaign_data.get('followup_days', 3),
                        'selection_criteria': campaign_data.get('selection_criteria', '{}'),
                        'status': campaign_data.get('status', 'active')
                    })
                    
                    campaign_id = result.fetchone()[0]
                    
                    # Add contacts to campaign
                    if contacts:
                        for contact_email in contacts:
                            contact_query = text("""
                                INSERT INTO campaign_contacts (campaign_id, contact_email, status) 
                                VALUES (:campaign_id, :contact_email, :status)
                                ON CONFLICT (campaign_id, contact_email) 
                                DO UPDATE SET 
                                    status = :status,
                                    updated_at = CURRENT_TIMESTAMP
                            """)
                            conn.execute(contact_query, {
                                'campaign_id': campaign_id,
                                'contact_email': contact_email,
                                'status': 'active'
                            })
                    
                    current_app.logger.info(f"Successfully created campaign: {campaign_data['name']} with ID {campaign_id}")
                    return campaign_id
                    
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error creating campaign: {e}")
            return None
        except Exception as e:
            current_app.logger.error(f"Unexpected error creating campaign: {e}")
            return None

    def to_dict(self) -> Dict:
        """Convert campaign to dictionary for JSON serialization."""
        base_dict = {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'description': self.description,
            'email_template': self.email_template,
            'priority': self.priority,
            'schedule_date': self.schedule_date.isoformat() if isinstance(self.schedule_date, datetime) else str(self.schedule_date) if self.schedule_date else None,
            'followup_days': self.followup_days,
            'selection_criteria': self.selection_criteria,
            'status': self.status,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at) if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else str(self.updated_at) if self.updated_at else None
        }
        
        # Add email statistics if campaign has an ID
        if self.id:
            try:
                stats = self.get_campaign_stats(self.id)
                base_dict.update({
                    'emails_sent': stats.get('sent_emails', 0),
                    'total_emails': stats.get('total_emails', 0),
                    'failed_emails': stats.get('failed_emails', 0),
                    'success_rate': stats.get('success_rate', 0),
                    'target_contacts_count': stats.get('total_contacts', 0),
                    'active_contacts': stats.get('active_contacts', 0),
                    'responses_received': 0  # This would need to be calculated from a response tracking system
                })
            except Exception as e:
                current_app.logger.warning(f"Failed to get campaign stats for campaign {self.id}: {e}")
                # Provide default values if stats can't be retrieved
                base_dict.update({
                    'emails_sent': 0,
                    'total_emails': 0,
                    'failed_emails': 0,
                    'success_rate': 0,
                    'target_contacts_count': 0,
                    'active_contacts': 0,
                    'responses_received': 0
                })
        else:
            # For new campaigns without ID, provide default values
            base_dict.update({
                'emails_sent': 0,
                'total_emails': 0,
                'failed_emails': 0,
                'success_rate': 0,
                'target_contacts_count': 0,
                'active_contacts': 0,
                'responses_received': 0
            })
            
        return base_dict
    
    def save(self):
        """Save this campaign instance to the database."""
        engine = self._get_db_engine()
        if not engine:
            current_app.logger.error("Failed to save campaign: Database engine not available.")
            return False

        try:
            with engine.connect() as conn:
                with conn.begin():
                    if self.id:
                        # Update existing campaign
                        update_query = text("""
                            UPDATE campaigns 
                            SET name = :name, 
                                type = :type,
                                description = :description, 
                                email_template = :email_template,
                                priority = :priority,
                                schedule_date = :schedule_date,
                                followup_days = :followup_days,
                                selection_criteria = :selection_criteria,
                                campaign_settings = :campaign_settings,
                                status = :status,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = :id
                        """)
                        result = conn.execute(update_query, {
                            'id': self.id,
                            'name': self.name,
                            'type': self.type,
                            'description': self.description,
                            'email_template': self.email_template,
                            'priority': self.priority,
                            'schedule_date': self.schedule_date,
                            'followup_days': self.followup_days,
                            'selection_criteria': self.selection_criteria,
                            'campaign_settings': self.campaign_settings,
                            'status': self.status
                        })
                        
                        if result.rowcount > 0:
                            current_app.logger.info(f"Successfully updated campaign ID: {self.id}")
                            return True
                        else:
                            current_app.logger.warning(f"No campaign found with ID: {self.id}")
                            return False
                    else:
                        # Insert new campaign
                        insert_query = text("""
                            INSERT INTO campaigns (name, type, description, email_template, 
                                                 priority, schedule_date, followup_days, 
                                                 selection_criteria, campaign_settings, status) 
                            VALUES (:name, :type, :description, :email_template, 
                                   :priority, :schedule_date, :followup_days, 
                                   :selection_criteria, :campaign_settings, :status)
                            RETURNING id
                        """)
                        result = conn.execute(insert_query, {
                            'name': self.name,
                            'type': self.type,
                            'description': self.description,
                            'email_template': self.email_template,
                            'priority': self.priority,
                            'schedule_date': self.schedule_date,
                            'followup_days': self.followup_days,
                            'selection_criteria': self.selection_criteria,
                            'campaign_settings': self.campaign_settings,
                            'status': self.status
                        })
                        self.id = result.fetchone()[0]
                        
                        current_app.logger.info(f"Successfully saved new campaign: {self.name} with ID {self.id}")
                        return True
                        
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error saving campaign: {e}")
            return False
        except Exception as e:
            current_app.logger.error(f"Unexpected error saving campaign: {e}")
            return False
    
    def delete(self):
        """Delete this campaign instance from the database."""
        if self.id:
            return self.__class__.delete(self.id)
        return False 

    @classmethod
    def delete_all_campaigns(cls) -> Dict[str, int]:
        """Delete all campaigns and their associated data (campaign_contacts and email_history).
        
        Returns:
            Dict with counts of deleted records: {'campaigns': X, 'campaign_contacts': Y, 'email_history': Z}
        """
        engine = cls._get_db_engine()
        if not engine:
            current_app.logger.error("Failed to delete all campaigns: Database engine not available.")
            return {'campaigns': 0, 'campaign_contacts': 0, 'email_history': 0}

        try:
            with engine.connect() as conn:
                with conn.begin():
                    # Delete from report_clicks first to avoid foreign key violations
                    # This handles both direct and indirect campaign associations
                    report_clicks_result = conn.execute(text("""
                        DELETE FROM report_clicks
                        WHERE campaign_id IN (SELECT id FROM campaigns)
                    """))
                    report_clicks_count = report_clicks_result.rowcount

                    # Delete associated email_history records
                    email_history_result = conn.execute(text("""
                        DELETE FROM email_history 
                        WHERE campaign_id IS NOT NULL
                    """))
                    email_history_count = email_history_result.rowcount
                    
                    # Delete campaign_contacts records
                    campaign_contacts_result = conn.execute(text("""
                        DELETE FROM campaign_contacts
                    """))
                    campaign_contacts_count = campaign_contacts_result.rowcount
                    
                    # Finally, delete campaigns
                    campaigns_result = conn.execute(text("""
                        DELETE FROM campaigns
                    """))
                    campaigns_count = campaigns_result.rowcount
                    
                    current_app.logger.info(
                        f"Successfully deleted all campaigns and associated data: "
                        f"{campaigns_count} campaigns, {campaign_contacts_count} campaign_contacts, "
                        f"{email_history_count} email_history records, {report_clicks_count} report_clicks records"
                    )
                    
                    return {
                        'campaigns': campaigns_count,
                        'campaign_contacts': campaign_contacts_count,
                        'email_history': email_history_count,
                        'report_clicks': report_clicks_count
                    }
                    
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error deleting all campaigns: {e}")
            return {'campaigns': 0, 'campaign_contacts': 0, 'email_history': 0, 'report_clicks': 0}
        except Exception as e:
            current_app.logger.error(f"Unexpected error deleting all campaigns: {e}")
            return {'campaigns': 0, 'campaign_contacts': 0, 'email_history': 0, 'report_clicks': 0} 