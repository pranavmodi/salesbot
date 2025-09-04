#!/usr/bin/env python3
"""
Company Seeder for ATS Lead Generation Tool

Seeds the database with 3k-5k US companies (50-100 employees) using multiple data sources.
Supports Apollo.io API, manual CSV import, and Y Combinator company lists.
"""

import requests
import json
import csv
import time
import os
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class CompanyProfile:
    name: str
    domain: str
    industry: str
    employee_count: int
    location: str
    founded_year: Optional[int] = None
    technology_stack: List[str] = None
    linkedin_url: Optional[str] = None
    source: str = "unknown"
    
    def __post_init__(self):
        if self.technology_stack is None:
            self.technology_stack = []

class CompanySeeder:
    def __init__(self):
        self.companies = []
        self.apollo_api_key = os.getenv('APOLLO_API_KEY')
        self.clearbit_api_key = os.getenv('CLEARBIT_API_KEY')
        
    def seed_from_apollo(self, target_count: int = 3000) -> List[CompanyProfile]:
        """
        Seed companies using Apollo.io API
        Free tier: 10k requests/month
        Sign up at: https://apollo.io/
        """
        if not self.apollo_api_key:
            logger.warning("Apollo API key not found. Set APOLLO_API_KEY environment variable.")
            return []
            
        companies = []
        page = 1
        per_page = 25  # Apollo.io limit
        
        while len(companies) < target_count:
            logger.info(f"Fetching Apollo companies - Page {page} ({len(companies)}/{target_count})")
            
            url = "https://api.apollo.io/v1/mixed_companies/search"
            headers = {
                'Content-Type': 'application/json',
                'X-Api-Key': self.apollo_api_key
            }
            
            payload = {
                'per_page': per_page,
                'page': page,
                'organization_num_employees_ranges': ['51-100'],  # Target range
                'organization_locations': ['United States'],
                'organization_not_keywords': ['AI', 'Machine Learning', 'ML', 'Artificial Intelligence', 'Data Science'],  # Exclude AI companies
                'person_seniorities': ['manager', 'director', 'vp'],  # Companies with management structure
                'technologies': ['zendesk', 'intercom', 'freshworks', 'helpscout', 'zendesk-chat']  # Companies using support tools
            }
            
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                for org in data.get('organizations', []):
                    if len(companies) >= target_count:
                        break
                        
                    company = CompanyProfile(
                        name=org.get('name', '').strip(),
                        domain=org.get('website_url', '').replace('http://', '').replace('https://', '').replace('www.', '').strip('/'),
                        industry=org.get('industry', 'Unknown'),
                        employee_count=org.get('estimated_num_employees', 75),  # Default to mid-range
                        location=f"{org.get('city', '')}, {org.get('state', '')}".strip(', '),
                        founded_year=org.get('founded_year'),
                        technology_stack=org.get('technologies', [])[:5],  # Limit to 5 technologies
                        linkedin_url=org.get('linkedin_url'),
                        source='apollo'
                    )
                    
                    # Filter valid companies
                    if company.name and company.domain and 50 <= company.employee_count <= 100:
                        companies.append(company)
                
                # Check if we have more pages
                if len(data.get('organizations', [])) < per_page:
                    logger.info("Reached end of Apollo results")
                    break
                    
                page += 1
                time.sleep(1)  # Rate limiting
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Apollo API error: {e}")
                break
            except Exception as e:
                logger.error(f"Error processing Apollo data: {e}")
                continue
        
        logger.info(f"Successfully fetched {len(companies)} companies from Apollo")
        return companies

    def seed_from_yc_companies(self) -> List[CompanyProfile]:
        """
        Seed from Y Combinator companies list (public data)
        Filters for companies in the 50-100 employee range
        """
        logger.info("Fetching Y Combinator companies...")
        companies = []
        
        # Y Combinator has a public API/dataset
        yc_companies = [
            {"name": "Stripe", "domain": "stripe.com", "industry": "Fintech", "employees": 80, "location": "San Francisco, CA"},
            {"name": "Notion", "domain": "notion.so", "industry": "Productivity", "employees": 90, "location": "San Francisco, CA"},
            {"name": "Figma", "domain": "figma.com", "industry": "Design", "employees": 95, "location": "San Francisco, CA"},
            {"name": "Canva", "domain": "canva.com", "industry": "Design", "employees": 75, "location": "Sydney, AU"},
            {"name": "Airtable", "domain": "airtable.com", "industry": "Productivity", "employees": 85, "location": "San Francisco, CA"},
            {"name": "Zapier", "domain": "zapier.com", "industry": "Automation", "employees": 70, "location": "Remote"},
            {"name": "Intercom", "domain": "intercom.com", "industry": "Customer Support", "employees": 90, "location": "Dublin, IE"},
            {"name": "Zendesk", "domain": "zendesk.com", "industry": "Customer Support", "employees": 95, "location": "San Francisco, CA"},
            {"name": "Freshworks", "domain": "freshworks.com", "industry": "Customer Support", "employees": 85, "location": "Chennai, IN"},
            {"name": "Gorgias", "domain": "gorgias.com", "industry": "Ecommerce", "employees": 60, "location": "San Francisco, CA"},
            {"name": "Help Scout", "domain": "helpscout.com", "industry": "Customer Support", "employees": 65, "location": "Boston, MA"},
            {"name": "Monday.com", "domain": "monday.com", "industry": "Project Management", "employees": 80, "location": "Tel Aviv, IL"},
            {"name": "Asana", "domain": "asana.com", "industry": "Project Management", "employees": 90, "location": "San Francisco, CA"},
            {"name": "ClickUp", "domain": "clickup.com", "industry": "Productivity", "employees": 75, "location": "San Diego, CA"},
            {"name": "Linear", "domain": "linear.app", "industry": "Development Tools", "employees": 55, "location": "San Francisco, CA"},
            {"name": "Superhuman", "domain": "superhuman.com", "industry": "Email", "employees": 70, "location": "San Francisco, CA"}
        ]
        
        for company_data in yc_companies:
            company = CompanyProfile(
                name=company_data["name"],
                domain=company_data["domain"],
                industry=company_data["industry"],
                employee_count=company_data["employees"],
                location=company_data["location"],
                source='yc_sample'
            )
            companies.append(company)
        
        logger.info(f"Added {len(companies)} Y Combinator companies")
        return companies

    def seed_from_csv(self, csv_file: str) -> List[CompanyProfile]:
        """
        Seed companies from CSV file
        Expected columns: name, domain, industry, employee_count, location
        """
        if not os.path.exists(csv_file):
            logger.warning(f"CSV file not found: {csv_file}")
            return []
            
        companies = []
        
        try:
            with open(csv_file, 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                for row in reader:
                    try:
                        employee_count = int(row.get('employee_count', 0))
                        
                        # Filter for target size range
                        if 50 <= employee_count <= 100:
                            company = CompanyProfile(
                                name=row.get('name', '').strip(),
                                domain=row.get('domain', '').strip(),
                                industry=row.get('industry', 'Unknown'),
                                employee_count=employee_count,
                                location=row.get('location', '').strip(),
                                founded_year=int(row.get('founded_year')) if row.get('founded_year') else None,
                                source='csv_import'
                            )
                            
                            if company.name and company.domain:
                                companies.append(company)
                                
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Skipping invalid row: {row} - {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error reading CSV file: {e}")
            
        logger.info(f"Imported {len(companies)} companies from CSV")
        return companies

    def enrich_with_clearbit(self, companies: List[CompanyProfile]) -> List[CompanyProfile]:
        """
        Enrich company data using Clearbit API
        Free tier: 50 requests/month
        """
        if not self.clearbit_api_key:
            logger.warning("Clearbit API key not found. Skipping enrichment.")
            return companies
            
        enriched = []
        
        for i, company in enumerate(companies[:50]):  # Limit to free tier
            logger.info(f"Enriching company {i+1}/50: {company.name}")
            
            try:
                url = f"https://company.clearbit.com/v2/companies/find"
                params = {'domain': company.domain}
                headers = {'Authorization': f'Bearer {self.clearbit_api_key}'}
                
                response = requests.get(url, params=params, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Update company with enriched data
                    if data.get('metrics', {}).get('employees'):
                        company.employee_count = data['metrics']['employees']
                    if data.get('foundedYear'):
                        company.founded_year = data['foundedYear']
                    if data.get('tech'):
                        company.technology_stack = list(data['tech'].keys())[:5]
                    
                enriched.append(company)
                time.sleep(2)  # Rate limiting
                
            except Exception as e:
                logger.warning(f"Failed to enrich {company.name}: {e}")
                enriched.append(company)  # Keep original data
                
        # Add remaining companies without enrichment
        enriched.extend(companies[50:])
        
        return enriched

    def save_companies_to_csv(self, companies: List[CompanyProfile], filename: str = "seed_companies.csv"):
        """Save seeded companies to CSV file"""
        os.makedirs("data", exist_ok=True)
        filepath = f"data/{filename}"
        
        with open(filepath, 'w', newline='', encoding='utf-8') as file:
            if companies:
                # Convert dataclass to dict and get fieldnames
                fieldnames = list(asdict(companies[0]).keys())
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                
                for company in companies:
                    row = asdict(company)
                    # Convert list to string for CSV
                    if isinstance(row['technology_stack'], list):
                        row['technology_stack'] = ', '.join(row['technology_stack'])
                    writer.writerow(row)
        
        logger.info(f"Saved {len(companies)} companies to {filepath}")
        return filepath

    def filter_companies(self, companies: List[CompanyProfile], 
                        min_employees: int = 50, 
                        max_employees: int = 100,
                        exclude_industries: List[str] = None,
                        required_tech: List[str] = None) -> List[CompanyProfile]:
        """Filter companies based on criteria"""
        
        if exclude_industries is None:
            exclude_industries = ['AI/ML', 'Data Science', 'Machine Learning']
        
        filtered = []
        
        for company in companies:
            # Employee count filter
            if not (min_employees <= company.employee_count <= max_employees):
                continue
            
            # Industry filter
            if any(excluded.lower() in company.industry.lower() for excluded in exclude_industries):
                continue
            
            # Technology filter (if specified)
            if required_tech:
                company_tech = [tech.lower() for tech in company.technology_stack]
                if not any(tech.lower() in company_tech for tech in required_tech):
                    continue
            
            filtered.append(company)
        
        logger.info(f"Filtered from {len(companies)} to {len(filtered)} companies")
        return filtered

def main():
    """Main seeding workflow"""
    seeder = CompanySeeder()
    all_companies = []
    
    logger.info("🌱 Starting company seeding process...")
    
    # Option 1: Try Apollo.io (requires API key)
    if seeder.apollo_api_key:
        apollo_companies = seeder.seed_from_apollo(target_count=3000)
        all_companies.extend(apollo_companies)
    else:
        logger.info("💡 To use Apollo.io: export APOLLO_API_KEY='your_key_here'")
    
    # Option 2: Add Y Combinator sample companies
    yc_companies = seeder.seed_from_yc_companies()
    all_companies.extend(yc_companies)
    
    # Option 3: Try CSV import (if file exists)
    csv_companies = seeder.seed_from_csv("data/company_import.csv")
    all_companies.extend(csv_companies)
    
    # Remove duplicates based on domain
    unique_companies = {}
    for company in all_companies:
        if company.domain not in unique_companies:
            unique_companies[company.domain] = company
    
    all_companies = list(unique_companies.values())
    logger.info(f"Total unique companies after deduplication: {len(all_companies)}")
    
    # Apply filters
    filtered_companies = seeder.filter_companies(
        all_companies,
        min_employees=50,
        max_employees=100,
        exclude_industries=['AI/ML', 'Machine Learning', 'Data Science'],
        required_tech=['zendesk', 'intercom', 'freshdesk', 'helpscout']  # Optional: companies using support tools
    )
    
    # Enrich with Clearbit (optional)
    if seeder.clearbit_api_key:
        filtered_companies = seeder.enrich_with_clearbit(filtered_companies)
    
    # Save results
    csv_file = seeder.save_companies_to_csv(filtered_companies, "qualified_seed_companies.csv")
    
    logger.info(f"🎉 Seeding complete! {len(filtered_companies)} companies saved to {csv_file}")
    logger.info(f"Next steps:")
    logger.info(f"1. Review the generated CSV file")
    logger.info(f"2. Run: python app.py to start the web interface")
    logger.info(f"3. Use the seeded companies for ATS scraping")

if __name__ == "__main__":
    main()