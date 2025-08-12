#!/usr/bin/env python3
"""
Clear Company Research Script

This script clears the company_research column from all records in the companies table.
"""

import os
import sys
import logging
import argparse
from typing import Optional
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
        logging.FileHandler('clear_company_research.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CompanyResearchCleaner:
    """Handles clearing company research data from the database."""
    
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
        logger.info("CompanyResearchCleaner initialized")

    def get_companies_with_research_count(self, tenant_id: str = None) -> int:
        """Get count of companies that have research data.
        
        Args:
            tenant_id: If provided, only count companies belonging to this tenant.
                      If None, counts all companies across all tenants.
        """
        if tenant_id:
            logger.info(f"Checking companies with research data for tenant {tenant_id}...")
        else:
            logger.info("Checking companies with research data across all tenants...")
        
        try:
            with self.engine.connect() as conn:
                # Build the WHERE clause
                where_conditions = [
                    "company_research IS NOT NULL",
                    "company_research != ''",
                    "markdown_report IS NOT NULL",
                    "strategic_imperatives IS NOT NULL",
                    "agent_recommendations IS NOT NULL",
                    "research_step_1_basic IS NOT NULL",
                    "research_step_2_strategic IS NOT NULL",
                    "research_step_3_report IS NOT NULL",
                    "llm_research_prompt IS NOT NULL",
                    "llm_research_results IS NOT NULL",
                    "llm_research_status IS NOT NULL",
                    "llm_research_step_1_basic IS NOT NULL",
                    "llm_research_step_2_strategic IS NOT NULL",
                    "llm_research_step_3_report IS NOT NULL",
                    "llm_markdown_report IS NOT NULL",
                    "llm_html_report IS NOT NULL",
                    "llm_research_step_status IS NOT NULL"
                ]
                
                where_clause = f"({' OR '.join(where_conditions)})"
                
                # Add tenant filtering if tenant_id is provided
                if tenant_id:
                    where_clause += " AND tenant_id = :tenant_id"
                    params = {"tenant_id": tenant_id}
                else:
                    params = {}
                
                query = f"""
                    SELECT COUNT(*) as count
                    FROM companies 
                    WHERE {where_clause}
                """
                
                result = conn.execute(text(query), params)
                
                count = result.fetchone().count
                logger.info(f"Found {count} companies with research data")
                return count
                
        except SQLAlchemyError as e:
            logger.error(f"Database error checking companies with research: {e}")
            return 0
        except Exception as e:
            logger.error(f"Unexpected error checking companies with research: {e}")
            return 0

    def clear_all_research(self, tenant_id: str = None) -> bool:
        """Clear company research data including LLM fields for companies.
        
        Args:
            tenant_id: If provided, only clear research for companies belonging to this tenant.
                      If None, clears research for ALL companies across ALL tenants (admin use).
        """
        if tenant_id:
            logger.info(f"🚨 CLEARING RESEARCH DATA for tenant {tenant_id}...")
        else:
            logger.info("🚨 CLEARING ALL COMPANY RESEARCH DATA (including LLM fields)...")
            logger.info("⚠️  WARNING: This affects ALL companies across ALL tenants!")
        logger.info("Fields to be cleared: old research, LLM research, step-by-step research, OpenAI tracking")
        
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    # Build the WHERE clause based on tenant filtering
                    where_conditions = [
                        "company_research IS NOT NULL",
                        "company_research != ''",
                        "markdown_report IS NOT NULL",
                        "strategic_imperatives IS NOT NULL",
                        "agent_recommendations IS NOT NULL", 
                        "research_step_1_basic IS NOT NULL",
                        "research_step_2_strategic IS NOT NULL",
                        "research_step_3_report IS NOT NULL",
                        "llm_research_prompt IS NOT NULL",
                        "llm_research_results IS NOT NULL",
                        "llm_research_status IS NOT NULL",
                        "llm_research_step_1_basic IS NOT NULL",
                        "llm_research_step_2_strategic IS NOT NULL",
                        "llm_research_step_3_report IS NOT NULL",
                        "llm_markdown_report IS NOT NULL",
                        "llm_html_report IS NOT NULL",
                        "llm_research_step_status IS NOT NULL",
                        "openai_response_id IS NOT NULL"
                    ]
                    
                    where_clause = f"({' OR '.join(where_conditions)})"
                    
                    # Add tenant filtering if tenant_id is provided
                    if tenant_id:
                        where_clause += " AND tenant_id = :tenant_id"
                        params = {"tenant_id": tenant_id}
                    else:
                        params = {}
                    
                    query = f"""
                        UPDATE companies 
                        SET 
                            -- Old research fields
                            company_research = NULL,
                            markdown_report = NULL,
                            strategic_imperatives = NULL,
                            agent_recommendations = NULL,
                            research_step_1_basic = NULL,
                            research_step_2_strategic = NULL,
                            research_step_3_report = NULL,
                            html_report = NULL,
                            research_status = 'pending',
                            research_started_at = NULL,
                            research_completed_at = NULL,
                            research_error = NULL,
                            
                            -- LLM research fields (from first migration)
                            llm_research_prompt = NULL,
                            llm_research_results = NULL,
                            llm_research_status = NULL,
                            llm_research_method = NULL,
                            llm_research_word_count = NULL,
                            llm_research_character_count = NULL,
                            llm_research_quality_score = NULL,
                            llm_research_updated_at = NULL,
                            
                            -- LLM step-by-step research fields (from second migration)
                            llm_research_step_1_basic = NULL,
                            llm_research_step_2_strategic = NULL,
                            llm_research_step_3_report = NULL,
                            llm_markdown_report = NULL,
                            llm_html_report = NULL,
                            llm_research_step_status = NULL,
                            llm_research_provider = NULL,
                            llm_research_started_at = NULL,
                            llm_research_completed_at = NULL,
                            
                            -- OpenAI background job tracking (if exists)
                            openai_response_id = NULL,
                            
                            -- PDF reports
                            pdf_report_base64 = NULL,
                            llm_pdf_report_base64 = NULL,
                            basic_research_pdf_base64 = NULL,
                            
                            -- Update timestamp
                            updated_at = CURRENT_TIMESTAMP
                        WHERE {where_clause}
                    """
                    
                    result = conn.execute(text(query), params)
                    
                    rows_affected = result.rowcount
                    logger.info(f"✅ Successfully cleared ALL research data (including LLM fields) from {rows_affected} companies")
                    return True
            
        except SQLAlchemyError as e:
            logger.error(f"Database error clearing research data: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error clearing research data: {e}")
            return False

    def clear_research_by_company_id(self, company_id: int) -> bool:
        """Clear research data for a specific company by ID."""
        logger.info(f"Clearing research data for company ID: {company_id}")
        
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    # First check if company exists
                    check_result = conn.execute(text("""
                        SELECT company_name FROM companies WHERE id = :company_id
                    """), {"company_id": company_id})
                    
                    company_row = check_result.fetchone()
                    if not company_row:
                        logger.warning(f"No company found with ID: {company_id}")
                        return False
                    
                    # Clear the research data - ALL fields including LLM
                    result = conn.execute(text("""
                        UPDATE companies 
                        SET 
                            -- Old research fields
                            company_research = NULL,
                            markdown_report = NULL,
                            strategic_imperatives = NULL,
                            agent_recommendations = NULL,
                            research_step_1_basic = NULL,
                            research_step_2_strategic = NULL,
                            research_step_3_report = NULL,
                            html_report = NULL,
                            research_status = 'pending',
                            research_started_at = NULL,
                            research_completed_at = NULL,
                            research_error = NULL,
                            
                            -- LLM research fields (from first migration)
                            llm_research_prompt = NULL,
                            llm_research_results = NULL,
                            llm_research_status = NULL,
                            llm_research_method = NULL,
                            llm_research_word_count = NULL,
                            llm_research_character_count = NULL,
                            llm_research_quality_score = NULL,
                            llm_research_updated_at = NULL,
                            
                            -- LLM step-by-step research fields (from second migration)
                            llm_research_step_1_basic = NULL,
                            llm_research_step_2_strategic = NULL,
                            llm_research_step_3_report = NULL,
                            llm_markdown_report = NULL,
                            llm_html_report = NULL,
                            llm_research_step_status = NULL,
                            llm_research_provider = NULL,
                            llm_research_started_at = NULL,
                            llm_research_completed_at = NULL,
                            
                            -- OpenAI background job tracking (if exists)
                            openai_response_id = NULL,
                            
                            -- Update timestamp
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :company_id
                    """), {"company_id": company_id})
                    
                    if result.rowcount > 0:
                        logger.info(f"Successfully cleared research data for company: {company_row.company_name}")
                        return True
                    else:
                        logger.warning(f"No research data to clear for company ID: {company_id}")
                        return False
            
        except SQLAlchemyError as e:
            logger.error(f"Database error clearing research for company {company_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error clearing research for company {company_id}: {e}")
            return False

    def clear_research_by_company_name(self, company_name: str) -> bool:
        """Clear research data for a specific company by name."""
        logger.info(f"Clearing research data for company: {company_name}")
        
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    result = conn.execute(text("""
                        UPDATE companies 
                        SET 
                            -- Old research fields
                            company_research = NULL,
                            markdown_report = NULL,
                            strategic_imperatives = NULL,
                            agent_recommendations = NULL,
                            research_step_1_basic = NULL,
                            research_step_2_strategic = NULL,
                            research_step_3_report = NULL,
                            html_report = NULL,
                            research_status = 'pending',
                            research_started_at = NULL,
                            research_completed_at = NULL,
                            research_error = NULL,
                            
                            -- LLM research fields (from first migration)
                            llm_research_prompt = NULL,
                            llm_research_results = NULL,
                            llm_research_status = NULL,
                            llm_research_method = NULL,
                            llm_research_word_count = NULL,
                            llm_research_character_count = NULL,
                            llm_research_quality_score = NULL,
                            llm_research_updated_at = NULL,
                            
                            -- LLM step-by-step research fields (from second migration)
                            llm_research_step_1_basic = NULL,
                            llm_research_step_2_strategic = NULL,
                            llm_research_step_3_report = NULL,
                            llm_markdown_report = NULL,
                            llm_html_report = NULL,
                            llm_research_step_status = NULL,
                            llm_research_provider = NULL,
                            llm_research_started_at = NULL,
                            llm_research_completed_at = NULL,
                            
                            -- OpenAI background job tracking (if exists)
                            openai_response_id = NULL,
                            
                            -- Update timestamp
                            updated_at = CURRENT_TIMESTAMP
                        WHERE LOWER(company_name) = LOWER(:company_name)
                    """), {"company_name": company_name})
                    
                    rows_affected = result.rowcount
                    if rows_affected > 0:
                        logger.info(f"Successfully cleared research data for {rows_affected} company/companies named: {company_name}")
                        return True
                    else:
                        logger.warning(f"No company found with name: {company_name}")
                        return False
            
        except SQLAlchemyError as e:
            logger.error(f"Database error clearing research for company {company_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error clearing research for company {company_name}: {e}")
            return False

def main():
    """Main function to run the company research clearing script."""
    parser = argparse.ArgumentParser(description='Clear company research data from companies table')
    parser.add_argument('--company-id', type=int, help='Clear research for a specific company by ID')
    parser.add_argument('--company-name', type=str, help='Clear research for a specific company by name')
    parser.add_argument('--all', action='store_true', help='Clear research data for all companies')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be cleared without actually doing it')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not any([args.company_id, args.company_name, args.all]):
        parser.error("Must specify one of: --company-id, --company-name, or --all")
    
    if sum([bool(args.company_id), bool(args.company_name), args.all]) > 1:
        parser.error("Can only specify one of: --company-id, --company-name, or --all")
    
    try:
        cleaner = CompanyResearchCleaner()
        
        if args.dry_run:
            logger.info("DRY RUN MODE - No actual clearing will occur")
            count = cleaner.get_companies_with_research_count()
            
            if args.all:
                logger.info(f"Would clear research data from {count} companies")
            elif args.company_id:
                logger.info(f"Would clear research data for company ID: {args.company_id}")
            elif args.company_name:
                logger.info(f"Would clear research data for company: {args.company_name}")
            return
        
        # Perform the actual clearing
        if args.all:
            if input("Are you sure you want to clear research data for ALL companies? (yes/no): ").lower() == 'yes':
                success = cleaner.clear_all_research()
                if success:
                    logger.info("✅ Successfully cleared all company research data")
                else:
                    logger.error("❌ Failed to clear company research data")
                    exit(1)
            else:
                logger.info("Operation cancelled by user")
        
        elif args.company_id:
            success = cleaner.clear_research_by_company_id(args.company_id)
            if success:
                logger.info(f"✅ Successfully cleared research data for company ID: {args.company_id}")
            else:
                logger.error(f"❌ Failed to clear research data for company ID: {args.company_id}")
                exit(1)
        
        elif args.company_name:
            success = cleaner.clear_research_by_company_name(args.company_name)
            if success:
                logger.info(f"✅ Successfully cleared research data for company: {args.company_name}")
            else:
                logger.error(f"❌ Failed to clear research data for company: {args.company_name}")
                exit(1)
            
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"Script failed with error: {e}")
        raise

if __name__ == "__main__":
    main() 