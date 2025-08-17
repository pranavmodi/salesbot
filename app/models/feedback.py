from typing import List, Dict, Optional
from flask import current_app
from app.tenant import current_tenant_id
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import os
import logging

class Feedback:
    """Feedback model for managing user feedback data from PostgreSQL database."""
    
    def __init__(self, data: Dict):
        self.id = data.get('id')
        self.user_id = data.get('user_id')
        self.user_email = data.get('user_email')
        self.user_name = data.get('user_name')
        self.tenant_id = data.get('tenant_id')
        self.message = data.get('message', '')
        self.category = data.get('category', 'general')  # general, bug, feature, other
        self.status = data.get('status', 'new')  # new, reviewed, resolved
        self.created_at = data.get('created_at')
        self.updated_at = data.get('updated_at')
        self.admin_notes = data.get('admin_notes', '')

    @staticmethod
    def _get_db_engine():
        """Get shared database engine."""
        from app.database import get_shared_engine
        return get_shared_engine()

    @staticmethod
    def create(user_id: str, user_email: str, user_name: str, tenant_id: str, 
               message: str, category: str = 'general') -> Optional['Feedback']:
        """Create a new feedback entry."""
        try:
            import uuid
            feedback_id = str(uuid.uuid4())
            
            engine = Feedback._get_db_engine()
            if not engine:
                current_app.logger.error("Could not get database engine")
                return None
                
            with engine.connect() as conn:
                with conn.begin():
                    result = conn.execute(text("""
                        INSERT INTO feedback (id, user_id, user_email, user_name, tenant_id, 
                                            message, category, status, created_at)
                        VALUES (:id, :user_id, :user_email, :user_name, :tenant_id, 
                                :message, :category, 'new', CURRENT_TIMESTAMP)
                        RETURNING id, created_at
                    """), {
                        'id': feedback_id,
                        'user_id': user_id,
                        'user_email': user_email,
                        'user_name': user_name,
                        'tenant_id': tenant_id,
                        'message': message,
                        'category': category
                    })
                    
                    row = result.fetchone()
                    if row:
                        feedback_data = {
                            'id': feedback_id,
                            'user_id': user_id,
                            'user_email': user_email,
                            'user_name': user_name,
                            'tenant_id': tenant_id,
                            'message': message,
                            'category': category,
                            'status': 'new',
                            'created_at': row.created_at,
                            'admin_notes': ''
                        }
                        return Feedback(feedback_data)
                        
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error creating feedback: {e}")
            return None
        except Exception as e:
            current_app.logger.error(f"Error creating feedback: {e}")
            return None

    @staticmethod
    def get_all_for_admin() -> List['Feedback']:
        """Get all feedback entries for admin view (cross-tenant)."""
        try:
            engine = Feedback._get_db_engine()
            if not engine:
                current_app.logger.error("Could not get database engine")
                return []
                
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, user_id, user_email, user_name, tenant_id, 
                           message, category, status, created_at, updated_at, admin_notes
                    FROM feedback
                    ORDER BY created_at DESC
                """))
                
                feedbacks = []
                for row in result:
                    feedback_data = {
                        'id': row.id,
                        'user_id': row.user_id,
                        'user_email': row.user_email,
                        'user_name': row.user_name,
                        'tenant_id': row.tenant_id,
                        'message': row.message,
                        'category': row.category,
                        'status': row.status,
                        'created_at': row.created_at,
                        'updated_at': row.updated_at,
                        'admin_notes': row.admin_notes or ''
                    }
                    feedbacks.append(Feedback(feedback_data))
                    
                return feedbacks
                
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error getting feedback: {e}")
            return []
        except Exception as e:
            current_app.logger.error(f"Error getting feedback: {e}")
            return []

    @staticmethod
    def update_status(feedback_id: str, status: str, admin_notes: str = '') -> bool:
        """Update feedback status and admin notes."""
        try:
            engine = Feedback._get_db_engine()
            if not engine:
                current_app.logger.error("Could not get database engine")
                return False
                
            with engine.connect() as conn:
                with conn.begin():
                    conn.execute(text("""
                        UPDATE feedback 
                        SET status = :status, admin_notes = :admin_notes, updated_at = CURRENT_TIMESTAMP
                        WHERE id = :feedback_id
                    """), {
                        'feedback_id': feedback_id,
                        'status': status,
                        'admin_notes': admin_notes
                    })
                    
                    return True
                    
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error updating feedback: {e}")
            return False
        except Exception as e:
            current_app.logger.error(f"Error updating feedback: {e}")
            return False

    @staticmethod
    def get_stats() -> Dict:
        """Get feedback statistics for admin dashboard."""
        try:
            engine = Feedback._get_db_engine()
            if not engine:
                current_app.logger.error("Could not get database engine")
                return {}
                
            with engine.connect() as conn:
                # Total feedback count
                result = conn.execute(text("SELECT COUNT(*) as total FROM feedback"))
                total = result.fetchone().total
                
                # Count by status
                result = conn.execute(text("""
                    SELECT status, COUNT(*) as count 
                    FROM feedback 
                    GROUP BY status
                """))
                status_counts = {row.status: row.count for row in result}
                
                # Count by category
                result = conn.execute(text("""
                    SELECT category, COUNT(*) as count 
                    FROM feedback 
                    GROUP BY category
                """))
                category_counts = {row.category: row.count for row in result}
                
                # Recent feedback (last 7 days)
                result = conn.execute(text("""
                    SELECT COUNT(*) as recent_count 
                    FROM feedback 
                    WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '7 days'
                """))
                recent_count = result.fetchone().recent_count
                
                return {
                    'total': total,
                    'status_counts': status_counts,
                    'category_counts': category_counts,
                    'recent_count': recent_count
                }
                
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error getting feedback stats: {e}")
            return {}
        except Exception as e:
            current_app.logger.error(f"Error getting feedback stats: {e}")
            return {}