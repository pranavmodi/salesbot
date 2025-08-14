from flask import Blueprint, redirect, request, current_app, jsonify
from app.models.report_click import ReportClick
from app.services.link_tracking_service import LinkTrackingService
from app.database import get_shared_engine
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

tracking_bp = Blueprint('tracking', __name__, url_prefix='/track')

@tracking_bp.route('/click/<tracking_id>')
def track_click(tracking_id):
    """Track link click and redirect to actual destination."""
    try:
        # Get click information
        user_agent = request.headers.get('User-Agent', '')
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        referer = request.headers.get('Referer', '')
        
        # Get the actual destination URL from tracking_id
        engine = get_shared_engine()
        with engine.connect() as conn:
            with conn.begin():
                # Look up the original URL and log the click
                result = conn.execute(text("""
                    SELECT original_url, company_id, campaign_id, tenant_id 
                    FROM link_tracking 
                    WHERE tracking_id = :tracking_id
                """), {'tracking_id': tracking_id})
                
                row = result.fetchone()
                if not row:
                    logger.warning(f"Invalid tracking ID: {tracking_id}")
                    return redirect('https://possibleminds.in')  # Fallback
                
                original_url = row.original_url
                company_id = row.company_id
                campaign_id = row.campaign_id
                
                # Record the click using our service
                LinkTrackingService.record_click(
                    tracking_id=tracking_id,
                    user_agent=user_agent,
                    ip_address=ip_address,
                    referer=referer
                )
                
                # Also log in report_clicks for backward compatibility
                try:
                    conn.execute(text("""
                        INSERT INTO report_clicks 
                        (company_id, campaign_id, tracking_id, clicked_at, ip_address, user_agent, referer, tenant_id)
                        VALUES (:company_id, :campaign_id, :tracking_id, CURRENT_TIMESTAMP, :ip_address, :user_agent, :referer, :tenant_id)
                    """), {
                        'company_id': company_id,
                        'campaign_id': campaign_id, 
                        'tracking_id': tracking_id,
                        'ip_address': ip_address,
                        'user_agent': user_agent,
                        'referer': referer,
                        'tenant_id': row.tenant_id
                    })
                except Exception as e:
                    logger.warning(f"Failed to log in report_clicks: {e}")
                
                logger.info(f"Tracked click: {tracking_id} → {original_url}")
                return redirect(original_url)
                
    except Exception as e:
        logger.error(f"Error tracking click {tracking_id}: {e}")
        # Still redirect to avoid broken user experience
        return redirect('https://possibleminds.in')

@tracking_bp.route('/analytics/<int:campaign_id>')
def get_campaign_link_analytics(campaign_id):
    """Get link tracking analytics for a specific campaign."""
    try:
        analytics = LinkTrackingService.get_link_tracking_analytics(campaign_id=campaign_id)
        return jsonify(analytics)
    except Exception as e:
        logger.error(f"Error getting campaign link analytics: {e}")
        return jsonify({'error': str(e), 'success': False}), 500