#!/usr/bin/env python3
"""
LLM Step 2 Handler

Manages Step 2 (Strategic Analysis) using the original AI research service.
This uses the identical prompts and logic from the original step-by-step researcher.
"""

import logging
import json
from typing import Optional, Dict, Any, List
from deepresearch.ai_research_service import AIResearchService

logger = logging.getLogger(__name__)


def validate_step_2_json_output(json_string: str, company_name: str) -> Dict[str, Any]:
    """
    Comprehensive validation of step 2 JSON output.
    Returns validation results with success flag and detailed feedback.
    """
    validation_result = {
        'is_valid': False,
        'errors': [],
        'warnings': [],
        'json_data': None,
        'validation_summary': ''
    }
    
    try:
        # 1. JSON Parsing Validation
        try:
            json_data = json.loads(json_string)
            validation_result['json_data'] = json_data
            logger.info(f"✅ Step 2 JSON parsing successful for {company_name}")
        except json.JSONDecodeError as e:
            validation_result['errors'].append(f"Invalid JSON format: {str(e)}")
            logger.error(f"❌ Step 2 JSON parsing failed for {company_name}: {e}")
            return validation_result
        
        # 2. Required Top-level Structure Validation  
        # Updated to match our actual JSON schema
        required_keys = ['introduction', 'strategic_imperatives', 'ai_agent_recommendations', 'expected_business_impact']
        missing_keys = []
        for key in required_keys:
            if key not in json_data:
                missing_keys.append(key)
        
        if missing_keys:
            validation_result['errors'].append(f"Missing required keys: {missing_keys}")
            logger.error(f"❌ Step 2 missing required keys for {company_name}: {missing_keys}")
            return validation_result
        
        # 3. Strategic Imperatives Validation
        strategic_imperatives = json_data.get('strategic_imperatives', [])
        if not isinstance(strategic_imperatives, list):
            validation_result['errors'].append("strategic_imperatives must be a list")
        elif len(strategic_imperatives) != 2:
            validation_result['warnings'].append(f"Found {len(strategic_imperatives)} strategic imperatives, expected exactly 2")
        
        # Validate each imperative structure (updated to match our schema)
        for i, imperative in enumerate(strategic_imperatives):
            if not isinstance(imperative, dict):
                validation_result['errors'].append(f"Strategic imperative {i+1} must be an object")
                continue
                
            required_imp_keys = ['title', 'context', 'ai_agent_opportunity', 'expected_impact']
            for imp_key in required_imp_keys:
                if imp_key not in imperative:
                    validation_result['errors'].append(f"Strategic imperative {i+1} missing key: {imp_key}")
                elif not imperative[imp_key] or not str(imperative[imp_key]).strip():
                    validation_result['errors'].append(f"Strategic imperative {i+1} has empty {imp_key}")
        
        # 4. AI Agent Recommendations Validation (updated to match our schema)
        ai_recommendations = json_data.get('ai_agent_recommendations', {})
        if not isinstance(ai_recommendations, dict):
            validation_result['errors'].append("ai_agent_recommendations must be an object")
        else:
            # Validate top-level structure
            required_ai_keys = ['introduction', 'priorities']
            for ai_key in required_ai_keys:
                if ai_key not in ai_recommendations:
                    validation_result['errors'].append(f"ai_agent_recommendations missing key: {ai_key}")
            
            # Validate priorities array
            priorities = ai_recommendations.get('priorities', [])
            if not isinstance(priorities, list):
                validation_result['errors'].append("ai_agent_recommendations.priorities must be an array")
            elif len(priorities) != 2:
                validation_result['warnings'].append(f"Found {len(priorities)} priorities, expected exactly 2")
            
            # Validate each priority item
            for i, priority in enumerate(priorities):
                if not isinstance(priority, dict):
                    validation_result['errors'].append(f"Priority {i+1} must be an object")
                    continue
                    
                required_priority_keys = ['imperative_reference', 'title', 'use_case', 'business_impact']
                for priority_key in required_priority_keys:
                    if priority_key not in priority:
                        validation_result['errors'].append(f"Priority {i+1} missing key: {priority_key}")
                    elif not priority[priority_key] or not str(priority[priority_key]).strip():
                        validation_result['errors'].append(f"Priority {i+1} has empty {priority_key}")
        
        # 5. Expected Business Impact Validation (updated to match our schema)
        expected_business_impact = json_data.get('expected_business_impact', [])
        if not isinstance(expected_business_impact, list):
            validation_result['errors'].append("expected_business_impact must be an array")
        elif len(expected_business_impact) < 3:
            validation_result['warnings'].append(f"Only {len(expected_business_impact)} business impact items found, expected 3")
        elif len(expected_business_impact) > 3:
            validation_result['warnings'].append(f"{len(expected_business_impact)} business impact items found, expected exactly 3")
        
        # Validate each business impact item is a non-empty string
        for i, impact_item in enumerate(expected_business_impact):
            if not isinstance(impact_item, str):
                validation_result['errors'].append(f"Expected business impact item {i+1} must be a string")
            elif not impact_item.strip():
                validation_result['errors'].append(f"Expected business impact item {i+1} is empty")
        
        # 6. Content Quality Validation
        introduction = json_data.get('introduction', '')
        if len(str(introduction).strip()) < 100:
            validation_result['warnings'].append("Introduction is too short, expected at least 100 characters")
        elif len(str(introduction).strip()) > 1000:
            validation_result['warnings'].append("Introduction is too long, recommended maximum 1000 characters")
        
        # 7. Final Validation Status
        if not validation_result['errors']:
            validation_result['is_valid'] = True
            validation_result['validation_summary'] = f"✅ Step 2 JSON validation passed for {company_name}"
            if validation_result['warnings']:
                validation_result['validation_summary'] += f" (with {len(validation_result['warnings'])} warnings)"
            logger.info(validation_result['validation_summary'])
        else:
            validation_result['validation_summary'] = f"❌ Step 2 JSON validation failed for {company_name} with {len(validation_result['errors'])} errors"
            logger.error(validation_result['validation_summary'])
        
        return validation_result
        
    except Exception as e:
        validation_result['errors'].append(f"Validation process failed: {str(e)}")
        validation_result['validation_summary'] = f"❌ Step 2 validation exception for {company_name}: {str(e)}"
        logger.error(validation_result['validation_summary'])
        return validation_result


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
            logger.info(f"Calling generate_strategic_recommendations for {company_name} with model {self.ai_service.model}")
            strategic_result = self.ai_service.generate_strategic_recommendations(
                company_name, 
                step_1_results
            )
            logger.info(f"Strategic result type: {type(strategic_result)}, has json_string: {'json_string' in strategic_result if isinstance(strategic_result, dict) else False}")
            
            if strategic_result:
                # Handle the format exactly like the original - returns both structured data and JSON string
                if isinstance(strategic_result, dict) and 'json_string' in strategic_result:
                    json_string = strategic_result['json_string']
                    logger.info(f"Strategic analysis completed for {company_name}: {len(json_string)} characters")
                    
                    # 🔍 VALIDATION: Validate JSON structure before proceeding
                    validation_result = validate_step_2_json_output(json_string, company_name)
                    
                    if validation_result['is_valid']:
                        logger.info(f"✅ Step 2 validation passed for {company_name}")
                        if validation_result['warnings']:
                            logger.warning(f"⚠️ Step 2 validation warnings for {company_name}: {validation_result['warnings']}")
                        return strategic_result  # Return full dict with both structured_data and json_string
                    else:
                        logger.error(f"❌ Step 2 validation failed for {company_name}")
                        logger.error(f"❌ Validation errors: {validation_result['errors']}")
                        logger.error(f"❌ Workflow STOPPED - will not proceed to Step 3 due to invalid JSON structure")
                        return None  # Stop workflow - don't proceed to step 3
                    
                else:
                    # Legacy format support with validation
                    logger.warning(f"Legacy format detected for {company_name}: {len(strategic_result)} characters")
                    
                    # Try to validate legacy format as JSON
                    validation_result = validate_step_2_json_output(str(strategic_result), company_name)
                    
                    if validation_result['is_valid']:
                        logger.info(f"✅ Legacy format validation passed for {company_name}")
                        return {'json_string': strategic_result, 'structured_data': validation_result['json_data']}
                    else:
                        logger.error(f"❌ Legacy format validation failed for {company_name}: {validation_result['errors']}")
                        logger.error(f"❌ Workflow STOPPED - legacy format is not valid JSON")
                        return None  # Stop workflow
            else:
                logger.error(f"❌ Failed to get strategic analysis for {company_name} - no results returned")
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