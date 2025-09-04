#!/usr/bin/env python3
"""
Database-Aware Company Seeder for Lead Generation Tool

Integrates the existing company seeding logic with the PostgreSQL database.
Stores companies directly in the database instead of CSV files.
"""

import os
import uuid
import logging
from typing import List, Optional
from datetime import datetime

from company_seeder import CompanySeeder, CompanyProfile
from database import get_database_manager
from models import Company, SeedingSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseSeeder:
    """Database-aware company seeder that stores results in PostgreSQL"""
    
    def __init__(self):
        self.db_manager = get_database_manager()
        self.company_seeder = CompanySeeder()
    
    def seed_companies_to_database(
        self,
        target_count: int = 3000,
        use_apollo: bool = False,
        apollo_api_key: Optional[str] = None,
        use_yc_data: bool = True,
        use_csv_import: bool = True,
        csv_file: str = "data/company_import.csv",
        min_employees: int = 50,
        max_employees: int = 100,
        exclude_ai_companies: bool = True,
        use_clearbit_enrichment: bool = False,
        session_id: Optional[str] = None
    ) -> dict:
        """
        Seed companies from multiple sources and store in database
        
        Returns:
            dict: Summary of seeding results
        """
        if not session_id:
            session_id = str(uuid.uuid4())
        
        logger.info(f"🌱 Starting database seeding session: {session_id}")
        
        # Create seeding session record
        seeding_session = self._create_seeding_session(session_id, {
            'target_count': target_count,
            'use_apollo': use_apollo,
            'use_yc_data': use_yc_data,
            'use_csv_import': use_csv_import,
            'min_employees': min_employees,
            'max_employees': max_employees,
            'exclude_ai_companies': exclude_ai_companies
        })
        
        try:
            all_companies = []
            
            # Set Apollo API key temporarily if provided
            original_apollo_key = None
            if apollo_api_key:
                original_apollo_key = os.environ.get('APOLLO_API_KEY')
                os.environ['APOLLO_API_KEY'] = apollo_api_key
            
            # Seed from Apollo if enabled
            if use_apollo and (apollo_api_key or self.company_seeder.apollo_api_key):
                logger.info("Fetching companies from Apollo.io...")
                apollo_companies = self.company_seeder.seed_from_apollo(target_count=target_count)
                all_companies.extend(apollo_companies)
                logger.info(f"Found {len(apollo_companies)} companies from Apollo")
            
            # Add Y Combinator data if enabled
            if use_yc_data:
                logger.info("Adding Y Combinator companies...")
                yc_companies = self.company_seeder.seed_from_yc_companies()
                all_companies.extend(yc_companies)
                logger.info(f"Added {len(yc_companies)} Y Combinator companies")
            
            # Import from CSV if enabled
            if use_csv_import and os.path.exists(csv_file):
                logger.info(f"Importing companies from CSV: {csv_file}")
                csv_companies = self.company_seeder.seed_from_csv(csv_file)
                all_companies.extend(csv_companies)
                logger.info(f"Imported {len(csv_companies)} companies from CSV")
            
            # Restore original Apollo API key
            if original_apollo_key is not None:
                os.environ['APOLLO_API_KEY'] = original_apollo_key
            elif apollo_api_key and 'APOLLO_API_KEY' in os.environ:
                del os.environ['APOLLO_API_KEY']
            
            # Remove duplicates based on domain
            unique_companies = {}
            for company in all_companies:
                if company.domain and company.domain not in unique_companies:
                    unique_companies[company.domain] = company
            all_companies = list(unique_companies.values())
            
            logger.info(f"Total unique companies after deduplication: {len(all_companies)}")
            
            # Apply filters
            filtered_companies = self.company_seeder.filter_companies(
                all_companies,
                min_employees=min_employees,
                max_employees=max_employees,
                exclude_industries=['AI/ML', 'Machine Learning', 'Data Science'] if exclude_ai_companies else []
            )
            
            logger.info(f"Companies after filtering: {len(filtered_companies)}")
            
            # Enrich with Clearbit if requested and API key available
            if use_clearbit_enrichment and self.company_seeder.clearbit_api_key:
                logger.info("Enriching companies with Clearbit data...")
                filtered_companies = self.company_seeder.enrich_with_clearbit(filtered_companies)
            
            # Store companies in database
            stored_count = self._store_companies_in_database(filtered_companies)
            
            # Update seeding session
            self._update_seeding_session(
                session_id,
                status='completed',
                companies_found=len(all_companies),
                companies_imported=stored_count
            )
            
            result = {
                'session_id': session_id,
                'status': 'completed',
                'total_found': len(all_companies),
                'after_deduplication': len(unique_companies),
                'after_filtering': len(filtered_companies),
                'stored_in_database': stored_count,
                'message': f'Successfully seeded {stored_count} companies to database'
            }
            
            logger.info(f"✅ Seeding completed: {stored_count} companies stored")
            return result
            
        except Exception as e:
            logger.error(f"Seeding failed: {e}")
            
            # Update session with failure
            self._update_seeding_session(
                session_id,
                status='failed',
                error_message=str(e)
            )
            
            return {
                'session_id': session_id,
                'status': 'failed',
                'error': str(e),
                'message': f'Seeding failed: {str(e)}'
            }
    
    def _create_seeding_session(self, session_id: str, config: dict) -> SeedingSession:
        """Create a new seeding session record"""
        with self.db_manager.session_scope() as session:
            seeding_session = SeedingSession(
                session_id=session_id,
                source='mixed',  # Multiple sources
                status='in_progress',
                config=config
            )
            session.add(seeding_session)
            session.commit()
            session.refresh(seeding_session)
            return seeding_session
    
    def _update_seeding_session(
        self,
        session_id: str,
        status: str,
        companies_found: int = 0,
        companies_imported: int = 0,
        error_message: Optional[str] = None
    ):
        """Update seeding session with results"""
        with self.db_manager.session_scope() as session:
            # Get fresh instance from database
            fresh_session = session.query(SeedingSession).filter(
                SeedingSession.session_id == session_id
            ).first()
            
            if fresh_session:
                fresh_session.status = status
                fresh_session.companies_found = companies_found
                fresh_session.companies_imported = companies_imported
                fresh_session.completed_at = datetime.now()
                if error_message:
                    fresh_session.error_message = error_message
                session.commit()
    
    def _store_companies_in_database(self, companies: List[CompanyProfile]) -> int:
        """Store CompanyProfile objects in the database"""
        stored_count = 0
        
        with self.db_manager.session_scope() as session:
            for company_profile in companies:
                try:
                    # Check if company already exists by domain
                    existing = session.query(Company).filter(
                        Company.domain == company_profile.domain
                    ).first()
                    
                    if existing:
                        # Update existing company if needed
                        if not existing.is_active:
                            existing.is_active = True
                            existing.updated_at = datetime.now()
                            logger.debug(f"Reactivated existing company: {company_profile.name}")
                        continue
                    
                    # Create new company record
                    db_company = Company(
                        name=company_profile.name,
                        domain=company_profile.domain,
                        industry=company_profile.industry,
                        employee_count=company_profile.employee_count,
                        location=company_profile.location,
                        founded_year=company_profile.founded_year,
                        technology_stack=company_profile.technology_stack or [],
                        linkedin_url=company_profile.linkedin_url,
                        source=company_profile.source
                    )
                    
                    session.add(db_company)
                    stored_count += 1
                    
                    if stored_count % 100 == 0:
                        logger.info(f"Stored {stored_count} companies so far...")
                        session.commit()  # Periodic commit for large batches
                
                except Exception as e:
                    logger.error(f"Failed to store company {company_profile.name}: {e}")
                    continue
            
            # Final commit
            session.commit()
        
        logger.info(f"Successfully stored {stored_count} new companies in database")
        return stored_count
    
    def get_companies_from_database(
        self,
        limit: int = 1000,
        source: Optional[str] = None,
        is_active: bool = True,
        min_employees: Optional[int] = None,
        max_employees: Optional[int] = None
    ) -> List[Company]:
        """Retrieve companies from database with filtering"""
        with self.db_manager.session_scope() as session:
            query = session.query(Company).filter(Company.is_active == is_active)
            
            if source:
                query = query.filter(Company.source == source)
            if min_employees:
                query = query.filter(Company.employee_count >= min_employees)
            if max_employees:
                query = query.filter(Company.employee_count <= max_employees)
            
            companies = query.order_by(Company.created_at.desc()).limit(limit).all()
            return companies
    
    def get_seeding_sessions(self, limit: int = 10) -> List[SeedingSession]:
        """Get recent seeding sessions"""
        with self.db_manager.session_scope() as session:
            sessions = session.query(SeedingSession).order_by(
                SeedingSession.started_at.desc()
            ).limit(limit).all()
            return sessions
    
    def export_companies_to_csv(
        self,
        filename: str = "database_export.csv",
        source: Optional[str] = None,
        limit: Optional[int] = None
    ) -> str:
        """Export companies from database to CSV file"""
        companies = self.get_companies_from_database(
            limit=limit or 10000,
            source=source
        )
        
        # Convert database companies to CompanyProfile objects
        company_profiles = []
        for company in companies:
            profile = CompanyProfile(
                name=company.name,
                domain=company.domain,
                industry=company.industry or "Unknown",
                employee_count=company.employee_count or 0,
                location=company.location or "",
                founded_year=company.founded_year,
                technology_stack=company.technology_stack or [],
                linkedin_url=company.linkedin_url,
                source=company.source
            )
            company_profiles.append(profile)
        
        # Use existing CSV export functionality
        filepath = self.company_seeder.save_companies_to_csv(company_profiles, filename)
        logger.info(f"Exported {len(company_profiles)} companies to {filepath}")
        return filepath

def main():
    """Main database seeding workflow"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Seed companies to database')
    parser.add_argument('--target-count', type=int, default=3000, help='Target number of companies')
    parser.add_argument('--apollo', action='store_true', help='Use Apollo.io API')
    parser.add_argument('--apollo-key', type=str, help='Apollo.io API key')
    parser.add_argument('--yc', action='store_true', default=True, help='Include Y Combinator companies')
    parser.add_argument('--csv', type=str, help='CSV file to import')
    parser.add_argument('--min-employees', type=int, default=50, help='Minimum employee count')
    parser.add_argument('--max-employees', type=int, default=100, help='Maximum employee count')
    parser.add_argument('--clearbit', action='store_true', help='Use Clearbit enrichment')
    parser.add_argument('--export', type=str, help='Export to CSV file after seeding')
    
    args = parser.parse_args()
    
    # Initialize database seeder
    seeder = DatabaseSeeder()
    
    # Run seeding
    result = seeder.seed_companies_to_database(
        target_count=args.target_count,
        use_apollo=args.apollo,
        apollo_api_key=args.apollo_key,
        use_yc_data=args.yc,
        use_csv_import=bool(args.csv),
        csv_file=args.csv or "data/company_import.csv",
        min_employees=args.min_employees,
        max_employees=args.max_employees,
        use_clearbit_enrichment=args.clearbit
    )
    
    print(f"\n🎉 Seeding Result:")
    print(f"Status: {result['status']}")
    print(f"Session ID: {result['session_id']}")
    if result['status'] == 'completed':
        print(f"Companies found: {result['total_found']}")
        print(f"After deduplication: {result['after_deduplication']}")
        print(f"After filtering: {result['after_filtering']}")
        print(f"Stored in database: {result['stored_in_database']}")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")
    
    # Export if requested
    if args.export and result['status'] == 'completed':
        export_file = seeder.export_companies_to_csv(args.export)
        print(f"Exported to: {export_file}")
    
    print(f"\nNext steps:")
    print(f"1. Run: python app.py to start the web application")
    print(f"2. Visit: http://localhost:8000 to view the seeded companies")
    print(f"3. Use the ATS scraping functionality to find job postings")

if __name__ == "__main__":
    main()