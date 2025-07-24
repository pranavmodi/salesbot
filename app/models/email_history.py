from datetime import datetime
from typing import List, Dict, Optional
from flask import current_app
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import logging

class EmailHistory:
    """Email history model for managing sent emails."""
    
    def __init__(self, data: Dict):
        self.id = data.get('id')
        self.date = data.get('date')
        self.to = data.get('to', '')
        self.subject = data.get('subject', '')
        self.body = data.get('body', '')
        self.status = data.get('status', 'pending')  # Standardized: sent, failed, pending, retry
        self.campaign_id = data.get('campaign_id')
        self.sent_via = data.get('sent_via')  # Email account used
        self.email_type = data.get('email_type', 'campaign')  # campaign, test, bulk, manual
        self.error_details = data.get('error_details')  # Specific error messages

    @classmethod
    def get_db_engine(cls):
        """Get database engine."""
        database_url = current_app.config.get('DATABASE_URL')
        if not database_url:
            current_app.logger.error("DATABASE_URL not configured.")
            return None
        try:
            return create_engine(
                database_url,
                pool_size=5,          # Maximum number of permanent connections
                max_overflow=10,      # Maximum number of overflow connections  
                pool_pre_ping=True,   # Verify connections before use
                pool_recycle=3600     # Recycle connections every hour
            )
        except Exception as e:
            current_app.logger.error(f"Error creating database engine: {e}")
            return None

    @classmethod
    def load_all(cls) -> List['EmailHistory']:
        """Load all email history from database."""
        engine = cls.get_db_engine()
        if not engine:
            return []
            
        history = []
        try:
            with engine.connect() as connection:
                result = connection.execute(
                    text('SELECT id, date, "to", subject, body, status, campaign_id, sent_via, email_type, error_details FROM email_history ORDER BY date DESC')
                )
                for row in result:
                    history.append(cls(dict(row._mapping)))
            current_app.logger.info(f"Loaded {len(history)} records from email_history table.")
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error loading history from database: {e}")
        except Exception as e:
            current_app.logger.error(f"An unexpected error occurred while loading history: {e}")
        return history

    @classmethod
    def save(cls, email_data: Dict) -> bool:
        """Save email to history."""
        engine = cls.get_db_engine()
        if not engine:
            current_app.logger.error("Failed to save to history: Database engine not available.")
            return False

        try:
            # Ensure date is in correct format
            if isinstance(email_data.get('date'), str):
                email_data['date'] = datetime.strptime(email_data['date'], "%Y-%m-%d %H:%M:%S")

            with engine.connect() as connection:
                with connection.begin():
                    insert_query = text(
                        'INSERT INTO email_history (date, "to", subject, body, status, campaign_id, sent_via, email_type, error_details) '
                        'VALUES (:date, :to, :subject, :body, :status, :campaign_id, :sent_via, :email_type, :error_details)'
                    )
                    connection.execute(insert_query, {
                        'date': email_data['date'],
                        'to': email_data['to'],
                        'subject': email_data['subject'],
                        'body': email_data['body'],
                        'status': email_data['status'],
                        'campaign_id': email_data.get('campaign_id'),
                        'sent_via': email_data.get('sent_via'),
                        'email_type': email_data.get('email_type', 'campaign'),
                        'error_details': email_data.get('error_details')
                    })
            current_app.logger.info(f"Successfully saved email to {email_data['to']} to history database.")
            return True
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error saving to history: {e}")
            return False
        except Exception as e:
            current_app.logger.error(f"An unexpected error occurred while saving to history: {e}")
            return False

    @classmethod
    def get_sent_emails_set(cls) -> set:
        """Get set of emails that have been sent to."""
        history = cls.load_all()
        return {record.to.lower() for record in history if record.to}

    @classmethod
    def get_by_campaign_id(cls, campaign_id: int, limit: Optional[int] = None) -> List['EmailHistory']:
        """Get all email history for a specific campaign, with an optional limit."""
        """Get all email history for a specific campaign."""
        engine = cls.get_db_engine()
        if not engine:
            return []
            
        history = []
        try:
            with engine.connect() as connection:
                if limit:
                    query_str = 'SELECT id, date, "to", subject, body, status, campaign_id, sent_via, email_type, error_details FROM email_history WHERE campaign_id = :campaign_id ORDER BY date DESC LIMIT :limit'
                    result = connection.execute(text(query_str),
                                                {"campaign_id": campaign_id, "limit": limit})
                else:
                    query_str = 'SELECT id, date, "to", subject, body, status, campaign_id, sent_via, email_type, error_details FROM email_history WHERE campaign_id = :campaign_id ORDER BY date DESC'
                    result = connection.execute(text(query_str),
                                                {"campaign_id": campaign_id})
                for row in result:
                    history.append(cls(dict(row._mapping)))
            current_app.logger.info(f"Loaded {len(history)} records for campaign {campaign_id}.")
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error loading history for campaign {campaign_id}: {e}")
        except Exception as e:
            current_app.logger.error(f"An unexpected error occurred while loading campaign history: {e}")
        return history

    @classmethod
    def get_campaign_emails_set(cls, campaign_id: int) -> set:
        """Get set of emails that have been sent to for a specific campaign."""
        history = cls.get_by_campaign(campaign_id)
        return {record.to.lower() for record in history if record.to}

    @classmethod
    def get_daily_count_for_campaign(cls, campaign_id: int, date: datetime.date) -> int:
        """Get number of emails sent today for a specific campaign."""
        engine = cls.get_db_engine()
        if not engine:
            return 0
            
        try:
            with engine.connect() as connection:
                result = connection.execute(
                    text("""
                        SELECT COUNT(*) 
                        FROM email_history 
                        WHERE campaign_id = :campaign_id 
                        AND DATE(date) = :date
                        AND status = 'sent'
                    """),
                    {"campaign_id": campaign_id, "date": date}
                )
                count = result.fetchone()[0]
                return count
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error getting daily count for campaign {campaign_id}: {e}")
            return 0
        except Exception as e:
            current_app.logger.error(f"Unexpected error getting daily count: {e}")
            return 0

    def to_dict(self) -> Dict:
        """Convert email history to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'date': self.date.strftime('%Y-%m-%d %H:%M:%S') if isinstance(self.date, datetime) else str(self.date),
            'to': self.to,
            'subject': self.subject,
            'body': self.body,
            'status': self.status,
            'campaign_id': self.campaign_id,
            'sent_via': self.sent_via,
            'email_type': self.email_type,
            'error_details': self.error_details
        }

    @classmethod
    def get_by_recipient_and_campaign(cls, recipient_email: str, campaign_id: int) -> Optional['EmailHistory']:
        """Get email history by recipient and campaign for click tracking."""
        engine = cls.get_db_engine()
        if not engine:
            return None
        
        try:
            with engine.connect() as connection:
                result = connection.execute(
                    text("""
                        SELECT id, date, "to", subject, body, status, campaign_id, sent_via, email_type, error_details 
                        FROM email_history 
                        WHERE "to" = :recipient_email AND campaign_id = :campaign_id
                        ORDER BY date DESC
                        LIMIT 1
                    """),
                    {'recipient_email': recipient_email, 'campaign_id': campaign_id}
                )
                row = result.fetchone()
                if row:
                    return cls(dict(row._mapping))
                return None
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error getting email history: {e}")
            return None

    @classmethod
    def get_campaign_stats(cls, campaign_id: int) -> Dict:
        """Get email statistics for a campaign."""
        engine = cls.get_db_engine()
        if not engine:
            return {}
        
        try:
            with engine.connect() as connection:
                result = connection.execute(
                    text("""
                        SELECT 
                            COUNT(*) as total_emails,
                            COUNT(CASE WHEN status = 'sent' THEN 1 END) as sent_emails,
                            COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_emails,
                            COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_emails,
                            COUNT(DISTINCT "to") as unique_recipients,
                            MIN(date) as first_sent,
                            MAX(date) as last_sent
                        FROM email_history 
                        WHERE campaign_id = :campaign_id
                    """),
                    {'campaign_id': campaign_id}
                )
                row = result.fetchone()
                if row:
                    return {
                        'total_emails': row.total_emails,
                        'sent_emails': row.sent_emails,
                        'failed_emails': row.failed_emails,
                        'pending_emails': row.pending_emails,
                        'unique_recipients': row.unique_recipients,
                        'first_sent': row.first_sent.isoformat() if row.first_sent else None,
                        'last_sent': row.last_sent.isoformat() if row.last_sent else None
                    }
                return {}
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error getting campaign stats: {e}")
            return {}