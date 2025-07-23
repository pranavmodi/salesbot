#!/usr/bin/env python3
"""
AI Research Service

Handles OpenAI API interactions for:
- Company research using GPT models
- Strategic analysis generation
- AI-powered business insights
"""

import os
import logging
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI

logger = logging.getLogger(__name__)

class AIResearchService:
    """Handles AI-powered research using OpenAI."""
    
    def __init__(self):
        load_dotenv()
        self.client = OpenAI(api_key=os.getenv("OPENAI_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "o3")
        logger.info("AIResearchService initialized")

    def research_company(self, company_name: str, company_domain: str = "") -> Optional[str]:
        """Use OpenAI to research a company and return comprehensive research."""
        logger.info(f"Researching company: {company_name}")
        
        # Construct website URL from domain
        website_url = ""
        if company_domain:
            if not company_domain.startswith(('http://', 'https://')):
                website_url = f"https://{company_domain}"
            else:
                website_url = company_domain

        system_prompt = """You are an expert B2B go-to-market strategist. Your task is to perform a comprehensive, desk-based diagnostic of companies for sales outreach purposes.

Follow this exact structure:

1 | Snapshot
Return a 3-sentence plain-English overview covering industry, core offering, size (revenue or headcount), and growth stage.

2 | Source Harvest
Pull and cite recent facts (≤ 12 months) from:
• Official sources: homepage, product pages, pricing, blog, annual or quarterly reports, investor decks, SEC/Companies House filings.
• Job postings on careers page or LinkedIn.
• News, PR, podcasts, founder interviews.
• Customer reviews (G2, Capterra, Trustpilot, Glassdoor for employer sentiment).
• Social media signals (LinkedIn posts, X/Twitter threads).

3 | Signals → Pain Hypotheses
For each major business function below, list observed signals (1-2 bullet points) → inferred pain hypothesis (1 bullet) in the table:

Function | Signals (facts) | Likely Pain-Point Hypothesis
GTM / Sales | | 
Marketing / Brand | | 
Product / R&D | | 
Customer Success | | 
Ops / Supply Chain | | 
People / Hiring | | 
Finance / Compliance | | 

4 | Top-3 Burning Problems
Rank the three most pressing, financially material pain points, citing the strongest evidence for each. Explain the business impact in one short paragraph per pain.

5 | Solution Hooks & Message Angles
For each of the Top-3 pains, suggest:
1. Solution hook (how our AI/LLM offering specifically relieves it).
2. One-line cold-email angle that provokes curiosity (≤ 25 words).
3. Metric to promise (e.g., "cut SDR research time by 40%").

Use H2 headings for sections 1-5. Return Markdown with inline citations (e.g., "(Crunchbase, Jan 2025)") after each fact. If information is missing, say "Data not found" instead of guessing. Keep total length ≤ 600 words."""

        user_prompt = f"""You are an expert B2B go-to-market strategist. Your task is to perform a comprehensive, desk-based diagnostic of the company named {company_name}{f" (website {website_url})" if website_url else ""}.

Company Details:
- Company Name: {company_name}
- Website: {website_url if website_url else 'Not available'}
- Domain: {company_domain if company_domain else 'Not available'}

Follow the exact structure provided in your system prompt. Begin now."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            research_content = response.choices[0].message.content.strip()
            logger.info(f"Successfully researched {company_name}")
            return research_content
            
        except Exception as e:
            logger.error(f"Error researching company {company_name}: {e}")
            return None

    def generate_strategic_recommendations(self, company_name: str, research_content: str) -> Optional[str]:
        """Generate executive-level strategic recommendations based on research."""
        logger.info(f"Generating strategic recommendations for: {company_name}")
        
        system_prompt = f"""You are a master business strategist, expert at writing reports for important executives. Think from first principles and come up with a high level strategy to improve {company_name}'s standing in the industry. 

Based on the provided analysis, create a comprehensive strategic report with the following structure:

# Strategic Analysis: {company_name}

## Executive Summary
Provide a 2-3 sentence high-level summary of the strategic opportunity and recommended direction.

## Industry Position & Competitive Landscape
Analyze the company's current market position, key competitors, and industry dynamics that affect strategic decisions.

## Strategic Recommendations
Provide 3-5 high-impact strategic recommendations that would significantly improve the company's market position. For each recommendation:
- State the recommendation clearly
- Explain the strategic rationale
- Identify key success metrics
- Estimate implementation timeline

## AI Agents: Strategic Priority Assessment
Evaluate whether AI agents should be among the top priorities for this organization:

### Priority Level: [HIGH/MEDIUM/LOW]
Provide clear justification for the priority level based on:
- Current business challenges that AI could address
- Industry adoption trends
- Competitive advantage potential
- ROI potential

### AI Agent Implementation Strategy
If AI agents are recommended, provide:
- Specific use cases most relevant to this company
- Implementation approach (pilot → scale)
- Expected business impact and metrics
- Integration considerations with existing systems
- Change management requirements

## Implementation Roadmap
Provide a high-level 12-18 month roadmap prioritizing the most critical strategic initiatives.

## Risk Assessment & Mitigation
Identify key risks to strategy execution and mitigation approaches.

Use professional executive language, data-driven insights, and actionable recommendations. Keep the total length around 800-1000 words."""

        user_prompt = f"""Based on the following research analysis of {company_name}, generate strategic recommendations:

{research_content}

Create a comprehensive strategic report following the structure provided in your system prompt."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            strategic_content = response.choices[0].message.content.strip()
            logger.info(f"Successfully generated strategic recommendations for {company_name}")
            return strategic_content
            
        except Exception as e:
            logger.error(f"Error generating strategic recommendations for {company_name}: {e}")
            return None 

    def generate_strategic_imperatives_and_agent_recommendations(self, company_name: str, research_content: str) -> tuple[Optional[str], Optional[str]]:
        """Generate strategic imperatives and AI agent recommendations based on research."""
        logger.info(f"Generating strategic imperatives and agent recommendations for: {company_name}")
        
        system_prompt = f"""You are a master business strategist specializing in AI transformation. Based on the company research provided, you will generate strategic imperatives and AI agent recommendations.

Your response must be in this EXACT format:

STRATEGIC_IMPERATIVES:
• [Strategic imperative 1 - one clear, actionable business priority]
• [Strategic imperative 2 - one clear, actionable business priority]

AGENT_RECOMMENDATIONS:
• [AI agent solution 1 that addresses imperative 1 - specific implementation]
• [AI agent solution 2 that addresses imperative 2 - specific implementation]

Requirements:
- Keep each bullet point concise (1-2 sentences maximum)
- Focus on high-impact, actionable priorities
- Make AI agent recommendations specific and implementable
- Ensure agent recommendations directly address the strategic imperatives
- Use professional executive language"""

        user_prompt = f"""Based on the following research analysis of {company_name}, generate strategic imperatives and AI agent recommendations:

{research_content}

Identify the 2 most critical strategic priorities for this company and propose specific AI agent solutions that would address each priority."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse the response to extract strategic imperatives and agent recommendations
            strategic_imperatives = None
            agent_recommendations = None
            
            if "STRATEGIC_IMPERATIVES:" in content and "AGENT_RECOMMENDATIONS:" in content:
                parts = content.split("AGENT_RECOMMENDATIONS:")
                strategic_part = parts[0].replace("STRATEGIC_IMPERATIVES:", "").strip()
                agent_part = parts[1].strip()
                
                strategic_imperatives = strategic_part
                agent_recommendations = agent_part
                
                logger.info(f"Successfully generated strategic imperatives and agent recommendations for {company_name}")
            else:
                logger.warning(f"Response format not as expected for {company_name}")
                
            return strategic_imperatives, agent_recommendations
            
        except Exception as e:
            logger.error(f"Error generating strategic imperatives and agent recommendations for {company_name}: {e}")
            return None, None