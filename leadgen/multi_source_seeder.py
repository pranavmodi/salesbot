#!/usr/bin/env python3
"""
Multi-Source Company Seeder

Integrates multiple data sources beyond Apollo for company seeding.
"""

import requests
import json
import time
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
import os

from company_seeder import CompanyProfile

logger = logging.getLogger(__name__)

class MultiSourceSeeder:
    def __init__(self):
        self.clearbit_api_key = os.getenv('CLEARBIT_API_KEY')
        self.hunter_api_key = os.getenv('HUNTER_API_KEY') 
        self.pdl_api_key = os.getenv('PDL_API_KEY')
        self.zoominfo_api_key = os.getenv('ZOOMINFO_API_KEY')
        
    def seed_from_clearbit_prospector(self, target_count: int = 1000) -> List[CompanyProfile]:
        """
        Seed companies using Clearbit Prospector API
        NOTE: Clearbit has NO free tier - requires paid plan ($99+/month)
        """
        if not self.clearbit_api_key:
            logger.warning("Clearbit API key not found - No free tier available, requires paid plan")
            return []
            
        companies = []
        page = 1
        
        while len(companies) < target_count:
            try:
                url = "https://prospector.clearbit.com/v1/companies/search"
                headers = {'Authorization': f'Bearer {self.clearbit_api_key}'}
                
                params = {
                    'page': page,
                    'limit': 25,
                    'employee_count_min': 50,
                    'employee_count_max': 100,
                    'location': 'United States',
                    'tech': ['zendesk', 'intercom', 'helpscout', 'freshdesk']  # Companies using support tools
                }
                
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
                
                for company_data in data.get('results', []):
                    company = CompanyProfile(
                        name=company_data.get('name', ''),
                        domain=company_data.get('domain', ''),
                        industry=company_data.get('category', {}).get('industry', ''),
                        employee_count=company_data.get('metrics', {}).get('employees', 75),
                        location=f"{company_data.get('geo', {}).get('city', '')}, {company_data.get('geo', {}).get('state', '')}",
                        founded_year=company_data.get('foundedYear'),
                        technology_stack=company_data.get('tech', [])[:5],
                        linkedin_url=company_data.get('linkedin', {}).get('handle'),
                        source='clearbit_prospector'
                    )
                    companies.append(company)
                    
                    if len(companies) >= target_count:
                        break
                
                if len(data.get('results', [])) < 25:
                    break
                    
                page += 1
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Clearbit Prospector error: {e}")
                break
        
        logger.info(f"Fetched {len(companies)} companies from Clearbit Prospector")
        return companies
    
    def seed_from_hunter_domain_search(self, target_count: int = 500) -> List[CompanyProfile]:
        """Seed companies using Hunter.io domain search"""
        if not self.hunter_api_key:
            logger.warning("Hunter API key not found")
            return []
            
        companies = []
        
        # Search for companies by domain patterns
        domain_patterns = [
            'customer support', 'help desk', 'customer success', 
            'saas', 'software', 'tech startup'
        ]
        
        for pattern in domain_patterns:
            try:
                url = "https://api.hunter.io/v2/domain-search"
                params = {
                    'query': pattern,
                    'limit': min(100, target_count - len(companies)),
                    'api_key': self.hunter_api_key
                }
                
                response = requests.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                for domain_data in data.get('data', {}).get('domains', []):
                    # Enrich domain with company data
                    company = self._enrich_domain_with_hunter(domain_data['domain'])
                    if company and 50 <= company.employee_count <= 100:
                        companies.append(company)
                        
                    if len(companies) >= target_count:
                        break
                        
                time.sleep(2)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Hunter domain search error for {pattern}: {e}")
                continue
        
        logger.info(f"Fetched {len(companies)} companies from Hunter")
        return companies
    
    def _enrich_domain_with_hunter(self, domain: str) -> Optional[CompanyProfile]:
        """Enrich a domain with company data from Hunter"""
        try:
            url = "https://api.hunter.io/v2/company"
            params = {
                'domain': domain,
                'api_key': self.hunter_api_key
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json().get('data', {})
            
            if data:
                return CompanyProfile(
                    name=data.get('name', ''),
                    domain=domain,
                    industry=data.get('industry', ''),
                    employee_count=data.get('headcount', 75),
                    location=f"{data.get('city', '')}, {data.get('country', '')}",
                    linkedin_url=data.get('linkedin'),
                    source='hunter'
                )
                
        except Exception as e:
            logger.warning(f"Failed to enrich domain {domain}: {e}")
            return None
    
    def seed_from_yc_extended(self) -> List[CompanyProfile]:
        """Extended Y Combinator company list with more companies"""
        companies = []
        
        # Batch 1: Current YC companies
        yc_batch_urls = [
            "https://api.ycombinator.com/v0.1/companies?batch=W23",
            "https://api.ycombinator.com/v0.1/companies?batch=S23", 
            "https://api.ycombinator.com/v0.1/companies?batch=W24",
            "https://api.ycombinator.com/v0.1/companies?batch=S24"
        ]
        
        for url in yc_batch_urls:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    batch_companies = response.json()
                    
                    for company_data in batch_companies:
                        if 50 <= company_data.get('team_size', 0) <= 100:
                            company = CompanyProfile(
                                name=company_data.get('name', ''),
                                domain=company_data.get('website', '').replace('https://', '').replace('http://', ''),
                                industry=company_data.get('vertical', ''),
                                employee_count=company_data.get('team_size', 75),
                                location=company_data.get('location', ''),
                                founded_year=company_data.get('founded_year'),
                                source='yc_extended'
                            )
                            companies.append(company)
                            
                time.sleep(1)
                
            except Exception as e:
                logger.warning(f"Failed to fetch YC batch from {url}: {e}")
                continue
        
        logger.info(f"Fetched {len(companies)} companies from YC extended")
        return companies
    
    def seed_from_builtwith(self, technologies: List[str], target_count: int = 1000) -> List[CompanyProfile]:
        """Find companies using specific technologies via BuiltWith"""
        # Note: BuiltWith requires paid API access
        # This is a placeholder for the implementation
        
        companies = []
        
        # Technologies that indicate customer support needs
        support_technologies = technologies or [
            'zendesk', 'intercom', 'freshworks', 'helpscout', 
            'drift', 'crisp', 'tawk-to', 'livechat'
        ]
        
        # Placeholder - would require BuiltWith API implementation
        logger.info("BuiltWith seeding requires paid API access")
        
        return companies
    
    def seed_from_indeed_companies(self, target_count: int = 500) -> List[CompanyProfile]:
        """Scrape Indeed for companies hiring support roles"""
        companies = []
        
        # Search queries for companies hiring support
        search_queries = [
            "customer support representative",
            "customer success manager", 
            "help desk technician",
            "technical support specialist"
        ]
        
        # Note: This would require careful scraping of Indeed
        # Following their robots.txt and terms of service
        
        logger.info("Indeed scraping requires careful implementation to follow ToS")
        
        return companies
    
    def seed_from_crunchbase_basic(self, target_count: int = 200) -> List[CompanyProfile]:
        """Limited free tier Crunchbase data"""
        companies = []
        
        # Crunchbase basic data (very limited free tier)
        # Would require paid access for meaningful volume
        
        logger.info("Crunchbase requires paid access for bulk data")
        
        return companies

def main():
    """Test multi-source seeding"""
    seeder = MultiSourceSeeder()
    
    all_companies = []
    
    # Try each source
    sources = [
        ('Clearbit Prospector', lambda: seeder.seed_from_clearbit_prospector(500)),
        ('Hunter Domain Search', lambda: seeder.seed_from_hunter_domain_search(300)), 
        ('YC Extended', lambda: seeder.seed_from_yc_extended()),
        ('BuiltWith', lambda: seeder.seed_from_builtwith(['zendesk', 'intercom'], 200))
    ]
    
    for source_name, source_func in sources:
        try:
            logger.info(f"Trying {source_name}...")
            companies = source_func()
            all_companies.extend(companies)
            logger.info(f"{source_name}: {len(companies)} companies")
        except Exception as e:
            logger.error(f"{source_name} failed: {e}")
    
    logger.info(f"Total companies from all sources: {len(all_companies)}")
    
    # Deduplicate by domain
    unique_companies = {}
    for company in all_companies:
        if company.domain and company.domain not in unique_companies:
            unique_companies[company.domain] = company
    
    logger.info(f"Unique companies after deduplication: {len(unique_companies)}")

if __name__ == "__main__":
    main()