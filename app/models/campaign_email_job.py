from datetime import datetime
from typing import List, Dict, Optional
from flask import current_app
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import os
import json

class CampaignEmailJob:
    """Model for persistent campaign email job scheduling."""
    
    # Shared database engine with connection pooling
    _engine = None
    
    def __init__(self, campaign_id=None, contact_email=None, contact_data=None, 
                 campaign_settings=None, scheduled_time=None, **kwargs):
        self.id = kwargs.get('id')
        self.campaign_id = campaign_id
        self.contact_email = contact_email
        self.contact_data = contact_data if isinstance(contact_data, str) else json.dumps(contact_data or {})
        self.campaign_settings = campaign_settings if isinstance(campaign_settings, str) else json.dumps(campaign_settings or {})
        self.scheduled_time = scheduled_time
        self.status = kwargs.get('status', 'pending')
        self.attempts = kwargs.get('attempts', 0)
        self.last_attempt = kwargs.get('last_attempt')
        self.error_message = kwargs.get('error_message')
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
    
    @property
    def contact_data_dict(self):
        """Parse contact data JSON string to dict."""
        try:
            return json.loads(self.contact_data) if isinstance(self.contact_data, str) else self.contact_data
        except (json.JSONDecodeError, TypeError):
            return {}
    
    @property
    def campaign_settings_dict(self):
        """Parse campaign settings JSON string to dict."""
        try:
            return json.loads(self.campaign_settings) if isinstance(self.campaign_settings, str) else self.campaign_settings
        except (json.JSONDecodeError, TypeError):
            return {}

    @classmethod
    def _get_db_engine(cls):
        """Get shared database engine with connection pooling."""
        if cls._engine is None:
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                current_app.logger.error("DATABASE_URL not configured.")
                return None
            try:
                # Configure connection pooling to limit concurrent connections
                cls._engine = create_engine(
                    database_url,
                    pool_size=5,          # Maximum number of permanent connections
                    max_overflow=10,      # Maximum number of overflow connections
                    pool_pre_ping=True,   # Verify connections before use
                    pool_recycle=3600     # Recycle connections every hour
                )
            except Exception as e:
                current_app.logger.error(f"Error creating database engine: {e}")
                return None
        return cls._engine

    def save(self) -> bool:
        """Save this email job to the database."""
        engine = self._get_db_engine()
        if not engine:
            return False
        
        try:
            with engine.connect() as conn:
                with conn.begin():
                    if self.id:
                        # Update existing job
                        update_query = text("""
                            UPDATE campaign_email_jobs 
                            SET status = :status,
                                attempts = :attempts,
                                last_attempt = :last_attempt,
                                error_message = :error_message,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = :id
                        """)
                        conn.execute(update_query, {
                            'id': self.id,
                            'status': self.status,
                            'attempts': self.attempts,
                            'last_attempt': self.last_attempt,
                            'error_message': self.error_message
                        })
                    else:
                        # Insert new job
                        insert_query = text("""
                            INSERT INTO campaign_email_jobs 
                            (campaign_id, contact_email, contact_data, campaign_settings, 
                             scheduled_time, status, attempts, created_at, updated_at)
                            VALUES (:campaign_id, :contact_email, :contact_data, :campaign_settings,
                                   :scheduled_time, :status, :attempts, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                            RETURNING id
                        """)
                        result = conn.execute(insert_query, {
                            'campaign_id': self.campaign_id,
                            'contact_email': self.contact_email,
                            'contact_data': self.contact_data,
                            'campaign_settings': self.campaign_settings,
                            'scheduled_time': self.scheduled_time,
                            'status': self.status,
                            'attempts': self.attempts
                        })
                        self.id = result.fetchone()[0]
                    
                    return True
                    
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error saving email job: {e}")
            return False
        except Exception as e:
            current_app.logger.error(f"Unexpected error saving email job: {e}")
            return False

    @classmethod
    def mark_as_processing(cls, job_id: int) -> bool:
        """Atomically mark a job as 'processing' to prevent race conditions."""
        engine = cls._get_db_engine()
        if not engine:
            return False
        
        try:
            with engine.connect() as conn:
                with conn.begin():
                    query = text("""
                        UPDATE campaign_email_jobs 
                        SET status = 'processing', 
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :job_id AND status = 'pending'
                    """)
                    result = conn.execute(query, {"job_id": job_id})
                    # rowcount tells us if the update was successful
                    return result.rowcount > 0
                    
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error marking job as processing: {e}")
            return False
        except Exception as e:
            current_app.logger.error(f"Unexpected error marking job as processing: {e}")
            return False

    @classmethod
    def get_pending_jobs(cls, limit=100) -> List['CampaignEmailJob']:
        """Get pending email jobs that are ready to be executed."""
        engine = cls._get_db_engine()
        if not engine:
            return []
        
        try:
            with engine.connect() as conn:
                query = text("""
                    SELECT id, campaign_id, contact_email, contact_data, campaign_settings,
                           scheduled_time, status, attempts, last_attempt, error_message,
                           created_at, updated_at
                    FROM campaign_email_jobs 
                    WHERE status = 'pending' 
                    AND scheduled_time <= CURRENT_TIMESTAMP
                    ORDER BY scheduled_time ASC
                    LIMIT :limit
                """)
                
                result = conn.execute(query, {"limit": limit})
                jobs = []
                
                for row in result:
                    job_data = dict(row._mapping)
                    jobs.append(cls(**job_data))
                
                return jobs
                
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error getting pending jobs: {e}")
            return []
        except Exception as e:
            current_app.logger.error(f"Unexpected error getting pending jobs: {e}")
            return []

    @classmethod
    def mark_as_executed(cls, job_id: int) -> bool:
        """Mark a job as successfully executed."""
        engine = cls._get_db_engine()
        if not engine:
            return False
        
        try:
            with engine.connect() as conn:
                with conn.begin():
                    query = text("""
                        UPDATE campaign_email_jobs 
                        SET status = 'executed', 
                            last_attempt = CURRENT_TIMESTAMP,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :job_id
                    """)
                    conn.execute(query, {"job_id": job_id})
                    return True
                    
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error marking job as executed: {e}")
            return False
        except Exception as e:
            current_app.logger.error(f"Unexpected error marking job as executed: {e}")
            return False

    @classmethod
    def mark_as_failed(cls, job_id: int, error_message: str, max_attempts=3) -> bool:
        """Mark a job as failed and increment attempts."""
        engine = cls._get_db_engine()
        if not engine:
            return False
        
        try:
            with engine.connect() as conn:
                with conn.begin():
                    # First get current attempts
                    get_query = text("SELECT attempts FROM campaign_email_jobs WHERE id = :job_id")
                    result = conn.execute(get_query, {"job_id": job_id})
                    row = result.fetchone()
                    
                    if not row:
                        return False
                    
                    new_attempts = row[0] + 1
                    new_status = 'failed' if new_attempts >= max_attempts else 'pending'
                    
                    update_query = text("""
                        UPDATE campaign_email_jobs 
                        SET status = :status,
                            attempts = :attempts,
                            last_attempt = CURRENT_TIMESTAMP,
                            error_message = :error_message,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :job_id
                    """)
                    conn.execute(update_query, {
                        "job_id": job_id,
                        "status": new_status,
                        "attempts": new_attempts,
                        "error_message": error_message
                    })
                    return True
                    
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error marking job as failed: {e}")
            return False
        except Exception as e:
            current_app.logger.error(f"Unexpected error marking job as failed: {e}")
            return False

    @classmethod
    def cleanup_old_jobs(cls, days_old=7) -> int:
        """Clean up old completed/failed jobs."""
        engine = cls._get_db_engine()
        if not engine:
            return 0
        
        try:
            with engine.connect() as conn:
                with conn.begin():
                    query = text("""
                        DELETE FROM campaign_email_jobs 
                        WHERE status IN ('executed', 'failed')
                        AND updated_at < CURRENT_TIMESTAMP - INTERVAL '%s days'
                    """ % days_old)
                    result = conn.execute(query)
                    return result.rowcount
                    
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error cleaning up old jobs: {e}")
            return 0
        except Exception as e:
            current_app.logger.error(f"Unexpected error cleaning up old jobs: {e}")
            return 0
    
    @classmethod
    def close_engine(cls):
        """Close the shared database engine and all connections."""
        if cls._engine:
            try:
                cls._engine.dispose()
                cls._engine = None
                current_app.logger.info("Database engine disposed successfully")
            except Exception as e:
                current_app.logger.error(f"Error disposing database engine: {e}")

    @classmethod
    def count_all_pending_jobs(cls) -> int:
        """Count all jobs with 'pending' status, regardless of scheduled time."""
        engine = cls._get_db_engine()
        if not engine:
            return 0
        
        try:
            with engine.connect() as conn:
                query = text("SELECT COUNT(*) FROM campaign_email_jobs WHERE status = 'pending'")
                result = conn.execute(query)
                count = result.scalar()
                return count or 0
        except Exception as e:
            current_app.logger.error(f"Error counting all pending jobs: {e}")
            return 0