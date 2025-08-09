#!/usr/bin/env python3
"""
LLM Workflow Orchestrator

Orchestrates the 3-step LLM research workflow:
1. Step 1: OpenAI Deep Research (background job)
2. Step 2: Strategic Analysis (regular LLM call using original AI service)
3. Step 3: Report Generation (using original report generator)

This replaces the monolithic logic in llm_deep_research_service.py with focused handlers.
"""

import logging
from typing import Optional, Dict, Any
from openai import OpenAI
from deepresearch.llm_step_1_handler import LLMStep1Handler
from deepresearch.llm_step_2_handler import LLMStep2Handler
from deepresearch.llm_step_3_handler import LLMStep3Handler

logger = logging.getLogger(__name__)

class LLMWorkflowOrchestrator:
    """Orchestrates the complete 3-step LLM research workflow."""
    
    def __init__(self, openai_client: OpenAI):
        self.openai_client = openai_client
        self.step_1_handler = LLMStep1Handler(openai_client)
        self.step_2_handler = LLMStep2Handler()
        self.step_3_handler = LLMStep3Handler()
        logger.info("LLMWorkflowOrchestrator initialized with all step handlers")
    
    def start_step_1(self, company_name: str, website_url: str, company_id: int) -> Optional[str]:
        """Start step 1 deep research background job."""
        logger.info(f"🚀 STEP 1: Starting deep research for {company_name}")
        return self.step_1_handler.start_deep_research(company_name, website_url, company_id)
    
    def process_step_1_completion_and_start_step_2(self, company_id: int, company_name: str, website_url: str, step_1_results: str):
        """Process step 1 completion and automatically start step 2."""
        try:
            logger.info(f"🚀 STEP 1 → STEP 2: Processing step 1 completion and starting step 2 for {company_name}")
            
            # Save step 1 results
            self._save_step_1_results(company_id, step_1_results)
            
            # Start step 2
            self._execute_step_2(company_id, company_name, website_url, step_1_results)
            
        except Exception as e:
            logger.error(f"Error in step 1→2 transition for {company_name}: {e}")
            self._mark_research_failed(company_id, f"Step 1→2 transition failed: {str(e)}")
    
    def _execute_step_2(self, company_id: int, company_name: str, website_url: str, step_1_results: str):
        """Execute step 2 strategic analysis."""
        try:
            logger.info(f"🚀 STEP 2: Starting strategic analysis for {company_name}")
            
            # Update status
            self._update_research_status(company_name, "Executing step 2 strategic analysis", company_id)
            
            # Perform strategic analysis using original AI service
            strategic_result = self.step_2_handler.perform_strategic_analysis(company_name, step_1_results)
            
            if not strategic_result:
                self._mark_research_failed(company_id, "Step 2 strategic analysis failed or validation failed")
                logger.error(f"🚫 WORKFLOW STOPPED for {company_name}: Step 2 strategic analysis returned None - this indicates either generation failure or validation failure")
                return
            
            # Extract and store AI agent recommendations (original logic)
            self.step_2_handler.extract_and_store_ai_recommendations(strategic_result, company_id, company_name)
            
            # Get the JSON string for database storage
            if isinstance(strategic_result, dict) and 'json_string' in strategic_result:
                strategic_analysis = strategic_result['json_string']
            else:
                strategic_analysis = strategic_result
            
            # Save step 2 results
            self._save_step_2_results(company_id, strategic_analysis)
            
            logger.info(f"✅ STEP 2: Completed strategic analysis for {company_name}")
            
            # Automatically start step 3
            self._execute_step_3(company_id, company_name, website_url, step_1_results, strategic_analysis)
            
        except Exception as e:
            logger.error(f"Error in step 2 execution for {company_name}: {e}")
            self._mark_research_failed(company_id, f"Step 2 failed: {str(e)}")
    
    def _execute_step_3(self, company_id: int, company_name: str, website_url: str, step_1_results: str, step_2_results: str):
        """Execute step 3 report generation."""
        try:
            logger.info(f"🚀 STEP 3: Starting report generation for {company_name}")
            
            # Update status
            self._update_research_status(company_name, "Generating comprehensive report", company_id)
            
            # Generate final report using original report generator
            report_data = self.step_3_handler.generate_final_report(company_name, step_1_results, step_2_results)
            
            if not report_data:
                self._mark_research_failed(company_id, "Step 3 report generation failed")
                return
            
            # Store report data using original database service method
            success = self.step_3_handler.store_report_data(company_id, company_name, step_1_results, step_2_results, report_data)
            
            if success:
                # Mark as completed
                self._mark_research_completed(company_id)
                logger.info(f"🎉 WORKFLOW COMPLETE: All 3 steps finished for {company_name}")
            else:
                self._mark_research_failed(company_id, "Failed to save report data")
            
        except Exception as e:
            logger.error(f"Error in step 3 execution for {company_name}: {e}")
            self._mark_research_failed(company_id, f"Step 3 failed: {str(e)}")
    
    def _save_step_1_results(self, company_id: int, results: str):
        """Save step 1 results to database."""
        from deepresearch.database_service import DatabaseService
        from sqlalchemy import text
        
        db_service = DatabaseService()
        with db_service.engine.connect() as conn:
            with conn.begin():
                conn.execute(text("""
                    UPDATE companies 
                    SET llm_research_step_1_basic = :results,
                        llm_research_step_status = 'step_1_completed',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :company_id
                """), {
                    'results': results,
                    'company_id': company_id
                })
    
    def _save_step_2_results(self, company_id: int, results: str):
        """Save step 2 results to database."""
        from deepresearch.database_service import DatabaseService
        from sqlalchemy import text
        
        db_service = DatabaseService()
        with db_service.engine.connect() as conn:
            with conn.begin():
                conn.execute(text("""
                    UPDATE companies 
                    SET llm_research_step_2_strategic = :results,
                        llm_research_step_status = 'step_2_completed',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :company_id
                """), {
                    'results': results,
                    'company_id': company_id
                })
    
    def _update_research_status(self, company_name: str, status: str, company_id: int):
        """Update research status in database."""
        from deepresearch.database_service import DatabaseService
        from sqlalchemy import text
        
        db_service = DatabaseService()
        with db_service.engine.connect() as conn:
            with conn.begin():
                conn.execute(text("""
                    UPDATE companies 
                    SET llm_research_step_status = :status,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :company_id
                """), {
                    'status': status,
                    'company_id': company_id
                })
        
        logger.info(f"Updated research status for {company_name}: {status}")
    
    def _mark_research_completed(self, company_id: int):
        """Mark research as completed."""
        from deepresearch.database_service import DatabaseService
        from sqlalchemy import text
        
        db_service = DatabaseService()
        with db_service.engine.connect() as conn:
            with conn.begin():
                conn.execute(text("""
                    UPDATE companies 
                    SET llm_research_step_status = 'step_3_completed',
                        llm_research_completed_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :company_id
                """), {
                    'company_id': company_id
                })
    
    def _mark_research_failed(self, company_id: int, error_message: str):
        """Mark research as failed."""
        from deepresearch.database_service import DatabaseService
        from sqlalchemy import text
        
        db_service = DatabaseService()
        with db_service.engine.connect() as conn:
            with conn.begin():
                conn.execute(text("""
                    UPDATE companies 
                    SET llm_research_step_status = :status,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :company_id
                """), {
                    'status': f'failed: {error_message}',
                    'company_id': company_id
                })
        
        logger.error(f"Marked research as failed for company {company_id}: {error_message}")
    
    def manual_trigger_step_2(self, company_id: int) -> Dict[str, Any]:
        """Manually trigger step 2 if step 1 is completed but step 2 hasn't started."""
        try:
            # Get company info and validate step 1 is completed
            from deepresearch.database_service import DatabaseService
            from sqlalchemy import text
            
            db_service = DatabaseService()
            with db_service.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT company_name, website_url, llm_research_step_status,
                           llm_research_step_1_basic, llm_research_step_2_strategic
                    FROM companies WHERE id = :company_id
                """), {'company_id': company_id})
                
                company_row = result.fetchone()
                if not company_row:
                    return {'success': False, 'error': f'Company {company_id} not found'}
                
                company_name = company_row[0]
                website_url = company_row[1] or ""
                current_status = company_row[2] or ""
                step_1_content = company_row[3] or ""
                step_2_content = company_row[4] or ""
            
            # Validate prerequisites
            if not step_1_content:
                return {'success': False, 'error': 'Step 1 must be completed before triggering step 2'}
            
            if step_2_content:
                return {'success': False, 'error': 'Step 2 is already completed'}
            
            if current_status and 'step_2' in current_status.lower():
                return {'success': False, 'error': 'Step 2 is already in progress'}
            
            logger.info(f"🔧 MANUAL TRIGGER: Starting step 2 for {company_name} (company_id: {company_id})")
            
            # Execute step 2
            self._execute_step_2(company_id, company_name, website_url, step_1_content)
            
            return {
                'success': True,
                'message': f'Step 2 manually triggered for {company_name}',
                'company_name': company_name
            }
            
        except Exception as e:
            logger.error(f"Error manually triggering step 2 for company {company_id}: {e}")
            return {'success': False, 'error': f'Failed to trigger step 2: {str(e)}'}
    
    def manual_trigger_step_3(self, company_id: int) -> Dict[str, Any]:
        """Manually trigger step 3 if step 2 is completed but step 3 hasn't started."""
        try:
            # Get company info and validate step 2 is completed
            from deepresearch.database_service import DatabaseService
            from sqlalchemy import text
            
            db_service = DatabaseService()
            with db_service.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT company_name, website_url, llm_research_step_status,
                           llm_research_step_1_basic, llm_research_step_2_strategic,
                           html_report, llm_research_completed_at
                    FROM companies WHERE id = :company_id
                """), {'company_id': company_id})
                
                company_row = result.fetchone()
                if not company_row:
                    return {'success': False, 'error': f'Company {company_id} not found'}
                
                company_name = company_row[0]
                website_url = company_row[1] or ""
                current_status = company_row[2] or ""
                step_1_content = company_row[3] or ""
                step_2_content = company_row[4] or ""
                html_report = company_row[5] or ""
                completed_at = company_row[6]
            
            # Validate prerequisites
            if not step_1_content:
                return {'success': False, 'error': 'Step 1 must be completed before triggering step 3'}
            
            if not step_2_content:
                return {'success': False, 'error': 'Step 2 must be completed before triggering step 3'}
            
            if html_report and completed_at:
                return {'success': False, 'error': 'Step 3 is already completed (HTML report exists)'}
            
            if current_status and 'step_3' in current_status.lower():
                return {'success': False, 'error': 'Step 3 is already in progress'}
            
            logger.info(f"🔧 MANUAL TRIGGER: Starting step 3 for {company_name} (company_id: {company_id})")
            
            # Execute step 3
            self._execute_step_3(company_id, company_name, website_url, step_1_content, step_2_content)
            
            return {
                'success': True,
                'message': f'Step 3 manually triggered for {company_name}',
                'company_name': company_name
            }
            
        except Exception as e:
            logger.error(f"Error manually triggering step 3 for company {company_id}: {e}")
            return {'success': False, 'error': f'Failed to trigger step 3: {str(e)}'}
    
    def get_step_status(self, company_id: int) -> Dict[str, Any]:
        """Get detailed status of all research steps for a company."""
        try:
            from deepresearch.database_service import DatabaseService
            from sqlalchemy import text
            
            db_service = DatabaseService()
            with db_service.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT company_name, llm_research_step_status,
                           llm_research_step_1_basic, llm_research_step_2_strategic,
                           html_report, llm_research_completed_at,
                           llm_research_started_at
                    FROM companies WHERE id = :company_id
                """), {'company_id': company_id})
                
                company_row = result.fetchone()
                if not company_row:
                    return {'success': False, 'error': f'Company {company_id} not found'}
                
                company_name = company_row[0]
                current_status = company_row[1] or ""
                step_1_content = company_row[2] or ""
                step_2_content = company_row[3] or ""
                html_report = company_row[4] or ""
                completed_at = company_row[5]
                started_at = company_row[6]
            
            # Determine step statuses and available actions
            step_1_completed = bool(step_1_content and not step_1_content.startswith('ERROR:'))
            step_2_completed = bool(step_2_content)
            step_3_completed = bool(html_report and completed_at)
            
            # Determine if manual triggers are available
            can_trigger_step_2 = step_1_completed and not step_2_completed and 'step_2' not in current_status.lower()
            can_trigger_step_3 = step_2_completed and not step_3_completed and 'step_3' not in current_status.lower()
            
            return {
                'success': True,
                'company_id': company_id,
                'company_name': company_name,
                'current_status': current_status,
                'started_at': started_at,
                'completed_at': completed_at,
                'steps': {
                    'step_1': {
                        'completed': step_1_completed,
                        'has_content': bool(step_1_content),
                        'content_length': len(step_1_content) if step_1_content else 0
                    },
                    'step_2': {
                        'completed': step_2_completed,
                        'has_content': bool(step_2_content),
                        'content_length': len(step_2_content) if step_2_content else 0,
                        'can_manual_trigger': can_trigger_step_2
                    },
                    'step_3': {
                        'completed': step_3_completed,
                        'has_content': bool(html_report),
                        'content_length': len(html_report) if html_report else 0,
                        'can_manual_trigger': can_trigger_step_3
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting step status for company {company_id}: {e}")
            return {'success': False, 'error': f'Failed to get step status: {str(e)}'}