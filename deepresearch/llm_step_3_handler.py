#!/usr/bin/env python3
"""
LLM Step 3 Handler

Manages Step 3 (Report Generation) using the original report generator.
This uses the identical logic and format from the original step-by-step researcher.
"""

import logging
import json
from typing import Optional, Dict, Any
from deepresearch.ai_research_service import AIResearchService
from deepresearch.report_generator import ReportGenerator

logger = logging.getLogger(__name__)

class LLMStep3Handler:
    """Handles Step 3 report generation using original report generator."""
    
    def __init__(self):
        self.ai_service = AIResearchService()
        self.report_generator = ReportGenerator()
        logger.info("LLMStep3Handler initialized with original AI service and report generator")
    
    def generate_final_report(self, company_name: str, step_1_results: str, step_2_results: str) -> Optional[Dict[str, str]]:
        """
        Generate final HTML/PDF report using the original logic.
        This is identical to the original step-by-step researcher _generate_final_report method.
        """
        try:
            logger.info(f"Starting final report generation for {company_name}")
            
            # Convert JSON string back to structured data for report rendering - identical logic
            try:
                strategic_data = json.loads(step_2_results)
            except (json.JSONDecodeError, TypeError):
                # If it's not JSON, treat as legacy format
                strategic_data = step_2_results
            
            # Generate strategic imperatives and agent recommendations - identical to original
            strategic_imperatives, agent_recommendations = self.ai_service.generate_strategic_imperatives_and_agent_recommendations(
                company_name, 
                step_1_results
            )
            
            # Generate HTML/PDF strategic report - identical to original
            report_data = self.report_generator.generate_strategic_report(
                company_name,
                step_1_results,
                strategic_data  # Pass structured data instead of JSON string
            )
            
            if report_data and report_data['html_report']:
                logger.info(f"Final report generated for {company_name}: {len(report_data['html_report'])} characters")
                return {
                    'html_report': report_data['html_report'],
                    'pdf_report_base64': report_data['pdf_report_base64'],
                    'strategic_imperatives': strategic_imperatives,
                    'agent_recommendations': agent_recommendations
                }
            else:
                logger.error(f"Failed to generate final report for {company_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error in final report generation for {company_name}: {e}")
            return None
    
    def store_report_data(self, company_id: int, company_name: str, step_1_results: str, step_2_results: str, report_data: Dict[str, str]) -> bool:
        """
        Store report data in database using the original database service method.
        This is identical to the original step-by-step researcher logic.
        """
        try:
            from deepresearch.database_service import DatabaseService
            from sqlalchemy import text
            
            db_service = DatabaseService()
            
            # First, store step 2 results if not already stored
            with db_service.engine.connect() as conn:
                with conn.begin():
                    # Update step 2 results and HTML/PDF reports
                    conn.execute(text("""
                        UPDATE companies 
                        SET llm_research_step_2_strategic = :step_2_results,
                            html_report = :html_report,
                            pdf_report_base64 = :pdf_report_base64,
                            strategic_imperatives = :strategic_imperatives,
                            agent_recommendations = :agent_recommendations,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :company_id
                    """), {
                        'company_id': company_id,
                        'step_2_results': step_2_results,
                        'html_report': report_data['html_report'],
                        'pdf_report_base64': report_data['pdf_report_base64'],
                        'strategic_imperatives': report_data.get('strategic_imperatives', ''),
                        'agent_recommendations': report_data.get('agent_recommendations', '')
                    })
            
            logger.info(f"Successfully stored report data for {company_name}")
            return True
                
        except Exception as e:
            logger.error(f"Error storing report data for {company_name}: {e}")
            return False