#!/usr/bin/env python3
"""
Data migration script to move leadgen data from the original database to salesbot.
This script migrates companies, job postings, scraping logs, and seeding sessions.
"""
import os
import sys
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import get_shared_engine
from app.models.leadgen_models import LeadgenCompany, LeadgenJobPosting, LeadgenScrapingLog, LeadgenSeedingSession

class LeadgenDataMigrator:
    def __init__(self, source_db_url: str, default_tenant_id: str = "default"):
        """
        Initialize the migrator.
        
        Args:
            source_db_url: Connection string to the original leadgen database
            default_tenant_id: Default tenant ID for migrated data
        """
        self.source_db_url = source_db_url
        self.default_tenant_id = default_tenant_id
        self.target_engine = get_shared_engine()
        
        # Create source database connection
        try:
            self.source_engine = create_engine(source_db_url)
            logger.info("✅ Connected to source leadgen database")
        except Exception as e:
            logger.error(f"❌ Failed to connect to source database: {e}")
            raise
        
        # Create sessions
        self.SourceSession = sessionmaker(bind=self.source_engine)
        self.TargetSession = sessionmaker(bind=self.target_engine)
    
    def check_source_tables(self) -> dict:
        """Check which tables exist in the source database."""
        tables = {}
        with self.source_engine.connect() as conn:
            # Check for companies table
            result = conn.execute(text("""
                SELECT COUNT(*) as count FROM information_schema.tables 
                WHERE table_name = 'companies'
            """))
            tables['companies'] = result.fetchone().count > 0
            
            # Check for job_postings table
            result = conn.execute(text("""
                SELECT COUNT(*) as count FROM information_schema.tables 
                WHERE table_name = 'job_postings'
            """))
            tables['job_postings'] = result.fetchone().count > 0
            
            # Check for scraping_logs table
            result = conn.execute(text("""
                SELECT COUNT(*) as count FROM information_schema.tables 
                WHERE table_name = 'scraping_logs'
            """))
            tables['scraping_logs'] = result.fetchone().count > 0
            
            # Check for seeding_sessions table
            result = conn.execute(text("""
                SELECT COUNT(*) as count FROM information_schema.tables 
                WHERE table_name = 'seeding_sessions'
            """))
            tables['seeding_sessions'] = result.fetchone().count > 0
        
        return tables
    
    def get_source_counts(self) -> dict:
        """Get record counts from source database."""
        counts = {}
        available_tables = self.check_source_tables()
        
        with self.source_engine.connect() as conn:
            for table, exists in available_tables.items():
                if exists:
                    result = conn.execute(text(f"SELECT COUNT(*) as count FROM {table}"))
                    counts[table] = result.fetchone().count
                else:
                    counts[table] = 0
        
        return counts
    
    def migrate_companies(self) -> int:
        """Migrate companies from source to target database."""
        logger.info("🏢 Starting company migration...")
        
        available_tables = self.check_source_tables()
        if not available_tables.get('companies'):
            logger.warning("⚠️ Source 'companies' table not found, skipping...")
            return 0
        
        migrated_count = 0
        
        with self.source_engine.connect() as source_conn:
            with self.TargetSession() as target_session:
                # Get all companies from source
                result = source_conn.execute(text("""
                    SELECT * FROM companies ORDER BY created_at ASC
                """))
                
                for row in result:
                    try:
                        # Check if company already exists in target
                        existing = target_session.query(LeadgenCompany).filter(
                            LeadgenCompany.name == row.name,
                            LeadgenCompany.domain == row.domain
                        ).first()
                        
                        if existing:
                            logger.debug(f"⏭️ Company already exists: {row.name}")
                            continue
                        
                        # Create new company in target database
                        new_company = LeadgenCompany(
                            name=row.name,
                            domain=row.domain,
                            industry=row.industry,
                            employee_count=row.employee_count,
                            location=row.location,
                            founded_year=row.founded_year,
                            technology_stack=row.technology_stack,
                            linkedin_url=row.linkedin_url,
                            source=row.source,
                            created_at=row.created_at,
                            updated_at=row.updated_at,
                            is_active=row.is_active,
                            ats_scraped=row.ats_scraped,
                            ats_scraped_at=row.ats_scraped_at,
                            last_scrape_status=row.last_scrape_status,
                            support_roles_count=row.support_roles_count,
                            sales_roles_count=row.sales_roles_count,
                            ai_roles_count=row.ai_roles_count,
                            lead_score=row.lead_score,
                            is_qualified_lead=row.is_qualified_lead,
                            support_intensity_score=getattr(row, 'support_intensity_score', 0),
                            digital_presence_score=getattr(row, 'digital_presence_score', 0),
                            growth_signals_score=getattr(row, 'growth_signals_score', 0),
                            implementation_feasibility_score=getattr(row, 'implementation_feasibility_score', 0),
                            lead_scoring_data=getattr(row, 'lead_scoring_data', None),
                            lead_scored_at=getattr(row, 'lead_scored_at', None),
                            tenant_id=getattr(row, 'tenant_id', None),
                            tenant_created_at=getattr(row, 'tenant_created_at', None),
                            salesbot_tenant_id=self.default_tenant_id
                        )
                        
                        target_session.add(new_company)
                        migrated_count += 1
                        
                        if migrated_count % 100 == 0:
                            target_session.commit()
                            logger.info(f"💾 Migrated {migrated_count} companies so far...")
                    
                    except Exception as e:
                        logger.error(f"❌ Error migrating company {row.name}: {e}")
                        target_session.rollback()
                        continue
                
                target_session.commit()
        
        logger.info(f"✅ Migrated {migrated_count} companies")
        return migrated_count
    
    def migrate_job_postings(self) -> int:
        """Migrate job postings from source to target database."""
        logger.info("💼 Starting job postings migration...")
        
        available_tables = self.check_source_tables()
        if not available_tables.get('job_postings'):
            logger.warning("⚠️ Source 'job_postings' table not found, skipping...")
            return 0
        
        migrated_count = 0
        company_id_mapping = {}
        
        # First, build a mapping of old company IDs to new ones
        with self.TargetSession() as target_session:
            companies = target_session.query(LeadgenCompany).all()
            for company in companies:
                # Use name+domain as key for mapping (since original IDs might be different)
                key = f"{company.name}|{company.domain or ''}"
                company_id_mapping[key] = company.id
        
        with self.source_engine.connect() as source_conn:
            with self.TargetSession() as target_session:
                # Get all job postings from source
                result = source_conn.execute(text("""
                    SELECT jp.*, c.name as company_name, c.domain as company_domain
                    FROM job_postings jp
                    LEFT JOIN companies c ON jp.company_id = c.id
                    ORDER BY jp.created_at ASC
                """))
                
                for row in result:
                    try:
                        # Find the corresponding company in target database
                        company_key = f"{row.company_name}|{row.company_domain or ''}"
                        target_company_id = company_id_mapping.get(company_key)
                        
                        if not target_company_id:
                            logger.warning(f"⚠️ Company not found for job posting: {row.title} at {row.company_name}")
                            continue
                        
                        # Create new job posting in target database
                        new_job_posting = LeadgenJobPosting(
                            company_id=target_company_id,
                            external_id=row.external_id,
                            title=row.title,
                            department=row.department,
                            location=row.location,
                            description=row.description,
                            requirements=row.requirements,
                            job_url=row.job_url,
                            role_category=row.role_category,
                            seniority_level=row.seniority_level,
                            ats_source=row.ats_source,
                            posted_date=row.posted_date,
                            created_at=row.created_at,
                            updated_at=row.updated_at,
                            is_active=row.is_active,
                            salesbot_tenant_id=self.default_tenant_id
                        )
                        
                        target_session.add(new_job_posting)
                        migrated_count += 1
                        
                        if migrated_count % 100 == 0:
                            target_session.commit()
                            logger.info(f"💾 Migrated {migrated_count} job postings so far...")
                    
                    except Exception as e:
                        logger.error(f"❌ Error migrating job posting {row.title}: {e}")
                        target_session.rollback()
                        continue
                
                target_session.commit()
        
        logger.info(f"✅ Migrated {migrated_count} job postings")
        return migrated_count
    
    def migrate_all(self) -> dict:
        """Migrate all data from source to target database."""
        logger.info("🚀 Starting complete leadgen data migration...")
        
        # Check source database
        source_counts = self.get_source_counts()
        logger.info("📊 Source database counts:")
        for table, count in source_counts.items():
            logger.info(f"  {table}: {count}")
        
        if sum(source_counts.values()) == 0:
            logger.warning("⚠️ No data found in source database")
            return {'migrated': 0, 'errors': 0}
        
        results = {
            'companies': 0,
            'job_postings': 0,
            'scraping_logs': 0,
            'seeding_sessions': 0,
            'errors': 0
        }
        
        try:
            # Migrate companies first (required for foreign keys)
            results['companies'] = self.migrate_companies()
            
            # Migrate job postings (depends on companies)
            results['job_postings'] = self.migrate_job_postings()
            
            # TODO: Add migration for scraping_logs and seeding_sessions if needed
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            results['errors'] += 1
        
        total_migrated = results['companies'] + results['job_postings']
        logger.info(f"🎉 Migration completed! Total records migrated: {total_migrated}")
        
        return results

def main():
    """Main migration function."""
    # Check for source database URL
    source_db_url = os.getenv('LEADGEN_SOURCE_DB_URL')
    if not source_db_url:
        logger.error("❌ LEADGEN_SOURCE_DB_URL environment variable not set")
        logger.info("💡 Set it like: export LEADGEN_SOURCE_DB_URL='postgresql://user:pass@host:port/leadgen_db'")
        return
    
    # Get default tenant ID (or use 'default')
    default_tenant_id = os.getenv('DEFAULT_TENANT_ID', 'default')
    logger.info(f"🔧 Using default tenant ID: {default_tenant_id}")
    
    try:
        # Initialize migrator
        migrator = LeadgenDataMigrator(source_db_url, default_tenant_id)
        
        # Run migration
        results = migrator.migrate_all()
        
        # Print summary
        logger.info("📋 Migration Summary:")
        for key, value in results.items():
            if key != 'errors':
                logger.info(f"  {key}: {value} records migrated")
        
        if results['errors'] > 0:
            logger.warning(f"⚠️ {results['errors']} errors occurred during migration")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()