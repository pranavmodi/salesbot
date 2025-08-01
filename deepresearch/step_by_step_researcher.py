#!/usr/bin/env python3
"""
Step-by-Step Deep Research System

This module handles comprehensive company research in stages:
1. Basic Company Research
2. Strategic Analysis 
3. Report Generation

Each step is stored separately in the database for tracking and recovery.
"""

import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime

from .database_service import DatabaseService
from .ai_research_service import AIResearchService
from .report_generator import ReportGenerator

logger = logging.getLogger(__name__)

class StepByStepResearcher:
    """Step-by-step deep research system with database persistence."""
    
    def __init__(self):
        self.db_service = DatabaseService()
        self.ai_service = AIResearchService()
        self.report_generator = ReportGenerator()
        logger.info("StepByStepResearcher initialized")

    def start_deep_research(self, company_id: int, force_refresh: bool = False) -> Dict[str, Any]:
        """Start deep research process for a company."""
        # Import here to avoid circular imports
        from app.models.company import Company
        
        logger.info(f"Starting deep research for company ID: {company_id}")
        
        # Get company details
        company = Company.get_by_id(company_id)
        if not company:
            return {'success': False, 'error': f'Company with ID {company_id} not found'}
        
        # Check for stuck research process (research_status = 'in_progress' for > 10 minutes)
        if hasattr(company, 'research_status') and company.research_status == 'in_progress':
            if hasattr(company, 'updated_at') and company.updated_at:
                from datetime import datetime, timedelta, timezone
                # Make both datetimes timezone-aware for comparison
                now = datetime.now(timezone.utc)
                updated_at = company.updated_at
                if updated_at.tzinfo is None:
                    updated_at = updated_at.replace(tzinfo=timezone.utc)
                
                time_elapsed = now - updated_at
                if time_elapsed > timedelta(minutes=10):
                    logger.warning(f"Research for {company.company_name} appears stuck (in_progress for {time_elapsed}). Resetting...")
                    force_refresh = True
        
        # Check if research already exists and not forcing refresh
        if not force_refresh and hasattr(company, 'research_status') and company.research_status == 'completed':
            logger.info(f"Company {company.company_name} already has completed research")
            return {
                'success': True, 
                'message': 'Research already completed',
                'status': 'completed',
                'company_name': company.company_name
            }
        
        # Check if research is already in progress
        if company.research_status == 'in_progress':
            logger.info(f"Research already in progress for company: {company.company_name}")
            return {
                'success': True,
                'message': 'Research already in progress',
                'status': 'in_progress',
                'company_name': company.company_name
            }
        
        try:
            # Set status to in_progress
            Company.update_research_status(company_id, 'in_progress')
            
            # Step 1: Basic Company Research
            logger.info(f"Step 1: Starting basic research for {company.company_name}")
            basic_research = self._perform_basic_research(company)
            
            if not basic_research:
                Company.update_research_status(company_id, 'failed', 'Failed at basic research step')
                return {'success': False, 'error': 'Failed to complete basic research'}
            
            # Store step 1 results
            Company.update_research_step(company_id, 1, basic_research)
            logger.info(f"Step 1 completed for {company.company_name}")
            
            # Step 2: Strategic Analysis
            logger.info(f"Step 2: Starting strategic analysis for {company.company_name}")
            strategic_result = self._perform_strategic_analysis(company, basic_research)
            
            if not strategic_result:
                Company.update_research_status(company_id, 'failed', 'Failed at strategic analysis step')
                return {'success': False, 'error': 'Failed to complete strategic analysis'}
            
            # Extract structured AI agent recommendations if available
            if isinstance(strategic_result, dict) and 'structured_data' in strategic_result:
                structured_data = strategic_result['structured_data']
                strategic_analysis = strategic_result['json_string']
                
                # Extract and store AI agent recommendations
                if 'ai_agent_recommendations' in structured_data:
                    ai_recommendations = structured_data['ai_agent_recommendations']['priorities']
                    logger.info(f"🤖 DEBUG: Found AI agent recommendations in structured data, storing {len(ai_recommendations)} recommendations")
                    success = Company.update_ai_agent_recommendations(company_id, ai_recommendations)
                    if success:
                        logger.info(f"✅ DEBUG: Successfully stored {len(ai_recommendations)} AI agent recommendations for {company.company_name}")
                    else:
                        logger.error(f"❌ DEBUG: Failed to store AI agent recommendations for {company.company_name}")
                else:
                    logger.warning(f"⚠️ DEBUG: No 'ai_agent_recommendations' found in structured_data for {company.company_name}")
                    logger.info(f"📋 DEBUG: Available keys in structured_data: {list(structured_data.keys())}")
            else:
                strategic_analysis = strategic_result
                
            # Store step 2 results
            Company.update_research_step(company_id, 2, strategic_analysis)
            logger.info(f"Step 2 completed for {company.company_name}")
            
            # Step 3: Report Generation
            logger.info(f"Step 3: Starting report generation for {company.company_name}")
            report_data = self._generate_final_report(company, basic_research, strategic_analysis)
            
            if not report_data:
                Company.update_research_status(company_id, 'failed', 'Failed at report generation step')
                return {'success': False, 'error': 'Failed to generate final report'}
            
            # Store step 3 results with HTML/PDF data and mark as completed
            success = self.db_service.update_company_research_with_reports(
                company_id,
                basic_research,
                html_report=report_data['html_report'],
                pdf_report_base64=report_data['pdf_report_base64'],
                strategic_imperatives=report_data['strategic_imperatives'],
                agent_recommendations=report_data['agent_recommendations']
            )
            
            if success:
                # Also update the step tracking and status
                Company.update_research_step(company_id, 3, report_data['html_report'][:1000] + "...")  # Truncated for step tracking
                Company.update_research_status(company_id, 'completed')
                logger.info(f"Step 3 completed for {company.company_name}")
            else:
                Company.update_research_status(company_id, 'failed', 'Failed to save report data')
                return {'success': False, 'error': 'Failed to save report data'}
            
            # Note: Markdown report is now only stored in database, not as disk file
            
            return {
                'success': True,
                'message': f'Deep research completed successfully for {company.company_name}',
                'status': 'completed',
                'company_name': company.company_name,
                'steps_completed': 3
            }
            
        except Exception as e:
            logger.error(f"Error during deep research for company {company_id}: {e}")
            Company.update_research_status(company_id, 'failed', str(e))
            return {'success': False, 'error': f'Research failed: {str(e)}'}

    def get_research_progress(self, company_id: int) -> Dict[str, Any]:
        """Get current research progress for a company."""
        from app.models.company import Company
        
        company = Company.get_by_id(company_id)
        if not company:
            return {'success': False, 'error': 'Company not found'}
        
        steps_completed = 0
        step_statuses = {}
        
        if company.research_step_1_basic:
            steps_completed += 1
            step_statuses['step_1'] = {
                'completed': True,
                'title': 'Basic Company Research',
                'content_length': len(company.research_step_1_basic)
            }
        else:
            step_statuses['step_1'] = {
                'completed': False,
                'title': 'Basic Company Research',
                'content_length': 0
            }
        
        if company.research_step_2_strategic:
            steps_completed += 1
            step_statuses['step_2'] = {
                'completed': True,
                'title': 'Strategic Analysis',
                'content_length': len(company.research_step_2_strategic)
            }
        else:
            step_statuses['step_2'] = {
                'completed': False,
                'title': 'Strategic Analysis',
                'content_length': 0
            }
        
        if company.research_step_3_report:
            steps_completed += 1
            step_statuses['step_3'] = {
                'completed': True,
                'title': 'Final Report',
                'content_length': len(company.research_step_3_report)
            }
        else:
            step_statuses['step_3'] = {
                'completed': False,
                'title': 'Final Report',
                'content_length': 0
            }
        
        return {
            'success': True,
            'company_name': company.company_name,
            'research_status': company.research_status,
            'steps_completed': steps_completed,
            'total_steps': 3,
            'step_statuses': step_statuses,
            'research_started_at': company.research_started_at,
            'research_completed_at': company.research_completed_at,
            'research_error': company.research_error
        }

    def _perform_basic_research(self, company) -> Optional[str]:
        """Perform basic company research (Step 1)."""
        try:
            # Extract domain from website URL
            company_domain = ''
            if company.website_url:
                if company.website_url.startswith(('http://', 'https://')):
                    company_domain = company.website_url.replace('https://', '').replace('http://', '').split('/')[0]
                else:
                    company_domain = company.website_url
            
            # Perform basic research
            research = self.ai_service.research_company(company.company_name, company_domain)
            
            if research:
                logger.info(f"Basic research completed for {company.company_name}: {len(research)} characters")
                return research
            else:
                logger.error(f"Failed to get basic research for {company.company_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error in basic research for {company.company_name}: {e}")
            return None

    def _perform_strategic_analysis(self, company, basic_research: str) -> Optional[str]:
        """Perform strategic analysis (Step 2)."""
        try:
            # Generate strategic recommendations
            strategic_result = self.ai_service.generate_strategic_recommendations(
                company.company_name, 
                basic_research
            )
            
            if strategic_result:
                # Handle new format that returns both structured data and JSON string
                if isinstance(strategic_result, dict) and 'json_string' in strategic_result:
                    json_string = strategic_result['json_string']
                    logger.info(f"Strategic analysis completed for {company.company_name}: {len(json_string)} characters")
                    return strategic_result  # Return full dict with both structured_data and json_string
                else:
                    # Legacy format support
                    logger.info(f"Strategic analysis completed for {company.company_name}: {len(strategic_result)} characters")
                    return strategic_result
            else:
                logger.error(f"Failed to get strategic analysis for {company.company_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error in strategic analysis for {company.company_name}: {e}")
            return None

    def _generate_final_report(self, company, basic_research: str, strategic_analysis: str) -> Optional[Dict[str, str]]:
        """Generate final HTML/PDF report (Step 3)."""
        try:
            # Convert JSON string back to structured data for report rendering
            import json
            try:
                strategic_data = json.loads(strategic_analysis)
            except (json.JSONDecodeError, TypeError):
                # If it's not JSON, treat as legacy format
                strategic_data = strategic_analysis
            # Generate strategic imperatives and agent recommendations
            strategic_imperatives, agent_recommendations = self.ai_service.generate_strategic_imperatives_and_agent_recommendations(
                company.company_name, 
                basic_research
            )
            
            # Generate HTML/PDF strategic report
            report_data = self.report_generator.generate_strategic_report(
                company.company_name,
                basic_research,
                strategic_data  # Pass structured data instead of JSON string
            )
            
            if report_data and report_data['html_report']:
                logger.info(f"Final report generated for {company.company_name}: {len(report_data['html_report'])} characters")
                return {
                    'html_report': report_data['html_report'],
                    'pdf_report_base64': report_data['pdf_report_base64'],
                    'strategic_imperatives': strategic_imperatives,
                    'agent_recommendations': agent_recommendations
                }
            else:
                logger.error(f"Failed to generate final report for {company.company_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error in final report generation for {company.company_name}: {e}")
            return None

    def resume_research(self, company_id: int) -> Dict[str, Any]:
        """Resume incomplete research from where it left off."""
        from app.models.company import Company
        
        logger.info(f"Attempting to resume research for company ID: {company_id}")
        
        company = Company.get_by_id(company_id)
        if not company:
            return {'success': False, 'error': 'Company not found'}
        
        if company.research_status == 'completed':
            return {'success': True, 'message': 'Research already completed', 'status': 'completed'}
        
        try:
            # Determine which step to resume from
            if not company.research_step_1_basic:
                # Start from step 1
                logger.info(f"Resuming from step 1 for {company.company_name}")
                return self.start_deep_research(company_id, force_refresh=True)
            
            elif not company.research_step_2_strategic:
                # Resume from step 2
                logger.info(f"Resuming from step 2 for {company.company_name}")
                Company.update_research_status(company_id, 'in_progress')
                
                strategic_result = self._perform_strategic_analysis(company, company.research_step_1_basic)
                if not strategic_result:
                    Company.update_research_status(company_id, 'failed', 'Failed at strategic analysis step (resume)')
                    return {'success': False, 'error': 'Failed to complete strategic analysis'}
                
                # Extract structured AI agent recommendations if available
                if isinstance(strategic_result, dict) and 'structured_data' in strategic_result:
                    structured_data = strategic_result['structured_data']
                    strategic_analysis = strategic_result['json_string']
                    
                    # Extract and store AI agent recommendations
                    if 'ai_agent_recommendations' in structured_data:
                        ai_recommendations = structured_data['ai_agent_recommendations']['priorities']
                        logger.info(f"🤖 DEBUG: Found AI agent recommendations in structured data, storing {len(ai_recommendations)} recommendations")
                        success = Company.update_ai_agent_recommendations(company_id, ai_recommendations)
                        if success:
                            logger.info(f"✅ DEBUG: Successfully stored {len(ai_recommendations)} AI agent recommendations for {company.company_name}")
                        else:
                            logger.error(f"❌ DEBUG: Failed to store AI agent recommendations for {company.company_name}")
                    else:
                        logger.warning(f"⚠️ DEBUG: No 'ai_agent_recommendations' found in structured_data for {company.company_name}")
                        logger.info(f"📋 DEBUG: Available keys in structured_data: {list(structured_data.keys())}")
                else:
                    strategic_analysis = strategic_result
                
                Company.update_research_step(company_id, 2, strategic_analysis)
                
                # Continue to step 3
                report_data = self._generate_final_report(company, company.research_step_1_basic, strategic_analysis)
                if not report_data:
                    Company.update_research_status(company_id, 'failed', 'Failed at report generation step (resume)')
                    return {'success': False, 'error': 'Failed to generate final report'}
                
                # Store step 3 results with HTML/PDF data and mark as completed
                success = self.db_service.update_company_research_with_reports(
                    company_id,
                    company.research_step_1_basic,
                    strategic_analysis=strategic_analysis,
                    html_report=report_data['html_report'],
                    pdf_report_base64=report_data['pdf_report_base64'],
                    strategic_imperatives=report_data.get('strategic_imperatives', ''),
                    agent_recommendations=report_data.get('agent_recommendations', ''),
                    status='completed'
                )
                
                return {
                    'success': True,
                    'message': f'Research resumed and completed for {company.company_name}',
                    'status': 'completed'
                }
            
            elif not company.research_step_3_report:
                # Resume from step 3
                logger.info(f"Resuming from step 3 for {company.company_name}")
                Company.update_research_status(company_id, 'in_progress')
                
                report_data = self._generate_final_report(
                    company, 
                    company.research_step_1_basic, 
                    company.research_step_2_strategic
                )
                
                if not report_data:
                    Company.update_research_status(company_id, 'failed', 'Failed at report generation step (resume)')
                    return {'success': False, 'error': 'Failed to generate final report'}
                
                # Store step 3 results with HTML/PDF data and mark as completed
                success = self.db_service.update_company_research_with_reports(
                    company_id,
                    company.research_step_1_basic,
                    strategic_analysis=company.research_step_2_strategic,
                    html_report=report_data['html_report'],
                    pdf_report_base64=report_data['pdf_report_base64'],
                    strategic_imperatives=report_data.get('strategic_imperatives', ''),
                    agent_recommendations=report_data.get('agent_recommendations', ''),
                    status='completed'
                )
                
                return {
                    'success': True,
                    'message': f'Research resumed and completed for {company.company_name}',
                    'status': 'completed'
                }
            
            else:
                # All steps completed, just update status
                Company.update_research_status(company_id, 'completed')
                return {
                    'success': True,
                    'message': f'Research was already complete for {company.company_name}',
                    'status': 'completed'
                }
                
        except Exception as e:
            logger.error(f"Error resuming research for company {company_id}: {e}")
            Company.update_research_status(company_id, 'failed', str(e))
            return {'success': False, 'error': f'Resume failed: {str(e)}'} 