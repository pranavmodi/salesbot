#!/usr/bin/env python3
"""
LLM Step 1 Handler

Manages Step 1 (Deep Research) using OpenAI background jobs.
This step uses OpenAI's deep research capabilities to gather comprehensive company intelligence.
"""

import logging
from typing import Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

class LLMStep1Handler:
    """Handles Step 1 deep research using OpenAI background jobs."""
    
    def __init__(self, openai_client: OpenAI):
        self.openai_client = openai_client
        logger.info("LLMStep1Handler initialized")
    
    def start_deep_research(self, company_name: str, website_url: str, company_id: int) -> Optional[str]:
        """Start OpenAI deep research background job for step 1."""
        try:
            logger.info(f"Starting OpenAI deep research for {company_name}")
            
            # Create step 1 prompt
            step_1_prompt = self._create_step_1_prompt(company_name, website_url)
            
            # Start OpenAI deep research background job
            response = self.openai_client.chat.completions.create(
                model="o4-mini-deep-research-2025-06-26",
                messages=[{"role": "user", "content": step_1_prompt}],
                background=True
            )
            
            response_id = response.id
            logger.info(f"OpenAI deep research background job started for {company_name}, response_id: {response_id}")
            
            return response_id
            
        except Exception as e:
            logger.error(f"Failed to start step 1 deep research for {company_name}: {e}")
            return None
    
    def _create_step_1_prompt(self, company_name: str, website_url: str) -> str:
        """Create comprehensive research prompt for step 1."""
        domain = ""
        if website_url:
            if website_url.startswith(('http://', 'https://')):
                domain = website_url.replace('https://', '').replace('http://', '').split('/')[0]
            else:
                domain = website_url
        
        return f"""You are an expert B2B go-to-market strategist conducting comprehensive company research for AI sales automation. Perform deep research analysis using all available tools and capabilities.

COMPANY TO RESEARCH: {company_name}
WEBSITE: {website_url if website_url else 'Not available'}
DOMAIN: {domain if domain else 'Not available'}

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

### 3. Operational Context Analysis
- Current technology infrastructure and capabilities
- Key operational challenges and bottlenecks
- Digital transformation initiatives
- Automation and AI adoption patterns

### 4. Strategic Intelligence Summary
- Primary growth drivers and strategic priorities
- Competitive positioning and market dynamics
- Innovation focus areas and R&D investment
- Geographic expansion and market penetration strategies

## Output Requirements

Provide comprehensive, well-sourced intelligence that forms the foundation for strategic analysis. Include specific data points, recent developments, and actionable insights about the company's current state and strategic direction.

Format your response in clear markdown with proper headings and bullet points for easy consumption by subsequent analysis steps.
"""