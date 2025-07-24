from datetime import datetime
from typing import List, Dict, Optional
from flask import current_app
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import os
import json

class ReportClick:
    """Model for tracking report link clicks and analytics."""
    
    def __init__(self, data: Dict):
        self.id = data.get('id')
        self.company_id = data.get('company_id')
        self.campaign_id = data.get('campaign_id')
        self.email_history_id = data.get('email_history_id')
        self.recipient_email = data.get('recipient_email')
        self.company_slug = data.get('company_slug')
        self.tracking_id = data.get('tracking_id')
        self.click_timestamp = data.get('click_timestamp')
        self.ip_address = data.get('ip_address')
        self.user_agent = data.get('user_agent')
        self.referer = data.get('referer')
        self.utm_source = data.get('utm_source')
        self.utm_medium = data.get('utm_medium')
        self.utm_campaign = data.get('utm_campaign')
        self.utm_content = data.get('utm_content')
        self.utm_term = data.get('utm_term')
        self.device_type = data.get('device_type')
        self.browser = data.get('browser')
        self.operating_system = data.get('operating_system')
        self.country = data.get('country')
        self.city = data.get('city')
        self.session_id = data.get('session_id')
        self.custom_data = data.get('custom_data')
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
    def save_click(cls, click_data: Dict) -> Optional[int]:
        """Save a click event to the database."""
        engine = cls._get_db_engine()
        if not engine:
            current_app.logger.error("Failed to save click: Database engine not available.")
            return None

        try:
            with engine.connect() as conn:
                with conn.begin():  # Use transaction
                    # Convert custom_data to JSON string if it exists
                    custom_data_json = json.dumps(click_data.get('custom_data')) if click_data.get('custom_data') else None
                    
                    now = datetime.now()
                    
                    query = text("""
                        INSERT INTO report_clicks (
                            company_id, campaign_id, email_history_id, recipient_email, 
                            company_slug, tracking_id, click_timestamp, ip_address, user_agent, 
                            referer, utm_source, utm_medium, utm_campaign, utm_content, utm_term,
                            device_type, browser, operating_system, country, city, session_id, 
                            custom_data, created_at, updated_at
                        ) VALUES (
                            :company_id, :campaign_id, :email_history_id, :recipient_email,
                            :company_slug, :tracking_id, :click_timestamp, :ip_address, :user_agent,
                            :referer, :utm_source, :utm_medium, :utm_campaign, :utm_content, :utm_term,
                            :device_type, :browser, :operating_system, :country, :city, :session_id,
                            :custom_data, :created_at, :updated_at
                        ) RETURNING id
                    """)
                    
                    result = conn.execute(query, {
                        'company_id': click_data.get('company_id'),
                        'campaign_id': click_data.get('campaign_id'),
                        'email_history_id': click_data.get('email_history_id'),
                        'recipient_email': click_data.get('recipient_email'),
                        'company_slug': click_data.get('company_slug'),
                        'tracking_id': click_data.get('tracking_id'),
                        'click_timestamp': click_data.get('click_timestamp', now),
                        'ip_address': click_data.get('ip_address'),
                        'user_agent': click_data.get('user_agent'),
                        'referer': click_data.get('referer'),
                        'utm_source': click_data.get('utm_source'),
                        'utm_medium': click_data.get('utm_medium'),
                        'utm_campaign': click_data.get('utm_campaign'),
                        'utm_content': click_data.get('utm_content'),
                        'utm_term': click_data.get('utm_term'),
                        'device_type': click_data.get('device_type'),
                        'browser': click_data.get('browser'),
                        'operating_system': click_data.get('operating_system'),
                        'country': click_data.get('country'),
                        'city': click_data.get('city'),
                        'session_id': click_data.get('session_id'),
                        'custom_data': custom_data_json,
                        'created_at': now,
                        'updated_at': now
                    })
                    
                    click_id = result.fetchone()[0]
                    
                    current_app.logger.info(f"Successfully saved click with ID: {click_id}")
                    return click_id
                
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error saving click: {e}")
            return None
        except Exception as e:
            current_app.logger.error(f"Unexpected error saving click: {e}")
            return None

    @classmethod
    def get_campaign_clicks(cls, campaign_id: int) -> List[Dict]:
        """Get all clicks for a specific campaign."""
        engine = cls._get_db_engine()
        if not engine:
            return []

        try:
            with engine.connect() as conn:
                query = text("""
                    SELECT rc.*, c.company_name, eh.subject as email_subject
                    FROM report_clicks rc
                    LEFT JOIN companies c ON rc.company_id = c.id
                    LEFT JOIN email_history eh ON rc.email_history_id = eh.id
                    WHERE rc.campaign_id = :campaign_id
                    ORDER BY rc.click_timestamp DESC
                """)
                
                result = conn.execute(query, {'campaign_id': campaign_id})
                
                clicks = []
                for row in result:
                    click_data = dict(row._mapping)
                    if click_data.get('custom_data'):
                        try:
                            click_data['custom_data'] = json.loads(click_data['custom_data'])
                        except (json.JSONDecodeError, TypeError):
                            click_data['custom_data'] = {}
                    clicks.append(click_data)
                
                return clicks
                
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error getting campaign clicks: {e}")
            return []
        except Exception as e:
            current_app.logger.error(f"Unexpected error getting campaign clicks: {e}")
            return []

    @classmethod
    def get_click_analytics(cls, campaign_id: int = None, date_range: Dict = None) -> Dict:
        """Get click analytics with optional filtering."""
        engine = cls._get_db_engine()
        if not engine:
            return {}

        try:
            with engine.connect() as conn:
                # Build WHERE conditions
                where_conditions = []
                params = {}
                
                if campaign_id:
                    where_conditions.append("campaign_id = :campaign_id")
                    params['campaign_id'] = campaign_id
                
                if date_range:
                    if date_range.get('start_date'):
                        where_conditions.append("click_timestamp >= :start_date")
                        params['start_date'] = date_range['start_date']
                    if date_range.get('end_date'):
                        where_conditions.append("click_timestamp <= :end_date")
                        params['end_date'] = date_range['end_date']
                
                where_clause = ""
                if where_conditions:
                    where_clause = " WHERE " + " AND ".join(where_conditions)
                
                # Get overall analytics (no GROUP BY)
                overall_query = f"""
                    SELECT 
                        COUNT(*) as total_clicks,
                        COUNT(DISTINCT recipient_email) as unique_recipients,
                        COUNT(DISTINCT company_id) as unique_companies,
                        COUNT(DISTINCT utm_campaign) as unique_campaigns
                    FROM report_clicks
                    {where_clause}
                """
                
                overall_result = conn.execute(text(overall_query), params)
                overall_row = overall_result.fetchone()
                
                analytics = {
                    'total_clicks': overall_row.total_clicks if overall_row else 0,
                    'unique_recipients': overall_row.unique_recipients if overall_row else 0,
                    'unique_companies': overall_row.unique_companies if overall_row else 0,
                    'unique_campaigns': overall_row.unique_campaigns if overall_row else 0,
                    'clicks_by_date': []
                }
                
                # Get clicks by date (with GROUP BY)
                date_query = f"""
                    SELECT 
                        DATE(click_timestamp) as click_date,
                        COUNT(*) as clicks_count
                    FROM report_clicks
                    {where_clause}
                    GROUP BY DATE(click_timestamp) 
                    ORDER BY click_date DESC
                """
                
                date_result = conn.execute(text(date_query), params)
                
                for row in date_result:
                    analytics['clicks_by_date'].append({
                        'date': row.click_date.isoformat() if row.click_date else None,
                        'clicks': row.clicks_count
                    })
                
                return analytics
                
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error getting click analytics: {e}")
            return {}
        except Exception as e:
            current_app.logger.error(f"Unexpected error getting click analytics: {e}")
            return {}

    @classmethod
    def get_company_click_stats(cls, company_id: int) -> Dict:
        """Get click statistics for a specific company."""
        engine = cls._get_db_engine()
        if not engine:
            return {}

        try:
            with engine.connect() as conn:
                query = text("""
                    SELECT 
                        COUNT(*) as total_clicks,
                        COUNT(DISTINCT recipient_email) as unique_recipients,
                        COUNT(DISTINCT campaign_id) as campaigns_clicked,
                        MIN(click_timestamp) as first_click,
                        MAX(click_timestamp) as last_click,
                        COUNT(DISTINCT DATE(click_timestamp)) as active_days
                    FROM report_clicks
                    WHERE company_id = :company_id
                """)
                
                result = conn.execute(query, {'company_id': company_id})
                row = result.fetchone()
                
                if row:
                    return {
                        'total_clicks': row.total_clicks,
                        'unique_recipients': row.unique_recipients,
                        'campaigns_clicked': row.campaigns_clicked,
                        'first_click': row.first_click.isoformat() if row.first_click else None,
                        'last_click': row.last_click.isoformat() if row.last_click else None,
                        'active_days': row.active_days
                    }
                
                return {}
                
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error getting company click stats: {e}")
            return {}
        except Exception as e:
            current_app.logger.error(f"Unexpected error getting company click stats: {e}")
            return {} 