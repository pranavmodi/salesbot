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
        # Use shared engine instead of creating a new one
        try:
            from app.database import get_shared_engine
            self.engine = get_shared_engine()
            logger.info("DatabaseService initialized with shared engine")
        except Exception as e:
            logger.error(f"Failed to get shared engine: {e}")
            # Fallback to creating minimal engine
            self.database_url = os.getenv("DATABASE_URL")
            if not self.database_url:
                raise ValueError("DATABASE_URL not found in environment variables")
            self.engine = create_engine(
                self.database_url,
                pool_size=1,
                max_overflow=1,
                pool_pre_ping=True,
                pool_recycle=1800
            )
            logger.warning("DatabaseService using fallback engine")

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

    def get_companies_with_research(self) -> Set[str]:
        """Get set of company names that already have research data."""
        logger.info("Checking companies with existing research...")
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT company_name FROM companies 
                    WHERE company_research IS NOT NULL AND company_research != ''
                """))
                existing = {row.company_name.strip().lower() for row in result}
                logger.info(f"Found {len(existing)} companies with existing research")
                return existing
                
        except SQLAlchemyError as e:
            logger.error(f"Database error checking companies with research: {e}")
            return set()
        except Exception as e:
            logger.error(f"Unexpected error checking companies with research: {e}")
            return set()

    def get_companies_without_research(self) -> List[Dict]:
        """Get companies that exist but don't have research data."""
        logger.info("Fetching companies without research...")
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, company_name, website_url, created_at
                    FROM companies 
                    WHERE company_research IS NULL OR company_research = ''
                    ORDER BY created_at ASC
                """))
                
                companies = []
                for row in result:
                    companies.append({
                        'id': row.id,
                        'company_name': row.company_name,
                        'website_url': row.website_url,
                        'created_at': row.created_at
                    })
                
                logger.info(f"Found {len(companies)} companies without research")
                return companies
                
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching companies without research: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching companies without research: {e}")
            return []

    def save_company_research(self, company_name: str, website_url: str, research: str, markdown_report: str = None, 
                            strategic_imperatives: str = None, agent_recommendations: str = None) -> bool:
        """Save company research to the companies table."""
        logger.info(f"Saving research for: {company_name}")
        
        company_data = {
            'company_name': company_name,
            'website_url': website_url,
            'company_research': research,
            'markdown_report': markdown_report,
            'strategic_imperatives': strategic_imperatives,
            'agent_recommendations': agent_recommendations
        }
        
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    insert_query = text("""
                        INSERT INTO companies (company_name, website_url, company_research, markdown_report, strategic_imperatives, agent_recommendations) 
                        VALUES (:company_name, :website_url, :company_research, :markdown_report, :strategic_imperatives, :agent_recommendations)
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

    def update_company_research(self, company_id: int, research: str, markdown_report: str = None, 
                              strategic_imperatives: str = None, agent_recommendations: str = None) -> bool:
        """Update existing company research in the companies table."""
        logger.info(f"Updating research for company ID: {company_id}")
        
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    update_params = {
                        'research': research,
                        'company_id': company_id
                    }
                    
                    update_fields = ['company_research = :research']
                    
                    if markdown_report is not None:
                        update_fields.append('markdown_report = :markdown_report')
                        update_params['markdown_report'] = markdown_report
                    
                    if strategic_imperatives is not None:
                        update_fields.append('strategic_imperatives = :strategic_imperatives')
                        update_params['strategic_imperatives'] = strategic_imperatives
                    
                    if agent_recommendations is not None:
                        update_fields.append('agent_recommendations = :agent_recommendations')
                        update_params['agent_recommendations'] = agent_recommendations
                    
                    update_query = text(f"""
                        UPDATE companies 
                        SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                        WHERE id = :company_id
                    """)
                    result = conn.execute(update_query, update_params)
                    
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
                    SELECT id, company_name, website_url, company_research, markdown_report, strategic_imperatives, agent_recommendations
                    FROM companies 
                    WHERE id = :company_id
                """), {"company_id": company_id})
                
                row = result.fetchone()
                if row:
                    return {
                        'id': row.id,
                        'company_name': row.company_name,
                        'website_url': row.website_url,
                        'company_research': row.company_research,
                        'markdown_report': row.markdown_report,
                        'strategic_imperatives': row.strategic_imperatives,
                        'agent_recommendations': row.agent_recommendations
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

    def get_company_markdown_report(self, company_id: int) -> Optional[str]:
        """Get just the markdown report for a specific company by ID."""
        logger.info(f"Fetching markdown report for company ID: {company_id}")
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT markdown_report FROM companies 
                    WHERE id = :company_id
                """), {"company_id": company_id})
                
                row = result.fetchone()
                if row:
                    return row.markdown_report
                else:
                    logger.warning(f"No company found with ID: {company_id}")
                    return None
                    
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching markdown report for company {company_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching markdown report for company {company_id}: {e}")
            return None

    def get_companies_with_reports(self) -> List[Dict]:
        """Get all companies that have markdown reports."""
        logger.info("Fetching companies with markdown reports...")
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, company_name, website_url, created_at, updated_at
                    FROM companies 
                    WHERE markdown_report IS NOT NULL
                    ORDER BY updated_at DESC
                """))
                
                companies = []
                for row in result:
                    companies.append({
                        'id': row.id,
                        'company_name': row.company_name,
                        'website_url': row.website_url,
                        'created_at': row.created_at,
                        'updated_at': row.updated_at
                    })
                
                logger.info(f"Found {len(companies)} companies with markdown reports")
                return companies
                
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching companies with reports: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching companies with reports: {e}")
            return []

    def update_existing_company_by_name(self, company_name: str, website_url: str, research: str, markdown_report: str = None, 
                                      strategic_imperatives: str = None, agent_recommendations: str = None) -> bool:
        """Update existing company research by company name."""
        logger.info(f"Updating existing company by name: {company_name}")
        
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    update_params = {
                        'website_url': website_url,
                        'research': research,
                        'company_name': company_name
                    }
                    
                    update_fields = ['website_url = :website_url', 'company_research = :research']
                    
                    if markdown_report is not None:
                        update_fields.append('markdown_report = :markdown_report')
                        update_params['markdown_report'] = markdown_report
                    
                    if strategic_imperatives is not None:
                        update_fields.append('strategic_imperatives = :strategic_imperatives')
                        update_params['strategic_imperatives'] = strategic_imperatives
                    
                    if agent_recommendations is not None:
                        update_fields.append('agent_recommendations = :agent_recommendations')
                        update_params['agent_recommendations'] = agent_recommendations
                    
                    update_query = text(f"""
                        UPDATE companies 
                        SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                        WHERE LOWER(company_name) = LOWER(:company_name)
                    """)
                    result = conn.execute(update_query, update_params)
                    
                    if result.rowcount > 0:
                        logger.info(f"Successfully updated existing company: {company_name}")
                        return True
                    else:
                        logger.warning(f"No company found with name: {company_name}")
                        return False
            
        except SQLAlchemyError as e:
            logger.error(f"Database error updating company {company_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error updating company {company_name}: {e}")
            return False

    def update_company_research_with_reports(self, company_id: int, research: str, html_report: str = None, 
                                           pdf_report_base64: str = None, strategic_imperatives: str = None, 
                                           agent_recommendations: str = None) -> bool:
        """Update company research with HTML/PDF reports and strategic data."""
        logger.info(f"Updating research with reports for company ID: {company_id}")
        
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    update_params = {
                        'research': research,
                        'company_id': company_id
                    }
                    
                    update_fields = ['company_research = :research']
                    
                    if html_report is not None:
                        update_fields.append('html_report = :html_report')
                        update_params['html_report'] = html_report
                    
                    if pdf_report_base64 is not None:
                        update_fields.append('pdf_report_base64 = :pdf_report_base64')
                        update_params['pdf_report_base64'] = pdf_report_base64
                    
                    if strategic_imperatives is not None:
                        update_fields.append('strategic_imperatives = :strategic_imperatives')
                        update_params['strategic_imperatives'] = strategic_imperatives
                    
                    if agent_recommendations is not None:
                        update_fields.append('agent_recommendations = :agent_recommendations')
                        update_params['agent_recommendations'] = agent_recommendations
                    
                    update_query = text(f"""
                        UPDATE companies 
                        SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                        WHERE id = :company_id
                    """)
                    result = conn.execute(update_query, update_params)
                    
                    if result.rowcount > 0:
                        logger.info(f"Successfully updated research with reports for company ID: {company_id}")
                        return True
                    else:
                        logger.warning(f"No company found with ID: {company_id}")
                        return False
            
        except SQLAlchemyError as e:
            logger.error(f"Database error updating company reports {company_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error updating company reports {company_id}: {e}")
            return False