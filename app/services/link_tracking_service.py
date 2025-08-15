"""
Link tracking service for campaign analytics.
Provides URL wrapping and tracking functionality for email campaigns.
"""

import re
import uuid
import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from flask import current_app, url_for
from sqlalchemy import text

from app.database import get_shared_engine
from app.tenant import current_tenant_id

logger = logging.getLogger(__name__)

class LinkTrackingService:
    """Service for tracking link clicks in email campaigns."""
    
    @staticmethod
    def wrap_links_in_email(email_body: str, campaign_id: Optional[int] = None, 
                          company_id: Optional[int] = None, contact_email: Optional[str] = None) -> Tuple[str, List[str]]:
        """
        Wrap all links in email body with tracking URLs.
        
        Args:
            email_body: HTML email body content
            campaign_id: Optional campaign ID for tracking
            company_id: Optional company ID for tracking  
            contact_email: Optional contact email for tracking
            
        Returns:
            Tuple of (modified_email_body, list_of_tracking_ids)
        """
        if not email_body:
            return email_body, []
        
        # Find all links in the email body (both href attributes and standalone URLs)
        # Simplified regex to better handle markdown links and standalone URLs
        link_pattern = r'href=["\']([^"\']+)["\']|\[([^\]]+)\]\(([^)]+)\)|(https?://[^\s<>"\']+)'
        matches = re.finditer(link_pattern, email_body, re.IGNORECASE)
        
        tracking_ids = []
        modified_body = email_body
        offset = 0  # Track offset for string replacements
        
        logger.info(f"Processing email body for link tracking. Body length: {len(email_body)}")
        logger.info(f"Link pattern: {link_pattern}")
        
        for match in matches:
            logger.info(f"Match groups: {match.groups()}")
            
            if match.group(1):  # href attribute match
                original_url = match.group(1)
                full_match = match.group(0)
                is_href = True
                is_markdown = False
                logger.info(f"Found href link: {original_url}")
            elif match.group(2) and match.group(3):  # markdown link match [text](url)
                original_url = match.group(3)
                link_text = match.group(2)
                full_match = match.group(0)
                is_href = False
                is_markdown = True
                logger.info(f"Found markdown link: [{link_text}]({original_url})")
            elif match.group(4):  # standalone URL match
                original_url = match.group(4)
                full_match = original_url
                is_href = False
                is_markdown = False
                logger.info(f"Found standalone URL: {original_url}")
            else:
                logger.warning(f"No valid match groups found: {match.groups()}")
                continue
            
            # Clean trailing punctuation from URLs more carefully
            # Only remove punctuation that's clearly not part of the URL
            # Be more conservative about what we remove
            original_url_cleaned = original_url.strip()
            
            # Only remove trailing punctuation if it's clearly not part of the URL
            # Don't remove closing parentheses, brackets, or other URL characters
            if original_url_cleaned.endswith(('.', ',', ';', '!', '?')):
                original_url_cleaned = original_url_cleaned.rstrip('.,;!?')
            
            logger.info(f"URL cleaning: '{original_url}' -> '{original_url_cleaned}'")
            original_url = original_url_cleaned
            
            # Skip if it's already a tracking URL, email, tel, or anchor link
            if (original_url.startswith(('mailto:', 'tel:', '#')) or 
                '/track/click/' in original_url or
                not urlparse(original_url).netloc):
                logger.info(f"Skipping URL: {original_url} (already tracked or invalid)")
                continue
                
            # Create tracking URL
            tracking_id = LinkTrackingService.create_tracking_record(
                original_url, campaign_id, company_id, contact_email
            )
            
            if tracking_id:
                tracking_url = url_for('tracking.track_click', tracking_id=tracking_id, _external=True)
                tracking_ids.append(tracking_id)
                logger.info(f"Created tracking URL: {tracking_url} for original: {original_url}")
                
                # Replace the URL in the email body
                start_pos = match.start() + offset
                end_pos = match.end() + offset
                
                if is_href:
                    # Replace the URL inside href attribute
                    new_href = full_match.replace(original_url, tracking_url)
                    modified_body = modified_body[:start_pos] + new_href + modified_body[end_pos:]
                    offset += len(new_href) - len(full_match)
                    logger.info(f"Replaced href: {full_match} -> {new_href}")
                elif is_markdown:
                    # Replace the URL in markdown link [text](url)
                    new_markdown = f'[{link_text}]({tracking_url})'
                    modified_body = modified_body[:start_pos] + new_markdown + modified_body[end_pos:]
                    offset += len(new_markdown) - len(full_match)
                    logger.info(f"Replaced markdown: '{full_match}' -> '{new_markdown}'")
                    logger.info(f"Replacement details: start_pos={start_pos}, end_pos={end_pos}, offset={offset}")
                else:
                    # Replace standalone URL
                    modified_body = modified_body[:start_pos] + tracking_url + modified_body[end_pos:]
                    offset += len(tracking_url) - len(original_url)
                    logger.info(f"Replaced standalone: {full_match} -> {tracking_url}")
            else:
                logger.warning(f"Failed to create tracking record for URL: {original_url}")
        
        logger.info(f"Link tracking complete. Modified {len(tracking_ids)} links.")
        
        # Debug: Check if there are any remaining broken links
        remaining_broken = re.findall(r'\[([^\]]+)\]\(([^)]*$)', modified_body)
        if remaining_broken:
            logger.warning(f"Found potentially broken markdown links: {remaining_broken}")
        
        return modified_body, tracking_ids
    
    @staticmethod
    def create_tracking_record(original_url: str, campaign_id: Optional[int] = None,
                             company_id: Optional[int] = None, contact_email: Optional[str] = None) -> Optional[str]:
        """
        Create a tracking record in the database.
        
        Args:
            original_url: The original URL to track
            campaign_id: Optional campaign ID
            company_id: Optional company ID  
            contact_email: Optional contact email
            
        Returns:
            Tracking ID string if successful, None otherwise
        """
        try:
            tenant_id = current_tenant_id()
            if not tenant_id:
                logger.error("No tenant context available for link tracking")
                return None
                
            tracking_id = str(uuid.uuid4())
            
            engine = get_shared_engine()
            with engine.connect() as conn:
                with conn.begin():
                    conn.execute(text("""
                        INSERT INTO link_tracking (tracking_id, original_url, campaign_id, company_id, contact_email, tenant_id)
                        VALUES (:tracking_id, :original_url, :campaign_id, :company_id, :contact_email, :tenant_id)
                    """), {
                        'tracking_id': tracking_id,
                        'original_url': original_url,
                        'campaign_id': campaign_id,
                        'company_id': company_id,
                        'contact_email': contact_email,
                        'tenant_id': tenant_id
                    })
            
            logger.info(f"Created link tracking record: {tracking_id} for {original_url}")
            return tracking_id
            
        except Exception as e:
            logger.error(f"Failed to create link tracking record: {e}")
            return None
    
    @staticmethod
    def get_link_tracking_analytics(campaign_id: Optional[int] = None, 
                                  company_id: Optional[int] = None,
                                  days_back: int = 30) -> Dict:
        """
        Get link tracking analytics for campaigns.
        
        Args:
            campaign_id: Optional specific campaign ID
            company_id: Optional specific company ID
            days_back: Number of days to look back for analytics
            
        Returns:
            Dictionary with analytics data
        """
        try:
            tenant_id = current_tenant_id()
            if not tenant_id:
                return {'error': 'No tenant context'}
            
            engine = get_shared_engine()
            with engine.connect() as conn:
                # Base query for link tracking data - using click data from link_tracking table itself
                base_query = """
                    SELECT 
                        lt.tracking_id,
                        lt.original_url,
                        lt.campaign_id,
                        lt.company_id,
                        lt.contact_email,
                        lt.created_at,
                        lt.click_count,
                        lt.last_clicked_at as last_clicked
                    FROM link_tracking lt
                    WHERE lt.tenant_id = :tenant_id
                    AND lt.created_at >= NOW() - INTERVAL ':days_back days'
                """
                
                params = {'tenant_id': tenant_id, 'days_back': days_back}
                
                if campaign_id:
                    base_query += " AND lt.campaign_id = :campaign_id"
                    params['campaign_id'] = campaign_id
                    
                if company_id:
                    base_query += " AND lt.company_id = :company_id" 
                    params['company_id'] = company_id
                
                # No need for GROUP BY since we're not using LEFT JOIN anymore
                base_query += " ORDER BY lt.created_at DESC"
                
                result = conn.execute(text(base_query), params)
                rows = result.fetchall()
                
                # Process results
                link_analytics = []
                total_links = len(rows)
                total_clicks = 0
                
                for row in rows:
                    click_count = row.click_count or 0
                    link_data = {
                        'tracking_id': row.tracking_id,
                        'original_url': row.original_url,
                        'campaign_id': row.campaign_id,
                        'company_id': row.company_id,
                        'contact_email': row.contact_email,
                        'created_at': row.created_at.isoformat() if row.created_at else None,
                        'click_count': click_count,
                        'last_clicked': row.last_clicked.isoformat() if row.last_clicked else None
                    }
                    link_analytics.append(link_data)
                    total_clicks += click_count
                
                return {
                    'success': True,
                    'analytics': {
                        'total_links': total_links,
                        'total_clicks': total_clicks,
                        'click_through_rate': round((total_clicks / total_links * 100), 2) if total_links > 0 else 0,
                        'links': link_analytics
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to get link tracking analytics: {e}")
            return {'error': str(e), 'success': False}
    
    @staticmethod
    def record_click(tracking_id: str, user_agent: str = None, ip_address: str = None, 
                    referer: str = None) -> bool:
        """
        Record a click event for a tracked link.
        
        Args:
            tracking_id: The tracking ID of the clicked link
            user_agent: User agent string
            ip_address: IP address of the clicker
            referer: HTTP referer header
            
        Returns:
            True if click was recorded successfully, False otherwise
        """
        try:
            tenant_id = current_tenant_id()
            if not tenant_id:
                logger.error("No tenant context available for click tracking")
                return False
            
            engine = get_shared_engine()
            with engine.connect() as conn:
                with conn.begin():
                    # First verify the tracking_id exists and belongs to this tenant
                    link_result = conn.execute(text("""
                        SELECT id FROM link_tracking 
                        WHERE tracking_id = :tracking_id AND tenant_id = :tenant_id
                    """), {
                        'tracking_id': tracking_id,
                        'tenant_id': tenant_id
                    })
                    
                    if not link_result.fetchone():
                        logger.warning(f"Invalid tracking ID or tenant mismatch: {tracking_id}")
                        return False
                    
                    # Record the click - we need to create the link_clicks table first
                    # For now, we'll extend the link_tracking table to include click data
                    # This is a simplified approach - in production you'd want separate click records
                    conn.execute(text("""
                        UPDATE link_tracking 
                        SET 
                            last_clicked_at = CURRENT_TIMESTAMP,
                            click_count = COALESCE(click_count, 0) + 1,
                            last_user_agent = :user_agent,
                            last_ip_address = :ip_address,
                            last_referer = :referer
                        WHERE tracking_id = :tracking_id AND tenant_id = :tenant_id
                    """), {
                        'tracking_id': tracking_id,
                        'tenant_id': tenant_id,
                        'user_agent': user_agent[:500] if user_agent else None,  # Limit length
                        'ip_address': ip_address[:50] if ip_address else None,
                        'referer': referer[:500] if referer else None
                    })
            
            logger.info(f"Recorded click for tracking ID: {tracking_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to record click for tracking ID {tracking_id}: {e}")
            return False