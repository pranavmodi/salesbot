#!/usr/bin/env python3
"""
LLM Step-by-Step Researcher

Handles step-by-step LLM deep research process similar to the existing
step-by-step researcher but using LLM deep research capabilities.

Process:
1. Step 1: LLM Basic Research - Comprehensive company intelligence gathering
2. Step 2: LLM Strategic Analysis - Strategic insights and AI agent recommendations
3. Step 3: LLM Report Generation - Final formatted reports
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class LLMStepByStepResearcher:
    """Handles step-by-step LLM deep research process."""
    
    def __init__(self):
        load_dotenv()
        logger.info("LLMStepByStepResearcher initialized")

    def start_llm_step_research(self, company_id: int, provider: str = 'claude', force_refresh: bool = False) -> Dict[str, Any]:
        """
        Start the step-by-step LLM research process for a company.
        
        Args:
            company_id: Company ID to research
            provider: LLM provider (claude, openai, perplexity, etc.)
            force_refresh: Whether to restart from step 1 even if data exists
            
        Returns:
            Dictionary with success status and step information
        """
        logger.critical(f"🚨 LLM STEP RESEARCH INITIATED: company_id={company_id}, provider={provider}, force_refresh={force_refresh}")
        logger.info(f"Starting LLM step research for company {company_id}, provider={provider}")
        
        # BULLETPROOF DATABASE CHECK BEFORE STARTING
        if not force_refresh:
            try:
                research_status = self._check_step_research_status(company_id)
                if research_status['already_in_progress']:
                    logger.error(f"🚨 BLOCKED: Step research already in progress for company {company_id}. Status: {research_status['status']}, Started: {research_status['started_at']}")
                    return {
                        'success': False,
                        'error': f"Research already in progress for company {company_id}. Current status: {research_status['status']}. Started at: {research_status['started_at']}",
                        'current_status': research_status['status'],
                        'started_at': research_status['started_at']
                    }
            except Exception as check_error:
                logger.error(f"🚨 DATABASE CHECK FAILED: {check_error}")
                # Continue with caution if database check fails
                pass
        
        try:
            from app.models.company import Company
            from deepresearch.database_service import DatabaseService
            
            # Get company
            company = Company.get_by_id(company_id)
            if not company:
                return {
                    'success': False,
                    'error': f'Company with ID {company_id} not found'
                }
            
            db_service = DatabaseService()
            
            # Determine starting step
            current_step = self._determine_current_step(company, force_refresh)
            
            # Check if Step 1 already exists and log appropriately
            has_step_1 = hasattr(company, 'llm_research_step_1_basic') and company.llm_research_step_1_basic
            if has_step_1 and current_step != 'step_1':
                step_1_source = "manual paste" if getattr(company, 'llm_research_provider', '') == 'manual_paste' else "previous research"
                logger.info(f"🔄 SKIPPING STEP 1: Step 1 already exists from {step_1_source} for {company.company_name}, starting from {current_step}")
            elif current_step == 'step_1':
                if force_refresh:
                    logger.info(f"🔄 FORCE REFRESH: Starting fresh Step 1 research for {company.company_name}")
                else:
                    logger.info(f"🚀 STARTING FRESH: No existing research found for {company.company_name}, starting from Step 1")
            
            # Update research metadata
            self._update_research_metadata(db_service, company_id, provider, current_step)
            
            # Execute the appropriate step
            if current_step == 'step_1':
                result = self._execute_step_1(company, provider)
            elif current_step == 'step_2':
                result = self._execute_step_2(company, provider)
            elif current_step == 'step_3':
                result = self._execute_step_3(company, provider)
            else:
                result = {
                    'success': False,
                    'error': f'Invalid step: {current_step}'
                }
            
            # If step completed successfully, automatically continue to next step
            # BUT: Don't auto-continue if it's a background job (OpenAI) that's still running
            if (result['success'] and 
                current_step != 'step_3' and 
                result.get('status') != 'background_job_running'):
                
                logger.info(f"Step {current_step} completed successfully for {company.company_name}, continuing to next step...")
                
                # Refresh company data to get updated step results
                company = Company.get_by_id(company_id)
                next_step = self._determine_current_step(company, False)
                
                if next_step in ['step_2', 'step_3']:
                    logger.info(f"Auto-executing {next_step} for {company.company_name}")
                    
                    # Execute next step
                    if next_step == 'step_2':
                        next_result = self._execute_step_2(company, provider)
                    elif next_step == 'step_3':
                        next_result = self._execute_step_3(company, provider)
                    
                    if next_result['success']:
                        logger.info(f"Step {next_step} auto-execution completed for {company.company_name}")
                        
                        # If step 2 completed, also execute step 3
                        if next_step == 'step_2':
                            logger.info(f"Step 2 completed, auto-executing step 3 for {company.company_name}")
                            company = Company.get_by_id(company_id)  # Refresh again
                            final_step = self._determine_current_step(company, False)
                            
                            if final_step == 'step_3':
                                final_result = self._execute_step_3(company, provider)
                                if final_result['success']:
                                    logger.info(f"All steps completed automatically for {company.company_name}")
                                    return {
                                        'success': True,
                                        'company_id': company_id,
                                        'company_name': company.company_name,
                                        'current_step': 'step_3',
                                        'provider': provider,
                                        'message': 'All 3 research steps completed automatically',
                                        'auto_progression': True
                                    }
                        
                        return {
                            'success': True,
                            'company_id': company_id,
                            'company_name': company.company_name,
                            'current_step': next_step,
                            'provider': provider,
                            'message': f'Steps {current_step} and {next_step} completed automatically',
                            'auto_progression': True
                        }
                    else:
                        logger.error(f"Auto-execution of {next_step} failed for {company.company_name}: {next_result.get('error')}")
            
            return {
                'success': result['success'],
                'company_id': company_id,
                'company_name': company.company_name,
                'current_step': current_step,
                'provider': provider,
                'message': result.get('message', ''),
                'error': result.get('error', '')
            }
            
        except Exception as e:
            logger.error(f"🚨 ERROR: LLM step research failed for company {company_id}: {e}")
            # Mark as failed in database
            try:
                self._mark_step_research_failed(company_id, str(e))
            except Exception as db_error:
                logger.error(f"Failed to mark research as failed in DB: {db_error}")
            
            return {
                'success': False,
                'error': str(e)
            }

    def _determine_current_step(self, company, force_refresh: bool) -> str:
        """Determine which step to execute based on current state."""
        if force_refresh:
            return 'step_1'
        
        # Check what steps are completed (excluding error results)
        has_step_1 = (hasattr(company, 'llm_research_step_1_basic') and 
                     company.llm_research_step_1_basic and 
                     not company.llm_research_step_1_basic.startswith('ERROR:'))
        
        has_step_2 = (hasattr(company, 'llm_research_step_2_strategic') and 
                     company.llm_research_step_2_strategic and 
                     not company.llm_research_step_2_strategic.startswith('ERROR:'))
        
        has_step_3 = (hasattr(company, 'llm_research_step_3_report') and 
                     company.llm_research_step_3_report and 
                     not company.llm_research_step_3_report.startswith('ERROR:'))
        
        # Also check for HTML report as step 3 indicator
        has_html_report = (hasattr(company, 'html_report') and 
                          company.html_report and 
                          not company.html_report.startswith('ERROR:'))
        
        if not has_step_1:
            return 'step_1'
        elif not has_step_2:
            return 'step_2'
        elif not has_step_3 and not has_html_report:
            return 'step_3'
        else:
            return 'completed'

    def _update_research_metadata(self, db_service, company_id: int, provider: str, step: str):
        """Update research metadata in database."""
        try:
            # Use the existing LLM research methods and add step-specific updates
            db_service.update_company_llm_research(
                company_id,
                status=f'in_progress_{step}'
            )
            
            # Update step-specific fields using direct SQL
            from sqlalchemy import text
            with db_service.engine.connect() as conn:
                with conn.begin():
                    conn.execute(text("""
                        UPDATE companies 
                        SET llm_research_step_status = :step_status,
                            llm_research_provider = :provider,
                            llm_research_started_at = COALESCE(llm_research_started_at, CURRENT_TIMESTAMP),
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :company_id
                    """), {
                        'step_status': step,
                        'provider': provider,
                        'company_id': company_id
                    })
            
            logger.info(f"Updated research metadata for company {company_id}: step={step}, provider={provider}")
            
        except Exception as e:
            logger.error(f"Error updating research metadata for company {company_id}: {e}")

    def _execute_step_1(self, company, provider: str) -> Dict[str, Any]:
        """Execute Step 1: LLM Basic Research."""
        logger.info(f"Executing Step 1 (LLM Basic Research) for {company.company_name}")
        
        try:
            from deepresearch.llm_deep_research_service import LLMDeepResearchService
            
            llm_service = LLMDeepResearchService()
            
            # Execute automatic research using the specified provider with safety tracking
            research_results = llm_service.research_company_deep(
                company.company_name,
                company.website_url or "",
                provider=provider,
                company_id=company.id,  # CRITICAL: Pass company_id for safety tracking
                from_step_researcher=True  # CRITICAL: Skip duplicate check since we're in step process
            )
            
            # Handle background job markers
            if research_results == "__BACKGROUND_JOB_STARTED__":
                logger.info(f"Background job started for {company.company_name}, will be completed asynchronously")
                return {
                    'success': True,
                    'message': f'Background research job started for {company.company_name} using {provider}. Job will complete asynchronously.',
                    'step': 'step_1',
                    'status': 'background_job_running',
                    'provider': provider,
                    'next_action': 'Background job is running. Status will update automatically when completed.'
                }
            elif research_results == "__BACKGROUND_JOB_IN_PROGRESS__":
                logger.info(f"Background job still in progress for {company.company_name}")
                return {
                    'success': True,
                    'message': f'Background research job for {company.company_name} is still in progress using {provider}.',
                    'step': 'step_1',
                    'status': 'background_job_running',
                    'provider': provider,
                    'next_action': 'Background job is running. Please wait for completion.'
                }
            
            if not research_results:
                # Store error status in database
                from deepresearch.database_service import DatabaseService
                from sqlalchemy import text
                db_service = DatabaseService()
                
                error_msg = f'Failed to execute {provider} research for {company.company_name}. Check API configuration and try again.'
                
                with db_service.engine.connect() as conn:
                    with conn.begin():
                        conn.execute(text("""
                            UPDATE companies 
                            SET llm_research_step_status = :status,
                                llm_research_step_1_basic = :error_msg,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = :company_id
                        """), {
                            'status': 'step_1_error',
                            'error_msg': f'ERROR: {error_msg}',
                            'company_id': company.id
                        })
                
                return {
                    'success': False,
                    'error': error_msg
                }
            
            # Store the research results - ONLY if they are actual results, NOT markers
            if isinstance(research_results, str) and research_results.startswith('__') and research_results.endswith('__'):
                logger.error(f"🚨 MARKER LEAK: Attempted to save marker '{research_results}' as research results for {company.company_name}")
                return {
                    'success': False,
                    'error': f'Internal marker {research_results} should not be saved as research results'
                }
            
            from deepresearch.database_service import DatabaseService
            db_service = DatabaseService()
            
            # Store step 1 results
            from sqlalchemy import text
            with db_service.engine.connect() as conn:
                with conn.begin():
                    conn.execute(text("""
                        UPDATE companies 
                        SET llm_research_step_1_basic = :results,
                            llm_research_step_status = 'step_1_completed',
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :company_id
                    """), {
                        'results': research_results,
                        'company_id': company.id
                    })
            
            logger.info(f"Step 1 completed for {company.company_name} using {provider}")
            
            return {
                'success': True,
                'message': f'Step 1 (LLM Basic Research) completed for {company.company_name} using {provider}. Research executed automatically.',
                'step': 'step_1',
                'status': 'completed',
                'results_length': len(research_results),
                'word_count': len(research_results.split()),
                'provider': provider,
                'next_action': 'Step 1 completed. Step 2 (Strategic Analysis) will begin automatically.'
            }
            
        except Exception as e:
            logger.error(f"Error in Step 1 for {company.company_name}: {e}")
            return {
                'success': False,
                'error': f'Step 1 failed: {str(e)}'
            }

    def _execute_step_2(self, company, provider: str) -> Dict[str, Any]:
        """Execute Step 2: LLM Strategic Analysis."""
        logger.info(f"Executing Step 2 (LLM Strategic Analysis) for {company.company_name}")
        
        try:
            # Get Step 1 results
            basic_research = getattr(company, 'llm_research_step_1_basic', '')
            if not basic_research:
                return {
                    'success': False,
                    'error': 'Step 1 basic research not found. Complete Step 1 first.'
                }
            
            # Check if Step 1 contains actual research results (not just prompt)
            if 'You are an expert B2B go-to-market strategist' in basic_research:
                return {
                    'success': False,
                    'error': 'Step 1 contains prompt, not research results. Submit research results first.'
                }
            
            # Create strategic analysis prompt based on Step 1 results
            strategic_prompt = self._create_strategic_analysis_prompt(company.company_name, basic_research)
            
            # Execute strategic analysis using structured JSON outputs
            from deepresearch.ai_research_service import AIResearchService
            ai_service = AIResearchService()
            
            # Use structured JSON generation for strategic analysis (NEW METHOD)
            logger.info(f"Using structured JSON generation for step 2 strategic analysis for {company.company_name}")
            # ENFORCED: Always use OpenAI for Step 2 generation via AIResearchService (already OpenAI-backed)
            strategic_result_dict = ai_service.generate_strategic_recommendations(company.company_name, basic_research)
            
            if strategic_result_dict and isinstance(strategic_result_dict, dict) and 'json_string' in strategic_result_dict:
                strategic_results = strategic_result_dict['json_string']
                logger.info(f"✅ Successfully generated structured JSON for {company.company_name}: {len(strategic_results)} characters")
                
                # 🔍 VALIDATION: Import and validate JSON structure before proceeding
                from deepresearch.llm_step_2_handler import validate_step_2_json_output
                validation_result = validate_step_2_json_output(strategic_results, company.company_name)
                
                if not validation_result['is_valid']:
                    logger.error(f"❌ Step 2 JSON validation failed for {company.company_name}")
                    logger.error(f"❌ Validation errors: {validation_result['errors']}")
                    logger.error(f"❌ WORKFLOW STOPPED - will not proceed to Step 3 due to invalid JSON structure")
                    strategic_results = None  # Stop workflow
                else:
                    logger.info(f"✅ Step 2 JSON validation passed for {company.company_name}")
                    if validation_result['warnings']:
                        logger.warning(f"⚠️ Step 2 validation warnings for {company.company_name}: {validation_result['warnings']}")
            else:
                strategic_results = None
                logger.error(f"❌ Failed to generate structured JSON for {company.company_name}")
            
            if not strategic_results:
                error_msg = f'Step 2 strategic analysis failed for {company.company_name}. '
                if strategic_result_dict is None:
                    error_msg += f'No JSON generated by {provider} - provider may not be available or configured.'
                else:
                    error_msg += 'JSON structure validation failed - output does not match required schema.'
                
                return {
                    'success': False,
                    'error': error_msg,
                    'step': 'step_2_strategic_analysis',
                    'validation_failed': strategic_result_dict is not None  # True if validation failed, False if generation failed
                }
            
            # Store strategic analysis results
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
                        'results': strategic_results,
                        'company_id': company.id
                    })
            
            logger.info(f"Step 2 strategic analysis completed for {company.company_name} using {provider}")
            
            return {
                'success': True,
                'message': f'Step 2 (Strategic Analysis) completed for {company.company_name} using {provider}. Analysis executed automatically.',
                'step': 'step_2',
                'status': 'completed',
                'results_length': len(strategic_results),
                'word_count': len(strategic_results.split()),
                'provider': provider,
                'next_action': 'Step 2 completed. Step 3 (Report Generation) will begin automatically.'
            }
            
        except Exception as e:
            logger.error(f"Error in Step 2 for {company.company_name}: {e}")
            return {
                'success': False,
                'error': f'Step 2 failed: {str(e)}'
            }

    def _execute_step_3(self, company, provider: str) -> Dict[str, Any]:
        """Execute Step 3: LLM Report Generation."""
        logger.info(f"Executing Step 3 (LLM Report Generation) for {company.company_name}")
        
        try:
            # Get Step 1 and Step 2 results
            basic_research = getattr(company, 'llm_research_step_1_basic', '')
            strategic_analysis = getattr(company, 'llm_research_step_2_strategic', '')
            
            if not basic_research or not strategic_analysis:
                return {
                    'success': False,
                    'error': 'Steps 1 and 2 must be completed first.'
                }
            
            # Check if steps contain actual results (not prompts)
            if ('You are an expert B2B go-to-market strategist' in basic_research or 
                'You are an expert B2B go-to-market strategist' in strategic_analysis):
                return {
                    'success': False,
                    'error': 'Previous steps contain prompts, not results. Submit actual research results first.'
                }
            
            # Create report generation prompt
            report_prompt = self._create_report_generation_prompt(
                company.company_name, 
                basic_research, 
                strategic_analysis
            )
            
            # Execute report generation using regular completion (no web search needed)
            # ENFORCED: Always use OpenAI for Step 3 content generation
            from deepresearch.llm_deep_research_service import LLMDeepResearchService
            llm_service = LLMDeepResearchService()
            
            # Use regular completion for report generation (no deep research needed) with OpenAI provider enforced
            report_results = llm_service.execute_regular_completion(report_prompt, company.company_name, 'openai')
            
            if not report_results:
                return {
                    'success': False,
                    'error': f'Failed to execute {provider} report generation for {company.company_name}. Provider may not be available or configured.'
                }
            
            # Store report generation results
            from deepresearch.database_service import DatabaseService
            from sqlalchemy import text
            db_service = DatabaseService()
            
            with db_service.engine.connect() as conn:
                with conn.begin():
                    conn.execute(text("""
                        UPDATE companies 
                        SET llm_research_step_3_report = :results,
                            llm_research_step_status = 'step_3_completed',
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :company_id
                    """), {
                        'results': report_results,
                        'company_id': company.id
                    })
            
            # Generate final reports using the report generator (label as OpenAI)
            from deepresearch.llm_report_generator import LLMReportGenerator
            report_generator = LLMReportGenerator()
            report_result = report_generator.finalize_step_3_report(company.id, report_results, 'openai')
            
            if not report_result['success']:
                logger.error(f"Failed to generate final reports for company {company.id}: {report_result.get('error', 'Unknown error')}")
            
            # Mark as completed
            with db_service.engine.connect() as conn:
                with conn.begin():
                    conn.execute(text("""
                        UPDATE companies 
                        SET llm_research_step_status = 'completed',
                            llm_research_completed_at = CURRENT_TIMESTAMP
                        WHERE id = :company_id
                    """), {
                        'company_id': company.id
                    })
            
            logger.info(f"Step 3 report generation completed for {company.company_name} using {provider}")
            
            return {
                'success': True,
                'message': f'Step 3 (Report Generation) completed for {company.company_name} using {provider}. All LLM research steps completed successfully.',
                'step': 'step_3',
                'status': 'completed',
                'results_length': len(report_results),
                'word_count': len(report_results.split()),
                'provider': provider,
                'next_action': 'All LLM research steps completed. View final report.',
                'report_generated': report_result['success'] if report_result else False
            }
            
        except Exception as e:
            logger.error(f"Error in Step 3 for {company.company_name}: {e}")
            return {
                'success': False,
                'error': f'Step 3 failed: {str(e)}'
            }

    def _create_strategic_analysis_prompt(self, company_name: str, basic_research: str) -> str:
        """Create strategic analysis prompt based on basic research results."""
        
        prompt = f"""You are a McKinsey senior partner analyzing {company_name} to develop strategic imperatives and AI agent recommendations.

Based on the comprehensive research below, create a strategic analysis following this structure:

## Strategic Analysis for {company_name}

### Executive Summary
Provide a 3-4 sentence executive summary of {company_name}'s current situation, key challenges, and strategic positioning.

### Key Strategic Imperatives
Identify the top 3 most critical strategic imperatives for {company_name} based on the research:

**Imperative 1: [Clear Title]**
- Current Challenge: [Description of the business challenge]
- Strategic Opportunity: [How addressing this creates competitive advantage]
- Business Impact: [Quantified potential impact]
- Urgency Factors: [Why this needs immediate attention]

**Imperative 2: [Clear Title]**
- Current Challenge: [Description of the business challenge]
- Strategic Opportunity: [How addressing this creates competitive advantage]
- Business Impact: [Quantified potential impact]
- Urgency Factors: [Why this needs immediate attention]

**Imperative 3: [Clear Title]**
- Current Challenge: [Description of the business challenge]
- Strategic Opportunity: [How addressing this creates competitive advantage]
- Business Impact: [Quantified potential impact]
- Urgency Factors: [Why this needs immediate attention]

### AI Agent Solution Framework
For each strategic imperative, provide specific AI agent recommendations:

**For Imperative 1:**
- AI Agent Type: [Specific type of AI agent needed]
- Core Functionality: [What the agent would do day-to-day]
- Data Integration: [What data sources it would use]
- Expected ROI: [Quantified business impact]
- Implementation Timeline: [Realistic timeline]

**For Imperative 2:**
- AI Agent Type: [Specific type of AI agent needed]
- Core Functionality: [What the agent would do day-to-day]
- Data Integration: [What data sources it would use]
- Expected ROI: [Quantified business impact]
- Implementation Timeline: [Realistic timeline]

**For Imperative 3:**
- AI Agent Type: [Specific type of AI agent needed]
- Core Functionality: [What the agent would do day-to-day]
- Data Integration: [What data sources it would use]
- Expected ROI: [Quantified business impact]
- Implementation Timeline: [Realistic timeline]

### Cold Outreach Strategy
Provide specific messaging angles for each imperative:

**Imperative 1 Messaging:**
- Email Subject Line: [Compelling subject line ≤15 words]
- Opening Hook: [First sentence that creates curiosity]
- Value Proposition: [One sentence benefit statement]

**Imperative 2 Messaging:**
- Email Subject Line: [Compelling subject line ≤15 words]
- Opening Hook: [First sentence that creates curiosity]
- Value Proposition: [One sentence benefit statement]

**Imperative 3 Messaging:**
- Email Subject Line: [Compelling subject line ≤15 words]
- Opening Hook: [First sentence that creates curiosity]
- Value Proposition: [One sentence benefit statement]

### Implementation Roadmap
Provide a 6-month roadmap for addressing the strategic imperatives with AI agents:

**Month 1-2: [Phase Name]**
- Key Activities: [Specific actions]
- Deliverables: [Expected outcomes]
- Success Metrics: [How to measure progress]

**Month 3-4: [Phase Name]**
- Key Activities: [Specific actions]
- Deliverables: [Expected outcomes]
- Success Metrics: [How to measure progress]

**Month 5-6: [Phase Name]**
- Key Activities: [Specific actions]
- Deliverables: [Expected outcomes]
- Success Metrics: [How to measure progress]

## Research Foundation

{basic_research}

Based on this research, provide the strategic analysis following the exact structure above. Focus on actionable insights and specific AI agent solutions that address real business challenges identified in the research."""

        return prompt

    def _create_report_generation_prompt(self, company_name: str, basic_research: str, strategic_analysis: str) -> str:
        """Create report generation prompt to produce final formatted reports."""
        
        prompt = f"""You are an expert business strategist creating a comprehensive research report for {company_name}.

Create a professional, executive-ready report that combines the basic research and strategic analysis into a cohesive document.

## Report Requirements

Create a complete markdown report with the following structure:

### 1. Executive Summary
- Company overview (2-3 sentences)
- Key findings summary
- Strategic recommendations overview
- Expected business impact

### 2. Company Intelligence
- Business model and market position
- Key differentiators
- Financial indicators and growth signals
- Geographic presence and operations

### 3. Market Context & Competitive Landscape
- Industry trends affecting the company
- Competitive positioning
- Market opportunities and threats
- Technology adoption patterns

### 4. Strategic Analysis
- Top 3 strategic imperatives with detailed analysis
- Business impact assessment
- Urgency and priority ranking
- Implementation considerations

### 5. AI Agent Recommendations
- Specific AI solutions for each strategic imperative
- Technical implementation details
- Expected ROI and business benefits
- Timeline and resource requirements

### 6. Go-to-Market Strategy
- Messaging framework for each strategic imperative
- Target stakeholders and decision makers
- Outreach tactics and timing
- Success metrics and KPIs

### 7. Implementation Roadmap
- 6-month phased approach
- Key milestones and deliverables
- Resource requirements
- Risk mitigation strategies

## Formatting Requirements

- Use proper markdown formatting with headers, bullet points, and tables
- Include specific metrics and quantified benefits where possible
- Cite specific evidence from the research
- Keep executive summary to 150-200 words
- Total report length: 1000-1500 words
- Professional tone suitable for C-level executives

## Source Materials

### Basic Research:
{basic_research}

### Strategic Analysis:
{strategic_analysis}

Create the comprehensive markdown report now, ensuring it flows logically and provides actionable insights for {company_name}'s leadership team."""

        return prompt

    def submit_step_results(self, company_id: int, step: str, results: str, provider: str = 'claude') -> Dict[str, Any]:
        """
        Submit results for a specific step and advance to next step if applicable.
        NOTE: This method is now primarily for backward compatibility since steps execute automatically.
        
        Args:
            company_id: Company ID
            step: Step name (step_1, step_2, step_3)
            results: LLM-generated results
            provider: LLM provider used
            
        Returns:
            Dictionary with success status and next step information
        """
        logger.info(f"Submitting step {step} results for company {company_id} (backward compatibility mode)")
        
        try:
            from app.models.company import Company
            from deepresearch.database_service import DatabaseService
            from deepresearch.llm_deep_research_service import LLMDeepResearchService
            from sqlalchemy import text
            
            # Get company
            company = Company.get_by_id(company_id)
            if not company:
                return {
                    'success': False,
                    'error': f'Company with ID {company_id} not found'
                }
            
            # Validate results quality
            llm_service = LLMDeepResearchService()
            validation = llm_service.validate_research_quality(results)
            
            if not validation['is_valid']:
                return {
                    'success': False,
                    'error': 'Results quality validation failed',
                    'validation_issues': validation['issues'],
                    'quality_score': validation['quality_score']
                }
            
            # Store results in appropriate step field
            db_service = DatabaseService()
            
            if step == 'step_1':
                field_name = 'llm_research_step_1_basic'
                next_step = 'step_2'
                status = 'step_1_completed'
            elif step == 'step_2':
                field_name = 'llm_research_step_2_strategic'
                next_step = 'step_3'
                status = 'step_2_completed'
            elif step == 'step_3':
                field_name = 'llm_research_step_3_report'
                next_step = 'completed'
                status = 'completed'
                
                # For step 3, store results and generate final reports
                with db_service.engine.connect() as conn:
                    with conn.begin():
                        conn.execute(text(f"""
                            UPDATE companies 
                            SET {field_name} = :results,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = :company_id
                        """), {
                            'results': results,
                            'company_id': company_id
                        })
                
                # Generate final reports using the report generator
                from deepresearch.llm_report_generator import LLMReportGenerator
                report_generator = LLMReportGenerator()
                report_result = report_generator.finalize_step_3_report(company_id, results, provider)
                
                if not report_result['success']:
                    logger.error(f"Failed to generate final reports for company {company_id}: {report_result.get('error', 'Unknown error')}")
                
                # Mark as completed
                with db_service.engine.connect() as conn:
                    with conn.begin():
                        conn.execute(text("""
                            UPDATE companies 
                            SET llm_research_step_status = :status,
                                llm_research_completed_at = CURRENT_TIMESTAMP
                            WHERE id = :company_id
                        """), {
                            'status': status,
                            'company_id': company_id
                        })
            else:
                return {
                    'success': False,
                    'error': f'Invalid step: {step}'
                }
            
            # Store results for steps 1 and 2
            if step in ['step_1', 'step_2']:
                with db_service.engine.connect() as conn:
                    with conn.begin():
                        conn.execute(text(f"""
                            UPDATE companies 
                            SET {field_name} = :results,
                                llm_research_step_status = :status,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = :company_id
                        """), {
                            'results': results,
                            'status': status,
                            'company_id': company_id
                        })
            
            logger.info(f"Stored step {step} results for {company.company_name}")
            
            # If not completed, automatically execute next step
            next_step_info = {}
            if next_step != 'completed':
                # Auto-execute next step (new automatic approach)
                next_result = self.start_llm_step_research(company_id, provider, force_refresh=False)
                next_step_info = {
                    'next_step': next_step,
                    'next_step_result': next_result
                }
            else:
                next_step_info = {
                    'next_step': 'completed',
                    'message': 'All steps completed successfully'
                }
            
            return {
                'success': True,
                'company_id': company_id,
                'company_name': company.company_name,
                'step_completed': step,
                'quality_score': validation['quality_score'],
                'word_count': len(results.split()),
                'provider': provider,
                **next_step_info
            }
            
        except Exception as e:
            logger.error(f"Error submitting step {step} results for company {company_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_step_progress(self, company_id: int) -> Dict[str, Any]:
        """Get progress information for LLM step-by-step research."""
        try:
            from app.models.company import Company
            
            company = Company.get_by_id(company_id)
            if not company:
                return {
                    'success': False,
                    'error': f'Company with ID {company_id} not found'
                }
            
            # Check step completion status
            has_step_1 = hasattr(company, 'llm_research_step_1_basic') and company.llm_research_step_1_basic
            has_step_2 = hasattr(company, 'llm_research_step_2_strategic') and company.llm_research_step_2_strategic
            has_step_3 = hasattr(company, 'llm_research_step_3_report') and company.llm_research_step_3_report
            
            # Check for errors in steps
            step_1_has_error = has_step_1 and company.llm_research_step_1_basic.startswith('ERROR:')
            step_2_has_error = has_step_2 and company.llm_research_step_2_strategic.startswith('ERROR:')
            step_3_has_error = has_step_3 and company.llm_research_step_3_report.startswith('ERROR:')
            
            # Determine if steps contain results or prompts
            step_1_is_result = has_step_1 and not step_1_has_error and 'You are an expert B2B go-to-market strategist' not in company.llm_research_step_1_basic
            step_2_is_result = has_step_2 and not step_2_has_error and 'You are an expert B2B go-to-market strategist' not in company.llm_research_step_2_strategic
            step_3_is_result = has_step_3 and not step_3_has_error and 'You are an expert B2B go-to-market strategist' not in company.llm_research_step_3_report
            
            steps_completed = sum([bool(step_1_is_result), bool(step_2_is_result), bool(step_3_is_result)])
            total_steps = 3
            progress_percentage = (steps_completed / total_steps) * 100
            
            # Current step determination
            if step_1_has_error:
                current_step = 'step_1'
                current_status = 'error'
            elif step_2_has_error:
                current_step = 'step_2'
                current_status = 'error'
            elif step_3_has_error:
                current_step = 'step_3'
                current_status = 'error'
            elif not step_1_is_result:
                current_step = 'step_1'
                current_status = 'prompt_ready' if has_step_1 else 'not_started'
            elif not step_2_is_result:
                current_step = 'step_2'
                current_status = 'prompt_ready' if has_step_2 else 'needs_execution'
            elif not step_3_is_result:
                current_step = 'step_3'
                current_status = 'prompt_ready' if has_step_3 else 'needs_execution'
            else:
                current_step = 'completed'
                current_status = 'completed'
            
            step_details = [
                {
                    'step': 1,
                    'name': 'LLM Basic Research',
                    'status': 'error' if step_1_has_error else ('completed' if step_1_is_result else ('prompt_ready' if has_step_1 else 'pending')),
                    'has_prompt': has_step_1,
                    'has_results': step_1_is_result,
                    'has_error': step_1_has_error,
                    'error_message': company.llm_research_step_1_basic.replace('ERROR: ', '') if step_1_has_error else None,
                    'description': 'Comprehensive company intelligence gathering using LLM deep research'
                },
                {
                    'step': 2,
                    'name': 'LLM Strategic Analysis',
                    'status': 'error' if step_2_has_error else ('completed' if step_2_is_result else ('prompt_ready' if has_step_2 else 'pending')),
                    'has_prompt': has_step_2,
                    'has_results': step_2_is_result,
                    'has_error': step_2_has_error,
                    'error_message': company.llm_research_step_2_strategic.replace('ERROR: ', '') if step_2_has_error else None,
                    'description': 'Strategic imperatives and AI agent recommendations'
                },
                {
                    'step': 3,
                    'name': 'LLM Report Generation',
                    'status': 'error' if step_3_has_error else ('completed' if step_3_is_result else ('prompt_ready' if has_step_3 else 'pending')),
                    'has_prompt': has_step_3,
                    'has_results': step_3_is_result,
                    'has_error': step_3_has_error,
                    'error_message': company.llm_research_step_3_report.replace('ERROR: ', '') if step_3_has_error else None,
                    'description': 'Final comprehensive markdown and HTML reports'
                }
            ]
            
            return {
                'success': True,
                'company_id': company_id,
                'company_name': company.company_name,
                'progress_percentage': progress_percentage,
                'steps_completed': steps_completed,
                'total_steps': total_steps,
                'current_step': current_step,
                'current_status': current_status,
                'is_complete': current_step == 'completed',
                'step_details': step_details,
                'llm_research_step_status': getattr(company, 'llm_research_step_status', 'not_started'),
                'llm_research_provider': getattr(company, 'llm_research_provider', ''),
                'llm_research_started_at': getattr(company, 'llm_research_started_at', None),
                'llm_research_completed_at': getattr(company, 'llm_research_completed_at', None)
            }
            
        except Exception as e:
            logger.error(f"Error getting step progress for company {company_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _check_step_research_status(self, company_id: int) -> Dict[str, Any]:
        """Check if step research is already in progress to prevent duplicates."""
        try:
            from deepresearch.database_service import DatabaseService
            from sqlalchemy import text
            
            db_service = DatabaseService()
            with db_service.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT 
                        llm_research_step_status,
                        llm_research_started_at,
                        llm_research_provider,
                        llm_research_completed_at
                    FROM companies 
                    WHERE id = :company_id
                """), {'company_id': company_id})
                
                row = result.fetchone()
                if not row:
                    return {'already_in_progress': False, 'status': 'not_found'}
                
                status, started_at, provider, completed_at = row
                
                # Check if research is currently in progress
                in_progress_statuses = [
                    'api_call_initiated', 'background_job_running', 'step_1', 'step_2', 'step_3', 
                    'in_progress', 'in_progress_step_1', 'in_progress_step_2', 'in_progress_step_3'
                ]
                
                if status in in_progress_statuses:
                    # Allow if it's been more than 30 minutes since started (might be stuck)
                    import datetime
                    if started_at:
                        time_diff = datetime.datetime.now() - started_at
                        if time_diff.total_seconds() > 1800:  # 30 minutes timeout for steps
                            logger.warning(f"Step research for company {company_id} appears stuck (started {time_diff} ago), allowing retry")
                            return {'already_in_progress': False, 'status': 'timeout_retry_allowed'}
                    
                    return {
                        'already_in_progress': True,
                        'status': status,
                        'started_at': started_at,
                        'provider': provider,
                        'completed_at': completed_at
                    }
                
                return {'already_in_progress': False, 'status': status or 'pending'}
                
        except Exception as e:
            logger.error(f"Error checking step research status for company {company_id}: {e}")
            # On error, allow the request (fail open)
            return {'already_in_progress': False, 'status': 'check_failed'}
    
    def _mark_step_research_failed(self, company_id: int, error_message: str):
        """Mark step research as failed in database."""
        try:
            from deepresearch.database_service import DatabaseService
            from sqlalchemy import text
            
            db_service = DatabaseService()
            with db_service.engine.connect() as conn:
                with conn.begin():
                    conn.execute(text("""
                        UPDATE companies 
                        SET llm_research_step_status = 'failed',
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :company_id
                    """), {'company_id': company_id})
            
            logger.critical(f"🚨 DB STEP FAILED: Step research marked as failed in database for company {company_id}: {error_message}")
            
        except Exception as e:
            logger.error(f"Failed to mark step research as failed in DB for company {company_id}: {e}")