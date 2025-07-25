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
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_KEY"),
            timeout=120.0  # 2 minute timeout for API calls
        )
        self.model = os.getenv("OPENAI_MODEL", "o3")
        logger.info("AIResearchService initialized with 2-minute timeout")

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
            logger.info(f"Making OpenAI API call for {company_name} research...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            research_content = response.choices[0].message.content.strip()
            logger.info(f"Successfully researched {company_name} ({len(research_content)} characters)")
            return research_content
            
        except Exception as e:
            logger.error(f"Error researching company {company_name}: {type(e).__name__}: {e}")
            return None

    def generate_strategic_recommendations(self, company_name: str, research_content: str) -> Optional[str]:
        """Generate executive-level strategic recommendations based on research using structured outputs."""
        logger.info(f"Generating strategic recommendations for: {company_name} with structured outputs")
        
        # Define JSON schema for structured output
        response_schema = {
            "type": "object",
            "properties": {
                "introduction": {
                    "type": "string",
                    "description": "Opening statement about the analysis"
                },
                "strategic_imperatives": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Clear, action-oriented imperative title"
                            },
                            "context": {
                                "type": "string",
                                "description": "1-2 concise sentences explaining the current challenge/opportunity"
                            },
                            "ai_agent_opportunity": {
                                "type": "string",
                                "description": "2-3 detailed paragraphs explaining how AI agents solve this problem"
                            },
                            "expected_impact": {
                                "type": "string",
                                "description": "Quantifiable business outcome with specific metrics"
                            }
                        },
                        "required": ["title", "context", "ai_agent_opportunity", "expected_impact"],
                        "additionalProperties": False
                    },
                    "minItems": 2,
                    "maxItems": 2
                },
                "ai_agent_recommendations": {
                    "type": "object",
                    "properties": {
                        "introduction": {
                            "type": "string",
                            "description": "Introduction to the recommendations"
                        },
                        "priorities": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {
                                        "type": "string",
                                        "description": "Specific AI agent application title"
                                    },
                                    "use_case": {
                                        "type": "string",
                                        "description": "Concrete business application with specific details"
                                    },
                                    "business_impact": {
                                        "type": "string",
                                        "description": "Expected ROI/efficiency gain with numbers"
                                    }
                                },
                                "required": ["title", "use_case", "business_impact"],
                                "additionalProperties": False
                            },
                            "minItems": 2,
                            "maxItems": 2
                        }
                    },
                    "required": ["introduction", "priorities"],
                    "additionalProperties": False
                },
                "expected_business_impact": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "description": "Specific metric/improvement with percentage/dollar amounts or competitive advantage"
                    },
                    "minItems": 3,
                    "maxItems": 3
                }
            },
            "required": ["introduction", "strategic_imperatives", "ai_agent_recommendations", "expected_business_impact"],
            "additionalProperties": False
        }

        system_prompt = f"""You are a McKinsey senior partner writing a strategic brief for {company_name}'s executive team. Create a crisp, data-driven analysis that identifies their key strategic imperatives and explains how AI agents can radically transform their business to achieve competitive advantage.

Focus on how AI agents can solve fundamental problems, automate complex workflows, and create unfair advantages that competitors cannot easily replicate. Be specific about agent capabilities, data integration, and measurable business impact.

For each AI Agent Opportunity section, think like a technology visionary explaining how AI can radically transform the business:
- Describe the current manual/inefficient process that's holding them back
- Explain the specific AI agent capabilities that solve this (data processing, automation, decision-making)
- Detail the technical implementation (what data sources, what workflows, what learning mechanisms)
- Emphasize how this creates a competitive moat that others can't easily copy
- Use concrete examples of what the AI agents would actually do day-to-day

You must return your response in the exact JSON format specified in the schema. Write detailed, professional content for each section.

Guidelines:
- Introduction: Start with "Based on our analysis of {company_name}'s market position, competitive landscape, and operational context, we have identified the following strategic imperatives:"
- Strategic Imperatives: Exactly 2 imperatives with clear titles, context, detailed AI agent opportunities (2-3 paragraphs), and quantifiable expected impact
- AI Agent Recommendations: Introduction and exactly 2 priority recommendations with specific use cases and business impact metrics
- Expected Business Impact: Exactly 3 specific improvements with numbers/percentages or competitive advantages

Keep content professional, data-driven, and specific to AI agent applications. Total length should be 400-500 words."""

        user_prompt = f"""Based on the following research analysis of {company_name}, generate strategic recommendations in the required JSON format:

{research_content}

Return a complete JSON response following the exact schema structure."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "strategic_recommendations",
                        "schema": response_schema,
                        "strict": True
                    }
                }
            )
            
            # Parse the structured JSON response
            import json
            structured_data = json.loads(response.choices[0].message.content)
            
            # Convert structured data to formatted HTML/markdown
            formatted_content = self._format_structured_recommendations(structured_data)
            
            logger.info(f"Successfully generated structured strategic recommendations for {company_name}")
            return formatted_content
            
        except Exception as e:
            logger.error(f"Error generating strategic recommendations for {company_name}: {e}")
            return None 

    def _format_structured_recommendations(self, data: dict) -> str:
        """Convert structured JSON data to formatted HTML/markdown for the report."""
        html_parts = []
        
        # Add introduction
        html_parts.append(data["introduction"])
        html_parts.append("")
        
        # Add strategic imperatives
        for i, imperative in enumerate(data["strategic_imperatives"], 1):
            html_parts.append(f"### Strategic Imperative {i}: {imperative['title']}")
            html_parts.append("")
            html_parts.append(f"**📋 Context:** {imperative['context']}")
            html_parts.append("")
            html_parts.append(f"**🚀 AI Agent Opportunity:**")
            html_parts.append(imperative['ai_agent_opportunity'])
            html_parts.append("")
            html_parts.append(f"**💰 Expected Impact:** {imperative['expected_impact']}")
            html_parts.append("")
        
        # Add AI agent recommendations section
        html_parts.append("## 🤖 AI Agent Recommendations")
        html_parts.append("")
        html_parts.append(data["ai_agent_recommendations"]["introduction"])
        html_parts.append("")
        
        for i, priority in enumerate(data["ai_agent_recommendations"]["priorities"], 1):
            html_parts.append(f"**Priority {i}:** {priority['title']}")
            html_parts.append("")
            html_parts.append(f"- **Use Case:** {priority['use_case']}")
            html_parts.append(f"- **Business Impact:** {priority['business_impact']}")
            html_parts.append("")
        
        # Add expected business impact
        html_parts.append("## Expected Business Impact")
        html_parts.append("")
        html_parts.append("Implementation of these AI agent solutions can deliver:")
        html_parts.append("")
        for impact in data["expected_business_impact"]:
            html_parts.append(f"- {impact}")
        
        return "\n".join(html_parts)

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

    def generate_executive_summary(self, company_name: str, research_content: str) -> Optional[str]:
        """Generate a company-specific executive summary with background and operating landscape."""
        logger.info(f"Generating executive summary for: {company_name}")
        
        system_prompt = """You are a McKinsey senior partner writing an executive summary for a strategic analysis report. 

Create a concise, company-specific executive summary (2-3 sentences) that includes:
1. Company background and what they do
2. Operating landscape/market context  
3. Current state of play and strategic positioning

Make it specific to the company, not generic. Use the company's actual business model, industry, and situation.
Avoid generic phrases like "Based on comprehensive market analysis" or "competitive intelligence."
Write in a professional, executive tone suitable for a board presentation.

Example style:
"[Company] operates as a [specific business model] in the [specific industry/market], serving [customer base] through [key channels/approach]. The company faces [specific market conditions/challenges] while positioned to capitalize on [specific opportunities]. Our analysis identifies critical strategic imperatives that can [specific outcomes for this company]."
"""

        user_prompt = f"""Based on this company research, write a company-specific executive summary:

Company: {company_name}

Research Content:
{research_content}

Write a professional executive summary that captures this specific company's background, operating landscape, and strategic situation."""

        try:
            logger.info(f"Making OpenAI API call for {company_name} executive summary...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            executive_summary = response.choices[0].message.content.strip()
            logger.info(f"Successfully generated executive summary for {company_name} ({len(executive_summary)} characters)")
            return executive_summary
            
        except Exception as e:
            logger.error(f"Error generating executive summary for company {company_name}: {type(e).__name__}: {e}")
            return None