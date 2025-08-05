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
    
    # Class variable to track if startup recovery has been run
    _startup_recovery_completed = False
    # Singleton instance to prevent repeated initialization
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LLMDeepResearchService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Prevent repeated initialization
        if self._initialized:
            return
            
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
        
        # Initialize Perplexity client if API key is available
        self.perplexity_client = None
        self.perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
        if self.perplexity_api_key:
            # Store API key for direct HTTP requests since OpenAI client doesn't support Perplexity-specific parameters
            logger.info("LLMDeepResearchService initialized with Perplexity API key")
        else:
            logger.warning("PERPLEXITY_API_KEY not found - Perplexity Sonar research will not be available")
        
        # Mark as initialized to prevent repeated initialization
        self._initialized = True

    def research_company_deep(self, company_name: str, company_domain: str = "", provider: str = "claude", company_id: int = None, from_step_researcher: bool = False) -> Optional[str]:
        """
        Execute comprehensive company analysis using LLM deep research capabilities.
        
        Args:
            company_name: Name of the company to research
            company_domain: Company domain/website
            provider: LLM provider to use ('claude', 'openai', or 'perplexity')
            company_id: Company ID for safety tracking
            from_step_researcher: True if called from step-by-step researcher (skips duplicate check)
            
        Returns:
            Comprehensive research analysis string or None if failed
        """
        logger.critical(f"🚨 DEEP RESEARCH API CALL INITIATED: {company_name} using {provider} (company_id: {company_id})")
        logger.info(f"Starting LLM deep research for company: {company_name} using {provider}")
        
        # BULLETPROOF DATABASE CHECKS BEFORE API CALL (skip if called from step researcher)
        if company_id is not None and not from_step_researcher:
            try:
                # 1. Check if research is already in progress or completed
                research_status = self._check_database_research_status(company_id)
                if research_status['already_triggered']:
                    logger.error(f"🚨 BLOCKED: Research already triggered for company {company_id}. Status: {research_status['status']}, Started: {research_status['started_at']}")
                    raise Exception(f"Research already triggered for company {company_id}. Current status: {research_status['status']}. Started at: {research_status['started_at']}")
            except Exception as safety_error:
                logger.error(f"🚨 SAFETY CHECK FAILED: {safety_error}")
                raise safety_error
        elif from_step_researcher:
            logger.info(f"🚨 STEP RESEARCHER CALL: Skipping duplicate check for company {company_id} as this is called from step-by-step researcher")
        
        if company_id is not None and not from_step_researcher:
            try:
                # 2. Check concurrency and rate limits
                self._check_request_limits(company_id)
                
                # 3. Mark as triggered in database BEFORE making API call
                self._mark_research_triggered_in_db(company_id, provider)
                
                # 4. Register in memory tracking
                self._register_request_start(company_id)
                
            except Exception as safety_error:
                logger.error(f"🚨 SAFETY CHECK FAILED: {safety_error}")
                raise safety_error
        elif company_id is not None and from_step_researcher:
            # For step researcher, only do memory tracking (database already updated by step researcher)
            try:
                # Check concurrency and rate limits only
                self._check_request_limits(company_id)
                
                # Only register in memory tracking (skip database update)
                self._register_request_start(company_id)
                
            except Exception as safety_error:
                logger.error(f"🚨 STEP RESEARCHER SAFETY CHECK FAILED: {safety_error}")
                raise safety_error
        elif company_id is None:
            logger.warning("No company_id provided - skipping all safety checks")
        
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
            elif provider.lower() == "perplexity" and self.perplexity_api_key:
                result = self._execute_perplexity_research(research_prompt, company_name, company_id)
            else:
                logger.error(f"Provider {provider} not available or not configured")
                result = None
            
            # REGISTER COMPLETION AND UPDATE DATABASE
            if company_id is not None:
                # Estimate costs based on provider
                if provider.lower() == "openai":
                    estimated_cost = 0.5  # Higher estimate for OpenAI Deep Research
                elif provider.lower() == "perplexity":
                    estimated_cost = 0.2  # Moderate estimate for Perplexity Sonar
                else:
                    estimated_cost = 0.1  # Lower estimate for Claude
                self._register_request_end(company_id, estimated_cost)
                
                # Update database with completion status
                if result and result != "__BACKGROUND_JOB_STARTED__":
                    logger.critical(f"🚨 RESEARCH SUCCESS: {company_name} research completed successfully using {provider}")
                    self._mark_research_completed_in_db(company_id, result, provider)
                elif result == "__BACKGROUND_JOB_STARTED__":
                    logger.info(f"OpenAI background job started for {company_name}, no immediate result to save.")
                else:
                    logger.critical(f"🚨 RESEARCH FAILED: {company_name} research failed - API returned no results using {provider}")
                    self._mark_research_failed_in_db(company_id, f"{provider} API call returned no results (no fallback attempted)", provider)
            
            return result
                
        except Exception as e:
            # CLEANUP ON ERROR AND UPDATE DATABASE
            if company_id is not None:
                self._register_request_end(company_id, 0.0)  # No cost if failed
                # Mark as failed in database
                self._mark_research_failed_in_db(company_id, str(e), provider)
            
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
        logger.critical(f"🚨 CLAUDE API DEEP RESEARCH CALL MADE: company={company_name}, model=claude-3-5-sonnet-20241022")
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
            logger.critical(f"🚨 CLAUDE WEB SEARCH FAILED: {company_name} - {e}")
            logger.error(f"Claude web search API error for {company_name}: {e}")
            
            # NO FALLBACK - Return None to indicate failure
            logger.critical(f"🚨 NO FALLBACK: Claude research failed for {company_name}, no standard Claude API fallback will be attempted")
            return None

    def _execute_perplexity_research(self, research_prompt: str, company_name: str, company_id: int = None) -> Optional[str]:
        """Execute research using Perplexity Sonar Deep Research API."""
        logger.critical(f"🚨 PERPLEXITY API DEEP RESEARCH CALL MADE: company={company_name}, model=sonar-deep-research")
        logger.info(f"Executing Perplexity Sonar deep research for {company_name}")
        
        # Update status to show research is starting
        if company_id:
            self._update_research_status(company_name, "Preparing Perplexity deep research query", company_id)
        
        try:
            import requests
            import json
            import threading
            import time
            
            # Prepare the request payload
            payload = {
                "model": "sonar-deep-research",
                "messages": [
                    {
                        "role": "user", 
                        "content": f"""You are an expert B2B research analyst conducting comprehensive company research using Perplexity's deep search capabilities.

{research_prompt}

IMPORTANT: Use Perplexity's advanced web search to find:
- Current company information from their website and recent sources
- Latest news, press releases, and company announcements  
- Financial data, funding rounds, and growth metrics
- Technology stack and product information from multiple sources
- Customer reviews, testimonials, and market analysis
- Competitor analysis and industry trend data
- Leadership team information and recent hiring patterns
- Recent company developments and strategic initiatives

Provide comprehensive analysis with detailed source citations and URLs for all information found. Focus on actionable business intelligence for B2B sales purposes.

Company to research: {company_name}"""
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 8000,
                "search_mode": "web",  # Enable web search
                "reasoning_effort": "high"  # Use maximum reasoning capability
            }
            
            headers = {
                "Authorization": f"Bearer {self.perplexity_api_key}",
                "Content-Type": "application/json"
            }
            
            # Update status to show API call is being made
            if company_id:
                self._update_research_status(company_name, "Executing Perplexity Sonar deep research", company_id)
            
            # Start a progress indicator thread for long-running requests
            progress_active = True
            progress_messages = [
                "Perplexity is searching the web for company data",
                "Analyzing company information and market data", 
                "Gathering business intelligence insights",
                "Compiling comprehensive research report",
                "Finalizing deep research analysis"
            ]
            
            def update_progress():
                if not company_id:
                    return
                
                start_time = time.time()
                message_index = 0
                
                while progress_active:
                    elapsed = time.time() - start_time
                    
                    # Update progress message every 30 seconds
                    if elapsed > 30 and message_index < len(progress_messages) - 1:
                        message_index = min(int(elapsed // 30), len(progress_messages) - 1)
                        self._update_research_status(company_name, progress_messages[message_index], company_id)
                    
                    time.sleep(5)  # Check every 5 seconds
            
            # Start progress thread if we have a company_id
            progress_thread = None
            if company_id:
                progress_thread = threading.Thread(target=update_progress, daemon=True)
                progress_thread.start()
            
            try:
                # Make the API request
                response = requests.post(
                    "https://api.perplexity.ai/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=300  # 5 minute timeout
                )
            finally:
                # Stop progress updates
                progress_active = False
                if progress_thread:
                    progress_thread.join(timeout=1)
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Update status to show response is being processed
            if company_id:
                self._update_research_status(company_name, "Processing Perplexity research results", company_id)
            
            # Parse the response
            response_data = response.json()
            
            if 'choices' in response_data and len(response_data['choices']) > 0:
                research_results = response_data['choices'][0]['message']['content']
                
                # Check if response includes search results
                search_results_info = ""
                if 'search_results' in response_data:
                    search_count = len(response_data['search_results'])
                    search_results_info = f" with {search_count} web sources"
                    logger.info(f"Perplexity search used {search_count} web sources")
                
                # Update status to show completion
                if company_id:
                    self._update_research_status(company_name, "Perplexity research completed successfully", company_id)
                
                logger.info(f"Perplexity Sonar deep research completed for {company_name}: {len(research_results)} characters{search_results_info}")
                return research_results
            else:
                logger.error(f"Perplexity API returned no choices for {company_name}")
                return None
            
        except requests.exceptions.RequestException as e:
            logger.critical(f"🚨 PERPLEXITY SONAR DEEP RESEARCH FAILED: {company_name} - {e}")
            logger.error(f"Perplexity API request error for {company_name}: {e}")
            
            # Detailed error diagnosis for HTTP-specific issues
            if hasattr(e, 'response') and e.response is not None:
                status_code = e.response.status_code
                if status_code == 401:
                    logger.error(f"Perplexity API authentication failed (401). Check PERPLEXITY_API_KEY: {e}")
                elif status_code == 403:
                    logger.error(f"Perplexity API access forbidden (403). Check account permissions or billing: {e}")
                elif status_code == 429:
                    logger.error(f"Perplexity API rate limit exceeded (429): {e}")
                elif status_code == 400:
                    logger.error(f"Perplexity API bad request (400). Model or parameters may be incorrect: {e}")
                elif status_code == 404:
                    logger.error(f"Perplexity API endpoint not found (404). Check model name 'sonar-deep-research': {e}")
                elif status_code >= 500:
                    logger.error(f"Perplexity API server error ({status_code}). Service may be temporarily unavailable: {e}")
                else:
                    logger.error(f"Perplexity API HTTP error ({status_code}): {e}")
            else:
                logger.error(f"Perplexity API connection error: {e}")
            
            return None
            
        except Exception as e:
            logger.critical(f"🚨 PERPLEXITY SONAR DEEP RESEARCH FAILED: {company_name} - {e}")
            logger.error(f"Perplexity API unknown error for {company_name}: {e}")
            return None

    def _execute_openai_research(self, research_prompt: str, company_name: str, company_id: int = None) -> Optional[str]:
        """Execute research using OpenAI o4-mini Deep Research API in background mode."""
        logger.info(f"Starting OpenAI o4-mini deep research for {company_name} in background mode")
        
        try:
            # Validate OpenAI client supports responses endpoint
            if not hasattr(self.openai_client, 'responses'):
                error_msg = "OpenAI client does not have 'responses' attribute. Deep Research API not available with current client version."
                logger.error(error_msg)
                if company_id:
                    self._mark_research_failed_in_db(company_id, error_msg, "openai")
                return None
            
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
                
                # OpenAI Deep Research API call with proper background mode (per official docs)
                logger.info(f"Attempting OpenAI Deep Research API with background mode for {company_name}")
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
                    background=True  # OFFICIAL: background=True is supported per OpenAI docs
                )
                
                response_id = response.id
                logger.critical(f"🚨 OPENAI API DEEP RESEARCH CALL MADE: response_id={response_id}, company={company_name}, model=o4-mini-deep-research-2025-06-26")
                logger.info(f"OpenAI Deep Research background job started: {response_id} for {company_name}")
                
                # Store response_id in database for recovery after restarts AND mark as background job running
                self._store_response_id(company_id, response_id)
                logger.critical(f"🚨 DB UPDATED: OpenAI background job marked in database for company {company_id}, response_id={response_id}")
                
                # Update status to show background job is running (keep under 50 chars)
                self._update_research_status(company_name, "Executing step 1 with OpenAI deep research", company_id)
                
                # Start polling for status updates
                return self._poll_background_job(response_id, company_name, company_id)
                
            except Exception as deep_error:
                error_msg = str(deep_error)
                logger.critical(f"🚨 OPENAI DEEP RESEARCH FAILED: {company_name} - {deep_error}")
                
                # Detailed error diagnosis
                if "unexpected keyword argument 'background'" in error_msg:
                    logger.error(f"OpenAI client library does not support 'background' parameter. Client version may be outdated or feature not available for your API key: {deep_error}")
                elif "404" in error_msg or "Not Found" in error_msg:
                    logger.error(f"OpenAI Deep Research API endpoint not found. This feature may not be available for your API key or account: {deep_error}")
                elif "400" in error_msg or "Bad Request" in error_msg:
                    logger.error(f"OpenAI Deep Research API request malformed. Model or parameters may be incorrect: {deep_error}")
                elif "401" in error_msg or "Unauthorized" in error_msg:
                    logger.error(f"OpenAI API authentication failed or Deep Research not available for your account: {deep_error}")
                elif "403" in error_msg or "Forbidden" in error_msg:
                    logger.error(f"OpenAI Deep Research API access forbidden. This feature may require beta access or higher tier: {deep_error}")
                elif "503" in error_msg or "Service Unavailable" in error_msg:
                    logger.error(f"OpenAI Deep Research API is currently unavailable (503 Service Unavailable): {deep_error}")
                elif "429" in error_msg or "rate_limit" in error_msg.lower():
                    logger.error(f"Rate limit exceeded for OpenAI Deep Research API: {deep_error}")
                elif "insufficient_quota" in error_msg.lower():
                    logger.error(f"API quota exceeded for OpenAI Deep Research API: {deep_error}")
                else:
                    logger.error(f"OpenAI Deep Research API failed with unknown error: {deep_error}")
                
                # NO FALLBACK - Mark as failed and return None
                logger.critical(f"🚨 NO FALLBACK: Research failed for {company_name}, no GPT-4 fallback will be attempted")
                logger.info(f"DEBUGGING INFO: OpenAI client version in use, model attempted: o4-mini-deep-research-2025-06-26, background=True")
                
                # Update database to mark as failed
                if company_id:
                    self._mark_research_failed_in_db(company_id, f"OpenAI Deep Research API failed: {error_msg}", "openai")
                
                # Return None to indicate failure
                return None
            
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
    
    def _check_database_research_status(self, company_id: int) -> Dict[str, Any]:
        """Check database for existing research status to prevent duplicates."""
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
                        openai_response_id,
                        llm_research_step_1_basic,
                        llm_research_completed_at
                    FROM companies 
                    WHERE id = :company_id
                """), {'company_id': company_id})
                
                row = result.fetchone()
                if not row:
                    return {'already_triggered': False, 'status': 'not_found'}
                
                status, started_at, provider, response_id, step_1_data, completed_at = row
                
                # Check if research is already in progress or completed
                if status in ['background_job_running', 'step_1', 'step_2', 'step_3', 'in_progress', 'completed']:
                    # Allow if it's been more than 1 hour since started (might be stuck)
                    import datetime
                    if started_at:
                        time_diff = datetime.datetime.now() - started_at
                        if time_diff.total_seconds() > 3600:  # 1 hour timeout
                            logger.warning(f"Research for company {company_id} appears stuck (started {time_diff} ago), allowing retry")
                            return {'already_triggered': False, 'status': 'timeout_retry_allowed'}
                    
                    return {
                        'already_triggered': True,
                        'status': status,
                        'started_at': started_at,
                        'provider': provider,
                        'response_id': response_id,
                        'has_results': bool(step_1_data),
                        'completed_at': completed_at
                    }
                
                return {'already_triggered': False, 'status': status or 'pending'}
                
        except Exception as e:
            logger.error(f"Error checking database research status for company {company_id}: {e}")
            # On error, allow the request (fail open rather than fail closed)
            return {'already_triggered': False, 'status': 'check_failed'}
    
    def _mark_research_triggered_in_db(self, company_id: int, provider: str):
        """Mark research as triggered in database BEFORE making API call."""
        try:
            from deepresearch.database_service import DatabaseService
            from sqlalchemy import text
            
            db_service = DatabaseService()
            with db_service.engine.connect() as conn:
                with conn.begin():
                    conn.execute(text("""
                        UPDATE companies 
                        SET llm_research_step_status = 'api_call_initiated',
                            llm_research_provider = :provider,
                            llm_research_started_at = CURRENT_TIMESTAMP,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :company_id
                    """), {
                        'provider': provider,
                        'company_id': company_id
                    })
            
            logger.critical(f"🚨 DB MARKED: Research marked as triggered in database for company {company_id}, provider={provider}")
            
        except Exception as e:
            logger.error(f"Failed to mark research as triggered in DB for company {company_id}: {e}")
            # This is critical - if we can't mark it, we should fail the request
            raise Exception(f"Failed to mark research as triggered in database: {e}")
    
    def _mark_research_completed_in_db(self, company_id: int, results: str, provider: str):
        """Mark research as completed in database."""
        try:
            from deepresearch.database_service import DatabaseService
            # Validate results before saving - prevent marker leakage
            if isinstance(results, str) and results.startswith('__') and results.endswith('__'):
                logger.error(f"🚨 MARKER LEAK: Attempted to save marker '{results}' as research results for company {company_id}")
                self._mark_research_failed_in_db(company_id, f"Internal marker {results} should not be saved as research results", "openai")
                return
            
            from sqlalchemy import text
            
            db_service = DatabaseService()
            with db_service.engine.connect() as conn:
                with conn.begin():
                    conn.execute(text("""
                        UPDATE companies 
                        SET llm_research_step_status = 'step_1_completed',
                            llm_research_step_1_basic = :results,
                            llm_research_completed_at = CURRENT_TIMESTAMP,
                            openai_response_id = NULL,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :company_id
                    """), {
                        'results': results,
                        'company_id': company_id
                    })
            
            logger.critical(f"🚨 DB COMPLETED: Research marked as completed in database for company {company_id}")
            
        except Exception as e:
            logger.error(f"Failed to mark research as completed in DB for company {company_id}: {e}")
    
    def _mark_research_failed_in_db(self, company_id: int, error_message: str, provider: str):
        """Mark research as failed in database."""
        try:
            from deepresearch.database_service import DatabaseService
            from sqlalchemy import text
            
            db_service = DatabaseService()
            with db_service.engine.connect() as conn:
                with conn.begin():
                    error_text = f"ERROR: {error_message}"
                    conn.execute(text("""
                        UPDATE companies 
                        SET llm_research_step_status = 'failed',
                            llm_research_step_1_basic = :error_text,
                            openai_response_id = NULL,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :company_id
                    """), {
                        'error_text': error_text,
                        'company_id': company_id
                    })
            
            logger.critical(f"🚨 DB FAILED: Research marked as failed in database for company {company_id}: {error_message}")
            
        except Exception as e:
            logger.error(f"Failed to mark research as failed in DB for company {company_id}: {e}")
    
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
            
            # Log the most relevant fields from OpenAI response
            logger.info(f"🔍 OPENAI RAW RESPONSE for {response_id}:")
            logger.info(f"  Status: {status}")
            logger.info(f"  ID: {getattr(status_response, 'id', 'N/A')}")
            logger.info(f"  Created: {getattr(status_response, 'created_at', 'N/A')}")
            logger.info(f"  Model: {getattr(status_response, 'model', 'N/A')}")
            if hasattr(status_response, 'output_text') and status_response.output_text:
                logger.info(f"  Output Length: {len(status_response.output_text)} chars")
                logger.info(f"  Output Preview: {status_response.output_text[:100]}...")
            else:
                logger.info(f"  Output: None")
            if hasattr(status_response, 'usage'):
                logger.info(f"  Usage: {status_response.usage}")
            
            logger.info(f"POLLING STATUS: OpenAI job {response_id} for '{company_name}' has status: {status}")
            
            if status == 'completed':
                # Job completed - get the results
                logger.info(f"Background job {response_id} completed for {company_name}")
                results = status_response.output_text or ""
                
                # Clear the stored response ID since job is done
                self._clear_response_id(company_id)
                
                # Update final status
                self._update_research_status(company_name, "OpenAI research completed successfully", company_id)
                
                return results
            
            elif status == 'failed':
                # Job failed
                logger.error(f"Background job {response_id} failed for {company_name}")
                
                # Clear the stored response ID
                self._clear_response_id(company_id)
                
                # Update error status (keep under 50 chars)
                self._update_research_status(company_name, "OpenAI research failed - see logs", company_id)
                
                return None
            
            elif status in ['queued', 'in_progress']:
                # Job still running - update status and return None to indicate not ready
                logger.info(f"Background job {response_id} still {status} for {company_name}")
                
                # Keep status message under 50 chars
                status_msg = f"OpenAI research {status}"
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
        """Poll background job status. Returns results if completed, marker if still running."""
        try:
            logger.info(f"Checking immediate status of background job {response_id} for {company_name}")
            
            # Check if the job completed immediately (some jobs finish very quickly)
            result = self._check_background_job_status(response_id, company_name, company_id)
            
            if result == "__BACKGROUND_JOB_IN_PROGRESS__":
                # Job is still running, frontend polling will handle it
                logger.info(f"Background job {response_id} for {company_name} is in progress, frontend will continue polling")
                return "__BACKGROUND_JOB_STARTED__"
            elif result:
                # Job completed immediately with results
                logger.info(f"Background job {response_id} for {company_name} completed immediately")
                return result
            else:
                # Job failed or couldn't be checked
                logger.warning(f"Background job {response_id} for {company_name} failed or couldn't be checked")
                return None
            
        except Exception as e:
            logger.error(f"Error checking background job status for {response_id} ({company_name}): {e}")
            return "__BACKGROUND_JOB_STARTED__"  # Assume it's running, let frontend handle it
    
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
        # Only run recovery once per application lifecycle
        if LLMDeepResearchService._startup_recovery_completed:
            logger.debug("Startup recovery already completed, skipping")
            return
            
        try:
            from deepresearch.database_service import DatabaseService
            from sqlalchemy import text
            
            logger.info("Checking for orphaned background research jobs on startup...")
            
            db_service = DatabaseService()
            with db_service.engine.connect() as conn:
                # Original query for jobs in 'background_job_running' state
                result = conn.execute(text("""
                    SELECT id, company_name, openai_response_id, llm_research_started_at
                    FROM companies 
                    WHERE openai_response_id IS NOT NULL
                    AND llm_research_step_status = 'background_job_running'
                """))
                
                background_jobs = result.fetchall()
                logger.info(f"Found {len(background_jobs)} jobs in 'background_job_running' state")
                
                # EXPANDED: Also check for jobs with OpenAI-specific statuses (queued, in_progress, etc.)
                result2 = conn.execute(text("""
                    SELECT id, company_name, openai_response_id, llm_research_started_at
                    FROM companies 
                    WHERE openai_response_id IS NOT NULL
                    AND (llm_research_step_status LIKE '%OpenAI%' 
                         OR llm_research_step_status IN ('background_job_running'))
                """))
                
                all_openai_jobs = result2.fetchall()
                logger.info(f"Found {len(all_openai_jobs)} total jobs with OpenAI response IDs")
                
                # Combine results (deduplicate by company_id)
                seen_companies = set()
                combined_jobs = []
                
                for job in background_jobs + all_openai_jobs:
                    if job[0] not in seen_companies:
                        combined_jobs.append(job)
                        seen_companies.add(job[0])
                
                orphaned_jobs = combined_jobs
                
                if not orphaned_jobs:
                    logger.info("No orphaned background jobs found")
                else:
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
                
                # Mark recovery as completed
                LLMDeepResearchService._startup_recovery_completed = True
                logger.info("Background job recovery check completed")
                        
        except Exception as e:
            logger.error(f"Error checking for orphaned background jobs: {e}")
            # Still mark as completed to prevent repeated attempts
            LLMDeepResearchService._startup_recovery_completed = True
    
    def _process_completed_background_job(self, company_id: int, results: str):
        """Process completed background job results using the refactored workflow orchestrator."""
        try:
            # Validate results before saving - prevent marker leakage
            if isinstance(results, str) and results.startswith('__') and results.endswith('__'):
                logger.error(f"🚨 MARKER LEAK: Attempted to save marker '{results}' as research results for company {company_id}")
                return
            
            # Get company info
            from deepresearch.database_service import DatabaseService
            from sqlalchemy import text
            
            db_service = DatabaseService()
            with db_service.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT company_name, website_url
                    FROM companies WHERE id = :company_id
                """), {'company_id': company_id})
                
                company_row = result.fetchone()
                if not company_row:
                    logger.error(f"Company {company_id} not found during background job processing")
                    return
                
                company_name = company_row[0]
                website_url = company_row[1] or ""
            
            logger.info(f"Processing completed step 1 background job for {company_name} (ID: {company_id})")
            
            # Use the workflow orchestrator to handle step 1 completion and progression
            from deepresearch.llm_workflow_orchestrator import LLMWorkflowOrchestrator
            orchestrator = LLMWorkflowOrchestrator(self.openai_client)
            orchestrator.process_step_1_completion_and_start_step_2(company_id, company_name, website_url, results)
            
        except Exception as e:
            logger.error(f"Error processing completed background job for company {company_id}: {e}")
    
    # Step 2 and 3 methods have been moved to dedicated handler classes:
    # - llm_step_2_handler.py: Handles strategic analysis using original AI service
    # - llm_step_3_handler.py: Handles report generation using original report generator
    # - llm_workflow_orchestrator.py: Orchestrates the complete 3-step workflow
    

    def poll_and_process_background_jobs(self) -> int:
        """Poll all active OpenAI background jobs and process completed ones. Returns count of processed jobs."""
        try:
            from deepresearch.database_service import DatabaseService
            from sqlalchemy import text
            
            db_service = DatabaseService()
            with db_service.engine.connect() as conn:
                # Find companies with active background jobs (expanded to include all OpenAI statuses)
                result = conn.execute(text("""
                    SELECT id, company_name, openai_response_id 
                    FROM companies 
                    WHERE openai_response_id IS NOT NULL
                    AND (llm_research_step_status LIKE '%OpenAI%' 
                         OR llm_research_step_status = 'background_job_running')
                """))
                
                active_jobs = result.fetchall()
                
                if not active_jobs:
                    return 0
                
                logger.debug(f"Found {len(active_jobs)} active background jobs to check")
                completed_count = 0
                
                for job in active_jobs:
                    company_id, company_name, response_id = job
                    logger.debug(f"Checking background job {response_id} for {company_name}")
                    
                    try:
                        # Check job status and process if completed
                        result = self._check_background_job_status(response_id, company_name, company_id)
                        
                        if result == "__BACKGROUND_JOB_IN_PROGRESS__":
                            logger.debug(f"Background job {response_id} for {company_name} still in progress")
                            continue
                        elif result:
                            logger.info(f"✅ Background job {response_id} for {company_name} completed, processing results")
                            # Process the results through the normal pipeline
                            self._process_completed_background_job(company_id, result)
                            completed_count += 1
                        else:
                            logger.warning(f"❌ Background job {response_id} for {company_name} failed")
                            # Job failed - clean up and mark as failed
                            self._clear_response_id(company_id)
                            self._mark_research_failed_in_db(company_id, "OpenAI background job failed", "openai")
                            
                    except Exception as job_error:
                        logger.error(f"Error processing background job {response_id} for {company_name}: {job_error}")
                        continue
                
                return completed_count
                
        except Exception as e:
            logger.error(f"Error polling OpenAI background jobs: {e}")
            return 0