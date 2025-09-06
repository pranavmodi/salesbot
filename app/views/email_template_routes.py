"""
Email Template Configuration Routes
API endpoints for managing configurable email templates
"""

from flask import Blueprint, request, jsonify, session, render_template, g
from app.models.email_template import EmailTemplate
from app.models.contact import Contact
from app.services.email_template_service import EmailTemplateService
from app.tenant import current_tenant_id
import logging

logger = logging.getLogger(__name__)

email_template_bp = Blueprint('email_template', __name__)
template_service = EmailTemplateService()

@email_template_bp.route('/api/email-templates', methods=['GET'])
def get_email_templates():
    """Get all email templates for the current tenant"""
    try:
        tenant_id = current_tenant_id()
        if not tenant_id:
            return jsonify({
                'success': False,
                'error': 'Tenant context required'
            }), 400
            
        templates = template_service.get_templates_for_tenant(tenant_id)
        
        template_data = []
        for template in templates:
            template_data.append({
                'id': template.id,
                'name': template.name,
                'description': template.description,
                'is_active': template.is_active,
                'is_default': template.is_default,
                'message_framework': template.message_framework.value if template.message_framework else None,
                'tone_level': template.tone_level.value if template.tone_level else None,
                'email_length': template.email_length.value if template.email_length else None,
                'cta_type': template.cta_type.value if template.cta_type else None,
                'usage_count': template.usage_count or 0,
                'created_at': template.created_at.isoformat() if template.created_at else None
            })
        
        return jsonify({
            'success': True,
            'templates': template_data
        })
    
    except Exception as e:
        logger.error(f"Error fetching email templates: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@email_template_bp.route('/api/email-templates', methods=['POST'])
def create_email_template():
    """Create a new email template"""
    try:
        tenant_id = current_tenant_id()
        if not tenant_id:
            return jsonify({
                'success': False,
                'error': 'Tenant context required'
            }), 400
            
        data = request.get_json()
        
        # Prepare template data
        template_data = {
            'tenant_id': tenant_id,
            'name': data.get('name'),
            'description': data.get('description'),
            'is_active': data.get('is_active', True),
            'is_default': data.get('is_default', False),
            'message_framework': data.get('message_framework'),
            'tone_level': data.get('tone_level'),
            'email_length': data.get('email_length'),
            'subject_templates': data.get('subject_templates', []),
            'subject_ab_test': data.get('subject_ab_test', False),
            'opening_style': data.get('opening_style', 'personal'),
            'opening_templates': data.get('opening_templates', []),
            'use_personal_connection': data.get('use_personal_connection', True),
            'reference_company_research': data.get('reference_company_research', True),
            'value_propositions': data.get('value_propositions', []),
            'pain_points': data.get('pain_points', {}),
            'social_proof_elements': data.get('social_proof_elements', []),
            'product_details': data.get('product_details', {}),
            'personalization_fields': data.get('personalization_fields', []),
            'industry_customization': data.get('industry_customization', {}),
            'role_customization': data.get('role_customization', {}),
            'cta_type': data.get('cta_type'),
            'cta_templates': data.get('cta_templates', []),
            'meeting_duration_options': data.get('meeting_duration_options', [15, 30]),
            'calendar_booking_url': data.get('calendar_booking_url'),
            'urgency_elements': data.get('urgency_elements', []),
            'closing_templates': data.get('closing_templates', []),
            'signature_template': data.get('signature_template'),
            'include_unsubscribe': data.get('include_unsubscribe', True),
            'gdpr_compliance_text': data.get('gdpr_compliance_text'),
            'legal_disclaimers': data.get('legal_disclaimers', []),
            'industry_compliance': data.get('industry_compliance', {}),
            'sender_name': data.get('sender_name'),
            'sender_title': data.get('sender_title'),
            'sender_company': data.get('sender_company'),
            'sender_contact_info': data.get('sender_contact_info', {}),
            'sender_personal_touch': data.get('sender_personal_touch'),
            'enable_ab_testing': data.get('enable_ab_testing', False),
            'ab_test_elements': data.get('ab_test_elements', []),
            'follow_up_sequence': data.get('follow_up_sequence', []),
            'max_follow_ups': data.get('max_follow_ups', 3),
            'follow_up_intervals': data.get('follow_up_intervals', [3, 7, 14])
        }
        
        # Create new template
        template = EmailTemplate(template_data)
        
        # TODO: If this is set as default, unset other defaults
        # This would require updating other templates in the database
        
        if template.save():
            return jsonify({
                'success': True,
                'template_id': template.id,
                'message': 'Email template created successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to save template'
            }), 500
    
    except Exception as e:
        logger.error(f"Error creating email template: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@email_template_bp.route('/api/email-templates/<int:template_id>', methods=['GET'])
def get_email_template(template_id):
    """Get a specific email template"""
    try:
        tenant_id = current_tenant_id()
        if not tenant_id:
            return jsonify({
                'success': False,
                'error': 'Tenant context required'
            }), 400
            
        template = EmailTemplate.get_by_id(template_id, tenant_id)
        
        if not template:
            return jsonify({
                'success': False,
                'error': 'Template not found'
            }), 404
        
        template_data = {
            'id': template.id,
            'name': template.name,
            'description': template.description,
            'is_active': template.is_active,
            'is_default': template.is_default,
            'message_framework': template.message_framework.value if template.message_framework else None,
            'tone_level': template.tone_level.value if template.tone_level else None,
            'email_length': template.email_length.value if template.email_length else None,
            'subject_templates': template.subject_templates or [],
            'subject_ab_test': template.subject_ab_test,
            'opening_style': template.opening_style,
            'opening_templates': template.opening_templates or [],
            'use_personal_connection': template.use_personal_connection,
            'reference_company_research': template.reference_company_research,
            'value_propositions': template.value_propositions or [],
            'pain_points': template.pain_points or {},
            'social_proof_elements': template.social_proof_elements or [],
            'product_details': template.product_details or {},
            'personalization_fields': template.personalization_fields or [],
            'industry_customization': template.industry_customization or {},
            'role_customization': template.role_customization or {},
            'cta_type': template.cta_type.value if template.cta_type else None,
            'cta_templates': template.cta_templates or [],
            'meeting_duration_options': template.meeting_duration_options or [15, 30],
            'calendar_booking_url': template.calendar_booking_url,
            'urgency_elements': template.urgency_elements or [],
            'closing_templates': template.closing_templates or [],
            'signature_template': template.signature_template,
            'include_unsubscribe': template.include_unsubscribe,
            'gdpr_compliance_text': template.gdpr_compliance_text,
            'legal_disclaimers': template.legal_disclaimers or [],
            'industry_compliance': template.industry_compliance or {},
            'sender_name': template.sender_name,
            'sender_title': template.sender_title,
            'sender_company': template.sender_company,
            'sender_contact_info': template.sender_contact_info or {},
            'sender_personal_touch': template.sender_personal_touch,
            'enable_ab_testing': template.enable_ab_testing,
            'ab_test_elements': template.ab_test_elements or [],
            'follow_up_sequence': template.follow_up_sequence or [],
            'max_follow_ups': template.max_follow_ups or 3,
            'follow_up_intervals': template.follow_up_intervals or [3, 7, 14],
            'usage_count': template.usage_count or 0,
            'created_at': template.created_at.isoformat() if template.created_at else None,
            'updated_at': template.updated_at.isoformat() if template.updated_at else None
        }
        
        return jsonify({
            'success': True,
            'template': template_data
        })
    
    except Exception as e:
        logger.error(f"Error fetching email template: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@email_template_bp.route('/api/email-templates/<int:template_id>', methods=['PUT'])
def update_email_template(template_id):
    """Update an existing email template"""
    try:
        tenant_id = current_tenant_id()
        if not tenant_id:
            return jsonify({
                'success': False,
                'error': 'Tenant context required'
            }), 400
            
        template = EmailTemplate.get_by_id(template_id, tenant_id)
        
        if not template:
            return jsonify({
                'success': False,
                'error': 'Template not found'
            }), 404
        
        data = request.get_json()
        
        # Update template fields
        for field in ['name', 'description', 'is_active', 'is_default',
                      'message_framework', 'tone_level', 'email_length',
                      'subject_templates', 'subject_ab_test', 'opening_style',
                      'opening_templates', 'use_personal_connection',
                      'reference_company_research', 'value_propositions',
                      'pain_points', 'social_proof_elements', 'product_details',
                      'personalization_fields', 'industry_customization',
                      'role_customization', 'cta_type', 'cta_templates',
                      'meeting_duration_options', 'calendar_booking_url',
                      'urgency_elements', 'closing_templates', 'signature_template',
                      'include_unsubscribe', 'gdpr_compliance_text',
                      'legal_disclaimers', 'industry_compliance',
                      'sender_name', 'sender_title', 'sender_company',
                      'sender_contact_info', 'sender_personal_touch',
                      'enable_ab_testing', 'ab_test_elements',
                      'follow_up_sequence', 'max_follow_ups', 'follow_up_intervals']:
            
            if field in data:
                setattr(template, field, data[field])
        
        # TODO: If this is set as default, unset other defaults
        # This would require updating other templates in the database
        
        if template.save():
            return jsonify({
                'success': True,
                'message': 'Email template updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to save template'
            }), 500
    
    except Exception as e:
        logger.error(f"Error updating email template: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@email_template_bp.route('/api/compose/email/configurable', methods=['POST'])
def compose_configurable_email():
    """Generate an email using configurable templates"""
    try:
        tenant_id = current_tenant_id()
        if not tenant_id:
            return jsonify({
                'success': False,
                'error': 'Tenant context required'
            }), 400
            
        data = request.get_json()
        
        # Get contact
        contact_email = data.get('contact_email')
        if not contact_email:
            return jsonify({
                'success': False,
                'error': 'Contact email is required'
            }), 400
        
        # Find contact using the Contact model method
        contact = Contact.get_by_email(contact_email)
        
        if not contact:
            return jsonify({
                'success': False,
                'error': 'Contact not found'
            }), 404
        
        # Get template
        template_id = data.get('template_id')
        if template_id:
            template = EmailTemplate.get_by_id(template_id, tenant_id)
            if not template or not template.is_active:
                template = None
        else:
            # Use default template or create one
            template = template_service.get_default_template(tenant_id)
            if not template:
                template = template_service.create_default_template(tenant_id)
        
        if not template:
            return jsonify({
                'success': False,
                'error': 'No active email template found'
            }), 404
        
        # Get demo configuration
        demo_config = data.get('demo_config', {})
        
        # Get A/B test variant
        ab_test_variant = data.get('ab_test_variant')
        
        # Generate personalized email
        result = template_service.generate_personalized_email(
            contact=contact,
            template=template,
            demo_config=demo_config,
            ab_test_variant=ab_test_variant
        )
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error composing configurable email: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@email_template_bp.route('/api/email-templates/<int:template_id>/analytics', methods=['GET'])
def get_template_analytics(template_id):
    """Get analytics for a specific email template"""
    try:
        tenant_id = current_tenant_id()
        if not tenant_id:
            return jsonify({
                'success': False,
                'error': 'Tenant context required'
            }), 400
            
        analytics = template_service.get_template_analytics(template_id, tenant_id)
        
        return jsonify({
            'success': True,
            'analytics': analytics
        })
    
    except Exception as e:
        logger.error(f"Error fetching template analytics: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@email_template_bp.route('/templates')
def email_templates_page():
    """Render the email templates management page"""
    tenant_id = current_tenant_id()
    if not tenant_id:
        return "Tenant context required", 400
    return render_template('email_templates.html')