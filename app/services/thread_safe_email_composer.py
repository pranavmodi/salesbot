# Thread-safe wrapper for email composition operations
import threading
import weakref
import gc
from typing import Dict, Optional, Any
from contextlib import contextmanager
import time
import logging

logger = logging.getLogger(__name__)

class ThreadSafeEmailComposer:
    """Thread-safe wrapper for email composition with proper memory management."""
    
    def __init__(self):
        self._local = threading.local()
        self._session_pool = weakref.WeakValueDictionary()
        self._lock = threading.RLock()
        self._cleanup_timer = None
        self._start_cleanup_timer()
    
    def _start_cleanup_timer(self):
        """Start periodic cleanup of resources."""
        def cleanup():
            try:
                with self._lock:
                    # Force garbage collection
                    collected = gc.collect()
                    logger.debug(f"Garbage collected {collected} objects")
                    
                    # Clear weak references that may be stale
                    stale_keys = [k for k, v in self._session_pool.items() if v is None]
                    for key in stale_keys:
                        self._session_pool.pop(key, None)
                        
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
            finally:
                # Reschedule cleanup
                self._cleanup_timer = threading.Timer(60.0, cleanup)
                self._cleanup_timer.daemon = True
                self._cleanup_timer.start()
        
        cleanup()
    
    def _get_tenant_api_key(self, key_name: str):
        """Get tenant-specific API key or fallback to environment variable."""
        try:
            from app.tenant import current_tenant_id
            from app.models.tenant_settings import TenantSettings
            
            tenant_id = current_tenant_id()
            if tenant_id:
                tenant_key = TenantSettings.get_api_key(tenant_id, key_name)
                if tenant_key:
                    return tenant_key
                else:
                    logger.debug(f"No tenant-specific {key_name} found for tenant {tenant_id}, using fallback")
            else:
                logger.debug(f"No tenant context available, using fallback {key_name}")
        except Exception as e:
            logger.debug(f"Error getting tenant API key {key_name}: {e}, using fallback")
        
        # Fallback to environment variables
        import os
        fallback_keys = {
            'openai_api_key': os.getenv("OPENAI_API_KEY"),
            'anthropic_api_key': os.getenv("ANTHROPIC_API_KEY"),
            'perplexity_api_key': os.getenv("PERPLEXITY_API_KEY")
        }
        return fallback_keys.get(key_name)
    
    @contextmanager
    def _get_safe_openai_client(self):
        """Get thread-local OpenAI client with tenant-specific API key and proper cleanup."""
        import os
        from openai import OpenAI
        
        # Get tenant-specific API key
        openai_api_key = self._get_tenant_api_key('openai_api_key')
        if not openai_api_key:
            logger.error("No OpenAI API key available (tenant-specific or fallback)")
            yield None
            return
        
        # Create client with tenant-specific key (don't cache since tenant context may change)
        client = OpenAI(
            api_key=openai_api_key,
            timeout=30.0,
            max_retries=2
        )
        
        try:
            yield client
        finally:
            # Don't close client - reuse it for this thread
            pass
    
    @contextmanager
    def _get_safe_http_session(self):
        """Get thread-local HTTP session with proper cleanup."""
        import requests
        
        thread_id = threading.get_ident()
        
        # Try to get existing session for this thread
        session = self._session_pool.get(thread_id)
        
        if session is None:
            session = requests.Session()
            # Configure session for better memory management
            session.mount('https://', requests.adapters.HTTPAdapter(
                pool_connections=1,
                pool_maxsize=1,
                max_retries=2
            ))
            session.mount('http://', requests.adapters.HTTPAdapter(
                pool_connections=1,
                pool_maxsize=1,
                max_retries=2
            ))
            self._session_pool[thread_id] = session
        
        try:
            yield session
        finally:
            # Keep session alive for reuse, but ensure it's cleaned up properly
            pass
    
    def _safe_string_operation(self, operation_func, *args, max_size_mb=10, **kwargs):
        """Safely perform string operations with size limits."""
        try:
            # Check input size
            total_size = 0
            for arg in args:
                if isinstance(arg, str):
                    total_size += len(arg.encode('utf-8'))
            
            if total_size > max_size_mb * 1024 * 1024:
                logger.warning(f"String operation input too large: {total_size / 1024 / 1024:.2f}MB")
                raise ValueError(f"Input too large: {total_size / 1024 / 1024:.2f}MB > {max_size_mb}MB")
            
            # Perform operation
            result = operation_func(*args, **kwargs)
            
            # Check result size
            if isinstance(result, str):
                result_size = len(result.encode('utf-8'))
                if result_size > max_size_mb * 1024 * 1024:
                    logger.warning(f"String operation result too large: {result_size / 1024 / 1024:.2f}MB")
                    # Truncate instead of failing
                    max_chars = max_size_mb * 1024 * 1024 // 4  # Rough estimate for UTF-8
                    result = result[:max_chars] + "... [truncated for safety]"
            
            return result
            
        except Exception as e:
            logger.error(f"Safe string operation failed: {e}")
            raise
        finally:
            # Force garbage collection after large string operations
            if total_size > 1024 * 1024:  # 1MB threshold
                gc.collect()
    
    @contextmanager
    def _safe_database_operation(self):
        """Perform database operations with thread-safe session management."""
        from app.database import db
        
        # Ensure we have a fresh database session for this thread
        try:
            # Create a new session for this operation
            db.session.remove()  # Remove any existing session
            yield db
        except Exception as e:
            db.session.rollback()
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            try:
                db.session.commit()
            except:
                db.session.rollback()
            finally:
                db.session.remove()  # Clean up session
    
    def compose_email_safely(self, lead: Dict[str, str], calendar_url: str, 
                           extra_context: Optional[str] = None, 
                           composer_type: str = "deep_research", 
                           campaign_id: Optional[int] = None) -> Optional[Dict[str, str]]:
        """Thread-safe email composition with proper memory management."""
        
        thread_id = threading.get_ident()
        logger.info(f"Thread {thread_id}: Starting safe email composition for {lead.get('company', 'Unknown')}")
        
        try:
            # Import the actual composer
            from email_composers.email_composer_deep_research import DeepResearchEmailComposer
            
            # Create thread-local composer instance
            if not hasattr(self._local, 'composer'):
                self._local.composer = DeepResearchEmailComposer()
            
            composer = self._local.composer
            
            # Patch the composer methods for thread safety
            original_openai_client = composer.client
            original_publish_method = composer._publish_report_to_netlify
            
            try:
                # Replace with thread-safe versions
                with self._get_safe_openai_client() as safe_client:
                    if safe_client:
                        composer.client = safe_client
                    else:
                        logger.error("No OpenAI client available for email composition")
                        return None
                    
                    # Patch the HTTP request method
                    def safe_publish_report(company, recipient_email, campaign_id=None):
                        return self._safe_publish_report_to_netlify(
                            composer, company, recipient_email, campaign_id
                        )
                    
                    composer._publish_report_to_netlify = safe_publish_report
                    
                    # Perform the actual composition with size limits
                    result = self._safe_string_operation(
                        composer.compose_email,
                        lead, calendar_url, extra_context, None, campaign_id,
                        max_size_mb=5  # Limit email size to 5MB
                    )
                    
                    logger.info(f"Thread {thread_id}: Email composition completed successfully")
                    return result
                    
            finally:
                # Restore original methods
                composer.client = original_openai_client
                composer._publish_report_to_netlify = original_publish_method
                
        except Exception as e:
            logger.error(f"Thread {thread_id}: Email composition failed: {e}")
            return None
        finally:
            # Force cleanup for this thread
            gc.collect()
    
    def _safe_publish_report_to_netlify(self, composer, company, recipient_email, campaign_id=None):
        """Thread-safe version of report publishing."""
        try:
            with self._get_safe_http_session() as session:
                # Use the existing logic but with our safe session
                import json
                import hashlib
                import hmac
                import urllib.parse
                from datetime import datetime
                
                # Import constants directly since composer instance may not have them 
                import os
                NETLIFY_PUBLISH_URL = os.getenv("NETLIFY_PUBLISH_URL", "https://possibleminds.in/.netlify/functions/publish-report-persistent")
                NETLIFY_SECRET = os.getenv("NETLIFY_WEBHOOK_SECRET", "")
                
                logger.info(f"Thread {threading.get_ident()}: Publishing report for {company.company_name}")
                
                # Limit report size to prevent memory issues
                html_report = company.html_report
                if html_report and len(html_report) > 5 * 1024 * 1024:  # 5MB limit
                    logger.warning(f"HTML report too large ({len(html_report)} chars), truncating")
                    html_report = html_report[:5 * 1024 * 1024] + "... [truncated for email safety]"
                
                payload = {
                    "company_id": f"comp_{company.id}",
                    "company_name": company.company_name,
                    "company_website": company.website_url or "",
                    "contact_id": f"contact_{recipient_email.split('@')[0]}",
                    "generated_date": datetime.now().strftime("%Y-%m-%d"),
                    "html_report": html_report
                }
                
                raw_body = json.dumps(payload, separators=(',', ':'))
                headers = {"Content-Type": "application/json"}
                
                if NETLIFY_SECRET:
                    signature = hmac.new(
                        NETLIFY_SECRET.encode('utf-8'),
                        raw_body.encode('utf-8'),
                        hashlib.sha256
                    ).hexdigest()
                    headers["X-Hub-Signature-256"] = f"sha256={signature}"
                
                # Use our thread-safe session with timeout
                response = session.post(
                    NETLIFY_PUBLISH_URL,
                    headers=headers,
                    data=raw_body,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    public_url = result.get('data', {}).get('publishUrl') or result.get('public_url')
                    
                    if public_url:
                        # Create tracking URL
                        import re
                        slug_match = re.search(r'/reports/([^/?]+)', public_url)
                        company_slug = slug_match.group(1) if slug_match else company.company_name.lower().replace(' ', '-').replace('&', 'and')
                        
                        tracking_params = {
                            'slug': company_slug,
                            'utm_source': 'email',
                            'utm_medium': 'outreach',
                            'utm_campaign': 'deep_research',
                            'utm_content': 'strategic_analysis',
                            'company': company.company_name.lower().replace(' ', '_'),
                            'recipient': recipient_email.split('@')[0] if recipient_email else 'unknown',
                            'campaign_id': campaign_id if campaign_id else 'unknown'
                        }
                        
                        base_tracking_url = "https://possibleminds.in/.netlify/functions/click-tracking"
                        url_params = urllib.parse.urlencode(tracking_params)
                        tracked_url = f"{base_tracking_url}?{url_params}"
                        
                        logger.info(f"Thread {threading.get_ident()}: Report published successfully")
                        return tracked_url
                
                logger.error(f"Thread {threading.get_ident()}: Report publishing failed ({response.status_code})")
                return ""
                
        except Exception as e:
            logger.error(f"Thread {threading.get_ident()}: Report publishing error: {e}")
            return ""
        finally:
            # Force cleanup after HTTP operations
            gc.collect()
    
    def __del__(self):
        """Cleanup resources when composer is destroyed."""
        try:
            if self._cleanup_timer:
                self._cleanup_timer.cancel()
            
            # Close all sessions in pool
            for session in self._session_pool.values():
                try:
                    session.close()
                except:
                    pass
            
            self._session_pool.clear()
            
        except:
            pass

# Global thread-safe instance
_thread_safe_composer = None
_composer_lock = threading.Lock()

def get_thread_safe_composer():
    """Get the global thread-safe email composer instance."""
    global _thread_safe_composer
    
    if _thread_safe_composer is None:
        with _composer_lock:
            if _thread_safe_composer is None:
                _thread_safe_composer = ThreadSafeEmailComposer()
    
    return _thread_safe_composer