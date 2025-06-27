from datetime import datetime
from typing import List, Dict, Optional
from flask import current_app
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import os
import logging

class Campaign:
    """Campaign model for managing email campaign data."""
    
    def __init__(self, data: Dict):
        self.id = data.get('id')
        self.name = data.get('name', '')
        self.description = data.get('description', '')
        self.status = data.get('status', 'active')  # active, paused, completed
        self.created_at = data.get('created_at')
        self.updated_at = data.get('updated_at')

    @staticmethod
    def _get_db_engine():
        """Get database engine from environment."""
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            current_app.logger.error("DATABASE_URL not configured.")
            return None
        try:
            return create_engine(database_url)
        except Exception as e:
            current_app.logger.error(f"Error creating database engine: {e}")
            return None

    @classmethod
    def load_all(cls) -> List['Campaign']:
        """Load all campaigns from PostgreSQL database."""
        campaigns = []
        engine = cls._get_db_engine()
        if not engine:
            return campaigns
            
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, name, description, status, created_at, updated_at
                    FROM campaigns 
                    ORDER BY created_at DESC
                """))
                
                for row in result:
                    campaign_data = dict(row._mapping)
                    campaigns.append(cls(campaign_data))
                    
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
                    SELECT id, name, description, status, created_at, updated_at
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
                    SELECT id, name, description, status, created_at, updated_at
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
                        INSERT INTO campaigns (name, description, status) 
                        VALUES (:name, :description, :status)
                    """)
                    conn.execute(insert_query, {
                        'name': campaign_data['name'],
                        'description': campaign_data.get('description', ''),
                        'status': campaign_data.get('status', 'active')
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
                            description = :description, 
                            status = :status,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :id
                    """)
                    result = conn.execute(update_query, {
                        'id': campaign_id,
                        'name': campaign_data['name'],
                        'description': campaign_data.get('description', ''),
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
                result = conn.execute(text("""
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
                
                row = result.fetchone()
                if row:
                    return {
                        'total_emails': row.total_emails or 0,
                        'sent_emails': row.sent_emails or 0,
                        'failed_emails': row.failed_emails or 0,
                        'unique_recipients': row.unique_recipients or 0,
                        'first_email_date': row.first_email_date,
                        'last_email_date': row.last_email_date,
                        'success_rate': round((row.sent_emails / row.total_emails * 100) if row.total_emails > 0 else 0, 2)
                    }
                    
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error getting campaign stats: {e}")
        except Exception as e:
            current_app.logger.error(f"Unexpected error getting campaign stats: {e}")
            
        return {}

    def to_dict(self) -> Dict:
        """Convert campaign to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at),
            'updated_at': self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else str(self.updated_at)
        } 