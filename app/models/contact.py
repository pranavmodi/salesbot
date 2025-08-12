from typing import List, Dict, Optional
from flask import current_app
from app.tenant import current_tenant_id
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import os
import logging

class Contact:
    """Contact model for managing lead data from PostgreSQL database."""
    
    def __init__(self, data: Dict):
        self.first_name = data.get('first_name', '') or data.get('First Name', '')
        self.last_name = data.get('last_name', '') or data.get('Last Name', '')
        self.full_name = data.get('full_name', '') or data.get('Full Name', '') or f"{self.first_name} {self.last_name}".strip()
        self.email = data.get('email', '') or data.get('Work Email', '')
        self.company = data.get('company_name', '') or data.get('Company Name', '')
        self.company_id = data.get('company_id')  # Foreign key to companies table
        self.job_title = data.get('job_title', '') or data.get('Job Title', '')
        self.location = data.get('location', '') or data.get('Location', '')
        self.linkedin_profile = data.get('linkedin_profile', '') or data.get('LinkedIn Profile', '')
        self.company_domain = data.get('company_domain', '') or data.get('Company Domain', '')
        self.raw_data = data

    @property
    def initials(self) -> str:
        """Get contact initials for avatar display."""
        if self.first_name:
            return self.first_name[0].upper()
        return '?'

    @property
    def display_name(self) -> str:
        """Get display name for the contact."""
        # Construct name from first_name and last_name to avoid corrupted full_name data
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        elif self.full_name and self.full_name != self.company:
            # Only use full_name if it's different from company name
            return self.full_name
        else:
            return 'Unknown'

    @staticmethod
    def _get_db_engine():
        """Get shared database engine."""
        try:
            from app.database import get_shared_engine
            return get_shared_engine()
        except Exception as e:
            if hasattr(current_app, 'logger'):
                current_app.logger.error(f"Error getting shared database engine: {e}")
            else:
                print(f"Error getting shared database engine: {e}")
            return None

    @classmethod
    def load_all(cls) -> List['Contact']:
        """Load all contacts from PostgreSQL database."""
        contacts = []
        engine = cls._get_db_engine()
        if not engine:
            return contacts
        tenant_id = current_tenant_id()
        if not tenant_id:
            current_app.logger.warning("Tenant not resolved in Contact.load_all; returning empty list")
            return contacts
            
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT email, first_name, last_name, full_name, job_title, 
                           company_name, company_domain, linkedin_profile, location, 
                           phone, linkedin_message, company_id, created_at, updated_at
                    FROM contacts 
                    WHERE tenant_id = :tenant_id
                    ORDER BY created_at DESC
                """), {"tenant_id": tenant_id})
                
                for row in result:
                    contact_data = dict(row._mapping)
                    contacts.append(cls(contact_data))
                    
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error loading contacts from database: {e}")
        except Exception as e:
            current_app.logger.error(f"Unexpected error loading contacts: {e}")
            
        return contacts

    @classmethod
    def get_paginated(cls, page: int = 1, per_page: int = 10) -> Dict:
        """Get paginated contacts from PostgreSQL database."""
        contacts = []
        total = 0
        engine = cls._get_db_engine()
        
        if not engine:
            return {
                'contacts': [],
                'current_page': page,
                'total_pages': 0,
                'per_page': per_page,
                'total_contacts': 0
            }
        tenant_id = current_tenant_id()
        if not tenant_id:
            current_app.logger.warning("Tenant not resolved in Contact.get_paginated; returning empty page")
            return {
                'contacts': [],
                'current_page': page,
                'total_pages': 0,
                'per_page': per_page,
                'total_contacts': 0
            }
            
        try:
            with engine.connect() as conn:
                # Get total count
                count_result = conn.execute(text("SELECT COUNT(*) FROM contacts WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
                total = count_result.scalar()
                
                # Get paginated results
                offset = (page - 1) * per_page
                result = conn.execute(text("""
                    SELECT email, first_name, last_name, full_name, job_title, 
                           company_name, company_domain, linkedin_profile, location, 
                           phone, linkedin_message, company_id, created_at, updated_at
                    FROM contacts 
                    WHERE tenant_id = :tenant_id
                    ORDER BY created_at DESC
                    LIMIT :limit OFFSET :offset
                """), {"limit": per_page, "offset": offset, "tenant_id": tenant_id})
                
                for row in result:
                    contact_data = dict(row._mapping)
                    contacts.append(cls(contact_data))
                    
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error getting paginated contacts: {e}")
        except Exception as e:
            current_app.logger.error(f"Unexpected error getting paginated contacts: {e}")
        
        total_pages = (total + per_page - 1) // per_page
        
        return {
            'contacts': contacts,
            'current_page': page,
            'total_pages': total_pages,
            'per_page': per_page,
            'total_contacts': total
        }

    @classmethod
    def search(cls, query: str) -> List['Contact']:
        """Search contacts by name, email, or company in PostgreSQL database."""
        contacts = []
        engine = cls._get_db_engine()
        if not engine:
            return contacts
        tenant_id = current_tenant_id()
        if not tenant_id:
            current_app.logger.warning("Tenant not resolved in Contact.search; returning empty list")
            return contacts
            
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT email, first_name, last_name, full_name, job_title, 
                           company_name, company_domain, linkedin_profile, location, 
                           phone, linkedin_message, company_id, created_at, updated_at
                    FROM contacts 
                    WHERE tenant_id = :tenant_id AND (
                       first_name ILIKE :search OR last_name ILIKE :search 
                       OR full_name ILIKE :search OR company_name ILIKE :search 
                       OR email ILIKE :search OR job_title ILIKE :search)
                    ORDER BY created_at DESC
                    LIMIT 50
                """), {"search": f"%{query}%", "tenant_id": tenant_id})
                
                for row in result:
                    contact_data = dict(row._mapping)
                    contacts.append(cls(contact_data))
                    
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error searching contacts: {e}")
        except Exception as e:
            current_app.logger.error(f"Unexpected error searching contacts: {e}")
            
        return contacts

    @classmethod
    def get_contact_campaigns(cls, contact_email: str) -> List[Dict]:
        """Get all campaigns that a contact belongs to."""
        engine = cls._get_db_engine()
        if not engine:
            return []
        tenant_id = current_tenant_id()
        if not tenant_id:
            current_app.logger.warning("Tenant not resolved in Contact.get_contact_campaigns; returning empty list")
            return []
            
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT c.*, cc.status as contact_status, cc.added_at, cc.updated_at as status_updated_at
                    FROM campaigns c
                    JOIN campaign_contacts cc ON c.id = cc.campaign_id
                    WHERE cc.contact_email = :contact_email AND c.tenant_id = :tenant_id
                    ORDER BY cc.added_at DESC
                """), {"contact_email": contact_email, "tenant_id": tenant_id})
                
                campaigns = []
                for row in result:
                    campaign_data = dict(row._mapping)
                    campaigns.append(campaign_data)
                
                return campaigns
                    
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error getting contact campaigns: {e}")
        except Exception as e:
            current_app.logger.error(f"Unexpected error getting contact campaigns: {e}")
            
        return []

    @classmethod
    def get_by_email(cls, email: str) -> Optional['Contact']:
        """Get a contact by email address."""
        engine = cls._get_db_engine()
        if not engine:
            return None
        tenant_id = current_tenant_id()
        if not tenant_id:
            current_app.logger.warning("Tenant not resolved in Contact.get_by_email; returning None")
            return None
            
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT email, first_name, last_name, full_name, job_title, 
                           company_name, company_domain, linkedin_profile, location, 
                           phone, linkedin_message, company_id, created_at, updated_at
                    FROM contacts 
                    WHERE tenant_id = :tenant_id AND LOWER(email) = LOWER(:email)
                    LIMIT 1
                """), {"email": email, "tenant_id": tenant_id})
                
                row = result.fetchone()
                if row:
                    contact_data = dict(row._mapping)
                    return cls(contact_data)
                    
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error getting contact by email: {e}")
        except Exception as e:
            current_app.logger.error(f"Unexpected error getting contact by email: {e}")
            
        return None

    @classmethod
    def get_by_id(cls, contact_id: int) -> Optional['Contact']:
        """Get a contact by ID - Note: contacts table uses email as primary key."""
        current_app.logger.warning("get_by_id called but contacts table uses email as primary key")
        return None

    @classmethod
    def get_contacts_not_in_campaign(cls, campaign_id: int, limit: int = 100) -> List['Contact']:
        """Get contacts that are not yet part of a specific campaign."""
        engine = cls._get_db_engine()
        if not engine:
            return []
        tenant_id = current_tenant_id()
        if not tenant_id:
            current_app.logger.warning("Tenant not resolved in Contact.get_contacts_not_in_campaign; returning empty list")
            return []
            
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT c.email, c.first_name, c.last_name, c.full_name, c.job_title, 
                           c.company_name, c.company_domain, c.linkedin_profile, c.location, 
                           c.phone, c.linkedin_message, c.company_id, c.created_at, c.updated_at
                    FROM contacts c
                    LEFT JOIN campaign_contacts cc ON c.email = cc.contact_email AND cc.campaign_id = :campaign_id
                    WHERE cc.contact_email IS NULL AND c.tenant_id = :tenant_id
                    ORDER BY c.created_at DESC
                    LIMIT :limit
                """), {"campaign_id": campaign_id, "limit": limit, "tenant_id": tenant_id})
                
                contacts = []
                for row in result:
                    contact_data = dict(row._mapping)
                    contacts.append(cls(contact_data))
                
                return contacts
                    
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error getting contacts not in campaign: {e}")
        except Exception as e:
            current_app.logger.error(f"Unexpected error getting contacts not in campaign: {e}")
            
        return []

    def to_dict(self) -> Dict:
        """Convert contact to dictionary for JSON serialization."""
        return {
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'email': self.email,
            'company': self.company,
            'company_id': self.company_id,
            'job_title': self.job_title,
            'location': self.location,
            'linkedin_profile': self.linkedin_profile,
            'company_domain': self.company_domain,
            'initials': self.initials,
            'display_name': self.display_name
        } 