#!/usr/bin/env python3
"""
Extract Companies Script

This script extracts unique companies from the contacts table 
and inserts them into the companies table as placeholders.
"""

import os
import sys
import logging
from typing import Dict, List, Set
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Add the parent directory to sys.path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('extract_companies.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CompanyExtractor:
    """Handles extracting companies from contacts and inserting into companies table."""
    
    def __init__(self):
        load_dotenv()
        self.database_url = os.getenv("DATABASE_URL")
        
        if not self.database_url:
            raise ValueError("DATABASE_URL not found in environment variables")
        
        self.engine = create_engine(
            self.database_url,
            pool_size=5,          # Maximum number of permanent connections
            max_overflow=10,      # Maximum number of connections that can overflow the pool
            pool_pre_ping=True,   # Verify connections before use
            pool_recycle=3600     # Recycle connections every hour
        )
        logger.info("CompanyExtractor initialized")

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
                      AND TRIM(company_name) != ''
                    GROUP BY company_name, company_domain
                    ORDER BY contact_count DESC, company_name ASC
                """))
                
                companies = []
                for row in result:
                    company_name = row.company_name.strip()
                    company_domain = row.company_domain.strip() if row.company_domain else ''
                    
                    # Create website URL from domain
                    website_url = ''
                    if company_domain:
                        if not company_domain.startswith(('http://', 'https://')):
                            website_url = f"https://{company_domain}"
                        else:
                            website_url = company_domain
                    
                    companies.append({
                        'company_name': company_name,
                        'company_domain': company_domain,
                        'website_url': website_url,
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

    def insert_company_placeholder(self, company_data: Dict) -> bool:
        """Insert a company placeholder into the companies table."""
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    insert_query = text("""
                        INSERT INTO companies (company_name, website_url, company_research) 
                        VALUES (:company_name, :website_url, :company_research)
                    """)
                    conn.execute(insert_query, {
                        'company_name': company_data['company_name'],
                        'website_url': company_data['website_url'],
                        'company_research': f"Company extracted from contacts table. {company_data['contact_count']} contacts from this company. Research pending."
                    })
            
            logger.info(f"Successfully inserted placeholder for: {company_data['company_name']}")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Database error inserting company {company_data['company_name']}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error inserting company {company_data['company_name']}: {e}")
            return False

    def extract_and_insert_companies(self):
        """Main processing function to extract companies and insert placeholders."""
        logger.info("Starting company extraction process...")
        
        # Get unique companies from contacts
        contact_companies = self.get_unique_companies_from_contacts()
        if not contact_companies:
            logger.warning("No companies found in contacts table")
            return {'success': False, 'message': 'No companies found in contacts table'}
        
        # Get existing companies to avoid duplicates
        existing_companies = self.get_existing_companies()
        
        # Filter out companies that already exist
        new_companies = []
        for company in contact_companies:
            if company['company_name'].strip().lower() not in existing_companies:
                new_companies.append(company)
        
        if not new_companies:
            logger.info("All companies from contacts already exist in companies table")
            return {'success': True, 'message': 'All companies already exist in companies table', 'inserted': 0}
        
        logger.info(f"Found {len(new_companies)} new companies to insert")
        
        # Insert new companies
        inserted_count = 0
        failed_count = 0
        
        for company in new_companies:
            if self.insert_company_placeholder(company):
                inserted_count += 1
            else:
                failed_count += 1
        
        logger.info(f"Company extraction completed. Inserted: {inserted_count}, Failed: {failed_count}")
        return {
            'success': True,
            'message': f'Successfully inserted {inserted_count} companies. {failed_count} failed.',
            'inserted': inserted_count,
            'failed': failed_count
        }

def main():
    """Main function to run the company extraction."""
    try:
        extractor = CompanyExtractor()
        result = extractor.extract_and_insert_companies()
        
        if result['success']:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result['message']}")
            
    except Exception as e:
        logger.error(f"Fatal error in company extraction: {e}")
        print(f"❌ Fatal error: {e}")

if __name__ == "__main__":
    main() 