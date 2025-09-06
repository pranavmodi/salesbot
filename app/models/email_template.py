"""
Email Template Configuration Models
Highly configurable email composition system for cold outreach
"""

from typing import List, Dict, Optional, Any
from flask import current_app
from app.tenant import current_tenant_id
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import json
import logging
import enum
import os

logger = logging.getLogger(__name__)

class MessageFramework(enum.Enum):
    AIDA = "AIDA"  # Attention, Interest, Desire, Action
    PAS = "PAS"    # Problem, Agitation, Solution
    PROBLEM_SOLUTION = "PROBLEM_SOLUTION"
    STORYTELLING = "STORYTELLING"
    DIRECT = "DIRECT"
    CONSULTATIVE = "CONSULTATIVE"

class ToneLevel(enum.Enum):
    FORMAL = "FORMAL"
    SEMI_FORMAL = "SEMI_FORMAL"
    CASUAL = "CASUAL"
    CONVERSATIONAL = "CONVERSATIONAL"

class EmailLength(enum.Enum):
    SHORT = "SHORT"      # 50-100 words
    MEDIUM = "MEDIUM"    # 100-200 words  
    LONG = "LONG"        # 200+ words

class CTAType(enum.Enum):
    MEETING = "MEETING"
    DEMO = "DEMO"
    CALL = "CALL"
    TRIAL = "TRIAL"
    DOWNLOAD = "DOWNLOAD"
    WEBSITE = "WEBSITE"
    REPLY = "REPLY"

class EmailTemplate:
    """Main email template configuration"""
    
    def __init__(self, data: Dict):
        self.id = data.get('id')
        self.tenant_id = data.get('tenant_id')
        self.name = data.get('name')
        self.description = data.get('description')
        self.is_active = data.get('is_active', True)
        self.is_default = data.get('is_default', False)
        self.created_at = data.get('created_at')
        self.updated_at = data.get('updated_at')
        
        # Template Structure Configuration
        self.message_framework = self._get_enum_value(MessageFramework, data.get('message_framework'), MessageFramework.DIRECT)
        self.tone_level = self._get_enum_value(ToneLevel, data.get('tone_level'), ToneLevel.SEMI_FORMAL)
        self.email_length = self._get_enum_value(EmailLength, data.get('email_length'), EmailLength.MEDIUM)
        
        # Subject Line Configuration
        self.subject_templates = self._parse_json_field(data.get('subject_templates'), [])
        self.subject_ab_test = data.get('subject_ab_test', False)
        
        # Opening Configuration
        self.opening_style = data.get('opening_style', 'personal')
        self.opening_templates = self._parse_json_field(data.get('opening_templates'), [])
        self.use_personal_connection = data.get('use_personal_connection', True)
        self.reference_company_research = data.get('reference_company_research', True)
        
        # Body Content Configuration  
        self.value_propositions = self._parse_json_field(data.get('value_propositions'), [])
        self.pain_points = self._parse_json_field(data.get('pain_points'), {})
        self.social_proof_elements = self._parse_json_field(data.get('social_proof_elements'), [])
        self.product_details = self._parse_json_field(data.get('product_details'), {})
        
        # Personalization Settings
        self.personalization_fields = self._parse_json_field(data.get('personalization_fields'), [])
        self.industry_customization = self._parse_json_field(data.get('industry_customization'), {})
        self.role_customization = self._parse_json_field(data.get('role_customization'), {})
        
        # Call-to-Action Configuration
        self.cta_type = self._get_enum_value(CTAType, data.get('cta_type'), CTAType.MEETING)
        self.cta_templates = self._parse_json_field(data.get('cta_templates'), [])
        self.meeting_duration_options = self._parse_json_field(data.get('meeting_duration_options'), [15, 30])
        self.calendar_booking_url = data.get('calendar_booking_url')
        self.urgency_elements = self._parse_json_field(data.get('urgency_elements'), [])
        
        # Closing & Signature
        self.closing_templates = self._parse_json_field(data.get('closing_templates'), [])
        self.signature_template = data.get('signature_template')
        self.include_unsubscribe = data.get('include_unsubscribe', True)
        
        # Compliance & Legal
        self.gdpr_compliance_text = data.get('gdpr_compliance_text')
        self.legal_disclaimers = self._parse_json_field(data.get('legal_disclaimers'), [])
        self.industry_compliance = self._parse_json_field(data.get('industry_compliance'), {})
        
        # Sender Configuration
        self.sender_name = data.get('sender_name')
        self.sender_title = data.get('sender_title')
        self.sender_company = data.get('sender_company')
        self.sender_contact_info = self._parse_json_field(data.get('sender_contact_info'), {})
        self.sender_personal_touch = data.get('sender_personal_touch')
        
        # A/B Testing Configuration
        self.enable_ab_testing = data.get('enable_ab_testing', False)
        self.ab_test_elements = self._parse_json_field(data.get('ab_test_elements'), [])
        
        # Follow-up Configuration  
        self.follow_up_sequence = self._parse_json_field(data.get('follow_up_sequence'), [])
        self.max_follow_ups = data.get('max_follow_ups', 3)
        self.follow_up_intervals = self._parse_json_field(data.get('follow_up_intervals'), [3, 7, 14])
        
        # Performance Tracking
        self.usage_count = data.get('usage_count', 0)
        self.success_metrics = self._parse_json_field(data.get('success_metrics'), {})

    def _get_enum_value(self, enum_class, value, default):
        """Safely get enum value"""
        if not value:
            return default
        try:
            return enum_class(value)
        except ValueError:
            return default

    def _get_enum_string_value(self, value):
        """Safely get enum value as string - handles both string and enum objects"""
        if value is None:
            return None
        # If it's already a string, return it
        if isinstance(value, str):
            return value
        # If it's an enum object, get its value
        if hasattr(value, 'value'):
            return value.value
        # Fallback
        return str(value)

    def _parse_json_field(self, value, default):
        """Safely parse JSON field"""
        if value is None:
            return default
        if isinstance(value, (dict, list)):
            return value
        try:
            return json.loads(value) if isinstance(value, str) else default
        except (json.JSONDecodeError, TypeError):
            return default

    @staticmethod
    def _get_db_engine():
        """Get database engine using the shared connection"""
        try:
            from app.database import get_shared_engine
            return get_shared_engine()
        except Exception as e:
            logger.error(f"Failed to get database engine: {e}")
            # Fallback to direct connection
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                raise Exception("DATABASE_URL not configured")
            return create_engine(database_url)

    @classmethod
    def get_by_id(cls, template_id: int, tenant_id: str = None) -> Optional['EmailTemplate']:
        """Get email template by ID"""
        if not tenant_id:
            tenant_id = current_tenant_id()
        
        try:
            engine = cls._get_db_engine()
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT * FROM email_templates 
                    WHERE id = :template_id AND tenant_id = :tenant_id
                """), {
                    'template_id': template_id,
                    'tenant_id': tenant_id
                })
                
                row = result.fetchone()
                if row:
                    return cls(dict(row._mapping))
                return None
                
        except Exception as e:
            logger.error(f"Error fetching email template {template_id}: {e}")
            return None

    @classmethod
    def get_all_for_tenant(cls, tenant_id: str = None) -> List['EmailTemplate']:
        """Get all email templates for a tenant"""
        if not tenant_id:
            tenant_id = current_tenant_id()
        
        try:
            engine = cls._get_db_engine()
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT * FROM email_templates 
                    WHERE tenant_id = :tenant_id
                    ORDER BY is_default DESC, name ASC
                """), {'tenant_id': tenant_id})
                
                templates = []
                for row in result:
                    templates.append(cls(dict(row._mapping)))
                return templates
                
        except Exception as e:
            logger.error(f"Error fetching email templates for tenant {tenant_id}: {e}")
            return []

    @classmethod
    def get_default_for_tenant(cls, tenant_id: str = None) -> Optional['EmailTemplate']:
        """Get the default email template for a tenant"""
        if not tenant_id:
            tenant_id = current_tenant_id()
        
        try:
            engine = cls._get_db_engine()
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT * FROM email_templates 
                    WHERE tenant_id = :tenant_id AND is_default = true AND is_active = true
                    ORDER BY created_at DESC
                    LIMIT 1
                """), {'tenant_id': tenant_id})
                
                row = result.fetchone()
                if row:
                    return cls(dict(row._mapping))
                return None
                
        except Exception as e:
            logger.error(f"Error fetching default email template for tenant {tenant_id}: {e}")
            return None

    def save(self) -> bool:
        """Save the email template to the database"""
        try:
            engine = self._get_db_engine()
            with engine.connect() as conn:
                with conn.begin():
                    if self.id:
                        # Update existing template
                        conn.execute(text("""
                            UPDATE email_templates SET
                                name = :name,
                                description = :description,
                                is_active = :is_active,
                                is_default = :is_default,
                                updated_at = :updated_at,
                                message_framework = :message_framework,
                                tone_level = :tone_level,
                                email_length = :email_length,
                                subject_templates = :subject_templates,
                                subject_ab_test = :subject_ab_test,
                                opening_style = :opening_style,
                                opening_templates = :opening_templates,
                                use_personal_connection = :use_personal_connection,
                                reference_company_research = :reference_company_research,
                                value_propositions = :value_propositions,
                                pain_points = :pain_points,
                                social_proof_elements = :social_proof_elements,
                                product_details = :product_details,
                                personalization_fields = :personalization_fields,
                                industry_customization = :industry_customization,
                                role_customization = :role_customization,
                                cta_type = :cta_type,
                                cta_templates = :cta_templates,
                                meeting_duration_options = :meeting_duration_options,
                                calendar_booking_url = :calendar_booking_url,
                                urgency_elements = :urgency_elements,
                                closing_templates = :closing_templates,
                                signature_template = :signature_template,
                                include_unsubscribe = :include_unsubscribe,
                                gdpr_compliance_text = :gdpr_compliance_text,
                                legal_disclaimers = :legal_disclaimers,
                                industry_compliance = :industry_compliance,
                                sender_name = :sender_name,
                                sender_title = :sender_title,
                                sender_company = :sender_company,
                                sender_contact_info = :sender_contact_info,
                                sender_personal_touch = :sender_personal_touch,
                                enable_ab_testing = :enable_ab_testing,
                                ab_test_elements = :ab_test_elements,
                                follow_up_sequence = :follow_up_sequence,
                                max_follow_ups = :max_follow_ups,
                                follow_up_intervals = :follow_up_intervals
                            WHERE id = :id AND tenant_id = :tenant_id
                        """), self._get_update_params())
                    else:
                        # Insert new template
                        result = conn.execute(text("""
                            INSERT INTO email_templates (
                                tenant_id, name, description, is_active, is_default, created_at, updated_at,
                                message_framework, tone_level, email_length, subject_templates, subject_ab_test,
                                opening_style, opening_templates, use_personal_connection, reference_company_research,
                                value_propositions, pain_points, social_proof_elements, product_details,
                                personalization_fields, industry_customization, role_customization,
                                cta_type, cta_templates, meeting_duration_options, calendar_booking_url, urgency_elements,
                                closing_templates, signature_template, include_unsubscribe,
                                gdpr_compliance_text, legal_disclaimers, industry_compliance,
                                sender_name, sender_title, sender_company, sender_contact_info, sender_personal_touch,
                                enable_ab_testing, ab_test_elements, follow_up_sequence, max_follow_ups, follow_up_intervals,
                                usage_count, success_metrics
                            ) VALUES (
                                :tenant_id, :name, :description, :is_active, :is_default, :created_at, :updated_at,
                                :message_framework, :tone_level, :email_length, :subject_templates, :subject_ab_test,
                                :opening_style, :opening_templates, :use_personal_connection, :reference_company_research,
                                :value_propositions, :pain_points, :social_proof_elements, :product_details,
                                :personalization_fields, :industry_customization, :role_customization,
                                :cta_type, :cta_templates, :meeting_duration_options, :calendar_booking_url, :urgency_elements,
                                :closing_templates, :signature_template, :include_unsubscribe,
                                :gdpr_compliance_text, :legal_disclaimers, :industry_compliance,
                                :sender_name, :sender_title, :sender_company, :sender_contact_info, :sender_personal_touch,
                                :enable_ab_testing, :ab_test_elements, :follow_up_sequence, :max_follow_ups, :follow_up_intervals,
                                :usage_count, :success_metrics
                            ) RETURNING id
                        """), self._get_insert_params())
                        
                        new_id = result.fetchone()[0]
                        self.id = new_id
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving email template: {e}")
            return False

    def _get_insert_params(self) -> Dict:
        """Get parameters for insert query"""
        now = datetime.utcnow()
        return {
            'tenant_id': self.tenant_id,
            'name': self.name,
            'description': self.description,
            'is_active': self.is_active,
            'is_default': self.is_default,
            'created_at': now,
            'updated_at': now,
            'message_framework': self._get_enum_string_value(self.message_framework),
            'tone_level': self._get_enum_string_value(self.tone_level),
            'email_length': self._get_enum_string_value(self.email_length),
            'subject_templates': json.dumps(self.subject_templates),
            'subject_ab_test': self.subject_ab_test,
            'opening_style': self.opening_style,
            'opening_templates': json.dumps(self.opening_templates),
            'use_personal_connection': self.use_personal_connection,
            'reference_company_research': self.reference_company_research,
            'value_propositions': json.dumps(self.value_propositions),
            'pain_points': json.dumps(self.pain_points),
            'social_proof_elements': json.dumps(self.social_proof_elements),
            'product_details': json.dumps(self.product_details),
            'personalization_fields': json.dumps(self.personalization_fields),
            'industry_customization': json.dumps(self.industry_customization),
            'role_customization': json.dumps(self.role_customization),
            'cta_type': self._get_enum_string_value(self.cta_type),
            'cta_templates': json.dumps(self.cta_templates),
            'meeting_duration_options': json.dumps(self.meeting_duration_options),
            'calendar_booking_url': self.calendar_booking_url,
            'urgency_elements': json.dumps(self.urgency_elements),
            'closing_templates': json.dumps(self.closing_templates),
            'signature_template': self.signature_template,
            'include_unsubscribe': self.include_unsubscribe,
            'gdpr_compliance_text': self.gdpr_compliance_text,
            'legal_disclaimers': json.dumps(self.legal_disclaimers),
            'industry_compliance': json.dumps(self.industry_compliance),
            'sender_name': self.sender_name,
            'sender_title': self.sender_title,
            'sender_company': self.sender_company,
            'sender_contact_info': json.dumps(self.sender_contact_info),
            'sender_personal_touch': self.sender_personal_touch,
            'enable_ab_testing': self.enable_ab_testing,
            'ab_test_elements': json.dumps(self.ab_test_elements),
            'follow_up_sequence': json.dumps(self.follow_up_sequence),
            'max_follow_ups': self.max_follow_ups,
            'follow_up_intervals': json.dumps(self.follow_up_intervals),
            'usage_count': self.usage_count or 0,
            'success_metrics': json.dumps(self.success_metrics)
        }

    def _get_update_params(self) -> Dict:
        """Get parameters for update query"""
        params = self._get_insert_params()
        params['id'] = self.id
        params['updated_at'] = datetime.utcnow()
        return params

class EmailTemplateUsage:
    """Track template usage and performance"""
    
    def __init__(self, data: Dict):
        self.id = data.get('id')
        self.template_id = data.get('template_id')
        self.tenant_id = data.get('tenant_id')
        self.contact_email = data.get('contact_email')
        self.generated_subject = data.get('generated_subject')
        self.generated_body = data.get('generated_body')
        self.personalization_data = self._parse_json_field(data.get('personalization_data'), {})
        self.sent_at = data.get('sent_at')
        self.opened_at = data.get('opened_at')
        self.clicked_at = data.get('clicked_at')
        self.replied_at = data.get('replied_at')
        self.bounced_at = data.get('bounced_at')
        self.ab_test_variant = data.get('ab_test_variant')
        self.created_at = data.get('created_at')

    def _parse_json_field(self, value, default):
        """Safely parse JSON field"""
        if value is None:
            return default
        if isinstance(value, (dict, list)):
            return value
        try:
            return json.loads(value) if isinstance(value, str) else default
        except (json.JSONDecodeError, TypeError):
            return default

    @staticmethod
    def _get_db_engine():
        """Get database engine using the shared connection"""
        try:
            from app.database import get_shared_engine
            return get_shared_engine()
        except Exception as e:
            logger.error(f"Failed to get database engine: {e}")
            # Fallback to direct connection
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                raise Exception("DATABASE_URL not configured")
            return create_engine(database_url)

    def save(self) -> bool:
        """Save the usage record to the database"""
        try:
            engine = self._get_db_engine()
            with engine.connect() as conn:
                with conn.begin():
                    result = conn.execute(text("""
                        INSERT INTO email_template_usage (
                            template_id, tenant_id, contact_email, generated_subject, generated_body,
                            personalization_data, ab_test_variant, created_at
                        ) VALUES (
                            :template_id, :tenant_id, :contact_email, :generated_subject, :generated_body,
                            :personalization_data, :ab_test_variant, :created_at
                        ) RETURNING id
                    """), {
                        'template_id': self.template_id,
                        'tenant_id': self.tenant_id,
                        'contact_email': self.contact_email,
                        'generated_subject': self.generated_subject,
                        'generated_body': self.generated_body,
                        'personalization_data': json.dumps(self.personalization_data),
                        'ab_test_variant': self.ab_test_variant,
                        'created_at': datetime.utcnow()
                    })
                    
                    new_id = result.fetchone()[0]
                    self.id = new_id
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving email template usage: {e}")
            return False