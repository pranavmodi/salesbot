#!/usr/bin/env python3
"""
Deep Research Background Scheduler

Independent scheduler for managing OpenAI background research jobs.
Separated from campaign scheduler for better separation of concerns.
"""

import logging
from typing import Optional
from flask import current_app
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from deepresearch.llm_deep_research_service import LLMDeepResearchService

# Configure logging
logger = logging.getLogger(__name__)

# Create a single, shared instance of the research service to avoid re-initialization
llm_research_service = LLMDeepResearchService()

class DeepResearchScheduler:
    """Independent scheduler for deep research background jobs."""
    
    def __init__(self):
        self.scheduler = None
        self._initialized = False
    
    def init_app(self, app):
        """Initialize the deep research scheduler with Flask app."""
        if self._initialized:
            # Skip duplicate initialization
            return
            
        try:
            # Configure scheduler with minimal setup for reliability
            jobstores = {
                'default': MemoryJobStore()
            }
            executors = {
                'default': ThreadPoolExecutor(max_workers=2)  # Limited workers for background jobs
            }
            job_defaults = {
                'coalesce': True,
                'max_instances': 1,
                'misfire_grace_time': 30
            }
            
            self.scheduler = BackgroundScheduler(
                jobstores=jobstores,
                executors=executors,
                job_defaults=job_defaults,
                timezone='UTC'
            )
            
            # Add event listeners
            self.scheduler.add_listener(self._job_executed_listener, EVENT_JOB_EXECUTED)
            self.scheduler.add_listener(self._job_error_listener, EVENT_JOB_ERROR)
            
            # Start the scheduler
            self.scheduler.start()
            # Scheduler started successfully
            
            # Schedule the OpenAI polling job
            self._schedule_background_jobs()
            
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize deep research scheduler: {e}")
            raise
    
    def _schedule_background_jobs(self):
        """Schedule the background polling jobs."""
        try:
            # OpenAI background job polling (every 10 seconds)
            self.scheduler.add_job(
                func=poll_openai_background_jobs,
                trigger='interval',
                seconds=10,
                id='poll_openai_background_jobs',
                replace_existing=True,
                max_instances=1,
                coalesce=True
            )
            
            # Background job polling scheduled
            
        except Exception as e:
            logger.error(f"Failed to schedule deep research background jobs: {e}")
    
    def _job_executed_listener(self, event):
        """Handle successful job execution."""
        try:
            if not event.job_id.startswith('poll_openai'):
                logger.debug(f"Deep research job {event.job_id} executed successfully")
        except Exception:
            pass  # Silent in case of context issues
    
    def _job_error_listener(self, event):
        """Handle job execution errors."""
        try:
            logger.error(f"Deep research job {event.job_id} failed: {event.exception}")
        except Exception:
            pass  # Silent in case of context issues
    
    def shutdown(self):
        """Shutdown the scheduler gracefully."""
        if self.scheduler and self.scheduler.running:
            try:
                self.scheduler.shutdown(wait=True)
                logger.info("Deep research scheduler shut down successfully")
            except Exception as e:
                logger.error(f"Error shutting down deep research scheduler: {e}")

# Global scheduler instance
deep_research_scheduler = DeepResearchScheduler()

def poll_openai_background_jobs():
    """Module-level function to poll OpenAI for research job completions."""
    try:
        from app import create_app
        
        # Create a fresh app instance for background thread
        app = create_app()
        
        with app.app_context():
            app.logger.debug("🔍 Deep Research: Polling OpenAI background jobs...")
            
            # Use the shared, globally-defined service instance
            completed_jobs = llm_research_service.poll_and_process_background_jobs()
            
            if completed_jobs > 0:
                app.logger.info(f"✅ Deep Research: Processed {completed_jobs} completed OpenAI background jobs")
            else:
                app.logger.debug("Deep Research: No completed OpenAI background jobs found")
                
    except Exception as e:
        # Use print for background thread errors since Flask logger might not be available
        print(f"Deep Research: Error polling OpenAI background jobs: {e}")
        import traceback
        traceback.print_exc()