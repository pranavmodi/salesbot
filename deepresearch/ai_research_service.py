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
                ],
                timeout=120.0  # Explicit 2-minute timeout
            )
            
            research_content = response.choices[0].message.content.strip()
            logger.info(f"Successfully researched {company_name} ({len(research_content)} characters)")
            return research_content
            
        except Exception as e:
            logger.error(f"Error researching company {company_name}: {type(e).__name__}: {e}")
            # Return a fallback response to prevent complete failure
            return f"Research timeout or error for {company_name}. Please try again later."

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
                },
                timeout=120.0  # Explicit 2-minute timeout
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
        
        # Add AI agent recommendations section with proper HTML
        html_parts.append('<div class="recommendations-section">')
        html_parts.append('<h2><span class="emoji">🤖</span> AI Agent Recommendations</h2>')
        html_parts.append(f'<p>{data["ai_agent_recommendations"]["introduction"]}</p>')
        
        # Create grid layout for priority recommendations
        html_parts.append('<div class="recommendations-grid">')
        for i, priority in enumerate(data["ai_agent_recommendations"]["priorities"], 1):
            html_parts.append('<div class="priority-card">')
            html_parts.append(f'<div class="priority-title"><span class="emoji">🎯</span> Priority {i}: {priority["title"]}</div>')
            html_parts.append(f'<div style="margin: 10px 0;"><strong>Use Case:</strong> {priority["use_case"]}</div>')
            html_parts.append(f'<div style="margin: 10px 0;"><strong>Business Impact:</strong> {priority["business_impact"]}</div>')
            html_parts.append('</div>')
        html_parts.append('</div>')
        html_parts.append('</div>')
        
        # Add expected business impact section with proper HTML
        html_parts.append('<div class="impact-section">')
        html_parts.append('<h2>Expected Business Impact</h2>')
        html_parts.append('<p>Implementation of these AI agent solutions can deliver:</p>')
        html_parts.append('<ul class="impact-list">')
        for impact in data["expected_business_impact"]:
            html_parts.append(f'<li>{impact}</li>')
        html_parts.append('</ul>')
        html_parts.append('</div>')
        
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
                ],
                timeout=120.0  # Explicit 2-minute timeout
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

Create a company-specific executive summary that includes:
1. Company background and what they do (2-3 sentences)
2. Operating landscape/market context  
3. Current state of play and strategic positioning
4. Two bullet points showing how AI agents can solve their key strategic imperatives

Make it specific to the company, not generic. Use the company's actual business model, industry, and situation.
Avoid generic phrases like "Based on comprehensive market analysis" or "competitive intelligence."
Write in a professional, executive tone suitable for a board presentation.

Format:
"[Company] operates as a [specific business model] in the [specific industry/market], serving [customer base] through [key channels/approach]. The company faces [specific market conditions/challenges] while positioned to capitalize on [specific opportunities]. Our analysis identifies critical strategic imperatives that can [specific outcomes for this company].

• **Strategic Imperative 1**: [Brief description of how AI agents can solve their first key business problem]
• **Strategic Imperative 2**: [Brief description of how AI agents can solve their second key business problem]"
"""

        user_prompt = f"""Based on this company research, write a company-specific executive summary:

Company: {company_name}

Research Content:
{research_content}

Write a professional executive summary that captures this specific company's background, operating landscape, and strategic situation, followed by two bullet points showing how AI agents can address their key strategic imperatives."""

        try:
            logger.info(f"Making OpenAI API call for {company_name} executive summary...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                timeout=120.0  # Explicit 2-minute timeout
            )
            
            executive_summary = response.choices[0].message.content.strip()
            logger.info(f"Successfully generated executive summary for {company_name} ({len(executive_summary)} characters)")
            return executive_summary
            
        except Exception as e:
            logger.error(f"Error generating executive summary for company {company_name}: {type(e).__name__}: {e}")
            return None

    def generate_executive_summary_with_imperatives(self, company_name: str, basic_research: str, strategic_content: str) -> Optional[str]:
        """Generate executive summary with bullet points that match the actual strategic imperatives using structured outputs."""
        logger.info(f"Generating executive summary with imperatives for: {company_name}")
        
        # Extract strategic imperative titles from the strategic content
        import re
        imperative_matches = re.findall(r'### Strategic Imperative \d+: (.+?)(?=\n|$)', strategic_content)
        
        if len(imperative_matches) < 2:
            # Fallback to the original method if we can't extract imperatives
            return self.generate_executive_summary(company_name, basic_research)
        
        # Define JSON schema for structured executive summary
        response_schema = {
            "type": "object",
            "properties": {
                "company_background": {
                    "type": "string",
                    "description": "4-5 sentences covering what the company does, business model, industry position, market context, current challenges, and strategic positioning"
                },
                "transition_statement": {
                    "type": "string",
                    "description": "One sentence introducing the strategic imperatives that follow, explaining what AI agents can deliver for this company"
                },
                "strategic_imperatives": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Exact strategic imperative title from the report"
                            },
                            "ai_impact": {
                                "type": "string",
                                "description": "One concise sentence describing the AI agent solution and its quantified business impact"
                            }
                        },
                        "required": ["title", "ai_impact"],
                        "additionalProperties": False
                    },
                    "minItems": 2,
                    "maxItems": 2
                }
            },
            "required": ["company_background", "transition_statement", "strategic_imperatives"],
            "additionalProperties": False
        }

        system_prompt = f"""You are a McKinsey senior partner writing an executive summary for a strategic analysis report.

Create a company-specific executive summary with:
1. Company background: 4-5 comprehensive sentences covering:
   - What the company does and their business model
   - Industry position and market context
   - Current challenges and competitive landscape
   - Strategic positioning and growth stage
   
2. Transition statement: One sentence introducing the strategic imperatives, explaining what AI agents can specifically deliver for this company's situation

3. Two strategic imperatives with concise AI impact statements that match these EXACT titles:
   - "{imperative_matches[0]}" 
   - "{imperative_matches[1]}"

For each imperative, provide only ONE sentence that captures the core AI agent solution and its quantified business impact.

Make it specific to the company, not generic. Use the company's actual business model, industry, and situation.
Avoid generic phrases like "Based on comprehensive market analysis" or "competitive intelligence."
Write in a professional, executive tone suitable for a board presentation.

You must return your response in the exact JSON format specified in the schema."""

        user_prompt = f"""Based on this company research and strategic analysis, generate a structured executive summary:

Company: {company_name}

Basic Research:
{basic_research}

Strategic Analysis:
{strategic_content[:1000]}...

Return a JSON response with:
- company_background: 4-5 detailed sentences about the company's business, market position, challenges, and strategy
- transition_statement: One sentence introducing what AI agents can deliver for this specific company
- strategic_imperatives: Two items with exact titles and ONE concise sentence each about AI impact"""

        try:
            logger.info(f"Making OpenAI API call for {company_name} executive summary with structured outputs...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "executive_summary",
                        "schema": response_schema,
                        "strict": True
                    }
                },
                timeout=120.0  # Explicit 2-minute timeout
            )
            
            # Parse the structured JSON response
            import json
            structured_data = json.loads(response.choices[0].message.content)
            
            # Format the structured data into markdown
            formatted_summary = self._format_structured_executive_summary(structured_data)
            
            logger.info(f"Successfully generated structured executive summary for {company_name} ({len(formatted_summary)} characters)")
            return formatted_summary
            
        except Exception as e:
            logger.error(f"Error generating structured executive summary for company {company_name}: {type(e).__name__}: {e}")
            # Fallback to the original method
            return self.generate_executive_summary(company_name, basic_research)

    def _format_structured_executive_summary(self, data: dict) -> str:
        """Convert structured executive summary data to formatted HTML with links to strategic imperatives."""
        parts = []
        
        # Add company background as paragraph (larger section)
        parts.append(f"<p>{data['company_background']}</p>")
        
        # Add transition statement
        parts.append(f"<p>{data['transition_statement']}</p>")
        
        # Add strategic imperatives as concise HTML list with links
        parts.append("<ul style='margin-top: 15px; padding-left: 0; list-style: none;'>")
        for i, imperative in enumerate(data["strategic_imperatives"], 1):
            # Create anchor link to the strategic imperative section
            imperative_id = f"imperative-{i}"
            parts.append(f"<li style='margin-bottom: 12px; padding-left: 0;'><span style='color: #0066cc; font-weight: bold;'>•</span> <a href=\"#{imperative_id}\" style='color: #0066cc; text-decoration: none; font-weight: bold;'>{imperative['title']}</a>: {imperative['ai_impact']}</li>")
        parts.append("</ul>")
        
        return "\n".join(parts)