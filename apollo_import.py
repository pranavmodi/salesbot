#!/usr/bin/env python3
"""
Apollo.io API Integration Script for SalesBot

This script pulls lead data from Apollo.io API and imports it into SalesBot's contact system.
Supports filtering by company size, industry, location, and other criteria.

Usage:
    python apollo_import.py --industry healthcare --employees 50-200 --location "United States" --pages 5
    python apollo_import.py --config healthcare_config.json
    python apollo_import.py --help
"""

import os
import sys
import json
import csv
import time
import argparse
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('apollo_import.log')
    ]
)
logger = logging.getLogger(__name__)

class ApolloAPIClient:
    """Apollo.io API client for fetching lead data."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.apollo.io/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.rate_limit_delay = 1.5  # seconds between requests (free plan: ~50/min)
        
    def search_people(self, search_params: Dict[str, Any], page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        """Search for people using Apollo API."""
        url = f"{self.base_url}/contacts/search"
        
        payload = {
            "page": page,
            "per_page": min(per_page, 200),  # Apollo max is 200
            **search_params
        }
        
        logger.info(f"Fetching page {page} with {per_page} results per page...")
        
        try:
            # Debug logging
            logger.info(f"Making request to: {url}")
            logger.info(f"Headers: {dict(self.headers)}")
            logger.info(f"Payload keys: {list(payload.keys())}")
            
            response = requests.post(url, headers=self.headers, json=payload)
            
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            
            if response.status_code == 401:
                logger.error("Authentication failed - checking API key format...")
                logger.error(f"API key starts with: {self.api_key[:10]}..." if len(self.api_key) > 10 else f"API key: {self.api_key}")
                logger.error("Response body: " + response.text)
            
            response.raise_for_status()
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response content: {e.response.text}")
            raise
    
    def get_organization_info(self, domain: str) -> Optional[Dict[str, Any]]:
        """Get detailed organization information by domain."""
        url = f"{self.base_url}/organizations/domain_lookup"
        
        payload = {"domain": domain}
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            
            time.sleep(self.rate_limit_delay)
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Organization lookup failed for {domain}: {e}")
            return None

class SalesBotImporter:
    """Import Apollo data into SalesBot database."""
    
    def __init__(self, tenant_id: str = None):
        self.tenant_id = tenant_id
        
    def import_contacts(self, people_data: List[Dict[str, Any]], source: str = "apollo") -> int:
        """Import contacts into SalesBot database."""
        try:
            from app import create_app
            from app.models.contact import Contact
            from app.models.company import Company
            from app.database import get_shared_engine
            from sqlalchemy import text
            
            app = create_app()
            with app.app_context():
                imported_count = 0
                skipped_count = 0
                
                for person in people_data:
                    try:
                        # Extract contact data
                        first_name = person.get('first_name', '').strip()
                        last_name = person.get('last_name', '').strip()
                        email = person.get('email', '').strip()
                        title = person.get('title', '').strip()
                        
                        # Extract company data
                        org = person.get('organization', {})
                        company_name = org.get('name', '').strip()
                        company_website = org.get('website_url', '').strip()
                        
                        # Skip if essential data is missing
                        if not email or not first_name or not company_name:
                            logger.warning(f"Skipping incomplete record: {email}")
                            skipped_count += 1
                            continue
                        
                        # Check if contact already exists
                        existing_contact = Contact.get_by_email(email)
                        if existing_contact:
                            logger.info(f"Contact already exists: {email}")
                            skipped_count += 1
                            continue
                        
                        # Create/get company
                        company = Company.get_by_name(company_name)
                        if not company:
                            company = Company.create(
                                company_name=company_name,
                                website_url=company_website,
                                source=source
                            )
                            logger.info(f"Created company: {company_name}")
                        
                        # Create contact
                        contact = Contact.create(
                            name=f"{first_name} {last_name}".strip(),
                            email=email,
                            company_name=company_name,
                            position=title,
                            source=source,
                            tenant_id=self.tenant_id
                        )
                        
                        imported_count += 1
                        logger.info(f"Imported contact: {contact.name} ({contact.email})")
                        
                    except Exception as e:
                        logger.error(f"Failed to import contact {person.get('email', 'unknown')}: {e}")
                        skipped_count += 1
                        continue
                
                logger.info(f"Import complete: {imported_count} imported, {skipped_count} skipped")
                return imported_count
                
        except Exception as e:
            logger.error(f"Import failed: {e}")
            raise

def build_search_params(args) -> Dict[str, Any]:
    """Build Apollo API search parameters from command line arguments."""
    params = {}
    
    # Employee count ranges
    if args.employees:
        if args.employees == "50-200":
            params["q_organization_num_employees_ranges"] = ["51-200"]
        elif args.employees == "200-1000":
            params["q_organization_num_employees_ranges"] = ["201-1000"]
        elif args.employees == "1000+":
            params["q_organization_num_employees_ranges"] = ["1001+"]
        else:
            # Custom range
            params["q_organization_num_employees_ranges"] = [args.employees]
    
    # Industry filtering
    if args.industry:
        industry_mappings = {
            "healthcare": ["Healthcare", "Medical Practice", "Hospital & Health Care", "Pharmaceuticals", "Medical Devices"],
            "technology": ["Information Technology", "Software", "Computer Software", "Internet"],
            "finance": ["Financial Services", "Banking", "Investment Banking", "Insurance"],
            "education": ["Education", "Higher Education", "E-Learning"],
            "manufacturing": ["Manufacturing", "Industrial Manufacturing", "Automotive"],
            "retail": ["Retail", "E-commerce", "Consumer Goods"]
        }
        
        industries = industry_mappings.get(args.industry.lower(), [args.industry])
        params["q_organization_industry_tags"] = industries
    
    # Location filtering
    if args.location:
        params["person_locations"] = [args.location]
    
    # Email verification
    if args.verified_emails:
        params["contact_email_status"] = "verified"
    
    # Job titles
    if args.titles:
        params["person_titles"] = args.titles
    
    # Seniority level
    if args.seniority:
        seniority_mappings = {
            "executive": ["c_suite", "vp"],
            "management": ["director", "manager"],
            "individual": ["individual_contributor"]
        }
        levels = seniority_mappings.get(args.seniority.lower(), [args.seniority])
        params["person_seniorities"] = levels
    
    return params

def export_to_csv(people_data: List[Dict[str, Any]], filename: str) -> None:
    """Export Apollo data to CSV file."""
    logger.info(f"Exporting {len(people_data)} contacts to {filename}")
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow([
            'Name', 'First Name', 'Last Name', 'Email', 'Position', 
            'Company', 'Company URL', 'LinkedIn', 'Phone', 'Location', 'Source'
        ])
        
        # Write data
        for person in people_data:
            first_name = person.get('first_name', '')
            last_name = person.get('last_name', '')
            name = f"{first_name} {last_name}".strip()
            email = person.get('email', '')
            title = person.get('title', '')
            
            org = person.get('organization', {})
            company = org.get('name', '')
            company_url = org.get('website_url', '')
            
            linkedin = person.get('linkedin_url', '')
            phone = person.get('phone_numbers', [{}])[0].get('raw_number', '') if person.get('phone_numbers') else ''
            location = person.get('city', '')
            
            writer.writerow([
                name, first_name, last_name, email, title,
                company, company_url, linkedin, phone, location, 'apollo'
            ])
    
    logger.info(f"CSV export complete: {filename}")

def load_config(config_file: str) -> Dict[str, Any]:
    """Load configuration from JSON file."""
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config file {config_file}: {e}")
        raise

def create_sample_config():
    """Create a sample configuration file."""
    sample_config = {
        "search_params": {
            "industry": "healthcare",
            "employees": "50-200",
            "location": "United States",
            "verified_emails": True,
            "titles": ["Manager", "Director", "VP"],
            "seniority": "management"
        },
        "fetch_settings": {
            "pages": 5,
            "per_page": 50,
            "rate_limit_delay": 1.0
        },
        "output": {
            "csv_filename": "apollo_leads_{timestamp}.csv",
            "import_to_salesbot": True,
            "tenant_id": None
        }
    }
    
    with open('apollo_config_sample.json', 'w') as f:
        json.dump(sample_config, f, indent=2)
    
    logger.info("Created sample config file: apollo_config_sample.json")

def main():
    parser = argparse.ArgumentParser(description="Import leads from Apollo.io API")
    
    # Search parameters
    parser.add_argument('--industry', help='Industry filter (healthcare, technology, finance, etc.)')
    parser.add_argument('--employees', help='Employee count range (50-200, 200-1000, 1000+)')
    parser.add_argument('--location', default='United States', help='Location filter')
    parser.add_argument('--titles', nargs='+', help='Job titles to search for')
    parser.add_argument('--seniority', help='Seniority level (executive, management, individual)')
    parser.add_argument('--verified-emails', action='store_true', help='Only fetch verified emails')
    
    # Fetch settings
    parser.add_argument('--pages', type=int, default=5, help='Number of pages to fetch')
    parser.add_argument('--per-page', type=int, default=50, help='Results per page (max 200)')
    parser.add_argument('--api-key', help='Apollo API key (or set APOLLO_API_KEY env var)')
    
    # Output options
    parser.add_argument('--csv-only', action='store_true', help='Export to CSV only (don\'t import to SalesBot)')
    parser.add_argument('--csv-filename', help='CSV output filename')
    parser.add_argument('--tenant-id', help='SalesBot tenant ID for import')
    
    # Configuration
    parser.add_argument('--config', help='Load settings from JSON config file')
    parser.add_argument('--create-sample-config', action='store_true', help='Create sample config file')
    
    args = parser.parse_args()
    
    # Create sample config if requested
    if args.create_sample_config:
        create_sample_config()
        return
    
    # Load configuration if provided
    if args.config:
        config = load_config(args.config)
        # Override with command line args if provided
        for key, value in vars(args).items():
            if value is not None and key in config.get('search_params', {}):
                config['search_params'][key] = value
    else:
        config = {'search_params': {}, 'fetch_settings': {}, 'output': {}}
    
    # Get API key
    api_key = args.api_key or os.getenv('APOLLO_API_KEY')
    if not api_key:
        logger.error("APOLLO_API_KEY not found in environment variables or as argument.")
        logger.error("Please ensure it is set in your .env file or passed via --api-key.")
        return 1
    
    # Build search parameters
    search_params = build_search_params(args)
    if args.verified_emails or config.get('search_params', {}).get('verified_emails'):
        search_params['contact_email_status'] = 'verified'
    
    logger.info(f"Search parameters: {search_params}")
    
    # Initialize Apollo client
    client = ApolloAPIClient(api_key)
    
    # Fetch data
    all_people = []
    pages = args.pages or config.get('fetch_settings', {}).get('pages', 5)
    per_page = getattr(args, 'per_page', None) or config.get('fetch_settings', {}).get('per_page', 50)
    
    logger.info(f"Fetching {pages} pages with {per_page} results per page...")
    
    try:
        for page in range(1, pages + 1):
            logger.info(f"Fetching page {page}/{pages}...")
            
            response = client.search_people(search_params, page=page, per_page=per_page)
            
            people = response.get('people', [])
            if not people:
                logger.info(f"No more results at page {page}")
                break
            
            all_people.extend(people)
            logger.info(f"Page {page}: {len(people)} contacts fetched (total: {len(all_people)})")
            
            # Check if we've reached the end
            pagination = response.get('pagination', {})
            total_pages = pagination.get('total_pages', 0)
            if page >= total_pages:
                logger.info(f"Reached last page ({total_pages})")
                break
    
    except Exception as e:
        logger.error(f"Failed to fetch data: {e}")
        return 1
    
    if not all_people:
        logger.warning("No contacts found matching criteria")
        return 0
    
    logger.info(f"Successfully fetched {len(all_people)} contacts")
    
    # Export to CSV
    csv_filename = (args.csv_filename or 
                   config.get('output', {}).get('csv_filename', '') or
                   f"apollo_leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    
    export_to_csv(all_people, csv_filename)
    
    # Import to SalesBot if requested
    if not args.csv_only and config.get('output', {}).get('import_to_salesbot', True):
        try:
            tenant_id = args.tenant_id or config.get('output', {}).get('tenant_id')
            importer = SalesBotImporter(tenant_id=tenant_id)
            imported_count = importer.import_contacts(all_people)
            logger.info(f"Successfully imported {imported_count} contacts to SalesBot")
        except Exception as e:
            logger.error(f"Failed to import to SalesBot: {e}")
            logger.info(f"Data saved to CSV: {csv_filename}")
            return 1
    
    logger.info("Apollo import completed successfully!")
    return 0

if __name__ == '__main__':
    sys.exit(main())