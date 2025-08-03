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
            provider: LLM provider (claude, openai, etc.)
            force_refresh: Whether to restart from step 1 even if data exists
            
        Returns:
            Dictionary with success status and step information
        """
        logger.info(f"Starting LLM step research for company {company_id}, provider={provider}")
        
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
            logger.error(f"Error in LLM step research for company {company_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _determine_current_step(self, company, force_refresh: bool) -> str:
        """Determine which step to execute based on current state."""
        if force_refresh:
            return 'step_1'
        
        # Check what steps are completed
        has_step_1 = hasattr(company, 'llm_research_step_1_basic') and company.llm_research_step_1_basic
        has_step_2 = hasattr(company, 'llm_research_step_2_strategic') and company.llm_research_step_2_strategic
        has_step_3 = hasattr(company, 'llm_research_step_3_report') and company.llm_research_step_3_report
        
        if not has_step_1:
            return 'step_1'
        elif not has_step_2:
            return 'step_2'
        elif not has_step_3:
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
            
            # Execute automatic research using the specified provider
            research_results = llm_service.research_company_deep(
                company.company_name,
                company.website_url or "",
                provider=provider
            )
            
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
            
            # Store the research results
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
            
            # Execute strategic analysis using the LLM provider
            from deepresearch.llm_deep_research_service import LLMDeepResearchService
            llm_service = LLMDeepResearchService()
            
            # Execute the strategic analysis
            if provider.lower() == "claude" and llm_service.anthropic_client:
                strategic_results = llm_service._execute_claude_research(strategic_prompt, company.company_name)
            elif provider.lower() == "openai" and llm_service.openai_client:
                strategic_results = llm_service._execute_openai_research(strategic_prompt, company.company_name)
            else:
                return {
                    'success': False,
                    'error': f'Provider {provider} not available or not configured for strategic analysis.'
                }
            
            if not strategic_results:
                return {
                    'success': False,
                    'error': f'Failed to execute {provider} strategic analysis for {company.company_name}.'
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
            
            # Execute report generation using the LLM provider
            from deepresearch.llm_deep_research_service import LLMDeepResearchService
            llm_service = LLMDeepResearchService()
            
            # Execute the report generation
            if provider.lower() == "claude" and llm_service.anthropic_client:
                report_results = llm_service._execute_claude_research(report_prompt, company.company_name)
            elif provider.lower() == "openai" and llm_service.openai_client:
                report_results = llm_service._execute_openai_research(report_prompt, company.company_name)
            else:
                return {
                    'success': False,
                    'error': f'Provider {provider} not available or not configured for report generation.'
                }
            
            if not report_results:
                return {
                    'success': False,
                    'error': f'Failed to execute {provider} report generation for {company.company_name}.'
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
            
            # Generate final reports using the report generator
            from deepresearch.llm_report_generator import LLMReportGenerator
            report_generator = LLMReportGenerator()
            report_result = report_generator.finalize_step_3_report(company.id, report_results, provider)
            
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