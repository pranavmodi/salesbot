from datetime import datetime, timedelta
import time
import pytz
from typing import Dict, List, Optional
from flask import current_app
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from sqlalchemy import text
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
        
        # If it's a campaign job that failed due to timing, retry it
        if 'campaign_' in event.job_id and 'immediate' in event.job_id:
            try:
                campaign_id = int(event.job_id.split('_')[1])
                current_app.logger.warning(f"🔄 DEBUG: Retrying campaign {campaign_id} due to execution failure")
                
                # Retry with a longer delay
                import datetime
                from app.services.campaign_scheduler import campaign_scheduler
                retry_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=5)
                retry_job_id = f"campaign_{campaign_id}_retry"
                
                campaign_scheduler.scheduler.add_job(
                    func=execute_campaign_job,
                    args=[campaign_id],
                    trigger='date',
                    run_date=retry_time,
                    id=retry_job_id,
                    replace_existing=True
                )
                current_app.logger.info(f"🔄 DEBUG: Campaign {campaign_id} rescheduled for retry at {retry_time}")
            except Exception as retry_error:
                current_app.logger.error(f"Failed to retry campaign job: {retry_error}")
    except:
        print(f"Job {event.job_id} failed: {event.exception}")

# Static campaign execution function - starts individual email scheduling
def execute_campaign_job(campaign_id: int):
    """Thread-safe function to start a campaign by scheduling individual emails."""
    from flask import current_app
    from app import create_app
    import random
    import gc
    import threading
    
    # Create application context for background job
    app = create_app()
    with app.app_context():
        thread_id = threading.get_ident()
        try:
            current_app.logger.info(f"🚀 Thread {thread_id}: Starting execution of campaign {campaign_id}")
            
            # Get campaign details
            campaign = Campaign.get_by_id(campaign_id)
            if not campaign:
                current_app.logger.error(f"❌ DEBUG: Campaign {campaign_id} not found during execution")
                return
            
            current_app.logger.info(f"📋 DEBUG: Campaign {campaign_id} found - Name: {campaign.name}, Status: {campaign.status}")
            
            # Check if campaign is paused
            if campaign.status == 'paused':
                current_app.logger.info(f"⏸️ DEBUG: Campaign {campaign_id} is paused, skipping execution")
                return
            
            # Check if campaign already has jobs scheduled (prevent duplicate execution)
            from app.database import get_shared_engine
            try:
                engine = get_shared_engine()
                if engine:
                    with engine.connect() as conn:
                        jobs_count_result = conn.execute(text("""
                            SELECT COUNT(*) FROM campaign_email_jobs 
                            WHERE campaign_id = :campaign_id
                        """), {"campaign_id": campaign_id})
                        existing_jobs_count = jobs_count_result.scalar()
                        if existing_jobs_count > 0:
                            current_app.logger.warning(f"🚫 DEBUG: Campaign {campaign_id} already has {existing_jobs_count} jobs scheduled, skipping duplicate execution")
                            return
            except Exception as e:
                current_app.logger.warning(f"Could not check existing jobs count: {e}")
                # Continue with execution if check fails
            
            current_app.logger.info(f"🔄 DEBUG: Updating campaign {campaign_id} status to active")
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
            current_app.logger.info(f"👥 DEBUG: Getting contacts for campaign {campaign_id}")
            pending_contacts = Campaign.get_campaign_contacts(campaign_id, status='active')
            
            current_app.logger.info(f"📊 DEBUG: Found {len(pending_contacts) if pending_contacts else 0} pending contacts for campaign {campaign_id}")
            
            if not pending_contacts:
                current_app.logger.warning(f"⚠️ DEBUG: No pending contacts for campaign {campaign_id} - marking as completed")
                Campaign.update_status(campaign_id, 'completed')
                return
            
            current_app.logger.info(f"📅 DEBUG: Scheduling {len(pending_contacts)} individual emails for campaign {campaign_id}")
            
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
                    # Check if jobs already exist for this contact in this campaign
                    from app.database import get_shared_engine
                    existing_jobs_check = False
                    try:
                        engine = get_shared_engine()
                        if engine:
                            with engine.connect() as conn:
                                existing_result = conn.execute(text("""
                                    SELECT COUNT(*) FROM campaign_email_jobs 
                                    WHERE campaign_id = :campaign_id AND contact_email = :contact_email
                                """), {"campaign_id": campaign_id, "contact_email": contact['email']})
                                existing_count = existing_result.scalar()
                                if existing_count > 0:
                                    current_app.logger.info(f"⚠️ DEBUG: Skipping {contact['email']} - {existing_count} jobs already exist")
                                    continue
                    except Exception as check_error:
                        current_app.logger.warning(f"Could not check for existing jobs: {check_error}")
                        # Continue with job creation if check fails
                    if i == 0:
                        # First email can be sent immediately or with minimal delay
                        delay_seconds = random.randint(30, 120)  # 30 seconds to 2 minutes
                    else:
                        # Subsequent emails with random delays
                        delay_seconds = calculate_delay(i)
                    
                    cumulative_delay += delay_seconds
                    
                    # Schedule the individual email in database
                    # Use timezone-aware UTC time so PostgreSQL handles it correctly
                    import pytz
                    utc_now = datetime.now(pytz.UTC)  # timezone-aware UTC
                    run_time = utc_now + timedelta(seconds=cumulative_delay)
                    # Keep timezone-aware for proper database storage
                    # PostgreSQL will convert this correctly to its local timezone
                    
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
                    
                    current_app.logger.info(f"💾 DEBUG: Attempting to save email job for {contact['email']} scheduled for {run_time}")
                    if email_job.save():
                        scheduled_count += 1
                        current_app.logger.info(f"✅ DEBUG: Scheduled email {i+1}/{len(pending_contacts)} to {contact['email']} for {run_time} (delay: {delay_seconds}s)")
                    else:
                        current_app.logger.error(f"❌ DEBUG: Failed to save email job for {contact['email']}")
                    
                except Exception as e:
                    current_app.logger.error(f"Error scheduling email for {contact.get('email', 'unknown')}: {e}")
                    continue
            
            current_app.logger.info(f"Campaign {campaign_id} email scheduling completed: {scheduled_count} emails scheduled over {cumulative_delay/60:.1f} minutes")
                
        except Exception as e:
            current_app.logger.error(f"Error scheduling campaign {campaign_id}: {e}")
            Campaign.update_status(campaign_id, 'failed')
        finally:
            # Force garbage collection to clean up resources
            gc.collect()

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
            # Convert to UTC for database storage
            next_send_time_utc = next_send_time.astimezone(pytz.UTC).replace(tzinfo=None)
            
            # Create a new CampaignEmailJob in the database instead of using scheduler
            from app.models.campaign_email_job import CampaignEmailJob
            from flask import current_app
            
            # Create a new database job for the rescheduled email
            email_job = CampaignEmailJob(
                campaign_id=campaign_id,
                contact_email=contact['email'],
                contact_data=contact,
                campaign_settings=settings,
                scheduled_time=next_send_time_utc,
                status='pending'
            )
            
            if email_job.save():
                current_app.logger.info(f"📅 Rescheduled email to {contact['email']} for next business hours: {next_send_time}")
            else:
                current_app.logger.error(f"❌ Failed to reschedule email for {contact['email']}")
                raise Exception("Failed to save rescheduled email job")
            
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Error rescheduling for business hours: {e}")

def _reschedule_for_next_day(campaign_id: int, contact: Dict, settings: Dict):
    """Reschedule email for next day."""
    try:
        from app.services.campaign_scheduler import campaign_scheduler
        
        # Schedule for tomorrow at a random time in the morning
        import random
        tomorrow = datetime.utcnow() + timedelta(days=1)
        # Random time between 9 AM and 11 AM
        random_hour = random.randint(9, 11)
        random_minute = random.randint(0, 59)
        next_send_time = tomorrow.replace(hour=random_hour, minute=random_minute, second=0, microsecond=0)
        
        # Create a new CampaignEmailJob in the database instead of using scheduler
        from app.models.campaign_email_job import CampaignEmailJob
        from flask import current_app
        
        # Create a new database job for the rescheduled email
        email_job = CampaignEmailJob(
            campaign_id=campaign_id,
            contact_email=contact['email'],
            contact_data=contact,
            campaign_settings=settings,
            scheduled_time=next_send_time,
            status='pending'
        )
        
        if email_job.save():
            current_app.logger.info(f"📅 Rescheduled email to {contact['email']} for next day: {next_send_time}")
        else:
            current_app.logger.error(f"❌ Failed to reschedule email for {contact['email']}")
            raise Exception("Failed to save rescheduled email job")
        
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Error rescheduling for next day: {e}")

# Background job to process pending email jobs
def process_pending_email_jobs():
    """Process pending email jobs from the database."""
    from flask import current_app
    from app import create_app
    import gc
    
    # Create application context for background job
    app = create_app()
    with app.app_context():
        try:
            # Get pending jobs that are ready to execute
            current_app.logger.info(f"🔍 DEBUG: Checking for pending email jobs...")
            pending_jobs = CampaignEmailJob.get_pending_jobs(limit=10)  # Reduced from 50 to 10
            
            current_app.logger.info(f"📧 DEBUG: Found {len(pending_jobs)} pending email jobs ready to process")
            
            if not pending_jobs:
                current_app.logger.info(f"💤 DEBUG: No pending jobs ready for execution")
                return  # Silent return when no jobs
            
            current_app.logger.info(f"🚀 DEBUG: Processing {len(pending_jobs)} pending email jobs")
            
            # Process only ONE job per cycle to respect timing intervals
            # This prevents multiple emails from being sent simultaneously
            for job in pending_jobs[:1]:  # Only process the first job
                # Check if enough time has passed since last email from this campaign
                if not _can_send_email_now(job.campaign_id):
                    current_app.logger.info(f"⏱️ Timing constraint: Skipping job {job.id} - not enough time since last email from campaign {job.campaign_id}")
                    break
                
                # Attempt to lock the job for processing to prevent race conditions
                if CampaignEmailJob.mark_as_processing(job.id):
                    try:
                        current_app.logger.info(f"Processing email job {job.id} for {job.contact_email}")
                        # Execute the email job
                        result = _execute_email_job(job)
                        
                        if result == 'rescheduled':
                            CampaignEmailJob.mark_as_executed(job.id)
                            current_app.logger.info(f"📅 Email job processed - rescheduled for {job.contact_email} (campaign {job.campaign_id})")
                        elif result:
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
        finally:
            # Force garbage collection to clean up resources
            gc.collect()

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
            return 'rescheduled'  # Mark as rescheduled, not sent
        
        # Check daily limit
        from app.models.email_history import EmailHistory
        daily_limit = settings.get('daily_email_limit', 50)
        emails_sent_today = EmailHistory.get_daily_count_for_campaign(job.campaign_id, datetime.now().date())
        
        if emails_sent_today >= daily_limit:
            # Reschedule for tomorrow
            _reschedule_for_next_day(job.campaign_id, contact_data, settings)
            return 'rescheduled'  # Mark as rescheduled, not sent
        
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
        # Import current_app at the top to ensure it's available
        from flask import current_app
        
        # Get campaign details for email composition
        campaign = Campaign.get_by_id(campaign_id)
        
        if not campaign:
            current_app.logger.error(f"Campaign {campaign_id} not found during email sending")
            return False
        
        current_app.logger.info(f"🔄 DEBUG: _send_campaign_email called for campaign {campaign_id}, contact {contact.get('email')}, template: {settings.get('email_template', 'warm')}")
        
        # Skip EmailService.compose_email and go directly to fallback for deep_research template
        template_type = settings.get('email_template', 'warm')
        if template_type == 'deep_research':
            current_app.logger.info(f"📧 DEBUG: Using direct deep_research composer for better debugging")
            email_content = _compose_fallback_email(campaign, contact, settings)
        else:
            # Generate email content using EmailService for non-deep_research templates
            email_content = EmailService.compose_email(
                contact_id=contact.get('email'),  # Use email as contact_id since it searches by email anyway
                calendar_url=os.getenv("CALENDAR_URL", "https://calendly.com/pranav-modi/15-minute-meeting"),
                extra_context=f"This email is part of the '{campaign.name}' campaign.",
                composer_type=template_type,
                campaign_id=campaign_id
            )
            
            if not email_content:
                # Fallback email composition
                current_app.logger.info(f"⚠️ DEBUG: EmailService.compose_email failed, using fallback")
                email_content = _compose_fallback_email(campaign, contact, settings)
        
        # Check if email composition was successful and content is ready
        if email_content is None:
            current_app.logger.warning(f"🚫 DEBUG: Email composition aborted for {contact.get('email')} - research not ready")
            return False  # Do not send email, research is still in progress
        elif email_content and 'subject' in email_content and 'body' in email_content:
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
        # current_app is already imported at the top of the function
        current_app.logger.error(f"Error sending campaign email: {e}")
        return False

def _compose_fallback_email(campaign: Campaign, contact: Dict, settings: Dict) -> Dict:
    """Compose fallback email when main composer fails."""
    try:
        from flask import current_app
        from email_composers.email_composer_warm import WarmEmailComposer
        from email_composers.email_composer_alt_subject import AltSubjectEmailComposer
        from email_composers.email_composer_deep_research import DeepResearchEmailComposer
        
        template_type = settings.get('email_template', 'deep_research')  # Changed default to deep_research
        
        # Extract company name with smart fallback from website domain (needed for all composers)
        company_name = contact.get('company_name') or contact.get('company')
        current_app.logger.info(f"📊 DEBUG: Contact company data - company_name: '{contact.get('company_name')}', company: '{contact.get('company')}', domain: '{contact.get('company_domain')}'")
        
        if not company_name and contact.get('company_domain'):
            # Extract company name from domain (e.g., "chocolatetherapy.us" -> "Chocolate Therapy")
            domain = contact.get('company_domain').replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0]
            domain_parts = domain.split('.')[0]  # Remove TLD
            company_name = ' '.join(word.capitalize() for word in domain_parts.replace('-', ' ').replace('_', ' ').split())
            current_app.logger.info(f"🌐 DEBUG: Extracted company name from domain: '{company_name}' from '{contact.get('company_domain')}'")
            
        current_app.logger.info(f"🏢 DEBUG: Final company name for email composer: '{company_name}'")
        
        if template_type == "alt_subject":
            composer = AltSubjectEmailComposer()
        elif template_type == "deep_research":
            # Use thread-safe composer for deep research to prevent malloc errors
            from app.services.thread_safe_email_composer import get_thread_safe_composer
            thread_safe_composer = get_thread_safe_composer()
            
            # Use the thread-safe compose method instead of creating direct instance
            lead_data = {
                "name": contact.get('first_name') or contact.get('name') or 'there',
                "email": contact.get('email'),
                "company": company_name or 'your company',
                "position": contact.get('job_title') or contact.get('title') or '',
                "website": contact.get('company_domain') or '',
                "notes": "",
            }
            
            calendar_url = os.getenv("CALENDAR_URL", "https://calendly.com/pranav-modi/15-minute-meeting")
            extra_context = f"This email is part of the '{campaign.name}' campaign."
            
            current_app.logger.info(f"🛡️ DEBUG: Using thread-safe deep research composer for campaign {campaign.id}")
            
            return thread_safe_composer.compose_email_safely(
                lead=lead_data,
                calendar_url=calendar_url,
                extra_context=extra_context,
                composer_type="deep_research",
                campaign_id=campaign.id
            )
        elif template_type == "possible_minds":
            from email_composers.email_composer_possible_minds import PossibleMindsEmailComposer
            composer = PossibleMindsEmailComposer()
        else:
            composer = WarmEmailComposer()
        
        lead_data = {
            "name": contact.get('display_name') or contact.get('full_name') or f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip(),
            "email": contact.get('email'),
            "company": company_name,  # Now uses smart extraction
            "position": contact.get('job_title'),
            "website": contact.get('company_domain'),
            "notes": f"Campaign: {campaign.name}",
        }
        
        calendar_url = os.getenv("CALENDAR_URL", "https://calendly.com/pranav-modi/15-minute-meeting")
        
        current_app.logger.info(f"🎯 DEBUG: Calling {template_type} composer for {contact.get('email')} with campaign_id={campaign.id}")
        current_app.logger.info(f"📋 DEBUG: Lead data - Company: {lead_data.get('company')}, Email: {lead_data.get('email')}")
        
        email_content = composer.compose_email(
            lead=lead_data, 
            calendar_url=calendar_url, 
            extra_context=f"This email is part of the '{campaign.name}' campaign.",
            campaign_id=campaign.id
        )
        
        # Handle case where composer returns None (research not ready)
        if email_content is None:
            current_app.logger.warning(f"🚫 DEBUG: Composer returned None for {contact.get('email')} - research not ready")
            return None  # Propagate the None to prevent email sending
        
        current_app.logger.info(f"📧 DEBUG: Email composer returned content: {bool(email_content)}")
        if email_content and 'body' in email_content:
            has_placeholder = '[REPORT_LINK_PLACEHOLDER]' in email_content['body']
            has_report_link = 'strategic analysis report' in email_content['body']
            current_app.logger.info(f"🔗 DEBUG: Email body - Has placeholder: {has_placeholder}, Has report link: {has_report_link}")
            if has_placeholder:
                current_app.logger.warning(f"⚠️ DEBUG: Email still contains placeholder - report URL generation failed")
            if has_report_link:
                current_app.logger.info(f"✅ DEBUG: Email contains actual report link")
                
        return email_content
        
    except Exception as e:
        # current_app is already imported at the top of the function
        current_app.logger.error(f"Error in fallback email composition: {e}")
        return {}

def _can_send_email_now(campaign_id: int) -> bool:
    """Check if enough time has passed since the last email from this campaign to respect timing rules."""
    try:
        from app.models.email_history import EmailHistory
        from app.models.campaign import Campaign
        from datetime import datetime, timedelta
        
        # Get campaign settings to determine minimum delay
        settings = Campaign.get_campaign_settings(campaign_id)
        email_frequency = settings.get('email_frequency', {'value': 30, 'unit': 'minutes'})
        
        # Convert frequency to minutes
        if email_frequency['unit'] == 'hours':
            min_delay_minutes = email_frequency['value'] * 60
        else:  # assume minutes
            min_delay_minutes = email_frequency['value']
        
        # Get the last email sent for this campaign
        engine = Campaign._get_db_engine()
        if not engine:
            return True  # Allow if we can't check
        
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT MAX(date) as last_email_time
                FROM email_history 
                WHERE campaign_id = :campaign_id 
                AND status = 'sent'
            """), {"campaign_id": campaign_id})
            
            row = result.fetchone()
            if not row or not row.last_email_time:
                return True  # No previous emails, allow sending
            
            last_email_time = row.last_email_time
            time_since_last = datetime.utcnow() - last_email_time.replace(tzinfo=None)
            required_delay = timedelta(minutes=min_delay_minutes)
            
            can_send = time_since_last >= required_delay
            
            if not can_send:
                remaining_minutes = (required_delay - time_since_last).total_seconds() / 60
                current_app.logger.info(f"⏱️ Campaign {campaign_id}: Need to wait {remaining_minutes:.1f} more minutes (last email: {last_email_time})")
            
            return can_send
            
    except Exception as e:
        current_app.logger.error(f"Error checking timing constraints: {e}")
        return True  # Allow sending if check fails

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
            
            # Use shared database engine for APScheduler job store
            from app.database import get_shared_engine
            scheduler_engine = get_shared_engine()
            
            jobstores = {
                'default': SQLAlchemyJobStore(engine=scheduler_engine, tablename='scheduler_jobs')
            }
            
            executors = {
                'default': ThreadPoolExecutor(3),  # Use standard APScheduler ThreadPoolExecutor
            }
            
            job_defaults = {
                'coalesce': True,   # Combine multiple pending jobs into one
                'max_instances': 1,  # Only one instance of each job type at a time
                'misfire_grace_time': 60,  # Allow 60 seconds grace time for delayed execution
                'replace_existing': True   # Replace existing jobs with same ID to prevent conflicts
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
    
    def _setup_scheduler_minimal(self):
        """Setup minimal APScheduler configuration as fallback."""
        try:
            # Configure job store to use same database
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                current_app.logger.error("DATABASE_URL not configured for scheduler")
                return
            
            # Use shared database engine for APScheduler job store
            from app.database import get_shared_engine
            scheduler_engine = get_shared_engine()
            
            jobstores = {
                'default': SQLAlchemyJobStore(engine=scheduler_engine, tablename='scheduler_jobs')
            }
            
            executors = {
                'default': ThreadPoolExecutor(1),  # Minimal 1 thread configuration
            }
            
            job_defaults = {
                'coalesce': True,   # Combine multiple pending jobs into one
                'max_instances': 1,  # Only one instance of each job type at a time
                'misfire_grace_time': 120  # Allow 2 minutes grace time for delayed execution
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
            
            current_app.logger.info("Minimal scheduler configuration initialized")
            
        except Exception as e:
            current_app.logger.error(f"Failed to setup minimal scheduler: {e}")
            self.scheduler = None
    
    def _setup_background_jobs(self):
        """Setup recurring background jobs with proper error handling for concurrent instances."""
        try:
            # Check if job already exists to prevent duplicate registration
            existing_jobs = self.scheduler.get_jobs()
            existing_job_ids = [job.id for job in existing_jobs]
            
            if 'process_pending_emails' in existing_job_ids:
                current_app.logger.info("Background email processor already exists, skipping registration")
                return
            
            # Remove existing job if it exists (belt and suspenders approach)
            self._safe_remove_job('process_pending_emails')
            
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
            
            # Add recurring job to process pending email jobs every 60 seconds
            try:
                self.scheduler.add_job(
                    func=process_pending_email_jobs,
                    trigger='interval', 
                    seconds=60,  # Process every 60 seconds
                    id='process_pending_emails',
                    replace_existing=True,
                    max_instances=1,  # Prevent overlapping executions
                    coalesce=True    # Merge missed executions
                )
                
                current_app.logger.info("Background email processor scheduled (60sec interval)")
                
            except Exception as job_error:
                # If job registration fails due to threading issues, degrade gracefully
                if "can't start new thread" in str(job_error).lower() or "thread" in str(job_error).lower():
                    current_app.logger.warning("Thread limit reached - running without background email processor")
                    current_app.logger.warning("Campaigns will need manual triggering via dashboard")
                    # Try to fall back to a simpler configuration
                    try:
                        # Reduce thread pool to 1 and try again
                        self.scheduler.shutdown(wait=False)
                        self._setup_scheduler_minimal()
                        if self.scheduler:
                            self.scheduler.start()
                            current_app.logger.info("Scheduler started with minimal configuration")
                    except:
                        current_app.logger.warning("Minimal scheduler configuration also failed")
                elif "already exists" in str(job_error).lower() or "duplicate key" in str(job_error).lower():
                    current_app.logger.info("Background email processor already registered by another instance")
                else:
                    current_app.logger.error(f"Failed to schedule background job: {job_error}")
                    # Don't raise - continue without background processing
            
        except Exception as e:
            current_app.logger.error(f"Failed to setup background jobs: {e}")
    
    def _safe_remove_job(self, job_id: str) -> bool:
        """Safely remove a job if it exists."""
        try:
            if self.scheduler and self.scheduler.running:
                # Check if job exists first
                job = self.scheduler.get_job(job_id)
                if job:
                    self.scheduler.remove_job(job_id)
                    current_app.logger.debug(f"Successfully removed job: {job_id}")
                    return True
                else:
                    current_app.logger.debug(f"Job {job_id} does not exist, nothing to remove")
                    return False
            return False
        except Exception as e:
            current_app.logger.debug(f"Error removing job {job_id}: {e}")
            return False

    def start(self):
        """Start the scheduler with thread exhaustion handling."""
        if self.scheduler and not self.scheduler.running:
            try:
                self.scheduler.start()
                current_app.logger.info("Campaign scheduler started")
            except Exception as e:
                if "can't start new thread" in str(e).lower():
                    current_app.logger.warning("Thread limit reached - scheduler cannot start automatically")
                    current_app.logger.warning("Manual campaign execution available via dashboard")
                    # Set scheduler to None to indicate it's not available
                    self.scheduler = None
                else:
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
            
            # Check if scheduler is available
            if not self.scheduler:
                current_app.logger.warning(f"Scheduler unavailable - executing campaign {campaign_id} immediately via direct call")
                execute_campaign_job(campaign_id)
                return True
            
            # If no schedule date, start immediately with a small delay to avoid timing issues
            if not schedule_date:
                import datetime
                run_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=2)  # 2 second delay
                job_id = f"campaign_{campaign_id}_immediate"
                self.scheduler.add_job(
                    func=execute_campaign_job,
                    args=[campaign_id],
                    trigger='date',
                    run_date=run_time,
                    id=job_id,
                    replace_existing=True
                )
                current_app.logger.info(f"🚀 DEBUG: Campaign {campaign_id} scheduled for execution at {run_time} (2 second delay)")
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
            
            # Only try to remove scheduler jobs if scheduler is available
            if self.scheduler:
                for job_id in main_job_ids:
                    if self._safe_remove_job(job_id):
                        current_app.logger.info(f"Removed main job {job_id}")
                    else:
                        current_app.logger.debug(f"Job {job_id} was not found or could not be removed")
            else:
                current_app.logger.info(f"Scheduler unavailable - campaign {campaign_id} jobs cannot be removed from scheduler")
            
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