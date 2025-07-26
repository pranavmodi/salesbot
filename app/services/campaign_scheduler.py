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

# Reduce APScheduler logging noise
logging.getLogger('apscheduler.executors.default').setLevel(logging.WARNING)
logging.getLogger('apscheduler.scheduler').setLevel(logging.WARNING)

from app.models.campaign import Campaign
from app.models.contact import Contact
from app.models.campaign_email_job import CampaignEmailJob
from app.services.email_service import EmailService

# Static event listeners to avoid serialization issues
def job_executed_listener(event):
    """Handle job execution events."""
    # Only log non-background job executions to reduce noise
    if not event.job_id.startswith('process_pending_emails'):
        try:
            from flask import current_app
            current_app.logger.info(f"Job {event.job_id} executed successfully")
        except:
            pass  # Silent in case of context issues

def job_error_listener(event):
    """Handle job error events."""
    try:
        from flask import current_app
        current_app.logger.error(f"Job {event.job_id} failed: {event.exception}")
    except:
        print(f"Job {event.job_id} failed: {event.exception}")

# Static campaign execution function - starts individual email scheduling
def execute_campaign_job(campaign_id: int):
    """Static function to start a campaign by scheduling individual emails."""
    from flask import current_app
    from app import create_app
    import random
    
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
            
            current_app.logger.info(f"Scheduling {len(pending_contacts)} individual emails for campaign {campaign_id}")
            
            # Schedule individual email jobs with configurable random delays
            base_delay_minutes = email_frequency['value'] if email_frequency['unit'] == 'minutes' else email_frequency['value'] * 60
            
            # Get random delay configuration from settings
            random_delay_config = settings.get('random_delay', {'min_minutes': 1, 'max_minutes': 5})
            min_random_minutes = random_delay_config.get('min_minutes', 1)
            max_random_minutes = random_delay_config.get('max_minutes', 5)
            
            def calculate_delay(index):
                base_seconds = base_delay_minutes * 60
                # Add configurable random delay
                random_additional_minutes = random.randint(min_random_minutes, max_random_minutes)
                random_additional_seconds = random_additional_minutes * 60
                total_delay = base_seconds + random_additional_seconds
                return max(60, int(total_delay))  # Minimum 1 minute delay
            
            # Create persistent email jobs in database
            cumulative_delay = 0
            scheduled_count = 0
            
            from app.models.campaign_email_job import CampaignEmailJob
            
            for i, contact in enumerate(pending_contacts):
                try:
                    if i == 0:
                        # First email can be sent immediately or with minimal delay
                        delay_seconds = random.randint(30, 120)  # 30 seconds to 2 minutes
                    else:
                        # Subsequent emails with random delays
                        delay_seconds = calculate_delay(i)
                    
                    cumulative_delay += delay_seconds
                    
                    # Schedule the individual email in database
                    run_time = datetime.now() + timedelta(seconds=cumulative_delay)
                    
                    # Create a serializable version of the contact data
                    serializable_contact = {
                        'id': contact.get('id'),
                        'email': contact.get('email'),
                        'first_name': contact.get('first_name'),
                        'last_name': contact.get('last_name'),
                        'full_name': contact.get('full_name'),
                        'job_title': contact.get('job_title'),
                        'company_name': contact.get('company_name'),
                        'company_domain': contact.get('company_domain'),
                        'linkedin_profile': contact.get('linkedin_profile'),
                        'location': contact.get('location'),
                        'company_id': contact.get('company_id')
                    }

                    # Create a clean, serializable version of settings
                    serializable_settings = {
                        'email_frequency': settings.get('email_frequency'),
                        'random_delay': settings.get('random_delay'),
                        'timezone': settings.get('timezone'),
                        'daily_email_limit': settings.get('daily_email_limit'),
                        'respect_business_hours': settings.get('respect_business_hours'),
                        'business_hours': settings.get('business_hours'),
                        'email_template': settings.get('email_template')
                    }

                    email_job = CampaignEmailJob(
                        campaign_id=campaign_id,
                        contact_email=contact['email'],
                        contact_data=serializable_contact,
                        campaign_settings=serializable_settings,
                        scheduled_time=run_time,
                        status='pending'
                    )
                    
                    if email_job.save():
                        scheduled_count += 1
                        current_app.logger.info(f"Scheduled email {i+1}/{len(pending_contacts)} to {contact['email']} for {run_time} (delay: {delay_seconds}s)")
                    else:
                        current_app.logger.error(f"Failed to save email job for {contact['email']}")
                    
                except Exception as e:
                    current_app.logger.error(f"Error scheduling email for {contact.get('email', 'unknown')}: {e}")
                    continue
            
            current_app.logger.info(f"Campaign {campaign_id} email scheduling completed: {scheduled_count} emails scheduled over {cumulative_delay/60:.1f} minutes")
                
        except Exception as e:
            current_app.logger.error(f"Error scheduling campaign {campaign_id}: {e}")
            Campaign.update_status(campaign_id, 'failed')

# Static function to execute a single email within a campaign
def execute_single_email_job(campaign_id: int, contact: Dict, settings: Dict):
    """Execute a single email within a campaign."""
    from flask import current_app
    from app import create_app
    
    app = create_app()
    with app.app_context():
        try:
            # Check if campaign is still active
            campaign = Campaign.get_by_id(campaign_id)
            if not campaign:
                current_app.logger.error(f"Campaign {campaign_id} not found during single email execution")
                return
            
            if campaign.status == 'paused':
                current_app.logger.info(f"Campaign {campaign_id} is paused, skipping email to {contact['email']}")
                return
            
            if campaign.status not in ['active', 'scheduled']:
                current_app.logger.info(f"Campaign {campaign_id} status is {campaign.status}, skipping email to {contact['email']}")
                return
            
            # Check business hours if required
            timezone_str = settings.get('timezone', 'America/Los_Angeles')
            respect_business_hours = settings.get('respect_business_hours', True)
            business_hours = settings.get('business_hours', {})
            
            if respect_business_hours and not _is_business_hours(timezone_str, business_hours):
                current_app.logger.info(f"Outside business hours for campaign {campaign_id}, rescheduling email to {contact['email']}")
                # Reschedule for next business hour
                _reschedule_for_business_hours(campaign_id, contact, settings, timezone_str, business_hours)
                return
            
            # Check daily limit
            from app.models.email_history import EmailHistory
            daily_limit = settings.get('daily_email_limit', 50)
            emails_sent_today = EmailHistory.get_daily_count_for_campaign(campaign_id, datetime.now().date())
            
            if emails_sent_today >= daily_limit:
                current_app.logger.info(f"Daily email limit reached for campaign {campaign_id}, rescheduling email to {contact['email']}")
                # Reschedule for tomorrow
                _reschedule_for_next_day(campaign_id, contact, settings)
                return
            
            current_app.logger.info(f"Executing single email for campaign {campaign_id} to {contact['email']}")
            
            # Send email to contact
            success = _send_campaign_email(campaign_id, contact, settings)
            
            if success:
                # Mark contact as completed
                Campaign.update_contact_status_in_campaign(
                    campaign_id, contact['email'], 'completed'
                )
                current_app.logger.info(f"Email sent successfully to {contact['email']} for campaign {campaign_id}")
            else:
                # Mark contact as failed
                Campaign.update_contact_status_in_campaign(
                    campaign_id, contact['email'], 'failed'
                )
                current_app.logger.error(f"Failed to send email to {contact['email']} for campaign {campaign_id}")
            
            # Check if campaign is complete
            remaining_contacts = Campaign.get_campaign_contacts(campaign_id, status='active')
            if not remaining_contacts:
                Campaign.update_status(campaign_id, 'completed')
                current_app.logger.info(f"Campaign {campaign_id} completed successfully")
                
        except Exception as e:
            current_app.logger.error(f"Error executing single email for campaign {campaign_id}, contact {contact.get('email', 'unknown')}: {e}")
            # Mark contact as failed
            try:
                Campaign.update_contact_status_in_campaign(
                    campaign_id, contact['email'], 'failed'
                )
            except:
                pass

def _reschedule_for_business_hours(campaign_id: int, contact: Dict, settings: Dict, timezone_str: str, business_hours: Dict):
    """Reschedule email for next business hours."""
    try:
        import pytz
        from app.services.campaign_scheduler import campaign_scheduler
        
        tz = pytz.timezone(timezone_str)
        current_time = datetime.now(tz)
        
        # Calculate next business hour
        start_time = datetime.strptime(business_hours.get('start_time', '09:00'), '%H:%M').time()
        next_send_time = None
        
        # Try today first
        today_start = current_time.replace(hour=start_time.hour, minute=start_time.minute, second=0, microsecond=0)
        if today_start > current_time:
            weekday = current_time.strftime('%A').lower()
            if business_hours.get('days', {}).get(weekday, True):
                next_send_time = today_start
        
        # If not today, find next business day
        if not next_send_time:
            for days_ahead in range(1, 8):
                check_date = current_time + timedelta(days=days_ahead)
                weekday = check_date.strftime('%A').lower()
                if business_hours.get('days', {}).get(weekday, True):
                    next_send_time = check_date.replace(hour=start_time.hour, minute=start_time.minute, second=0, microsecond=0)
                    break
        
        if next_send_time:
            # Convert to UTC for scheduler
            next_send_time_utc = next_send_time.astimezone(pytz.UTC).replace(tzinfo=None)
            
            job_id = f"campaign_{campaign_id}_email_rescheduled_{contact['email'].replace('@', '_at_').replace('.', '_dot_')}"
            
            campaign_scheduler.scheduler.add_job(
                func=execute_single_email_job,
                args=[campaign_id, contact, settings],
                trigger='date',
                run_date=next_send_time_utc,
                id=job_id,
                replace_existing=True
            )
            
            from flask import current_app
            current_app.logger.info(f"Rescheduled email to {contact['email']} for next business hours: {next_send_time}")
            
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Error rescheduling for business hours: {e}")

def _reschedule_for_next_day(campaign_id: int, contact: Dict, settings: Dict):
    """Reschedule email for next day."""
    try:
        from app.services.campaign_scheduler import campaign_scheduler
        
        # Schedule for tomorrow at a random time in the morning
        import random
        tomorrow = datetime.now() + timedelta(days=1)
        # Random time between 9 AM and 11 AM
        random_hour = random.randint(9, 11)
        random_minute = random.randint(0, 59)
        next_send_time = tomorrow.replace(hour=random_hour, minute=random_minute, second=0, microsecond=0)
        
        job_id = f"campaign_{campaign_id}_email_nextday_{contact['email'].replace('@', '_at_').replace('.', '_dot_')}"
        
        campaign_scheduler.scheduler.add_job(
            func=execute_single_email_job,
            args=[campaign_id, contact, settings],
            trigger='date',
            run_date=next_send_time,
            id=job_id,
            replace_existing=True
        )
        
        from flask import current_app
        current_app.logger.info(f"Rescheduled email to {contact['email']} for next day: {next_send_time}")
        
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Error rescheduling for next day: {e}")

# Background job to process pending email jobs
def process_pending_email_jobs():
    """Process pending email jobs from the database."""
    from flask import current_app
    from app import create_app
    
    app = create_app()
    with app.app_context():
        try:
            # Get pending jobs that are ready to execute
            pending_jobs = CampaignEmailJob.get_pending_jobs(limit=50)
            
            if not pending_jobs:
                return  # Silent return when no jobs
            
            current_app.logger.info(f"Found {len(pending_jobs)} pending email jobs to process.")
            
            for job in pending_jobs:
                # Attempt to lock the job for processing to prevent race conditions
                if CampaignEmailJob.mark_as_processing(job.id):
                    try:
                        current_app.logger.info(f"Processing email job {job.id} for {job.contact_email}")
                        # Execute the email job
                        success = _execute_email_job(job)
                        
                        if success:
                            CampaignEmailJob.mark_as_executed(job.id)
                            current_app.logger.info(f"✅ Email sent to {job.contact_email} (campaign {job.campaign_id})")
                        else:
                            CampaignEmailJob.mark_as_failed(job.id, "Email execution failed")
                            current_app.logger.error(f"❌ Email failed for {job.contact_email} (campaign {job.campaign_id})")
                            
                    except Exception as e:
                        CampaignEmailJob.mark_as_failed(job.id, str(e))
                        current_app.logger.error(f"Error executing email job {job.id}: {e}")
                else:
                    # Job was likely picked up by another worker, so we skip it
                    current_app.logger.debug(f"Skipping job {job.id}, already being processed by another worker.")
                    
        except Exception as e:
            current_app.logger.error(f"Error processing pending email jobs: {e}")

def _execute_email_job(job: CampaignEmailJob) -> bool:
    """Execute a single email job."""
    try:
        # Use the existing execute_single_email_job logic
        contact_data = job.contact_data_dict
        settings = job.campaign_settings_dict
        
        # Check if campaign is still active
        campaign = Campaign.get_by_id(job.campaign_id)
        if not campaign:
            return False
        
        if campaign.status == 'paused':
            return False
        
        if campaign.status not in ['active', 'scheduled']:
            return False
        
        # Check business hours if required
        timezone_str = settings.get('timezone', 'America/Los_Angeles')
        respect_business_hours = settings.get('respect_business_hours', True)
        business_hours = settings.get('business_hours', {})
        
        if respect_business_hours and not _is_business_hours(timezone_str, business_hours):
            # Reschedule for next business hour
            _reschedule_for_business_hours(job.campaign_id, contact_data, settings, timezone_str, business_hours)
            return True  # Mark as success since it was rescheduled
        
        # Check daily limit
        from app.models.email_history import EmailHistory
        daily_limit = settings.get('daily_email_limit', 50)
        emails_sent_today = EmailHistory.get_daily_count_for_campaign(job.campaign_id, datetime.now().date())
        
        if emails_sent_today >= daily_limit:
            # Reschedule for tomorrow
            _reschedule_for_next_day(job.campaign_id, contact_data, settings)
            return True  # Mark as success since it was rescheduled
        
        # Send email to contact
        success = _send_campaign_email(job.campaign_id, contact_data, settings)
        
        if success:
            # Mark contact as completed
            Campaign.update_contact_status_in_campaign(
                job.campaign_id, contact_data['email'], 'completed'
            )
            
            # Check if campaign is complete
            remaining_contacts = Campaign.get_campaign_contacts(job.campaign_id, status='active')
            if not remaining_contacts:
                Campaign.update_status(job.campaign_id, 'completed')
        else:
            # Mark contact as failed
            Campaign.update_contact_status_in_campaign(
                job.campaign_id, contact_data['email'], 'failed'
            )
        
        return success
        
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Error in _execute_email_job: {e}")
        return False

# Test mode execution function that bypasses all delays and restrictions
def execute_campaign_job_test_mode(campaign_id: int):
    """Execute campaign immediately for testing - bypasses all time constraints."""
    from flask import current_app
    from app import create_app
    
    # Create application context for background job
    app = create_app()
    with app.app_context():
        try:
            current_app.logger.info(f"🚀 TEST MODE: Starting immediate execution of campaign {campaign_id}")
            
            # Get campaign details
            campaign = Campaign.get_by_id(campaign_id)
            if not campaign:
                current_app.logger.error(f"Campaign {campaign_id} not found during test execution")
                return
            
            # Update status to active
            Campaign.update_status(campaign_id, 'active')
            
            # Get campaign settings
            settings = Campaign.get_campaign_settings(campaign_id)
            
            # Get contacts that need to be processed
            pending_contacts = Campaign.get_campaign_contacts(campaign_id, status='active')
            
            if not pending_contacts:
                current_app.logger.info(f"No pending contacts for campaign {campaign_id}")
                Campaign.update_status(campaign_id, 'completed')
                return
            
            current_app.logger.info(f"🔥 TEST MODE: Processing {len(pending_contacts)} contacts immediately (no delays)")
            
            # Process all contacts immediately without any delays or restrictions
            for i, contact in enumerate(pending_contacts, 1):
                try:
                    current_app.logger.info(f"🎯 TEST MODE: Processing contact {i}/{len(pending_contacts)}: {contact.get('email', 'unknown')}")
                    
                    # Send email to contact
                    success = _send_campaign_email(campaign_id, contact, settings)
                    
                    if success:
                        # Mark contact as completed
                        Campaign.update_contact_status_in_campaign(
                            campaign_id, contact['email'], 'completed'
                        )
                        current_app.logger.info(f"✅ TEST MODE: Email sent to {contact['email']} for campaign {campaign_id}")
                    else:
                        # Mark contact as failed
                        Campaign.update_contact_status_in_campaign(
                            campaign_id, contact['email'], 'failed'
                        )
                        current_app.logger.error(f"❌ TEST MODE: Failed to send email to {contact['email']} for campaign {campaign_id}")
                    
                    # NO DELAYS in test mode - process immediately
                    
                except Exception as contact_error:
                    current_app.logger.error(f"💥 TEST MODE: Error processing contact {contact.get('email', 'unknown')}: {contact_error}")
                    continue
            
            # Mark campaign as completed
            Campaign.update_status(campaign_id, 'completed')
            current_app.logger.info(f"🎉 TEST MODE: Campaign {campaign_id} completed immediately")
            
        except Exception as e:
            current_app.logger.error(f"💥 TEST MODE: Error executing campaign {campaign_id}: {e}")
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
        elif template_type == "possible_minds":
            from email_composers.email_composer_possible_minds import PossibleMindsEmailComposer
            composer = PossibleMindsEmailComposer()
        else:
            composer = WarmEmailComposer()
        
        # Extract company name with smart fallback from website domain
        company_name = contact.get('company_name') or contact.get('company')
        if not company_name and contact.get('company_domain'):
            # Extract company name from domain (e.g., "chocolatetherapy.us" -> "Chocolate Therapy")
            domain = contact.get('company_domain').replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0]
            domain_parts = domain.split('.')[0]  # Remove TLD
            company_name = ' '.join(word.capitalize() for word in domain_parts.replace('-', ' ').replace('_', ' ').split())
        
        lead_data = {
            "name": contact.get('display_name') or contact.get('full_name') or f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip(),
            "email": contact.get('email'),
            "company": company_name,  # Now uses smart extraction
            "position": contact.get('job_title'),
            "website": contact.get('company_domain'),
            "notes": f"Campaign: {campaign.name}",
        }
        
        calendar_url = os.getenv("CALENDAR_URL", "https://calendly.com/pranav-modi/15-minute-meeting")
        email_content = composer.compose_email(
            lead=lead_data, 
            calendar_url=calendar_url, 
            extra_context=f"This email is part of the '{campaign.name}' campaign.",
            campaign_id=campaign.id
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
    
    def init_app(self, app):
        """Initialize the scheduler with the Flask app context."""
        with app.app_context():
            self._setup_scheduler()
            self._setup_background_jobs()
            self.start()
    
    def _setup_scheduler(self):
        """Setup APScheduler with database persistence."""
        try:
            # Configure job store to use same database
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                current_app.logger.error("DATABASE_URL not configured for scheduler")
                return
            
            # Configure SQLAlchemy job store with connection pooling
            from sqlalchemy import create_engine
            # Create engine with connection pooling to prevent "too many clients" errors
            scheduler_engine = create_engine(
                database_url,
                pool_size=5,          # Maximum number of permanent connections to keep open
                max_overflow=10,      # Maximum number of connections that can overflow the pool
                pool_pre_ping=True,   # Verify connections before use
                pool_recycle=3600     # Recycle connections every hour
            )
            
            jobstores = {
                'default': SQLAlchemyJobStore(engine=scheduler_engine, tablename='scheduler_jobs')
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
    
    def _setup_background_jobs(self):
        """Setup recurring background jobs."""
        try:
            # Remove existing job if it exists
            try:
                self.scheduler.remove_job('process_pending_emails')
            except:
                pass
            
            # Count pending emails in queue
            try:
                ready_jobs = CampaignEmailJob.get_pending_jobs(limit=1000)
                ready_count = len(ready_jobs)
                
                total_pending_count = CampaignEmailJob.count_all_pending_jobs()
                
                if total_pending_count > 0:
                    current_app.logger.info(f"📧 Email queue: {ready_count} ready now, {total_pending_count} total pending.")
                else:
                    current_app.logger.info("📧 Email queue: Empty")
            except Exception as e:
                current_app.logger.warning(f"Could not check email queue: {e}")
            
            # Add recurring job to process pending email jobs every 2 minutes
            self.scheduler.add_job(
                func=process_pending_email_jobs,
                trigger='interval',
                seconds=120,  # Reduced from 30 to 120 seconds to avoid connection overload
                id='process_pending_emails',
                replace_existing=True,
                max_instances=1,  # Prevent overlapping executions
                coalesce=True    # Merge missed executions
            )
            
            current_app.logger.info("Background email processor scheduled (2min interval)")
            
        except Exception as e:
            current_app.logger.error(f"Failed to setup background jobs: {e}")
    
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
                
                # Clean up database connections
                from app.models.campaign_email_job import CampaignEmailJob
                CampaignEmailJob.close_engine()
                
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
        """Pause a running campaign and all its scheduled emails."""
        try:
            # Update campaign status first
            success = Campaign.update_status(campaign_id, 'paused')
            
            if success:
                # Mark all pending email jobs for this campaign as paused
                try:
                    engine = CampaignEmailJob._get_db_engine()
                    if engine:
                        with engine.connect() as conn:
                            with conn.begin():
                                result = conn.execute(text("""
                                    UPDATE campaign_email_jobs 
                                    SET status = 'paused', updated_at = CURRENT_TIMESTAMP 
                                    WHERE campaign_id = :campaign_id AND status = 'pending'
                                """), {"campaign_id": campaign_id})
                                paused_count = result.rowcount
                                current_app.logger.info(f"Campaign {campaign_id} paused successfully. Paused {paused_count} scheduled emails")
                except Exception as e:
                    current_app.logger.error(f"Error pausing email jobs for campaign {campaign_id}: {e}")
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
                # Resume all paused email jobs for this campaign
                try:
                    engine = CampaignEmailJob._get_db_engine()
                    if engine:
                        with engine.connect() as conn:
                            with conn.begin():
                                result = conn.execute(text("""
                                    UPDATE campaign_email_jobs 
                                    SET status = 'pending', updated_at = CURRENT_TIMESTAMP 
                                    WHERE campaign_id = :campaign_id AND status = 'paused'
                                """), {"campaign_id": campaign_id})
                                resumed_count = result.rowcount
                                current_app.logger.info(f"Campaign {campaign_id} resumed successfully. Resumed {resumed_count} email jobs")
                except Exception as e:
                    current_app.logger.error(f"Error resuming email jobs for campaign {campaign_id}: {e}")
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
    
    def associate_contacts_with_campaign(self, campaign_id: int, target_contacts: List[Dict]) -> bool:
        """Associate contacts with a campaign."""
        try:
            if not target_contacts:
                current_app.logger.info(f"No contacts to associate with campaign {campaign_id}")
                return True
            
            # Extract email addresses from contact dictionaries
            contact_emails = []
            for contact in target_contacts:
                email = contact.get('email')
                if email:
                    contact_emails.append(email)
            
            if not contact_emails:
                current_app.logger.warning(f"No valid email addresses found in contacts for campaign {campaign_id}")
                return False
            
            # Use Campaign model's bulk add method
            result = Campaign.bulk_add_contacts_to_campaign(campaign_id, contact_emails, status='active')
            
            current_app.logger.info(f"Associated {result['success']} contacts with campaign {campaign_id}, {result['failed']} failed")
            
            if result['errors']:
                for error in result['errors']:
                    current_app.logger.error(f"Contact association error: {error}")
            
            return result['success'] > 0
            
        except Exception as e:
            current_app.logger.error(f"Error associating contacts with campaign {campaign_id}: {e}")
            return False
    
    def cancel_campaign(self, campaign_id: int) -> bool:
        """Cancel a scheduled campaign and all its individual email jobs."""
        try:
            # Remove main campaign jobs
            main_job_ids = [
                f"campaign_{campaign_id}_immediate",
                f"campaign_{campaign_id}_scheduled",
                f"campaign_{campaign_id}_resume"
            ]
            
            for job_id in main_job_ids:
                try:
                    self.scheduler.remove_job(job_id)
                    current_app.logger.info(f"Removed main job {job_id}")
                except:
                    pass  # Job might not exist
            
            # Mark all pending email jobs for this campaign as cancelled
            try:
                engine = CampaignEmailJob._get_db_engine()
                if engine:
                    with engine.connect() as conn:
                        with conn.begin():
                            result = conn.execute(text("""
                                UPDATE campaign_email_jobs 
                                SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP 
                                WHERE campaign_id = :campaign_id AND status = 'pending'
                            """), {"campaign_id": campaign_id})
                            cancelled_count = result.rowcount
                            current_app.logger.info(f"Cancelled {cancelled_count} pending email jobs for campaign {campaign_id}")
            except Exception as e:
                current_app.logger.error(f"Error cancelling email jobs for campaign {campaign_id}: {e}")
            
            # Update campaign status to cancelled
            success = Campaign.update_status(campaign_id, 'cancelled')
            
            if success:
                current_app.logger.info(f"Campaign {campaign_id} cancelled successfully")
            
            return success
            
        except Exception as e:
            current_app.logger.error(f"Error cancelling campaign {campaign_id}: {e}")
            return False

# Global scheduler instance
campaign_scheduler = CampaignScheduler() 