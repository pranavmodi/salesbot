import csv
from typing import List, Dict, Optional
from flask import current_app

class Contact:
    """Contact model for managing lead data."""
    
    def __init__(self, data: Dict):
        self.first_name = data.get('First Name', '')
        self.last_name = data.get('Last Name', '')
        self.full_name = data.get('Full Name', f"{self.first_name} {self.last_name}".strip())
        self.email = data.get('Work Email', '')
        self.company = data.get('Company Name', '')
        self.job_title = data.get('Job Title', '')
        self.location = data.get('Location', '')
        self.linkedin_profile = data.get('LinkedIn Profile', '')
        self.company_domain = data.get('Company Domain', '')
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
        return self.full_name or self.first_name or 'Unknown'

    @classmethod
    def load_all(cls) -> List['Contact']:
        """Load all contacts from CSV file."""
        contacts = []
        try:
            csv_path = current_app.config['CSV_FILE_PATH']
            with open(csv_path, mode='r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)
                for row in csv_reader:
                    contacts.append(cls(row))
        except Exception as e:
            current_app.logger.error(f"Error loading contacts: {str(e)}")
        return contacts

    @classmethod
    def get_paginated(cls, page: int = 1, per_page: int = 10) -> Dict:
        """Get paginated contacts."""
        all_contacts = cls.load_all()
        total = len(all_contacts)
        total_pages = (total + per_page - 1) // per_page
        
        start_idx = (page - 1) * per_page
        end_idx = min(start_idx + per_page, total)
        contacts = all_contacts[start_idx:end_idx]
        
        return {
            'contacts': contacts,
            'current_page': page,
            'total_pages': total_pages,
            'per_page': per_page,
            'total_contacts': total
        }

    @classmethod
    def search(cls, query: str) -> List['Contact']:
        """Search contacts by name, email, or company."""
        all_contacts = cls.load_all()
        query = query.lower()
        
        return [
            contact for contact in all_contacts
            if (query in contact.display_name.lower() or
                query in contact.email.lower() or
                query in contact.company.lower() or
                query in contact.job_title.lower())
        ]

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