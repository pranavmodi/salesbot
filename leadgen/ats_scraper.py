#!/usr/bin/env python3
"""
ATS Job Board Scraper for Lead Generation

Scrapes public ATS job boards to find companies (50-100 employees) 
hiring for customer support roles - indicating growth and support pain points.
"""

import requests
import json
import csv
import time
import re
from urllib.parse import urlparse
from dataclasses import dataclass
from typing import List, Dict, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class JobPosting:
    company: str
    domain: str
    title: str
    department: str
    location: str
    posted_date: str
    source: str
    ats_type: str

@dataclass
class CompanyLead:
    company: str
    domain: str
    support_roles: int
    sales_roles: int
    ai_roles: int
    total_roles: int
    ats_type: str
    estimated_size: str

class ATSScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        self.companies_found = []
        
    def is_support_role(self, title: str, department: str = "") -> bool:
        """Check if job title indicates customer support role"""
        support_keywords = [
            'customer support', 'customer success', 'customer service', 
            'support specialist', 'help desk', 'technical support',
            'customer experience', 'client success', 'user success',
            'support engineer', 'customer care', 'cx', 'cs rep'
        ]
        
        title_lower = title.lower()
        dept_lower = department.lower()
        
        return any(keyword in title_lower or keyword in dept_lower 
                  for keyword in support_keywords)
    
    def is_sales_role(self, title: str, department: str = "") -> bool:
        """Check if job title indicates sales role"""
        sales_keywords = [
            'sales', 'account executive', 'business development', 
            'sdr', 'bdr', 'sales development', 'account manager',
            'revenue', 'partnerships', 'sales rep', 'inside sales'
        ]
        
        title_lower = title.lower()
        dept_lower = department.lower()
        
        return any(keyword in title_lower or keyword in dept_lower 
                  for keyword in sales_keywords)
    
    def is_ai_role(self, title: str, department: str = "") -> bool:
        """Check if job title indicates AI/ML role"""
        ai_keywords = [
            'machine learning', 'ai', 'artificial intelligence',
            'data scientist', 'ml engineer', 'nlp', 'deep learning',
            'mlops', 'ai researcher', 'computer vision'
        ]
        
        title_lower = title.lower()
        dept_lower = department.lower()
        
        return any(keyword in title_lower or keyword in dept_lower 
                  for keyword in ai_keywords)

    def extract_domain(self, url_or_domain: str) -> str:
        """Extract clean domain from URL"""
        if not url_or_domain:
            return ""
        
        if not url_or_domain.startswith('http'):
            url_or_domain = 'https://' + url_or_domain
            
        try:
            parsed = urlparse(url_or_domain)
            domain = parsed.netloc.lower()
            # Remove www prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except:
            return url_or_domain.lower()

    def scrape_greenhouse_board(self, company_slug: str) -> List[JobPosting]:
        """Scrape Greenhouse public job board"""
        jobs = []
        
        try:
            # Try both embed and direct board URLs
            urls = [
                f"https://boards.greenhouse.io/{company_slug}/embed/job_board",
                f"https://api.greenhouse.io/v1/boards/{company_slug}/jobs"
            ]
            
            for url in urls:
                try:
                    response = self.session.get(url, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Handle different response formats
                        job_list = data.get('jobs', data) if isinstance(data, dict) else data
                        
                        for job in job_list:
                            if isinstance(job, dict):
                                jobs.append(JobPosting(
                                    company=company_slug.replace('-', ' ').title(),
                                    domain=self.extract_domain(job.get('company_url', f"{company_slug}.com")),
                                    title=job.get('title', ''),
                                    department=job.get('departments', [{}])[0].get('name', '') if job.get('departments') else '',
                                    location=job.get('location', {}).get('name', '') if job.get('location') else '',
                                    posted_date=job.get('updated_at', ''),
                                    source=url,
                                    ats_type='greenhouse'
                                ))
                        break
                        
                except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError) as e:
                    logger.debug(f"Failed to scrape {url}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error scraping Greenhouse for {company_slug}: {e}")
            
        return jobs

    def scrape_lever_board(self, company_slug: str) -> List[JobPosting]:
        """Scrape Lever public job board"""
        jobs = []
        
        try:
            url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                for job in data:
                    jobs.append(JobPosting(
                        company=job.get('categories', {}).get('company', company_slug).title(),
                        domain=self.extract_domain(job.get('hostedUrl', f"{company_slug}.com")),
                        title=job.get('text', ''),
                        department=job.get('categories', {}).get('department', ''),
                        location=job.get('categories', {}).get('location', ''),
                        posted_date=job.get('createdAt', ''),
                        source=url,
                        ats_type='lever'
                    ))
                    
        except Exception as e:
            logger.error(f"Error scraping Lever for {company_slug}: {e}")
            
        return jobs

    def discover_greenhouse_companies(self, sample_companies: List[str]) -> List[str]:
        """Discover Greenhouse companies by trying common company name variations"""
        found_companies = []
        
        for company in sample_companies:
            # Try various slug formats
            slugs = [
                company.lower().replace(' ', '-'),
                company.lower().replace(' ', ''),
                company.lower().replace('inc', '').replace('llc', '').strip().replace(' ', '-'),
                ''.join(company.lower().split())
            ]
            
            for slug in set(slugs):  # Remove duplicates
                try:
                    url = f"https://boards.greenhouse.io/{slug}"
                    response = self.session.head(url, timeout=5)
                    if response.status_code == 200:
                        found_companies.append(slug)
                        logger.info(f"Found Greenhouse board: {slug}")
                        break
                except:
                    continue
                    
                time.sleep(0.5)  # Rate limiting
                
        return found_companies

    def analyze_company_jobs(self, jobs: List[JobPosting]) -> CompanyLead:
        """Analyze jobs for a company and create lead profile"""
        if not jobs:
            return None
            
        company = jobs[0].company
        domain = jobs[0].domain
        ats_type = jobs[0].ats_type
        
        support_roles = sum(1 for job in jobs if self.is_support_role(job.title, job.department))
        sales_roles = sum(1 for job in jobs if self.is_sales_role(job.title, job.department))
        ai_roles = sum(1 for job in jobs if self.is_ai_role(job.title, job.department))
        total_roles = len(jobs)
        
        # Estimate company size based on total open roles
        if total_roles <= 5:
            estimated_size = "Small (50-100)"
        elif total_roles <= 15:
            estimated_size = "Medium (100-300)"
        else:
            estimated_size = "Large (300+)"
            
        return CompanyLead(
            company=company,
            domain=domain,
            support_roles=support_roles,
            sales_roles=sales_roles,
            ai_roles=ai_roles,
            total_roles=total_roles,
            ats_type=ats_type,
            estimated_size=estimated_size
        )

    def save_results_to_csv(self, leads: List[CompanyLead], filename: str = "company_leads.csv"):
        """Save company leads to CSV file"""
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = [
                'company', 'domain', 'support_roles', 'sales_roles', 'ai_roles', 
                'total_roles', 'ats_type', 'estimated_size', 'lead_score'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for lead in leads:
                # Calculate simple lead score
                lead_score = 0
                if lead.support_roles > 0:
                    lead_score += lead.support_roles * 3  # Support roles are high value
                if lead.sales_roles > 0:
                    lead_score += lead.sales_roles * 2    # Sales roles indicate growth
                if lead.ai_roles > 0:
                    lead_score -= 5  # AI roles are negative signal
                if lead.estimated_size == "Small (50-100)":
                    lead_score += 5  # Target size range
                    
                writer.writerow({
                    'company': lead.company,
                    'domain': lead.domain,
                    'support_roles': lead.support_roles,
                    'sales_roles': lead.sales_roles,
                    'ai_roles': lead.ai_roles,
                    'total_roles': lead.total_roles,
                    'ats_type': lead.ats_type,
                    'estimated_size': lead.estimated_size,
                    'lead_score': lead_score
                })
                
        logger.info(f"Saved {len(leads)} company leads to {filename}")

def main():
    scraper = ATSScraper()
    
    # Sample companies to test with - mix of known growing companies
    sample_companies = [
        "stripe", "notion", "figma", "canva", "airtable", "zapier", 
        "intercom", "zendesk", "freshworks", "gorgias", "helpscout",
        "monday", "asana", "clickup", "linear", "superhuman",
        "vercel", "netlify", "supabase", "planetscale", "railway"
    ]
    
    logger.info("Starting ATS lead generation scraping...")
    
    all_leads = []
    
    # Discover and scrape Greenhouse companies
    logger.info("Discovering Greenhouse companies...")
    greenhouse_companies = scraper.discover_greenhouse_companies(sample_companies)
    
    for company_slug in greenhouse_companies[:10]:  # Limit for testing
        logger.info(f"Scraping Greenhouse jobs for: {company_slug}")
        jobs = scraper.scrape_greenhouse_board(company_slug)
        
        if jobs:
            lead = scraper.analyze_company_jobs(jobs)
            if lead and (lead.support_roles > 0 or lead.sales_roles > 0):
                all_leads.append(lead)
                logger.info(f"Added lead: {lead.company} ({lead.support_roles} support, {lead.sales_roles} sales roles)")
        
        time.sleep(1)  # Rate limiting
    
    # Try some Lever companies
    logger.info("Scraping Lever companies...")
    lever_companies = sample_companies[:5]  # Try subset with Lever
    
    for company_slug in lever_companies:
        logger.info(f"Scraping Lever jobs for: {company_slug}")
        jobs = scraper.scrape_lever_board(company_slug)
        
        if jobs:
            lead = scraper.analyze_company_jobs(jobs)
            if lead and (lead.support_roles > 0 or lead.sales_roles > 0):
                all_leads.append(lead)
                logger.info(f"Added lead: {lead.company} ({lead.support_roles} support, {lead.sales_roles} sales roles)")
        
        time.sleep(1)  # Rate limiting
    
    # Filter and sort leads
    qualified_leads = [lead for lead in all_leads 
                      if lead.support_roles > 0 and lead.ai_roles == 0]
    
    qualified_leads.sort(key=lambda x: (x.support_roles + x.sales_roles), reverse=True)
    
    # Save results
    scraper.save_results_to_csv(qualified_leads, "leadgen/qualified_leads.csv")
    
    logger.info(f"\nFound {len(qualified_leads)} qualified leads!")
    logger.info("Top 5 leads:")
    for lead in qualified_leads[:5]:
        logger.info(f"  {lead.company}: {lead.support_roles} support, {lead.sales_roles} sales roles")

if __name__ == "__main__":
    main()