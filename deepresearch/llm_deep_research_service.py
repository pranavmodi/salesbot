#!/usr/bin/env python3
"""
LLM Deep Research Service

Handles deep research using Claude's native deep research functionality.
This provides an alternative research method that leverages Claude's enhanced
research capabilities while maintaining compatibility with existing system.
"""

import os
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import anthropic

logger = logging.getLogger(__name__)

class LLMDeepResearchService:
    """Handles deep research using Claude's native deep research capabilities."""
    
    def __init__(self):
        load_dotenv()
        self.anthropic_client = None
        self.openai_client = None
        
        # CRITICAL COST PROTECTION
        self.max_tokens_per_request = 8000  # Hard limit
        self.max_requests_per_hour = 10     # Rate limiting
        self.max_daily_spend = 5.00         # Daily spend limit in USD
        self.request_timeout = 120          # 2 minute timeout
        
        # BULLETPROOF CONCURRENCY PROTECTION
        self._active_requests = set()       # Track active company IDs
        self._request_timestamps = []       # Track request timing
        self._daily_cost_tracker = 0.0     # Track daily spending
        
        # Initialize Anthropic client if API key is available
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_api_key:
            self.anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
            logger.info("LLMDeepResearchService initialized with Anthropic client")
        else:
            logger.warning("ANTHROPIC_API_KEY not found - Claude research will not be available")
        
        # Initialize OpenAI client if API key is available
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key:
            from openai import OpenAI
            self.openai_client = OpenAI(
                api_key=openai_api_key,
                timeout=600.0  # 10 minute timeout - longer since we have streaming progress updates
            )
            logger.info("LLMDeepResearchService initialized with OpenAI client (600s timeout)")
        else:
            logger.warning("OPENAI_API_KEY not found - OpenAI research will not be available")

    def research_company_deep(self, company_name: str, company_domain: str = "", provider: str = "claude", company_id: int = None) -> Optional[str]:
        """
        Execute comprehensive company analysis using LLM deep research capabilities.
        
        Args:
            company_name: Name of the company to research
            company_domain: Company domain/website
            provider: LLM provider to use ('claude' or 'openai')
            company_id: Company ID for safety tracking
            
        Returns:
            Comprehensive research analysis string or None if failed
        """
        logger.info(f"Starting LLM deep research for company: {company_name} using {provider}")
        
        # BULLETPROOF SAFETY CHECKS
        if company_id is not None:
            try:
                self._check_request_limits(company_id)
                self._register_request_start(company_id)
            except Exception as safety_error:
                logger.error(f"SAFETY CHECK FAILED: {safety_error}")
                raise safety_error
        
        # Construct website URL from domain
        website_url = ""
        if company_domain:
            if not company_domain.startswith(('http://', 'https://')):
                website_url = f"https://{company_domain}"
            else:
                website_url = company_domain

        # Create the comprehensive research prompt
        research_prompt = self._create_deep_research_prompt(company_name, website_url, company_domain)
        
        try:
            result = None
            if provider.lower() == "claude" and self.anthropic_client:
                result = self._execute_claude_research(research_prompt, company_name)
            elif provider.lower() == "openai" and self.openai_client:
                result = self._execute_openai_research(research_prompt, company_name, company_id)
            else:
                logger.error(f"Provider {provider} not available or not configured")
                result = None
            
            # REGISTER COMPLETION
            if company_id is not None:
                estimated_cost = 0.5 if provider.lower() == "openai" else 0.1  # Higher estimate for OpenAI
                self._register_request_end(company_id, estimated_cost)
            
            return result
                
        except Exception as e:
            # CLEANUP ON ERROR
            if company_id is not None:
                self._register_request_end(company_id, 0.0)  # No cost if failed
            
            error_details = str(e)
            if "429" in error_details:
                logger.error(f"Rate limit exceeded for {provider} research on {company_name}: {e}")
            elif "insufficient_quota" in error_details:
                logger.error(f"API quota exceeded for {provider} research on {company_name}: {e}")
            elif "401" in error_details:
                logger.error(f"Authentication failed for {provider} research on {company_name}: {e}")
            else:
                logger.error(f"Error executing {provider} deep research for {company_name}: {e}")
            return None

    def _execute_claude_research(self, research_prompt: str, company_name: str) -> Optional[str]:
        """Execute research using Claude with web search capabilities."""
        logger.info(f"Executing Claude web search research for {company_name}")
        
        try:
            # Use Claude's message API with web search tool
            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                temperature=0.3,
                tools=[
                    {
                        "type": "web_search",
                        "web_search": {}
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": f"""You are an expert B2B research analyst with access to web search. Conduct comprehensive research on {company_name} using web search to gather current, accurate information.

{research_prompt}

IMPORTANT: Use web search extensively to find:
- Current company information from their website
- Recent news, press releases, and announcements
- Financial data, funding, and growth metrics
- Technology stack and product information
- Customer reviews and market position
- Competitor analysis and industry trends
- Job postings and hiring patterns

Provide detailed citations and sources for all information found."""
                    }
                ]
            )
            
            research_results = response.content[0].text
            logger.info(f"Claude web search research completed for {company_name}: {len(research_results)} characters")
            return research_results
            
        except Exception as e:
            logger.error(f"Claude web search API error for {company_name}: {e}")
            logger.warning(f"Falling back to standard Claude API for {company_name}")
            
            # Fallback to standard API if web search fails
            try:
                response = self.anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=4000,
                    temperature=0.3,
                    messages=[
                        {
                            "role": "user",
                            "content": research_prompt
                        }
                    ]
                )
                
                research_results = response.content[0].text
                logger.info(f"Claude fallback research completed for {company_name}: {len(research_results)} characters")
                return research_results
                
            except Exception as fallback_error:
                logger.error(f"Claude fallback API error for {company_name}: {fallback_error}")
                return None

    def _execute_openai_research(self, research_prompt: str, company_name: str, company_id: int = None) -> Optional[str]:
        """Execute research using OpenAI o4-mini Deep Research API in background mode."""
        logger.info(f"Starting OpenAI o4-mini deep research for {company_name} in background mode")
        
        try:
            # Check if we have an existing background job for this company
            existing_response_id = self._get_stored_response_id(company_id)
            if existing_response_id:
                logger.info(f"Found existing background job {existing_response_id} for {company_name}, checking status")
                return self._check_background_job_status(existing_response_id, company_name, company_id)
            
            # Start new background research job
            try:
                logger.info(f"Starting new OpenAI Deep Research API background job for {company_name}")
                
                # Create webhook URL for our app
                webhook_url = self._get_webhook_url()
                
                # Start background job (no streaming, returns immediately with response_id)
                response = self.openai_client.responses.create(
                    model="o4-mini-deep-research-2025-06-26",
                    input=[
                        {
                            "role": "user",
                            "content": f"""Conduct comprehensive deep research on {company_name} for B2B sales intelligence purposes.

{research_prompt}

Research Requirements:
- Use web search to find current, accurate company information
- Gather recent news, funding, and growth data
- Analyze technology stack and product offerings
- Research competitor landscape and market position
- Find key decision makers and contact information
- Identify pain points and business challenges
- Provide detailed citations for all information

Please conduct thorough research across multiple reliable sources and provide a comprehensive analysis with proper citations."""
                        }
                    ],
                    reasoning={"summary": "auto"},  
                    tools=[{"type": "web_search_preview"}],
                    background=True,  # CRITICAL: Run in background mode
                    webhook=webhook_url if webhook_url else None  # Optional webhook
                )
                
                response_id = response.id
                logger.info(f"OpenAI Deep Research background job started: {response_id} for {company_name}")
                
                # Store response_id in database for recovery after restarts
                self._store_response_id(company_id, response_id)
                
                # Update status to show background job is running
                self._update_research_status(company_name, f"Background research job started (ID: {response_id})", company_id)
                
                # Start polling for status updates
                return self._poll_background_job(response_id, company_name, company_id)
                
            except Exception as deep_error:
                error_msg = str(deep_error)
                if "503" in error_msg or "Service Unavailable" in error_msg:
                    logger.error(f"OpenAI Deep Research API is currently unavailable (503 Service Unavailable) for {company_name}: {deep_error}")
                    logger.info(f"Falling back to standard GPT-4 for {company_name}")
                elif "429" in error_msg or "rate_limit" in error_msg.lower():
                    logger.error(f"Rate limit exceeded for OpenAI Deep Research API for {company_name}: {deep_error}")
                    logger.info(f"Falling back to standard GPT-4 for {company_name}")
                elif "insufficient_quota" in error_msg.lower():
                    logger.error(f"API quota exceeded for OpenAI Deep Research API for {company_name}: {deep_error}")
                    logger.info(f"Falling back to standard GPT-4 for {company_name}")
                else:
                    logger.warning(f"OpenAI o4-mini Deep Research API failed for {company_name}: {deep_error}")
                    logger.info(f"Falling back to standard GPT-4 for {company_name}")
                
                # Fallback to standard GPT-4 API
                response = self.openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert business research analyst with access to comprehensive company intelligence."
                        },
                        {
                            "role": "user",
                            "content": research_prompt
                        }
                    ],
                    max_tokens=4000,
                    temperature=0.3
                )
                
                research_results = response.choices[0].message.content
                logger.info(f"OpenAI fallback research completed for {company_name}: {len(research_results)} characters")
                return research_results
            
        except Exception as e:
            logger.error(f"OpenAI API error for {company_name}: {e}")
            return None

    def get_research_prompt_only(self, company_name: str, company_domain: str = "") -> str:
        """Get the research prompt without executing it (for manual research)."""
        website_url = ""
        if company_domain:
            if not company_domain.startswith(('http://', 'https://')):
                website_url = f"https://{company_domain}"
            else:
                website_url = company_domain

        return self._create_deep_research_prompt(company_name, website_url, company_domain)

    def _create_deep_research_prompt(self, company_name: str, website_url: str, company_domain: str) -> str:
        """Create a comprehensive research prompt for Claude's deep research."""
        
        prompt = f"""You are an expert B2B go-to-market strategist conducting comprehensive company research for AI sales automation. Perform deep research analysis using all available tools and capabilities.

COMPANY TO RESEARCH: {company_name}
WEBSITE: {website_url if website_url else 'Not available'}
DOMAIN: {company_domain if company_domain else 'Not available'}

## Research Framework

Conduct a comprehensive analysis following this structured approach:

### 1. Company Intelligence Snapshot
Provide a concise 3-sentence overview covering:
- Industry vertical and core business model
- Company size (revenue estimates, employee count, growth stage)
- Precise headquarters location (city, state/country)
- Key differentiators in their market

### 2. Business Context Discovery
Research and cite recent information (≤ 12 months) from multiple sources:

**Official Sources:**
- Homepage, product pages, pricing information
- Company blog posts and thought leadership content
- Annual reports, investor presentations, SEC filings
- Press releases and company announcements

**Market Intelligence:**
- Job postings on careers page and LinkedIn (hiring patterns, roles, locations)
- News coverage, industry reports, podcast appearances
- Customer reviews (G2, Capterra, Trustpilot, Glassdoor)
- Social media signals (LinkedIn posts, executive commentary)
- Technology stack and tools they use

**Financial & Growth Signals:**
- Funding history and investor information
- Recent partnerships or acquisitions
- Market expansion efforts
- Revenue growth indicators

CRITICAL: Include accurate headquarters/office location information with specific city, state/province, and country. Verify location from multiple sources if possible.

### 3. Pain Point Analysis Matrix
For each business function, identify observable signals and infer likely pain points:

| Function | Observable Signals | Pain Point Hypothesis | Evidence Strength |
|----------|-------------------|----------------------|-------------------|
| Go-to-Market & Sales | [Research and document specific signals] | [Infer likely challenges] | [Rate 1-5] |
| Marketing & Brand | [Research and document specific signals] | [Infer likely challenges] | [Rate 1-5] |
| Product Development | [Research and document specific signals] | [Infer likely challenges] | [Rate 1-5] |
| Customer Success | [Research and document specific signals] | [Infer likely challenges] | [Rate 1-5] |
| Operations & Supply Chain | [Research and document specific signals] | [Infer likely challenges] | [Rate 1-5] |
| Talent & HR | [Research and document specific signals] | [Infer likely challenges] | [Rate 1-5] |
| Finance & Compliance | [Research and document specific signals] | [Infer likely challenges] | [Rate 1-5] |

### 4. Strategic Priority Assessment
Rank the top 3 most pressing, financially material challenges:

**Priority 1:** [Challenge name]
- Evidence: [Specific facts supporting this from your research]
- Business impact: [Quantified or estimated impact]
- Urgency indicators: [Why this is critical now]

**Priority 2:** [Challenge name]
- Evidence: [Specific facts supporting this from your research]
- Business impact: [Quantified or estimated impact] 
- Urgency indicators: [Why this is critical now]

**Priority 3:** [Challenge name]
- Evidence: [Specific facts supporting this from your research]
- Business impact: [Quantified or estimated impact]
- Urgency indicators: [Why this is critical now]

### 5. Solution Hooks & Message Angles
For each of the Top-3 priorities, suggest:
1. AI/automation solution approach that specifically addresses the pain point
2. One-line cold-email hook that provokes curiosity (≤ 25 words)
3. Metric to promise (e.g., "reduce manual work by 40%", "accelerate time-to-market by 3 weeks")

**For Priority 1:**
- Solution approach: [How AI/automation can solve this]
- Email hook: "[Compelling one-liner]"
- Promised metric: [Specific, measurable benefit]

**For Priority 2:**
- Solution approach: [How AI/automation can solve this]
- Email hook: "[Compelling one-liner]"
- Promised metric: [Specific, measurable benefit]

**For Priority 3:**
- Solution approach: [How AI/automation can solve this]
- Email hook: "[Compelling one-liner]"
- Promised metric: [Specific, measurable benefit]

### 6. Sales Engagement Intelligence
Provide actionable outreach insights:

**Key Decision Makers:**
- Research and identify 2-3 relevant stakeholders with names, titles
- Their professional background and recent activities
- Recent posts, articles, or content they've shared

**Conversation Starters:**
- 3 specific, researched conversation hooks based on recent company developments
- Industry trends currently affecting their business
- Competitor moves or market changes they should be aware of

**Timing Indicators:**
- Current business cycles or seasonal factors
- Recent company milestones, funding, or organizational changes
- Market events or regulatory changes creating urgency

### 7. Competitive & Market Context
Brief analysis of their competitive landscape:
- Main competitors and competitive positioning
- Current market trends affecting the industry
- Technology adoption patterns in their sector
- Market opportunities or threats on the horizon

## Research Quality Standards

**Citations Required:** Include specific sources with dates for all factual claims (e.g., "Company LinkedIn, January 2025" or "TechCrunch article, December 2024")

**Depth Requirements:**
- Go beyond surface-level website information
- Identify non-obvious pain points from hiring patterns, technology choices, recent news
- Connect industry trends to company-specific challenges
- Look for growth signals, expansion plans, recent changes

**Actionability Focus:**
- Every insight should connect to potential AI/automation solutions
- Business impact should be quantifiable where possible
- Solutions should be implementable and relevant to their stage/size
- Email hooks should be specific to their current situation

**Accuracy Standards:**
- If information cannot be verified, state "Information not available" rather than guessing
- Distinguish between confirmed facts and reasonable inferences
- Provide confidence levels for key assessments
- Cite sources for all major claims

## Success Criteria

Research should deliver:
1. **Comprehensive Coverage:** All business functions analyzed with specific insights
2. **Deep Intelligence:** Non-obvious insights from multiple data sources
3. **Action-Oriented:** Clear connection between problems and solution opportunities
4. **Evidence-Based:** Strong factual foundation with proper citations
5. **Business-Relevant:** Focus on financially material challenges and opportunities
6. **Current Context:** Emphasis on recent developments and current market position

Target length: 1000-1500 words with structured formatting.

Use your deep research capabilities to gather comprehensive, current information about this company from multiple sources and provide actionable business intelligence for AI sales automation purposes."""

        return prompt

    def format_research_for_system(self, raw_research: str) -> Dict[str, Any]:
        """
        Format raw research results into structured format compatible with existing system.
        
        Args:
            raw_research: Raw research output from Claude's deep research
            
        Returns:
            Dictionary with formatted research data
        """
        try:
            # Basic processing to ensure compatibility with existing system
            formatted_research = {
                'basic_research': raw_research,
                'research_method': 'llm_deep_research',
                'word_count': len(raw_research.split()),
                'character_count': len(raw_research),
                'timestamp': None  # Will be set by calling system
            }
            
            logger.info(f"Formatted LLM deep research: {formatted_research['word_count']} words, {formatted_research['character_count']} characters")
            return formatted_research
            
        except Exception as e:
            logger.error(f"Error formatting research results: {e}")
            return {
                'basic_research': raw_research,
                'research_method': 'llm_deep_research',
                'error': str(e)
            }

    def validate_research_quality(self, research_content: str) -> Dict[str, Any]:
        """
        Validate the quality and completeness of research results.
        
        Args:
            research_content: Research content to validate
            
        Returns:
            Validation results with quality metrics
        """
        validation_results = {
            'is_valid': True,
            'quality_score': 0,
            'completeness_metrics': {},
            'issues': []
        }
        
        try:
            # Check for key sections
            required_sections = [
                'Company Intelligence Snapshot',
                'Business Context Discovery', 
                'Pain Point Analysis',
                'Strategic Priority Assessment',
                'Solution Hooks',
                'Sales Engagement Intelligence'
            ]
            
            completeness_metrics = {}
            for section in required_sections:
                if section.lower() in research_content.lower():
                    completeness_metrics[section] = True
                    validation_results['quality_score'] += 10
                else:
                    completeness_metrics[section] = False
                    validation_results['issues'].append(f"Missing section: {section}")
            
            validation_results['completeness_metrics'] = completeness_metrics
            
            # Check content length
            word_count = len(research_content.split())
            if word_count < 500:
                validation_results['issues'].append(f"Content too short: {word_count} words (minimum 500)")
                validation_results['quality_score'] -= 20
            elif word_count > 2000:
                validation_results['issues'].append(f"Content too long: {word_count} words (maximum 2000)")
                validation_results['quality_score'] -= 10
            
            # Check for citations
            citation_indicators = ['(', 'source:', 'according to', 'reported by', 'announced']
            citation_count = sum(1 for indicator in citation_indicators if indicator in research_content.lower())
            
            if citation_count < 3:
                validation_results['issues'].append("Insufficient citations or source references")
                validation_results['quality_score'] -= 15
            
            # Overall validation
            if validation_results['quality_score'] < 50:
                validation_results['is_valid'] = False
            
            logger.info(f"Research validation completed: Score {validation_results['quality_score']}, Valid: {validation_results['is_valid']}")
            
        except Exception as e:
            logger.error(f"Error validating research quality: {e}")
            validation_results['is_valid'] = False
            validation_results['issues'].append(f"Validation error: {str(e)}")
        
        return validation_results
    
    def _update_research_status(self, company_name: str, status_message: str, company_id: int = None):
        """Update research status in database for real-time progress tracking."""
        try:
            from deepresearch.database_service import DatabaseService
            from sqlalchemy import text
            
            db_service = DatabaseService()
            with db_service.engine.connect() as conn:
                with conn.begin():
                    # Update the status in the database so progress polling can pick it up
                    if company_id is not None:
                        # Use company_id for precise updates (preferred)
                        conn.execute(text("""
                            UPDATE companies 
                            SET llm_research_step_status = :status,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = :company_id
                        """), {
                            'status': status_message,
                            'company_id': company_id
                        })
                    else:
                        # Fallback to company_name (less reliable)
                        conn.execute(text("""
                            UPDATE companies 
                            SET llm_research_step_status = :status,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE company_name = :company_name
                        """), {
                            'status': status_message,
                            'company_name': company_name
                        })
            
            logger.info(f"Updated research status for {company_name}: {status_message}")
            
        except Exception as e:
            logger.warning(f"Failed to update research status for {company_name}: {e}")
            # Don't fail the research if status update fails
    
    def _check_request_limits(self, company_id: int) -> bool:
        """BULLETPROOF: Check if request is allowed based on safety limits."""
        import time
        from datetime import datetime, timedelta
        
        current_time = time.time()
        
        # 1. CHECK FOR DUPLICATE CONCURRENT REQUESTS
        if company_id in self._active_requests:
            logger.error(f"BLOCKED: Research already in progress for company {company_id}")
            raise Exception(f"Research already in progress for company {company_id}. Wait for completion.")
        
        # 2. CHECK HOURLY RATE LIMIT
        hour_ago = current_time - 3600
        self._request_timestamps = [t for t in self._request_timestamps if t > hour_ago]
        
        if len(self._request_timestamps) >= self.max_requests_per_hour:
            logger.error(f"BLOCKED: Hourly rate limit exceeded ({self.max_requests_per_hour}/hour)")
            raise Exception(f"Rate limit exceeded: {self.max_requests_per_hour} requests per hour maximum")
        
        # 3. CHECK DAILY SPEND LIMIT
        if self._daily_cost_tracker >= self.max_daily_spend:
            logger.error(f"BLOCKED: Daily spend limit exceeded (${self._daily_cost_tracker:.2f}/${self.max_daily_spend})")
            raise Exception(f"Daily spending limit exceeded: ${self.max_daily_spend}")
        
        return True
    
    def _register_request_start(self, company_id: int):
        """Register start of request for tracking."""
        import time
        self._active_requests.add(company_id)
        self._request_timestamps.append(time.time())
        logger.info(f"SAFETY: Registered request start for company {company_id}")
    
    def _register_request_end(self, company_id: int, estimated_cost: float = 0.1):
        """Register end of request."""
        self._active_requests.discard(company_id)
        self._daily_cost_tracker += estimated_cost
        logger.info(f"SAFETY: Request completed for company {company_id}, cost: ${estimated_cost:.2f}")
    
    def _emergency_stop_all(self):
        """Emergency stop all active requests."""
        logger.critical("EMERGENCY STOP: Clearing all active requests")
        self._active_requests.clear()
    
    def _get_webhook_url(self) -> str:
        """Get webhook URL for OpenAI callbacks. Returns None if not configured."""
        import os
        base_url = os.getenv('WEBHOOK_BASE_URL')  # e.g., 'https://yourdomain.com'
        if base_url:
            return f"{base_url}/api/webhooks/openai-research"
        return None
    
    def _store_response_id(self, company_id: int, response_id: str):
        """Store OpenAI response ID in database for recovery after restarts."""
        try:
            from deepresearch.database_service import DatabaseService
            from sqlalchemy import text
            
            db_service = DatabaseService()
            with db_service.engine.connect() as conn:
                with conn.begin():
                    conn.execute(text("""
                        UPDATE companies 
                        SET openai_response_id = :response_id,
                            llm_research_step_status = :status,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :company_id
                    """), {
                        'response_id': response_id,
                        'status': 'background_job_running',
                        'company_id': company_id
                    })
            
            logger.info(f"Stored OpenAI response ID {response_id} for company {company_id}")
            
        except Exception as e:
            logger.error(f"Failed to store response ID {response_id} for company {company_id}: {e}")
    
    def _get_stored_response_id(self, company_id: int) -> str:
        """Get stored OpenAI response ID from database."""
        try:
            from deepresearch.database_service import DatabaseService
            from sqlalchemy import text
            
            db_service = DatabaseService()
            with db_service.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT openai_response_id, llm_research_step_status
                    FROM companies 
                    WHERE id = :company_id 
                    AND openai_response_id IS NOT NULL
                    AND llm_research_step_status = 'background_job_running'
                """), {'company_id': company_id})
                
                row = result.fetchone()
                if row:
                    response_id = row[0]
                    logger.info(f"Found stored response ID {response_id} for company {company_id}")
                    return response_id
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get stored response ID for company {company_id}: {e}")
            return None
    
    def _check_background_job_status(self, response_id: str, company_name: str, company_id: int) -> Optional[str]:
        """Check status of existing background job and return results if completed."""
        try:
            logger.info(f"Checking background job status for {response_id} ({company_name})")
            
            # Use OpenAI's GET /responses/{response_id} endpoint to check status
            status_response = self.openai_client.responses.retrieve(response_id)
            
            status = status_response.status  # 'queued', 'in_progress', 'completed', 'failed'
            
            if status == 'completed':
                # Job completed - get the results
                logger.info(f"Background job {response_id} completed for {company_name}")
                results = status_response.output_text or ""
                
                # Clear the stored response ID since job is done
                self._clear_response_id(company_id)
                
                # Update final status
                self._update_research_status(company_name, "Background research completed successfully!", company_id)
                
                return results
            
            elif status == 'failed':
                # Job failed
                logger.error(f"Background job {response_id} failed for {company_name}")
                
                # Clear the stored response ID
                self._clear_response_id(company_id)
                
                # Update error status
                self._update_research_status(company_name, f"Background job failed: {status_response.error or 'Unknown error'}", company_id)
                
                return None
            
            elif status in ['queued', 'in_progress']:
                # Job still running - update status and return None to indicate not ready
                logger.info(f"Background job {response_id} still {status} for {company_name}")
                
                status_msg = f"Background research {status}" + (f" (ID: {response_id})" if status == 'in_progress' else f" (ID: {response_id})")
                self._update_research_status(company_name, status_msg, company_id)
                
                # Return a special marker to indicate job is still running
                return "__BACKGROUND_JOB_IN_PROGRESS__"
            
            else:
                logger.warning(f"Unknown background job status '{status}' for {response_id} ({company_name})")
                return None
                
        except Exception as e:
            logger.error(f"Error checking background job status for {response_id} ({company_name}): {e}")
            return None
    
    def _poll_background_job(self, response_id: str, company_name: str, company_id: int) -> Optional[str]:
        """Poll background job status. Returns results if completed, None if still running, or triggers fallback."""
        try:
            # For the initial call, just return a marker that the job is starting
            # The frontend polling will handle checking for completion
            logger.info(f"Background job {response_id} started for {company_name}, polling will be handled by frontend")
            
            # Return special marker to indicate background job is running
            return "__BACKGROUND_JOB_STARTED__"
            
        except Exception as e:
            logger.error(f"Error setting up background job polling for {response_id} ({company_name}): {e}")
            return None
    
    def _clear_response_id(self, company_id: int):
        """Clear stored OpenAI response ID from database."""
        try:
            from deepresearch.database_service import DatabaseService
            from sqlalchemy import text
            
            db_service = DatabaseService()
            with db_service.engine.connect() as conn:
                with conn.begin():
                    conn.execute(text("""
                        UPDATE companies 
                        SET openai_response_id = NULL,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :company_id
                    """), {'company_id': company_id})
            
            logger.info(f"Cleared OpenAI response ID for company {company_id}")
            
        except Exception as e:
            logger.error(f"Failed to clear response ID for company {company_id}: {e}")
    
    def check_and_recover_background_jobs(self):
        """Check for and recover any orphaned background jobs on startup."""
        try:
            from deepresearch.database_service import DatabaseService
            from sqlalchemy import text
            
            logger.info("Checking for orphaned background research jobs on startup...")
            
            db_service = DatabaseService()
            with db_service.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, company_name, openai_response_id, llm_research_started_at
                    FROM companies 
                    WHERE openai_response_id IS NOT NULL
                    AND llm_research_step_status = 'background_job_running'
                """))
                
                orphaned_jobs = result.fetchall()
                
                if not orphaned_jobs:
                    logger.info("No orphaned background jobs found")
                    return
                
                logger.info(f"Found {len(orphaned_jobs)} orphaned background jobs, attempting recovery...")
                
                for company_id, company_name, response_id, started_at in orphaned_jobs:
                    logger.info(f"Recovering background job {response_id} for {company_name} (started: {started_at})")
                    
                    # Check job status and handle accordingly
                    result = self._check_background_job_status(response_id, company_name, company_id)
                    
                    if result == "__BACKGROUND_JOB_IN_PROGRESS__":
                        logger.info(f"Background job {response_id} for {company_name} is still running, will continue polling")
                    elif result:
                        logger.info(f"Background job {response_id} for {company_name} completed during downtime, results recovered")
                        # Process the results through the normal pipeline
                        self._process_completed_background_job(company_id, result)
                    else:
                        logger.warning(f"Background job {response_id} for {company_name} failed or couldn't be recovered")
                        
        except Exception as e:
            logger.error(f"Error checking for orphaned background jobs: {e}")
    
    def _process_completed_background_job(self, company_id: int, results: str):
        """Process completed background job results through the normal research pipeline."""
        try:
            # This would integrate with the step-by-step researcher to continue the pipeline
            # For now, just store the results in step 1
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
            
            logger.info(f"Processed completed background job results for company {company_id}")
            
        except Exception as e:
            logger.error(f"Error processing completed background job for company {company_id}: {e}")