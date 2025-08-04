#!/usr/bin/env python3
"""
LLM Step 2 Handler

Manages Step 2 (Strategic Analysis) using the original AI research service.
This uses the identical prompts and logic from the original step-by-step researcher.
"""

import logging
from typing import Optional, Dict, Any
from deepresearch.ai_research_service import AIResearchService

logger = logging.getLogger(__name__)

class LLMStep2Handler:
    """Handles Step 2 strategic analysis using original AI research service."""
    
    def __init__(self):
        self.ai_service = AIResearchService()
        logger.info("LLMStep2Handler initialized with original AI research service")
    
    def perform_strategic_analysis(self, company_name: str, step_1_results: str) -> Optional[Dict[str, Any]]:
        """
        Perform strategic analysis using the original AI research service.
        This is identical to the original step-by-step researcher logic.
        """
        try:
            logger.info(f"Starting strategic analysis for {company_name}")
            
            # Use the original AI service method - identical to step_by_step_researcher.py
            strategic_result = self.ai_service.generate_strategic_recommendations(
                company_name, 
                step_1_results
            )
            
            if strategic_result:
                # Handle the format exactly like the original - returns both structured data and JSON string
                if isinstance(strategic_result, dict) and 'json_string' in strategic_result:
                    json_string = strategic_result['json_string']
                    logger.info(f"Strategic analysis completed for {company_name}: {len(json_string)} characters")
                    return strategic_result  # Return full dict with both structured_data and json_string
                else:
                    # Legacy format support
                    logger.info(f"Strategic analysis completed for {company_name}: {len(strategic_result)} characters")
                    return {'json_string': strategic_result, 'structured_data': None}
            else:
                logger.error(f"Failed to get strategic analysis for {company_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error in strategic analysis for {company_name}: {e}")
            return None
    
    def extract_and_store_ai_recommendations(self, strategic_result: Dict[str, Any], company_id: int, company_name: str) -> bool:
        """
        Extract and store AI agent recommendations from structured data.
        This is identical to the original step-by-step researcher logic.
        """
        try:
            # Extract structured AI agent recommendations if available - identical logic
            if isinstance(strategic_result, dict) and 'structured_data' in strategic_result:
                structured_data = strategic_result['structured_data']
                
                # Extract and store AI agent recommendations
                if 'ai_agent_recommendations' in structured_data:
                    ai_recommendations = structured_data['ai_agent_recommendations']['priorities']
                    logger.info(f"🤖 DEBUG: Found AI agent recommendations in structured data, storing {len(ai_recommendations)} recommendations")
                    
                    from app.models.company import Company
                    success = Company.update_ai_agent_recommendations(company_id, ai_recommendations)
                    if success:
                        logger.info(f"✅ DEBUG: Successfully stored {len(ai_recommendations)} AI agent recommendations for {company_name}")
                        return True
                    else:
                        logger.error(f"❌ DEBUG: Failed to store AI agent recommendations for {company_name}")
                        return False
                else:
                    logger.warning(f"⚠️ DEBUG: No 'ai_agent_recommendations' found in structured_data for {company_name}")
                    logger.info(f"📋 DEBUG: Available keys in structured_data: {list(structured_data.keys())}")
                    return False
            else:
                logger.info(f"No structured data available for AI recommendations extraction for {company_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error extracting AI recommendations for {company_name}: {e}")
            return False