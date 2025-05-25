from typing import List, Dict, Optional
from flask import current_app
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
        """Get database engine from environment."""
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            current_app.logger.error("DATABASE_URL not configured.")
            return None
        try:
            return create_engine(database_url)
        except Exception as e:
            current_app.logger.error(f"Error creating database engine: {e}")
            return None

    @classmethod
    def load_all(cls) -> List['Contact']:
        """Load all contacts from PostgreSQL database."""
        contacts = []
        engine = cls._get_db_engine()
        if not engine:
            return contacts
            
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT email, first_name, last_name, full_name, job_title, 
                           company_name, company_domain, linkedin_profile, location, 
                           phone, linkedin_message, created_at, updated_at
                    FROM contacts 
                    ORDER BY created_at DESC
                """))
                
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
            
        try:
            with engine.connect() as conn:
                # Get total count
                count_result = conn.execute(text("SELECT COUNT(*) FROM contacts"))
                total = count_result.scalar()
                
                # Get paginated results
                offset = (page - 1) * per_page
                result = conn.execute(text("""
                    SELECT email, first_name, last_name, full_name, job_title, 
                           company_name, company_domain, linkedin_profile, location, 
                           phone, linkedin_message, created_at, updated_at
                    FROM contacts 
                    ORDER BY created_at DESC
                    LIMIT :limit OFFSET :offset
                """), {"limit": per_page, "offset": offset})
                
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
            
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT email, first_name, last_name, full_name, job_title, 
                           company_name, company_domain, linkedin_profile, location, 
                           phone, linkedin_message, created_at, updated_at
                    FROM contacts 
                    WHERE first_name ILIKE :search OR last_name ILIKE :search 
                       OR full_name ILIKE :search OR company_name ILIKE :search 
                       OR email ILIKE :search OR job_title ILIKE :search
                    ORDER BY created_at DESC
                    LIMIT 50
                """), {"search": f"%{query}%"})
                
                for row in result:
                    contact_data = dict(row._mapping)
                    contacts.append(cls(contact_data))
                    
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error searching contacts: {e}")
        except Exception as e:
            current_app.logger.error(f"Unexpected error searching contacts: {e}")
            
        return contacts

    def to_dict(self) -> Dict:
        """Convert contact to dictionary for JSON serialization."""
        return {
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'email': self.email,
            'company': self.company,
            'job_title': self.job_title,
            'location': self.location,
            'linkedin_profile': self.linkedin_profile,
            'company_domain': self.company_domain,
            'initials': self.initials,
            'display_name': self.display_name
        } 