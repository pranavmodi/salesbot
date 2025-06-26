#!/usr/bin/env python3
"""
Company Research Script

This script:
1. Extracts unique companies from the contacts table
2. Uses OpenAI to research each company
3. Populates the companies table with research data
"""

import os
import sys
import logging
import time
from typing import Dict, List, Optional, Set
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from openai import OpenAI

# Add the parent directory to sys.path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.company import Company
from app import create_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('company_research.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CompanyResearcher:
    """Handles company research using OpenAI."""
    
    def __init__(self):
        load_dotenv()
        self.client = OpenAI(api_key=os.getenv("OPENAI_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "o3")
        self.database_url = os.getenv("DATABASE_URL")
        
        if not self.database_url:
            raise ValueError("DATABASE_URL not found in environment variables")
        
        self.engine = create_engine(self.database_url)
        logger.info("CompanyResearcher initialized")

    def get_unique_companies_from_contacts(self) -> List[Dict[str, str]]:
        """Extract unique companies from contacts table with their domains."""
        logger.info("Extracting unique companies from contacts table...")
        
        try:
            with self.engine.connect() as conn:
                # Get unique companies with their domains and counts
                result = conn.execute(text("""
                    SELECT 
                        company_name,
                        company_domain,
                        COUNT(*) as contact_count
                    FROM contacts 
                    WHERE company_name IS NOT NULL 
                      AND company_name != '' 
                      AND company_name != 'Unknown'
                    GROUP BY company_name, company_domain
                    ORDER BY contact_count DESC, company_name ASC
                """))
                
                companies = []
                for row in result:
                    companies.append({
                        'company_name': row.company_name.strip(),
                        'company_domain': row.company_domain.strip() if row.company_domain else '',
                        'contact_count': row.contact_count
                    })
                
                logger.info(f"Found {len(companies)} unique companies in contacts table")
                return companies
                
        except SQLAlchemyError as e:
            logger.error(f"Database error extracting companies: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error extracting companies: {e}")
            return []

    def get_existing_companies(self) -> Set[str]:
        """Get set of company names that already exist in companies table."""
        logger.info("Checking existing companies in companies table...")
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT company_name FROM companies"))
                existing = {row.company_name.strip().lower() for row in result}
                logger.info(f"Found {len(existing)} existing companies in companies table")
                return existing
                
        except SQLAlchemyError as e:
            logger.error(f"Database error checking existing companies: {e}")
            return set()
        except Exception as e:
            logger.error(f"Unexpected error checking existing companies: {e}")
            return set()

    def research_company(self, company_name: str, company_domain: str = "") -> Optional[str]:
        """Use OpenAI to research a company and return comprehensive research."""
        logger.info(f"Researching company: {company_name}")
        
        # Construct website URL from domain
        website_url = ""
        if company_domain:
            if not company_domain.startswith(('http://', 'https://')):
                website_url = f"https://{company_domain}"
            else:
                website_url = company_domain

        system_prompt = """You are an expert B2B go-to-market strategist. Your task is to perform a comprehensive, desk-based diagnostic of companies for sales outreach purposes.

Follow this exact structure:

1 | Snapshot
Return a 3-sentence plain-English overview covering industry, core offering, size (revenue or headcount), and growth stage.

2 | Source Harvest
Pull and cite recent facts (≤ 12 months) from:
• Official sources: homepage, product pages, pricing, blog, annual or quarterly reports, investor decks, SEC/Companies House filings.
• Job postings on careers page or LinkedIn.
• News, PR, podcasts, founder interviews.
• Customer reviews (G2, Capterra, Trustpilot, Glassdoor for employer sentiment).
• Social media signals (LinkedIn posts, X/Twitter threads).

3 | Signals → Pain Hypotheses
For each major business function below, list observed signals (1-2 bullet points) → inferred pain hypothesis (1 bullet) in the table:

Function | Signals (facts) | Likely Pain-Point Hypothesis
GTM / Sales | | 
Marketing / Brand | | 
Product / R&D | | 
Customer Success | | 
Ops / Supply Chain | | 
People / Hiring | | 
Finance / Compliance | | 

4 | Top-3 Burning Problems
Rank the three most pressing, financially material pain points, citing the strongest evidence for each. Explain the business impact in one short paragraph per pain.

5 | Solution Hooks & Message Angles
For each of the Top-3 pains, suggest:
1. Solution hook (how our AI/LLM offering specifically relieves it).
2. One-line cold-email angle that provokes curiosity (≤ 25 words).
3. Metric to promise (e.g., "cut SDR research time by 40%").

Use H2 headings for sections 1-5. Return Markdown with inline citations (e.g., "(Crunchbase, Jan 2025)") after each fact. If information is missing, say "Data not found" instead of guessing. Keep total length ≤ 600 words."""

        user_prompt = f"""You are an expert B2B go-to-market strategist. Your task is to perform a comprehensive, desk-based diagnostic of the company named {company_name}{f" (website {website_url})" if website_url else ""}.

Company Details:
- Company Name: {company_name}
- Website: {website_url if website_url else 'Not available'}
- Domain: {company_domain if company_domain else 'Not available'}

Follow the exact structure provided in your system prompt. Begin now."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            research_content = response.choices[0].message.content.strip()
            logger.info(f"Successfully researched {company_name}")
            return research_content
            
        except Exception as e:
            logger.error(f"Error researching company {company_name}: {e}")
            return None

    def save_company_research(self, company_name: str, website_url: str, research: str) -> bool:
        """Save company research to the companies table."""
        logger.info(f"Saving research for: {company_name}")
        
        company_data = {
            'company_name': company_name,
            'website_url': website_url,
            'company_research': research
        }
        
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    insert_query = text("""
                        INSERT INTO companies (company_name, website_url, company_research) 
                        VALUES (:company_name, :website_url, :company_research)
                    """)
                    conn.execute(insert_query, company_data)
            
            logger.info(f"Successfully saved research for: {company_name}")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Database error saving company {company_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error saving company {company_name}: {e}")
            return False

    def update_company_research(self, company_id: int, research: str) -> bool:
        """Update existing company research in the companies table."""
        logger.info(f"Updating research for company ID: {company_id}")
        
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    update_query = text("""
                        UPDATE companies 
                        SET company_research = :research, updated_at = CURRENT_TIMESTAMP
                        WHERE id = :company_id
                    """)
                    result = conn.execute(update_query, {
                        'research': research,
                        'company_id': company_id
                    })
                    
                    if result.rowcount > 0:
                        logger.info(f"Successfully updated research for company ID: {company_id}")
                        return True
                    else:
                        logger.warning(f"No company found with ID: {company_id}")
                        return False
            
        except SQLAlchemyError as e:
            logger.error(f"Database error updating company {company_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error updating company {company_id}: {e}")
            return False

    def get_company_by_id(self, company_id: int) -> Optional[Dict]:
        """Get company details by ID."""
        logger.info(f"Fetching company by ID: {company_id}")
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, company_name, website_url, company_research
                    FROM companies 
                    WHERE id = :company_id
                """), {"company_id": company_id})
                
                row = result.fetchone()
                if row:
                    return {
                        'id': row.id,
                        'company_name': row.company_name,
                        'website_url': row.website_url,
                        'company_research': row.company_research
                    }
                else:
                    logger.warning(f"No company found with ID: {company_id}")
                    return None
                    
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching company {company_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching company {company_id}: {e}")
            return None

    def research_single_company_by_id(self, company_id: int) -> bool:
        """Research a single company by its ID."""
        logger.info(f"Starting research for company ID: {company_id}")
        
        # Get company details
        company = self.get_company_by_id(company_id)
        if not company:
            logger.error(f"Company with ID {company_id} not found")
            return False
        
        company_name = company['company_name']
        website_url = company['website_url'] or ''
        
        # Extract domain from website URL for research
        company_domain = ''
        if website_url:
            if website_url.startswith(('http://', 'https://')):
                company_domain = website_url.replace('https://', '').replace('http://', '').split('/')[0]
            else:
                company_domain = website_url
        
        logger.info(f"Researching company: {company_name}")
        
        # Research the company
        research = self.research_company(company_name, company_domain)
        
        if research:
            # Update the existing company record
            if self.update_company_research(company_id, research):
                logger.info(f"✅ Successfully researched and updated: {company_name}")
                return True
            else:
                logger.error(f"❌ Failed to update research for: {company_name}")
                return False
        else:
            logger.error(f"❌ Failed to research: {company_name}")
            return False

    def process_companies(self, max_companies: Optional[int] = None, delay_seconds: int = 2):
        """Main processing function to research and save companies."""
        logger.info("Starting company research process...")
        
        # Get unique companies from contacts
        contact_companies = self.get_unique_companies_from_contacts()
        if not contact_companies:
            logger.warning("No companies found in contacts table")
            return
        
        # Get existing companies to avoid duplicates
        existing_companies = self.get_existing_companies()
        
        # Filter out companies that already exist
        companies_to_research = []
        for company in contact_companies:
            if company['company_name'].lower() not in existing_companies:
                companies_to_research.append(company)
        
        logger.info(f"Found {len(companies_to_research)} new companies to research")
        
        if max_companies:
            companies_to_research = companies_to_research[:max_companies]
            logger.info(f"Limited to {max_companies} companies for this run")
        
        # Process each company
        successful_count = 0
        failed_count = 0
        
        for i, company in enumerate(companies_to_research, 1):
            logger.info(f"Processing {i}/{len(companies_to_research)}: {company['company_name']}")
            
            # Construct website URL
            website_url = ""
            if company['company_domain']:
                if not company['company_domain'].startswith(('http://', 'https://')):
                    website_url = f"https://{company['company_domain']}"
                else:
                    website_url = company['company_domain']
            
            # Research the company
            research = self.research_company(
                company['company_name'], 
                company['company_domain']
            )
            
            if research:
                # Save to database
                if self.save_company_research(company['company_name'], website_url, research):
                    successful_count += 1
                    logger.info(f"✅ Successfully processed: {company['company_name']}")
                else:
                    failed_count += 1
                    logger.error(f"❌ Failed to save: {company['company_name']}")
            else:
                failed_count += 1
                logger.error(f"❌ Failed to research: {company['company_name']}")
            
            # Add delay between API calls to avoid rate limiting
            if i < len(companies_to_research):
                logger.debug(f"Waiting {delay_seconds} seconds before next request...")
                time.sleep(delay_seconds)
        
        logger.info(f"""
Company Research Complete!
========================
Total companies processed: {len(companies_to_research)}
Successfully researched: {successful_count}
Failed: {failed_count}
Success rate: {(successful_count/len(companies_to_research)*100):.1f}%
        """)

def main():
    """Main function to run the company research script."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Research companies from contacts table')
    parser.add_argument('--max-companies', type=int, help='Maximum number of companies to process')
    parser.add_argument('--company-id', type=int, help='Research a specific company by ID')
    parser.add_argument('--delay', type=int, default=2, help='Delay between API calls in seconds')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be processed without actually doing it')
    
    args = parser.parse_args()
    
    try:
        researcher = CompanyResearcher()
        
        # Handle single company research
        if args.company_id:
            logger.info(f"Researching single company with ID: {args.company_id}")
            success = researcher.research_single_company_by_id(args.company_id)
            if success:
                logger.info("✅ Single company research completed successfully")
            else:
                logger.error("❌ Single company research failed")
                exit(1)
            return
        
        # Handle batch processing
        if args.dry_run:
            logger.info("DRY RUN MODE - No actual processing will occur")
            contact_companies = researcher.get_unique_companies_from_contacts()
            existing_companies = researcher.get_existing_companies()
            
            companies_to_research = [
                company for company in contact_companies 
                if company['company_name'].lower() not in existing_companies
            ]
            
            if args.max_companies:
                companies_to_research = companies_to_research[:args.max_companies]
            
            logger.info(f"Would process {len(companies_to_research)} companies:")
            for i, company in enumerate(companies_to_research[:10], 1):  # Show first 10
                logger.info(f"  {i}. {company['company_name']} ({company['contact_count']} contacts)")
            
            if len(companies_to_research) > 10:
                logger.info(f"  ... and {len(companies_to_research) - 10} more")
        else:
            researcher.process_companies(
                max_companies=args.max_companies,
                delay_seconds=args.delay
            )
            
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"Script failed with error: {e}")
        raise

if __name__ == "__main__":
    main() 