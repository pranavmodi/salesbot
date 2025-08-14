#!/usr/bin/env python3
"""
Content-Based Email Composer

Combines deep company research with content marketing to create compelling,
personalized emails that share valuable content while maintaining relevance
to the recipient's business context.
"""

import logging
import re
import openai
import os
from typing import Dict, Optional, List
from datetime import datetime
try:
    from app.models.tenant_settings import TenantSettings
    from app.tenant import current_tenant_id
    from app.services.link_tracking_service import LinkTrackingService
    from app.models.company import Company
except ImportError:
    # Handle case where app context is not available
    TenantSettings = None
    current_tenant_id = None
    LinkTrackingService = None
    Company = None

logger = logging.getLogger(__name__)

# ---- Context about the sender and content ----
SENDER_INFO = """
Pranav Modi is the founder of Possible Minds and a seasoned product manager and AI engineer.
The team at Possible Minds specializes in generating bespoke AI agents for enterprises across various industries.

Our AI agent solutions:
- are custom-built for specific business workflows and challenges
- integrate seamlessly with existing enterprise systems
- deploy rapidly with minimal operational disruption
- deliver measurable ROI through automation and enhanced capabilities

We've created impactful AI projects including healthcare AI chatbots, customer service automation, and specialized business process agents.
One notable example is our deployment at Precise Imaging, a diagnostic imaging company, where our healthcare AI agent helps reduce appointment no-shows and improves patient engagement.
We're actively working with enterprises across healthcare, finance, and service industries on transformative AI agent implementations.
"""

class ContentBasedEmailComposer:
    """
    Composes emails that combine company research insights with content marketing.
    Creates personalized, value-driven emails that position content as genuinely
    helpful resources rather than sales pitches.
    """
    
    def __init__(self):
        self.composer_name = "Content-Based Marketing"
        self.composer_type = "content_based"
        logger.info(f"Initialized {self.composer_name} composer")
    
    def _get_openai_api_key(self) -> Optional[str]:
        """Get OpenAI API key from tenant settings or environment."""
        try:
            # Try to get from current tenant settings first
            if TenantSettings and current_tenant_id:
                tenant_id = current_tenant_id()
                if tenant_id:
                    tenant_settings = TenantSettings()
                    settings = tenant_settings.get_tenant_settings(tenant_id)
                    api_key = settings.get('openai_api_key')
                    if api_key:
                        return api_key
            
            # Fallback to environment variable
            return os.getenv('OPENAI_API_KEY')
        except Exception as e:
            logger.warning(f"Could not get OpenAI API key from tenant settings: {e}")
            return os.getenv('OPENAI_API_KEY')
    
    def compose_email(self, lead: Dict, content_url: str, content_description: str, 
                     content_type: str = "blog_post", call_to_action: str = "learn_more",
                     calendar_url: str = None, extra_context: str = None, 
                     include_tracking: bool = True, campaign_id: int = None) -> Dict:
        """
        Compose a content-based marketing email using company research insights.
        
        Args:
            lead: Contact and company information dictionary
            content_url: URL of the content to share
            content_description: Description of the content's value and key points
            content_type: Type of content (blog_post, whitepaper, case_study, etc.)
            call_to_action: Desired action (learn_more, schedule_demo, download_resource)
            calendar_url: Optional calendar URL for meetings
            extra_context: Additional context for email personalization
            include_tracking: Whether to include email tracking
            
        Returns:
            Dictionary containing subject and body of the composed email
        """
        try:
            logger.info(f"Composing content-based email for {lead.get('name', 'Unknown')} at {lead.get('company_name', 'Unknown Company')}")
            
            # Extract key information
            contact_name = lead.get('name', 'there')
            contact_first_name = contact_name.split()[0] if contact_name != 'there' else 'there'
            company_name = lead.get('company_name', 'your company')
            contact_role = lead.get('position', 'team member')
            
            # Get company research insights
            company_research = self._extract_company_insights(lead)
            
            # Generate personalized email using OpenAI
            email_content = self._generate_email_with_openai(
                lead, content_url, content_description, content_type, 
                call_to_action, company_research, calendar_url, extra_context
            )
            
            logger.info(f"OpenAI generation result: {'Success' if email_content else 'Failed'}")
            
            if not email_content:
                # Fallback to template-based generation
                logger.warning("OpenAI generation failed, using fallback method")
                content_analysis = self._analyze_content_relevance(
                    content_description, content_type, company_research, contact_role
                )
                
                subject = self._generate_subject_line(
                    contact_first_name, company_name, content_analysis, content_type
                )
                
                body = self._generate_email_body(
                    lead, content_url, content_description, content_analysis,
                    call_to_action, calendar_url, extra_context
                )
            else:
                subject = email_content.get('subject', f"Valuable insights for {company_name}")
                body = email_content.get('body', f"Hi {contact_first_name},\n\nI thought you might find this relevant: {content_url}")
            
            # Add link tracking if available
            try:
                if LinkTrackingService and campaign_id:
                    # Get company_id for tracking
                    company_id = None
                    if Company and lead.get('company_name'):
                        companies = Company.get_companies_by_name(lead.get('company_name'))
                        if companies:
                            company_id = companies[0].id
                    
                    # Wrap links with tracking URLs
                    body, tracking_ids = LinkTrackingService.wrap_links_in_email(
                        email_body=body,
                        campaign_id=campaign_id,
                        company_id=company_id,
                        contact_email=lead.get('email')
                    )
                    logger.info(f"Wrapped {len(tracking_ids)} links for tracking in content-based email")
            except Exception as e:
                logger.warning(f"Failed to wrap links for tracking: {e}")
            
            # Add tracking if requested
            if include_tracking:
                body = self._add_tracking_pixel(body)
            
            result = {
                'subject': subject,
                'body': body,
                'composer_type': self.composer_type,
                'content_url': content_url,
                'content_type': content_type
            }
            
            logger.info(f"Successfully composed content-based email for {contact_name}")
            return result
            
        except Exception as e:
            logger.error(f"Error composing content-based email: {e}")
            return {
                'subject': f"Insights I thought you'd find relevant",
                'body': f"Hi {contact_first_name},\n\nI'm Pranav Modi, founder of Possible Minds. I recently published some insights that I thought might be relevant to your work at {company_name}.\n\nYou can check it out here: {content_url}\n\n{content_description}\n\nWould love to hear your thoughts if it resonates with what you're seeing in your industry.\n\nBest regards,\n\nPranav Modi\nFounder, Possible Minds",
                'composer_type': self.composer_type,
                'error': str(e)
            }
    
    def _generate_email_with_openai(self, lead: Dict, content_url: str, content_description: str,
                                   content_type: str, call_to_action: str, company_research: Dict,
                                   calendar_url: str = None, extra_context: str = None) -> Optional[Dict]:
        """Generate email content using OpenAI API."""
        try:
            api_key = self._get_openai_api_key()
            if not api_key:
                logger.error("No OpenAI API key available")
                return None
            
            # Initialize OpenAI client
            client = openai.OpenAI(api_key=api_key)
            
            # Extract key information
            contact_name = lead.get('name', 'there')
            contact_first_name = contact_name.split()[0] if contact_name != 'there' else 'there'
            company_name = lead.get('company_name', 'your company')
            contact_role = lead.get('position', 'team member')
            
            # Build company research context
            research_context = self._build_research_context(lead, company_research)
            
            # Create system prompt
            system_prompt = self._create_system_prompt(content_type, call_to_action)
            
            # Create user prompt with all context
            user_prompt = self._create_user_prompt(
                contact_name, contact_first_name, company_name, contact_role,
                content_url, content_description, research_context, 
                calendar_url, extra_context
            )
            
            logger.info(f"Generating content-based email for {contact_name} at {company_name}")
            
            # Make OpenAI API call
            response = client.chat.completions.create(
                model="gpt-4o",  # Using GPT-4o as specified in requirements
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            # Parse response
            generated_content = response.choices[0].message.content.strip()
            return self._parse_openai_response(generated_content)
            
        except Exception as e:
            logger.error(f"Error generating email with OpenAI: {e}")
            return None
    
    def _build_research_context(self, lead: Dict, company_research: Dict) -> str:
        """Build a comprehensive research context string."""
        context_parts = []
        
        # Add company basic info
        company_name = lead.get('company_name', '')
        if company_name:
            context_parts.append(f"Company: {company_name}")
        
        # Add industry if available
        if company_research.get('industry'):
            context_parts.append(f"Industry: {company_research['industry']}")
        
        # Add company stage
        if company_research.get('stage'):
            context_parts.append(f"Company stage: {company_research['stage']}")
        
        # Add research insights from various fields
        research_fields = [
            'company_research',
            'llm_research_step_1_basic',
            'llm_research_step_2_strategic',
            'llm_research_step_3_report'
        ]
        
        research_content = []
        for field in research_fields:
            if field in lead and lead[field]:
                # Take first 500 characters to avoid overwhelming the prompt
                content = lead[field][:500]
                if len(lead[field]) > 500:
                    content += "..."
                research_content.append(content)
        
        if research_content:
            context_parts.append(f"Research insights: {' '.join(research_content)}")
        
        return "\n".join(context_parts)
    
    def _create_system_prompt(self, content_type: str, call_to_action: str) -> str:
        """Create the system prompt for OpenAI."""
        cta_guidance = {
            'learn_more': 'encourage them to read the content and share thoughts',
            'schedule_demo': 'invite them to discuss how the insights apply to their situation',
            'download_resource': 'encourage them to access the resource and get their perspective',
            'register_event': 'invite them to join the event given their role and company focus'
        }
        
        content_type_guidance = {
            'blog_post': 'thought leadership piece with industry insights',
            'whitepaper': 'in-depth research document with strategic implications',
            'case_study': 'success story from a similar company or situation',
            'webinar': 'educational session with actionable insights',
            'product_update': 'new feature or capability that could benefit their business'
        }
        
        return f"""You are Pranav Modi, founder of Possible Minds, writing a personalized email to share content you've written and published. Your goal is to share valuable insights while building authentic relationships.

SENDER CONTEXT:
{SENDER_INFO.strip()}

CONTENT YOU'RE SHARING: {content_type} - {content_type_guidance.get(content_type, 'valuable business content')}
DESIRED OUTCOME: {cta_guidance.get(call_to_action, 'encourage engagement with the content')}

WRITING GUIDELINES:
1. Write as the author of the content, sharing your own insights and research
2. Include a brief, natural introduction of yourself and Possible Minds (2-3 sentences max)
3. Use the company research to make specific, relevant connections to their business
4. Position your content as insights from your experience working with similar companies
5. Keep tone professional but warm and conversational - write as a peer, not a salesperson
6. Make the relevance clear by connecting your content to their specific situation
7. Include a natural, appropriate call-to-action that invites dialogue
8. End with a professional signature

EMAIL STRUCTURE:
- Subject line (one compelling line that feels personal, not marketing-y)
- Personal greeting using their name
- Brief, natural self-introduction (who you are and what Possible Minds does)
- Context about why you're sharing this content (based on their company research)
- Content introduction - frame it as your own work/insights
- Specific connection to their company/role (using research insights)
- Natural call-to-action that invites response or discussion
- Professional closing with your signature

RESPONSE FORMAT:
Return the email in this exact format:
SUBJECT: [subject line]

BODY:
[email body]

IMPORTANT: Frame the content as your own work that you've published. Make it feel like a founder reaching out to share insights from their experience, not a marketing email."""

    def _create_user_prompt(self, contact_name: str, contact_first_name: str, 
                          company_name: str, contact_role: str, content_url: str,
                          content_description: str, research_context: str,
                          calendar_url: str = None, extra_context: str = None) -> str:
        """Create the user prompt with all context."""
        prompt_parts = [
            f"RECIPIENT DETAILS:",
            f"Name: {contact_name}",
            f"Role: {contact_role}",
            f"Company: {company_name}",
            "",
            f"YOUR PUBLISHED CONTENT TO SHARE:",
            f"URL: {content_url}",
            f"Description: {content_description}",
            f"Note: This is content YOU (Pranav Modi) have written and published on your website/blog.",
            "",
            f"COMPANY RESEARCH CONTEXT:",
            research_context or "Limited research available",
        ]
        
        if calendar_url:
            prompt_parts.extend([
                "",
                f"CALENDAR LINK (if relevant for CTA): {calendar_url}"
            ])
        
        if extra_context:
            prompt_parts.extend([
                "",
                f"ADDITIONAL CONTEXT:",
                extra_context
            ])
        
        prompt_parts.extend([
            "",
            "Generate a personalized email where you (Pranav Modi) are sharing content YOU wrote and published. Connect the content value to their specific business context using the research insights. Include a brief introduction of yourself and Possible Minds. Make it feel like a founder reaching out to share their own insights and expertise, not a sales pitch."
        ])
        
        return "\n".join(prompt_parts)
    
    def _parse_openai_response(self, response: str) -> Dict:
        """Parse the OpenAI response into subject and body."""
        try:
            # Split response into subject and body
            if "SUBJECT:" in response and "BODY:" in response:
                parts = response.split("BODY:", 1)
                subject_part = parts[0].replace("SUBJECT:", "").strip()
                body_part = parts[1].strip()
                
                return {
                    'subject': subject_part,
                    'body': body_part
                }
            else:
                # Fallback: treat entire response as body and generate simple subject
                lines = response.strip().split('\n')
                if len(lines) > 0:
                    # First line as subject if it looks like one, otherwise generate
                    first_line = lines[0].strip()
                    if len(first_line) < 80 and not first_line.lower().startswith('hi '):
                        return {
                            'subject': first_line,
                            'body': '\n'.join(lines[1:]).strip()
                        }
                
                return {
                    'subject': "Thought you'd find this interesting",
                    'body': response.strip()
                }
        except Exception as e:
            logger.error(f"Error parsing OpenAI response: {e}")
            return {
                'subject': "Valuable content for your team",
                'body': response.strip()
            }

    def _extract_company_insights(self, lead: Dict) -> Dict:
        """Extract and structure relevant company research insights."""
        insights = {
            'company_name': lead.get('company_name', ''),
            'industry': '',
            'stage': '',
            'challenges': [],
            'opportunities': [],
            'recent_developments': [],
            'strategic_focus': []
        }
        
        # Extract from various research fields
        research_fields = [
            'company_research',
            'llm_research_step_1_basic',
            'llm_research_step_2_strategic', 
            'llm_research_step_3_report'
        ]
        
        combined_research = ""
        for field in research_fields:
            if field in lead and lead[field]:
                combined_research += f" {lead[field]}"
        
        if combined_research:
            # Extract key themes using simple keyword matching
            research_lower = combined_research.lower()
            
            # Industry indicators
            industries = ['healthcare', 'fintech', 'saas', 'ecommerce', 'manufacturing', 'education', 'ai', 'biotech']
            for industry in industries:
                if industry in research_lower:
                    insights['industry'] = industry
                    break
            
            # Company stage indicators
            if any(term in research_lower for term in ['startup', 'early stage', 'seed']):
                insights['stage'] = 'early_stage'
            elif any(term in research_lower for term in ['series a', 'series b', 'growth']):
                insights['stage'] = 'growth'
            elif any(term in research_lower for term in ['enterprise', 'established', 'mature']):
                insights['stage'] = 'enterprise'
            
            # Challenge indicators
            challenge_keywords = ['scaling', 'growth', 'efficiency', 'automation', 'integration', 'compliance']
            insights['challenges'] = [kw for kw in challenge_keywords if kw in research_lower]
            
        return insights
    
    def _analyze_content_relevance(self, content_description: str, content_type: str, 
                                 company_insights: Dict, contact_role: str) -> Dict:
        """Analyze how the content relates to the company's situation."""
        analysis = {
            'relevance_score': 0.5,  # Default moderate relevance
            'key_connections': [],
            'value_propositions': [],
            'personalization_angle': ''
        }
        
        content_lower = content_description.lower()
        
        # Score relevance based on company insights
        relevance_factors = []
        
        # Industry alignment
        if company_insights['industry'] and company_insights['industry'] in content_lower:
            relevance_factors.append("industry_match")
            analysis['key_connections'].append(f"Directly relevant to {company_insights['industry']} industry")
        
        # Stage alignment
        if company_insights['stage']:
            stage_keywords = {
                'early_stage': ['startup', 'scaling', 'growth', 'founding'],
                'growth': ['scaling', 'expansion', 'optimization', 'team building'],
                'enterprise': ['enterprise', 'transformation', 'efficiency', 'compliance']
            }
            if any(kw in content_lower for kw in stage_keywords.get(company_insights['stage'], [])):
                relevance_factors.append("stage_match")
                analysis['key_connections'].append(f"Addresses {company_insights['stage']} company challenges")
        
        # Challenge alignment
        for challenge in company_insights['challenges']:
            if challenge in content_lower:
                relevance_factors.append("challenge_match")
                analysis['key_connections'].append(f"Addresses {challenge} challenges")
        
        # Role relevance
        role_keywords = {
            'cto': ['technology', 'technical', 'engineering', 'architecture', 'development'],
            'ceo': ['strategy', 'growth', 'leadership', 'vision', 'scaling'],
            'vp': ['operations', 'efficiency', 'management', 'optimization'],
            'director': ['team', 'process', 'workflow', 'productivity']
        }
        
        contact_role_lower = contact_role.lower()
        for role, keywords in role_keywords.items():
            if role in contact_role_lower and any(kw in content_lower for kw in keywords):
                relevance_factors.append("role_match")
                analysis['key_connections'].append(f"Relevant to {contact_role} responsibilities")
        
        # Calculate relevance score
        analysis['relevance_score'] = min(1.0, 0.3 + (len(relevance_factors) * 0.2))
        
        # Generate value propositions
        content_value_terms = ['insights', 'strategies', 'best practices', 'solutions', 'framework', 'guide']
        analysis['value_propositions'] = [term for term in content_value_terms if term in content_lower]
        
        # Determine personalization angle
        if 'industry_match' in relevance_factors:
            analysis['personalization_angle'] = 'industry_expertise'
        elif 'stage_match' in relevance_factors:
            analysis['personalization_angle'] = 'growth_stage'
        elif 'challenge_match' in relevance_factors:
            analysis['personalization_angle'] = 'problem_solving'
        else:
            analysis['personalization_angle'] = 'general_value'
        
        return analysis
    
    def _generate_subject_line(self, contact_name: str, company_name: str, 
                             content_analysis: Dict, content_type: str) -> str:
        """Generate a compelling, personalized subject line."""
        
        # Subject line templates based on relevance and personalization angle
        templates = {
            'industry_expertise': [
                f"Industry insights for {company_name}",
                f"{contact_name}, thought you'd find this relevant",
                f"Latest trends affecting {company_name}"
            ],
            'growth_stage': [
                f"Scaling insights for {company_name}",
                f"{contact_name}, relevant to your growth stage",
                f"Growth strategies for companies like {company_name}"
            ],
            'problem_solving': [
                f"Solutions for {company_name}'s challenges",
                f"{contact_name}, this addresses your current focus",
                f"Addressing key challenges at {company_name}"
            ],
            'general_value': [
                f"Valuable insights for {contact_name}",
                f"Thought this might interest you, {contact_name}",
                f"Relevant content for {company_name}"
            ]
        }
        
        angle = content_analysis.get('personalization_angle', 'general_value')
        relevance_score = content_analysis.get('relevance_score', 0.5)
        
        # Choose template based on relevance score
        template_options = templates.get(angle, templates['general_value'])
        
        if relevance_score > 0.7:
            return template_options[0]  # Most specific
        elif relevance_score > 0.5:
            return template_options[1]  # Moderately specific
        else:
            return template_options[2]  # General but still personalized
    
    def _generate_email_body(self, lead: Dict, content_url: str, content_description: str,
                           content_analysis: Dict, call_to_action: str, 
                           calendar_url: str = None, extra_context: str = None) -> str:
        """Generate the email body with personalized content."""
        
        contact_name = lead.get('name', 'there')
        contact_first_name = contact_name.split()[0] if contact_name != 'there' else 'there'
        company_name = lead.get('company_name', 'your company')
        contact_role = lead.get('position', 'your role')
        
        # Build email sections
        opener = self._generate_opener(contact_first_name, company_name, lead, content_analysis)
        context_bridge = self._generate_context_bridge(company_name, contact_role, content_analysis)
        content_intro = self._generate_content_introduction(content_description, content_analysis)
        value_prop = self._generate_value_proposition(company_name, content_analysis)
        cta = self._generate_call_to_action(call_to_action, calendar_url, content_url)
        signature = self._generate_signature()
        
        # Combine sections
        body_parts = [opener, context_bridge, content_intro, value_prop, cta, signature]
        
        # Add extra context if provided
        if extra_context:
            body_parts.insert(-2, f"\n{extra_context}\n")
        
        return "\n\n".join(filter(None, body_parts))
    
    def _generate_opener(self, contact_name: str, company_name: str, lead: Dict, 
                        content_analysis: Dict) -> str:
        """Generate a personalized opening line."""
        
        # Try to use specific research insights
        research_fields = ['company_research', 'llm_research_step_1_basic']
        company_insight = ""
        
        for field in research_fields:
            if field in lead and lead[field]:
                # Extract a relevant snippet (first sentence or key point)
                research_text = lead[field][:200]
                if '.' in research_text:
                    company_insight = research_text.split('.')[0] + '.'
                break
        
        if company_insight and len(company_insight) > 20:
            return f"Hi {contact_name},\n\nI was reading about {company_name}'s work in the industry and found something I thought you'd find valuable."
        else:
            # Fallback to general but warm opener
            return f"Hi {contact_name},\n\nHope you're doing well at {company_name}. I came across something that I thought might be relevant to your work."
    
    def _generate_context_bridge(self, company_name: str, contact_role: str, 
                               content_analysis: Dict) -> str:
        """Create a bridge between company context and content relevance."""
        
        connections = content_analysis.get('key_connections', [])
        
        if connections:
            primary_connection = connections[0]
            return f"Given {company_name}'s focus and your role as {contact_role}, I thought this would be particularly relevant since it {primary_connection.lower()}."
        else:
            return f"As someone in a {contact_role} role at {company_name}, I thought you might find this content valuable for your strategic planning."
    
    def _generate_content_introduction(self, content_description: str, 
                                     content_analysis: Dict) -> str:
        """Introduce the content with compelling highlights."""
        
        value_props = content_analysis.get('value_propositions', [])
        
        intro = f"I wanted to share this with you:\n\n{content_description}"
        
        if value_props:
            intro += f"\n\nWhat I found particularly valuable are the {', '.join(value_props[:2])} that could be directly applicable to your situation."
        
        return intro
    
    def _generate_value_proposition(self, company_name: str, content_analysis: Dict) -> str:
        """Generate company-specific value proposition."""
        
        relevance_score = content_analysis.get('relevance_score', 0.5)
        
        if relevance_score > 0.7:
            return f"The approaches outlined could be especially relevant for {company_name} given your current market position and growth trajectory."
        elif relevance_score > 0.5:
            return f"I think some of the strategies discussed could be adapted for {company_name}'s specific context."
        else:
            return f"While it's written for a general audience, I believe the core principles could be valuable for {company_name}."
    
    def _generate_call_to_action(self, cta_type: str, calendar_url: str = None, 
                               content_url: str = None) -> str:
        """Generate appropriate call-to-action based on type."""
        
        cta_templates = {
            'learn_more': f"You can read the full content here: {content_url}\n\nWould love to hear your thoughts if any of it resonates with your experience.",
            'schedule_demo': f"Check it out here: {content_url}\n\nIf you'd like to discuss how these concepts might apply to your specific situation, I'd be happy to chat." + (f" Feel free to grab time on my calendar: {calendar_url}" if calendar_url else ""),
            'download_resource': f"You can access it here: {content_url}\n\nI'd be curious to get your perspective on how this aligns with what you're seeing in your industry.",
            'register_event': f"You can learn more and register here: {content_url}\n\nI think the content would be particularly relevant given your role and company focus."
        }
        
        return cta_templates.get(cta_type, cta_templates['learn_more'])
    
    def _generate_signature(self) -> str:
        """Generate professional signature."""
        return "Best regards,\n\nPranav Modi\nFounder, Possible Minds\nAI Agent Solutions for Enterprise\n\nP.S. No pressure to respond - just thought you'd find the insights relevant to your work!"
    
    def _add_tracking_pixel(self, body: str) -> str:
        """Add tracking pixel to email body."""
        tracking_pixel = f"\n\n<!-- Email tracking pixel -->\n<img src=\"{self._get_tracking_url()}\" width=\"1\" height=\"1\" style=\"display:none;\" />"
        return body + tracking_pixel
    
    def _get_tracking_url(self) -> str:
        """Generate tracking URL for email analytics."""
        # This should integrate with your tracking system
        return "https://your-tracking-domain.com/track/email.gif"
    
    def get_composer_info(self) -> Dict:
        """Return information about this composer."""
        return {
            'name': self.composer_name,
            'type': self.composer_type,
            'description': 'Combines deep company research with content marketing for personalized, value-driven outreach',
            'required_fields': ['content_url', 'content_description'],
            'optional_fields': ['content_type', 'call_to_action'],
            'content_types': ['blog_post', 'whitepaper', 'case_study', 'webinar', 'product_update'],
            'cta_options': ['learn_more', 'schedule_demo', 'download_resource', 'register_event']
        }