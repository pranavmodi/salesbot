#!/usr/bin/env python3
"""
Database Service

Handles all database operations for company research including:
- Extracting companies from contacts
- Managing company records
- CRUD operations on companies table
"""

import os
import logging
from typing import Dict, List, Optional, Set
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

class DatabaseService:
    """Handles all database operations for company research."""
    
    def __init__(self):
        load_dotenv()
        self.database_url = os.getenv("DATABASE_URL")
        
        if not self.database_url:
            raise ValueError("DATABASE_URL not found in environment variables")
        
        self.engine = create_engine(self.database_url)
        logger.info("DatabaseService initialized")

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