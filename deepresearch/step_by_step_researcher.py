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
        
        # Check if research already exists and not forcing refresh
        if not force_refresh and company.research_status == 'completed':
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
            strategic_analysis = self._perform_strategic_analysis(company, basic_research)
            
            if not strategic_analysis:
                Company.update_research_status(company_id, 'failed', 'Failed at strategic analysis step')
                return {'success': False, 'error': 'Failed to complete strategic analysis'}
            
            # Store step 2 results
            Company.update_research_step(company_id, 2, strategic_analysis)
            logger.info(f"Step 2 completed for {company.company_name}")
            
            # Step 3: Report Generation
            logger.info(f"Step 3: Starting report generation for {company.company_name}")
            markdown_report = self._generate_final_report(company, basic_research, strategic_analysis)
            
            if not markdown_report:
                Company.update_research_status(company_id, 'failed', 'Failed at report generation step')
                return {'success': False, 'error': 'Failed to generate final report'}
            
            # Store step 3 results and mark as completed
            Company.update_full_research(company_id, basic_research, strategic_analysis, markdown_report)
            logger.info(f"Step 3 completed for {company.company_name}")
            
            # Write report file
            try:
                self.report_generator.write_report_file(company.company_name, markdown_report)
                logger.info(f"Report file written for {company.company_name}")
            except Exception as e:
                logger.warning(f"Failed to write report file for {company.company_name}: {e}")
            
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
            strategic_analysis = self.ai_service.generate_strategic_recommendations(
                company.company_name, 
                basic_research
            )
            
            if strategic_analysis:
                logger.info(f"Strategic analysis completed for {company.company_name}: {len(strategic_analysis)} characters")
                return strategic_analysis
            else:
                logger.error(f"Failed to get strategic analysis for {company.company_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error in strategic analysis for {company.company_name}: {e}")
            return None

    def _generate_final_report(self, company, basic_research: str, strategic_analysis: str) -> Optional[str]:
        """Generate final markdown report (Step 3)."""
        try:
            # Generate markdown report
            markdown_report = self.report_generator.generate_markdown_report(
                company.company_name,
                basic_research,
                strategic_analysis
            )
            
            if markdown_report:
                logger.info(f"Final report generated for {company.company_name}: {len(markdown_report)} characters")
                return markdown_report
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
                
                strategic_analysis = self._perform_strategic_analysis(company, company.research_step_1_basic)
                if not strategic_analysis:
                    Company.update_research_status(company_id, 'failed', 'Failed at strategic analysis step (resume)')
                    return {'success': False, 'error': 'Failed to complete strategic analysis'}
                
                Company.update_research_step(company_id, 2, strategic_analysis)
                
                # Continue to step 3
                markdown_report = self._generate_final_report(company, company.research_step_1_basic, strategic_analysis)
                if not markdown_report:
                    Company.update_research_status(company_id, 'failed', 'Failed at report generation step (resume)')
                    return {'success': False, 'error': 'Failed to generate final report'}
                
                Company.update_full_research(company_id, company.research_step_1_basic, strategic_analysis, markdown_report)
                
                return {
                    'success': True,
                    'message': f'Research resumed and completed for {company.company_name}',
                    'status': 'completed'
                }
            
            elif not company.research_step_3_report:
                # Resume from step 3
                logger.info(f"Resuming from step 3 for {company.company_name}")
                Company.update_research_status(company_id, 'in_progress')
                
                markdown_report = self._generate_final_report(
                    company, 
                    company.research_step_1_basic, 
                    company.research_step_2_strategic
                )
                
                if not markdown_report:
                    Company.update_research_status(company_id, 'failed', 'Failed at report generation step (resume)')
                    return {'success': False, 'error': 'Failed to generate final report'}
                
                Company.update_full_research(
                    company_id, 
                    company.research_step_1_basic, 
                    company.research_step_2_strategic, 
                    markdown_report
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