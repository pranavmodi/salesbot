from datetime import datetime, timedelta
import time
import pytz
from typing import Dict, List, Optional
from flask import current_app
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
import os
import logging

from app.models.campaign import Campaign
from app.models.contact import Contact
from app.services.email_service import EmailService

# Static event listeners to avoid serialization issues
def job_executed_listener(event):
    """Handle job execution events."""
    try:
        from flask import current_app
        current_app.logger.info(f"Job {event.job_id} executed successfully")
    except:
        print(f"Job {event.job_id} executed successfully")

def job_error_listener(event):
    """Handle job error events."""
    try:
        from flask import current_app
        current_app.logger.error(f"Job {event.job_id} failed: {event.exception}")
    except:
        print(f"Job {event.job_id} failed: {event.exception}")

# Static campaign execution function to avoid serialization issues
def execute_campaign_job(campaign_id: int):
    """Static function to execute a campaign - used by scheduler."""
    from flask import current_app
    from app import create_app
    
    # Create application context for background job
    app = create_app()
    with app.app_context():
        try:
            current_app.logger.info(f"Starting execution of campaign {campaign_id}")
            
            # Get campaign details
            campaign = Campaign.get_by_id(campaign_id)
            if not campaign:
                current_app.logger.error(f"Campaign {campaign_id} not found during execution")
                return
            
            # Check if campaign is paused
            if campaign.status == 'paused':
                current_app.logger.info(f"Campaign {campaign_id} is paused, skipping execution")
                return
            
            # Update status to active
            Campaign.update_status(campaign_id, 'active')
            
            # Get campaign settings
            settings = Campaign.get_campaign_settings(campaign_id)
            email_frequency = settings.get('email_frequency', {'value': 30, 'unit': 'minutes'})
            timezone_str = settings.get('timezone', 'America/Los_Angeles')
            daily_limit = settings.get('daily_email_limit', 50)
            respect_business_hours = settings.get('respect_business_hours', True)
            business_hours = settings.get('business_hours', {})
            
            # Get contacts that need to be processed
            pending_contacts = Campaign.get_campaign_contacts(campaign_id, status='active')
            
            if not pending_contacts:
                current_app.logger.info(f"No pending contacts for campaign {campaign_id}")
                Campaign.update_status(campaign_id, 'completed')
                return
            
            # Process contacts with rate limiting
            from app.models.email_history import EmailHistory
            emails_sent_today = EmailHistory.get_daily_count_for_campaign(campaign_id, datetime.now().date())
            
            for contact in pending_contacts:
                try:
                    # Check if campaign was paused during execution
                    current_campaign = Campaign.get_by_id(campaign_id)
                    if current_campaign.status == 'paused':
                        current_app.logger.info(f"Campaign {campaign_id} paused during execution")
                        break
                    
                    # Check daily limit
                    if emails_sent_today >= daily_limit:
                        current_app.logger.info(f"Daily email limit reached for campaign {campaign_id}")
                        # Would schedule for next day here
                        break
                    
                    # Check business hours
                    if respect_business_hours and not _is_business_hours(timezone_str, business_hours):
                        current_app.logger.info(f"Outside business hours for campaign {campaign_id}")
                        # Would schedule for next business hour here
                        break
                    
                    # Send email to contact
                    success = _send_campaign_email(campaign_id, contact, settings)
                    
                    if success:
                        # Mark contact as completed
                        Campaign.update_contact_status_in_campaign(
                            campaign_id, contact['email'], 'completed'
                        )
                        emails_sent_today += 1
                        
                        current_app.logger.info(f"Email sent to {contact['email']} for campaign {campaign_id}")
                    else:
                        # Mark contact as failed
                        Campaign.update_contact_status_in_campaign(
                            campaign_id, contact['email'], 'failed'
                        )
                        current_app.logger.error(f"Failed to send email to {contact['email']} for campaign {campaign_id}")
                    
                    # Apply frequency delay
                    if email_frequency['unit'] == 'minutes':
                        delay_seconds = email_frequency['value'] * 60
                    else:  # hours
                        delay_seconds = email_frequency['value'] * 3600
                    
                    # Don't delay on the last contact
                    remaining_contacts = Campaign.get_campaign_contacts(campaign_id, status='active')
                    if remaining_contacts:
                        current_app.logger.info(f"Waiting {email_frequency['value']} {email_frequency['unit']} before next email")
                        time.sleep(delay_seconds)
                
                except Exception as contact_error:
                    current_app.logger.error(f"Error processing contact {contact.get('email', 'unknown')}: {contact_error}")
                    continue
            
            # Check if campaign is complete
            remaining_contacts = Campaign.get_campaign_contacts(campaign_id, status='active')
            if not remaining_contacts:
                Campaign.update_status(campaign_id, 'completed')
                current_app.logger.info(f"Campaign {campaign_id} completed successfully")
                
        except Exception as e:
            current_app.logger.error(f"Error executing campaign {campaign_id}: {e}")
            Campaign.update_status(campaign_id, 'failed')

def _send_campaign_email(campaign_id: int, contact: Dict, settings: Dict) -> bool:
    """Send email for a specific campaign contact."""
    try:
        # Get campaign details for email composition
        campaign = Campaign.get_by_id(campaign_id)
        
        # Generate email content
        email_content = EmailService.compose_email(
            contact_id=None,
            calendar_url=os.getenv("CALENDAR_URL", "https://calendly.com/pranav-modi/15-minute-meeting"),
            extra_context=f"This email is part of the '{campaign.name}' campaign.",
            composer_type=settings.get('email_template', 'warm')
        )
        
        if not email_content:
            # Fallback email composition
            email_content = _compose_fallback_email(campaign, contact, settings)
        
        if email_content and 'subject' in email_content and 'body' in email_content:
            # Send the email
            recipient_name = contact.get('display_name') or contact.get('full_name') or f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
            
            success = EmailService.send_email_with_account(
                contact['email'],
                recipient_name,
                email_content['subject'],
                email_content['body'],
                None,  # Use primary account
                campaign_id=campaign_id  # Associate with campaign
            )
            
            return success
        
        return False
        
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Error sending campaign email: {e}")
        return False

def _compose_fallback_email(campaign: Campaign, contact: Dict, settings: Dict) -> Dict:
    """Compose fallback email when main composer fails."""
    try:
        from email_composers.email_composer_warm import WarmEmailComposer
        from email_composers.email_composer_alt_subject import AltSubjectEmailComposer
        from email_composers.email_composer_deep_research import DeepResearchEmailComposer
        
        template_type = settings.get('email_template', 'deep_research')  # Changed default to deep_research
        
        if template_type == "alt_subject":
            composer = AltSubjectEmailComposer()
        elif template_type == "deep_research":
            composer = DeepResearchEmailComposer()
        else:
            composer = WarmEmailComposer()
        
        lead_data = {
            "name": contact.get('display_name') or contact.get('full_name') or f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip(),
            "email": contact.get('email'),
            "company": contact.get('company'),
            "position": contact.get('job_title'),
            "website": contact.get('company_domain'),
            "notes": f"Campaign: {campaign.name}",
        }
        
        calendar_url = os.getenv("CALENDAR_URL", "https://calendly.com/pranav-modi/15-minute-meeting")
        email_content = composer.compose_email(
            lead=lead_data, 
            calendar_url=calendar_url, 
            extra_context=f"This email is part of the '{campaign.name}' campaign."
        )
        
        return email_content
        
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Error in fallback email composition: {e}")
        return {}

def _is_business_hours(timezone_str: str, business_hours: Dict) -> bool:
    """Check if current time is within business hours."""
    try:
        if not business_hours:
            return True
        
        tz = pytz.timezone(timezone_str)
        current_time = datetime.now(tz)
        
        # Check if current day is a business day
        weekday = current_time.strftime('%A').lower()
        if not business_hours.get('days', {}).get(weekday, True):
            return False
        
        # Check if current time is within business hours
        start_time = datetime.strptime(business_hours.get('start_time', '09:00'), '%H:%M').time()
        end_time = datetime.strptime(business_hours.get('end_time', '17:00'), '%H:%M').time()
        
        current_time_only = current_time.time()
        return start_time <= current_time_only <= end_time
        
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Error checking business hours: {e}")
        return True  # Default to allowing emails

class CampaignScheduler:
    """Background campaign scheduler with pause/resume functionality."""
    
    def __init__(self):
        self.scheduler = None
        self.running_campaigns = {}  # Track active campaign jobs
        self._setup_scheduler()
    
    def _setup_scheduler(self):
        """Setup APScheduler with database persistence."""
        try:
            # Configure job store to use same database
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                current_app.logger.error("DATABASE_URL not configured for scheduler")
                return
            
            jobstores = {
                'default': SQLAlchemyJobStore(url=database_url, tablename='scheduler_jobs')
            }
            
            executors = {
                'default': ThreadPoolExecutor(20),
            }
            
            job_defaults = {
                'coalesce': False,
                'max_instances': 3
            }
            
            self.scheduler = BackgroundScheduler(
                jobstores=jobstores,
                executors=executors,
                job_defaults=job_defaults,
                timezone=pytz.UTC
            )
            
            # Add event listeners using static methods to avoid serialization issues
            self.scheduler.add_listener(job_executed_listener, EVENT_JOB_EXECUTED)
            self.scheduler.add_listener(job_error_listener, EVENT_JOB_ERROR)
            
            current_app.logger.info("Campaign scheduler initialized successfully")
            
        except Exception as e:
            current_app.logger.error(f"Failed to setup campaign scheduler: {e}")
    
    def start(self):
        """Start the scheduler."""
        if self.scheduler and not self.scheduler.running:
            try:
                self.scheduler.start()
                current_app.logger.info("Campaign scheduler started")
            except Exception as e:
                current_app.logger.error(f"Failed to start scheduler: {e}")
    
    def stop(self):
        """Stop the scheduler."""
        if self.scheduler and self.scheduler.running:
            try:
                self.scheduler.shutdown()
                current_app.logger.info("Campaign scheduler stopped")
            except Exception as e:
                current_app.logger.error(f"Failed to stop scheduler: {e}")
    
    def _job_executed(self, event):
        """Handle job execution events."""
        current_app.logger.info(f"Job {event.job_id} executed successfully")
    
    def _job_error(self, event):
        """Handle job error events."""
        current_app.logger.error(f"Job {event.job_id} failed: {event.exception}")
    
    def schedule_campaign(self, campaign_id: int, schedule_date: Optional[str] = None) -> bool:
        """Schedule a campaign for execution."""
        try:
            # Get campaign from database
            campaign = Campaign.get_by_id(campaign_id)
            if not campaign:
                current_app.logger.error(f"Campaign {campaign_id} not found")
                return False
            
            # If no schedule date, start immediately
            if not schedule_date:
                job_id = f"campaign_{campaign_id}_immediate"
                self.scheduler.add_job(
                    func=execute_campaign_job,
                    args=[campaign_id],
                    id=job_id,
                    replace_existing=True
                )
                current_app.logger.info(f"Campaign {campaign_id} scheduled for immediate execution")
            else:
                # Parse schedule date and schedule for future
                schedule_dt = datetime.fromisoformat(schedule_date.replace('Z', '+00:00'))
                job_id = f"campaign_{campaign_id}_scheduled"
                self.scheduler.add_job(
                    func=execute_campaign_job,
                    args=[campaign_id],
                    trigger='date',
                    run_date=schedule_dt,
                    id=job_id,
                    replace_existing=True
                )
                current_app.logger.info(f"Campaign {campaign_id} scheduled for {schedule_dt}")
            
            # Update campaign status
            Campaign.update_status(campaign_id, 'scheduled')
            return True
            
        except Exception as e:
            current_app.logger.error(f"Failed to schedule campaign {campaign_id}: {e}")
            return False
    
    def pause_campaign(self, campaign_id: int) -> bool:
        """Pause a running campaign."""
        try:
            # Update campaign status
            success = Campaign.update_status(campaign_id, 'paused')
            
            if success:
                # Remove any scheduled jobs for this campaign
                job_id = f"campaign_{campaign_id}_resume"
                try:
                    self.scheduler.remove_job(job_id)
                except:
                    pass  # Job might not exist
                
                current_app.logger.info(f"Campaign {campaign_id} paused successfully")
                return True
            
            return False
            
        except Exception as e:
            current_app.logger.error(f"Error pausing campaign {campaign_id}: {e}")
            return False
    
    def resume_campaign(self, campaign_id: int) -> bool:
        """Resume a paused campaign."""
        try:
            # Update campaign status
            success = Campaign.update_status(campaign_id, 'active')
            
            if success:
                # Schedule immediate execution
                job_id = f"campaign_{campaign_id}_resume"
                self.scheduler.add_job(
                    func=execute_campaign_job,
                    args=[campaign_id],
                    id=job_id,
                    replace_existing=True
                )
                
                current_app.logger.info(f"Campaign {campaign_id} resumed successfully")
                return True
            
            return False
            
        except Exception as e:
            current_app.logger.error(f"Error resuming campaign {campaign_id}: {e}")
            return False
    
    def get_campaign_status(self, campaign_id: int) -> Dict:
        """Get detailed status of a campaign."""
        try:
            campaign = Campaign.get_by_id(campaign_id)
            if not campaign:
                return {'error': 'Campaign not found'}
            
            # Get contact statistics
            stats = Campaign.get_campaign_stats(campaign_id)
            
            # Get running status
            running_info = self.running_campaigns.get(campaign_id, {})
            
            return {
                'id': campaign_id,
                'name': campaign.name,
                'status': campaign.status,
                'created_at': campaign.created_at,
                'updated_at': campaign.updated_at,
                'stats': stats,
                'running_info': running_info
            }
            
        except Exception as e:
            current_app.logger.error(f"Error getting campaign status: {e}")
            return {'error': str(e)}

# Global scheduler instance
campaign_scheduler = CampaignScheduler() 