"""
Configurable Email Template Service for Cold Outreach
Handles highly customizable email generation based on templates and contact data
"""

import random
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import openai
from app.models.email_template import (
    EmailTemplate, EmailTemplateUsage, 
    MessageFramework, ToneLevel, EmailLength, CTAType
)
from app.models.contact import Contact
from app.models.company import Company
from app.tenant import current_tenant_id
import json
import logging

logger = logging.getLogger(__name__)

class EmailTemplateService:
    """Service for managing and generating configurable email templates"""
    
    def __init__(self):
        self.openai_client = openai.OpenAI()
    
    def get_templates_for_tenant(self, tenant_id: str) -> List[EmailTemplate]:
        """Get all email templates for a tenant"""
        return EmailTemplate.get_all_for_tenant(tenant_id)
    
    def get_default_template(self, tenant_id: str) -> Optional[EmailTemplate]:
        """Get the default email template for a tenant"""
        return EmailTemplate.get_default_for_tenant(tenant_id)
    
    def create_default_template(self, tenant_id: str) -> EmailTemplate:
        """Create a default email template with sensible defaults"""
        template_data = {
            'tenant_id': tenant_id,
            'name': "Default Cold Outreach",
            'description': "Standard cold outreach template for general use",
            'is_default': True,
            'message_framework': MessageFramework.DIRECT.value,
            'tone_level': ToneLevel.SEMI_FORMAL.value,
            'email_length': EmailLength.MEDIUM.value,
            
            # Subject lines
            'subject_templates': [
                "Quick question about {company}",
                "{first_name}, thought you'd find this interesting",
                "Helping {company} with {pain_point}",
                "5 minutes to discuss {value_prop}?",
                "{first_name} - {company} + {product_name}"
            ],
            
            # Opening templates
            'opening_templates': [
                "Hi {first_name},",
                "Hello {first_name},",
                "{first_name},",
                "Hi {first_name}, hope your week is going well."
            ],
            'opening_style': "personal",
            'use_personal_connection': True,
            'reference_company_research': True,
            
            # Value propositions
            'value_propositions': [
                "We help {industry} companies reduce costs by 30%",
                "Our solution increases {role_focus} efficiency by 40%",
                "Companies like yours see ROI within 90 days"
            ],
            
            # Pain points by industry/role
            'pain_points': {
                "default": ["manual processes", "inefficient workflows", "high costs"],
                "healthcare": ["patient wait times", "administrative burden", "compliance challenges"],
                "finance": ["regulatory compliance", "data silos", "manual reporting"],
                "technology": ["scaling challenges", "integration complexity", "security concerns"]
            },
            
            # Social proof
            'social_proof_elements': [
                "We've helped over 500 companies like {company}",
                "{similar_company} saw 40% improvement in 3 months",
                "Featured in {industry_publication} for innovation"
            ],
            
            # Product details
            'product_details': {
                "name": "Our Solution",
                "description": "AI-powered platform that streamlines operations",
                "key_features": ["Automation", "Analytics", "Integration"]
            },
            
            # Personalization fields
            'personalization_fields': [
                "first_name", "company", "job_title", "industry", "location"
            ],
            
            # CTA configuration
            'cta_type': CTAType.MEETING.value,
            'cta_templates': [
                "Would you be open to a 15-minute chat to explore how this could help {company}?",
                "Could we schedule a brief call to discuss your {pain_point} challenges?",
                "Would you have 15 minutes next week for a quick demo?"
            ],
            'meeting_duration_options': [15, 30],
            
            # Closing templates
            'closing_templates': [
                "Best regards,",
                "Thanks for your time,",
                "Looking forward to connecting,"
            ],
            
            # Sender info (will be customized per user)
            'sender_name': "Sales Team",
            'sender_title': "Account Executive",
            'sender_company': "Your Company",
            
            # Compliance
            'include_unsubscribe': True,
            'gdpr_compliance_text': "You received this email because you may be interested in our services. Reply STOP to unsubscribe."
        }
        
        template = EmailTemplate(template_data)
        if template.save():
            return template
        else:
            raise Exception("Failed to create default template")
    
    def generate_personalized_email(
        self, 
        contact: Contact, 
        template: EmailTemplate,
        demo_config: Optional[Dict] = None,
        ab_test_variant: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a personalized email using the template configuration
        
        Args:
            contact: Contact to send email to
            template: Email template configuration
            demo_config: Demo-specific configuration (tenant_id, campaign, etc.)
            ab_test_variant: Which A/B test variant to use
            
        Returns:
            Dictionary containing subject, body, and metadata
        """
        try:
            # Prepare personalization context
            context = self._build_personalization_context(contact, template, demo_config)
            
            # Select template variants (A/B testing)
            selected_templates = self._select_template_variants(template, ab_test_variant)
            
            # Generate subject line
            subject = self._generate_subject_line(context, selected_templates['subject_templates'])
            
            # Generate email body
            body = self._generate_email_body(contact, template, context, selected_templates)
            
            # Track usage
            self._track_template_usage(template, contact, subject, body, context, ab_test_variant)
            
            return {
                'subject': subject,
                'body': body,
                'template_id': template.id,
                'ab_test_variant': ab_test_variant,
                'personalization_context': context,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error generating personalized email: {str(e)}")
            return {
                'error': str(e),
                'success': False
            }
    
    def _build_personalization_context(
        self, 
        contact: Contact, 
        template: EmailTemplate, 
        demo_config: Optional[Dict]
    ) -> Dict[str, Any]:
        """Build context dictionary for email personalization"""
        
        # Basic contact information
        context = {
            'first_name': contact.first_name or 'there',
            'last_name': contact.last_name or '',
            'full_name': contact.display_name or f"{contact.first_name or ''} {contact.last_name or ''}".strip() or 'there',
            'email': contact.email,
            'job_title': contact.job_title or 'team member',
            'company': contact.company or 'your company',
            'location': contact.location or '',
            'phone': contact.phone or ''
        }
        
        # Company information (if available)
        if hasattr(contact, 'company_obj') and contact.company_obj:
            company = contact.company_obj
            context.update({
                'company_domain': company.domain,
                'company_size': getattr(company, 'employee_count', None),
                'company_industry': getattr(company, 'industry', None)
            })
        
        # Template-specific context
        context.update({
            'product_name': template.product_details.get('name', 'our solution') if template.product_details else 'our solution',
            'sender_name': template.sender_name or 'Sales Team',
            'sender_title': template.sender_title or 'Account Executive',
            'sender_company': template.sender_company or 'Our Company'
        })
        
        # Demo configuration
        if demo_config:
            context.update({
                'demo_url': f"https://getpossibleminds.com/tenants/{demo_config.get('tenant_id', '')}/control-panel?utm_source=email&utm_medium=email&utm_campaign={demo_config.get('campaign', 'cold-outreach')}",
                'tenant_id': demo_config.get('tenant_id', ''),
                'campaign': demo_config.get('campaign', 'cold-outreach')
            })
        
        # Industry and role-specific context
        context.update(self._get_industry_role_context(contact, template))
        
        return context
    
    def _get_industry_role_context(self, contact: Contact, template: EmailTemplate) -> Dict[str, Any]:
        """Get industry and role-specific context for personalization"""
        context = {}
        
        # Determine industry
        industry = None
        if hasattr(contact, 'company_obj') and contact.company_obj:
            industry = getattr(contact.company_obj, 'industry', None)
        
        # Get industry-specific pain points and value props
        if industry and template.industry_customization:
            industry_config = template.industry_customization.get(industry.lower(), {})
            context.update({
                'industry_pain_points': industry_config.get('pain_points', []),
                'industry_value_props': industry_config.get('value_props', [])
            })
        
        # Get role-specific context
        if contact.job_title and template.role_customization:
            role_lower = contact.job_title.lower()
            for role_key, role_config in template.role_customization.items():
                if role_key.lower() in role_lower or role_lower in role_key.lower():
                    context.update({
                        'role_pain_points': role_config.get('pain_points', []),
                        'role_motivations': role_config.get('motivations', []),
                        'role_focus': role_config.get('focus_areas', ['efficiency'])
                    })
                    break
        
        # Select relevant pain point and value prop
        pain_points = template.pain_points or {}
        if industry and industry.lower() in pain_points:
            context['pain_point'] = random.choice(pain_points[industry.lower()])
        elif 'default' in pain_points:
            context['pain_point'] = random.choice(pain_points['default'])
        else:
            context['pain_point'] = 'operational challenges'
        
        # Select value proposition
        if template.value_propositions:
            context['value_prop'] = random.choice(template.value_propositions)
        else:
            context['value_prop'] = 'increased efficiency'
        
        return context
    
    def _select_template_variants(self, template: EmailTemplate, ab_test_variant: Optional[str]) -> Dict[str, Any]:
        """Select appropriate template variants for A/B testing"""
        variants = {
            'subject_templates': template.subject_templates or ["Quick question about {company}"],
            'opening_templates': template.opening_templates or ["Hi {first_name},"],
            'cta_templates': template.cta_templates or ["Would you be open to a brief chat?"],
            'closing_templates': template.closing_templates or ["Best regards,"]
        }
        
        # If A/B testing is enabled and variant specified, select accordingly
        if template.enable_ab_testing and ab_test_variant and template.ab_test_elements:
            # Implement A/B test variant selection logic here
            # For now, use random selection
            pass
        
        return variants
    
    def _generate_subject_line(self, context: Dict[str, Any], subject_templates: List[str]) -> str:
        """Generate personalized subject line"""
        template = random.choice(subject_templates)
        return self._replace_variables(template, context)
    
    def _generate_email_body(
        self, 
        contact: Contact, 
        template: EmailTemplate, 
        context: Dict[str, Any],
        selected_templates: Dict[str, Any]
    ) -> str:
        """Generate the email body using AI with template configuration"""
        
        # Build the prompt for AI generation
        prompt = self._build_email_generation_prompt(contact, template, context, selected_templates)
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert cold email copywriter. Write personalized, engaging cold outreach emails that get responses. Follow the template configuration exactly."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=800
            )
            
            body = response.choices[0].message.content.strip()
            
            # Add compliance footer if required
            if template.include_unsubscribe and template.gdpr_compliance_text:
                body += f"\n\n{template.gdpr_compliance_text}"
            
            return body
            
        except Exception as e:
            logger.error(f"Error generating email with AI: {str(e)}")
            # Fallback to template-based generation
            return self._generate_fallback_email_body(context, selected_templates, template)
    
    def _build_email_generation_prompt(
        self, 
        contact: Contact, 
        template: EmailTemplate, 
        context: Dict[str, Any],
        selected_templates: Dict[str, Any]
    ) -> str:
        """Build the prompt for AI email generation"""
        
        prompt = f"""
Write a personalized cold outreach email with the following specifications:

RECIPIENT:
- Name: {context['first_name']} {context['last_name']}
- Job Title: {context['job_title']}
- Company: {context['company']}
- Email: {context['email']}

TEMPLATE CONFIGURATION:
- Framework: {template.message_framework.value}
- Tone: {template.tone_level.value}
- Length: {template.email_length.value}
- CTA Type: {template.cta_type.value}

OPENING STYLE: {template.opening_style}
- Use one of these openings: {selected_templates['opening_templates']}

VALUE PROPOSITIONS (choose most relevant):
{json.dumps(template.value_propositions, indent=2) if template.value_propositions else 'Focus on efficiency and cost savings'}

PAIN POINTS TO ADDRESS:
{context.get('pain_point', 'operational challenges')}

PRODUCT DETAILS:
{json.dumps(template.product_details, indent=2) if template.product_details else 'AI-powered solution that improves efficiency'}

SOCIAL PROOF ELEMENTS:
{json.dumps(template.social_proof_elements, indent=2) if template.social_proof_elements else 'Proven track record with similar companies'}

CALL-TO-ACTION:
- Type: {template.cta_type.value}
- Use one of: {selected_templates['cta_templates']}
- Meeting duration options: {template.meeting_duration_options}
{f"- Calendar booking URL: {template.calendar_booking_url}" if template.calendar_booking_url else ""}

CLOSING:
- Use one of: {selected_templates['closing_templates']}
- Signature: {template.sender_name}, {template.sender_title}

DEMO CONFIGURATION:
{f"- Include demo URL: {context.get('demo_url', '')}" if context.get('demo_url') else ""}

REQUIREMENTS:
- Be specific and personalized to {context['company']} and {context['job_title']}
- Reference their potential {context['pain_point']} challenges
- Keep the tone {template.tone_level.value.lower().replace('_', ' ')}
- Use {template.message_framework.value.lower().replace('_', ' ')} structure
- Make it {template.email_length.value.lower()} length
- Include a clear {template.cta_type.value.lower()} call-to-action
- Be genuine and avoid overly salesy language
- Focus on value for {context['company']}
"""
        
        return prompt
    
    def _generate_fallback_email_body(
        self, 
        context: Dict[str, Any], 
        selected_templates: Dict[str, Any],
        template: EmailTemplate
    ) -> str:
        """Generate email body using templates as fallback when AI fails"""
        
        opening = self._replace_variables(random.choice(selected_templates['opening_templates']), context)
        
        body_parts = [opening]
        
        # Add personalized intro
        if template.use_personal_connection:
            body_parts.append(f"I came across {context['company']} and was impressed by your work in {context.get('industry', 'your industry')}.")
        
        # Add value proposition
        if template.value_propositions:
            value_prop = self._replace_variables(random.choice(template.value_propositions), context)
            body_parts.append(value_prop)
        
        # Add social proof
        if template.social_proof_elements:
            social_proof = self._replace_variables(random.choice(template.social_proof_elements), context)
            body_parts.append(social_proof)
        
        # Add CTA
        cta = self._replace_variables(random.choice(selected_templates['cta_templates']), context)
        body_parts.append(cta)
        
        # Add closing
        closing = self._replace_variables(random.choice(selected_templates['closing_templates']), context)
        signature = f"{context['sender_name']}\n{context['sender_title']}"
        
        body_parts.extend([closing, signature])
        
        return "\n\n".join(body_parts)
    
    def _replace_variables(self, template: str, context: Dict[str, Any]) -> str:
        """Replace variables in template with context values"""
        result = template
        for key, value in context.items():
            placeholder = "{" + key + "}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))
        return result
    
    def _track_template_usage(
        self,
        template: EmailTemplate,
        contact: Contact,
        subject: str,
        body: str,
        context: Dict[str, Any],
        ab_test_variant: Optional[str]
    ):
        """Track template usage for analytics"""
        usage_data = {
            'template_id': template.id,
            'tenant_id': template.tenant_id,
            'contact_email': contact.email,
            'generated_subject': subject,
            'generated_body': body,
            'personalization_data': context,
            'ab_test_variant': ab_test_variant
        }
        
        usage = EmailTemplateUsage(usage_data)
        usage.save()
        
        # Update template usage count
        template.usage_count = (template.usage_count or 0) + 1
        template.save()
    
    def get_template_analytics(self, template_id: int, tenant_id: str) -> Dict[str, Any]:
        """Get analytics for a specific template"""
        template = EmailTemplate.get_by_id(template_id, tenant_id)
        if not template:
            return {'error': 'Template not found'}
        
        # For now, return basic analytics since we don't have usage tracking implemented yet
        return {
            'template_name': template.name,
            'total_sent': template.usage_count or 0,
            'open_rate': 0.0,  # Placeholder - would need email tracking implementation
            'click_rate': 0.0,  # Placeholder - would need click tracking implementation
            'reply_rate': 0.0,  # Placeholder - would need reply tracking implementation
            'usage_records': template.usage_count or 0
        }