#!/usr/bin/env python3
"""
Database Initialization Script for Lead Generation System

This script initializes the PostgreSQL database, creates tables, and provides
utility functions for database management.
"""

import sys
import os
import logging
from database import init_database, reset_database, get_database_manager, health_check
from models import Company, JobPosting, ScrapingLog, SeedingSession

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_database_if_not_exists():
    """
    Create the database if it doesn't exist
    This requires connecting to PostgreSQL as a superuser
    """
    from dotenv import load_dotenv
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    
    load_dotenv()
    
    # Connection parameters
    host = os.getenv('DB_HOST', 'localhost')
    port = os.getenv('DB_PORT', '5432')
    user = os.getenv('DB_USER', 'username')
    password = os.getenv('DB_PASSWORD', 'password')
    db_name = os.getenv('DB_NAME', 'leadgen_db')
    
    try:
        # Connect to PostgreSQL server (not specific database)
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database='postgres'  # Connect to default postgres database
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        exists = cursor.fetchone()
        
        if not exists:
            logger.info(f"Creating database: {db_name}")
            cursor.execute(f'CREATE DATABASE "{db_name}"')
            logger.info(f"Database {db_name} created successfully")
        else:
            logger.info(f"Database {db_name} already exists")
        
        cursor.close()
        conn.close()
        
        return True
        
    except psycopg2.Error as e:
        logger.error(f"Failed to create database: {e}")
        logger.info("Make sure PostgreSQL is running and credentials are correct")
        logger.info("You may need to create the database manually:")
        logger.info(f"  createdb -h {host} -p {port} -U {user} {db_name}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

def initialize_database(reset: bool = False):
    """Initialize database with tables"""
    try:
        logger.info("🗄️  Initializing database...")
        
        if reset:
            logger.info("Resetting database (dropping existing tables)...")
            db = reset_database()
        else:
            db = init_database()
        
        # Verify tables were created
        table_info = db.get_table_info()
        logger.info(f"Created {len(table_info)} tables:")
        for table_name, info in table_info.items():
            logger.info(f"  📋 {table_name}: {len(info['columns'])} columns")
        
        # Run health check
        health = health_check()
        if health['status'] == 'healthy':
            logger.info("✅ Database initialization successful!")
            return True
        else:
            logger.error(f"❌ Database health check failed: {health}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

def seed_demo_data():
    """Seed database with demo data for testing"""
    try:
        logger.info("🌱 Seeding demo data...")
        
        db = get_database_manager()
        
        # Demo companies data
        demo_companies = [
            {
                'name': 'TechStart Inc',
                'domain': 'techstart.com',
                'industry': 'SaaS',
                'employee_count': 75,
                'location': 'San Francisco, CA',
                'source': 'demo'
            },
            {
                'name': 'GrowthCorp',
                'domain': 'growthcorp.io',
                'industry': 'E-commerce',
                'employee_count': 85,
                'location': 'Austin, TX',
                'source': 'demo'
            },
            {
                'name': 'CustomerFirst Ltd',
                'domain': 'customerfirst.com',
                'industry': 'Customer Support',
                'employee_count': 65,
                'location': 'Denver, CO',
                'source': 'demo'
            }
        ]
        
        with db.session_scope() as session:
            # Check if demo data already exists
            existing = session.query(Company).filter(Company.source == 'demo').count()
            if existing > 0:
                logger.info(f"Demo data already exists ({existing} companies)")
                return True
            
            # Add demo companies
            companies_added = 0
            for company_data in demo_companies:
                company = Company(**company_data)
                session.add(company)
                companies_added += 1
            
            logger.info(f"Added {companies_added} demo companies")
            
        logger.info("✅ Demo data seeded successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Failed to seed demo data: {e}")
        return False

def show_database_stats():
    """Display current database statistics"""
    try:
        logger.info("📊 Database Statistics:")
        
        db = get_database_manager()
        with db.session_scope() as session:
            # Company stats
            total_companies = session.query(Company).count()
            active_companies = session.query(Company).filter(Company.is_active == True).count()
            scraped_companies = session.query(Company).filter(Company.ats_scraped == True).count()
            qualified_leads = session.query(Company).filter(Company.is_qualified_lead == True).count()
            
            logger.info(f"  Companies: {total_companies} total, {active_companies} active")
            logger.info(f"  Scraped: {scraped_companies} companies")
            logger.info(f"  Qualified Leads: {qualified_leads} companies")
            
            # Job postings stats
            total_jobs = session.query(JobPosting).count()
            support_jobs = session.query(JobPosting).filter(JobPosting.role_category == 'support').count()
            sales_jobs = session.query(JobPosting).filter(JobPosting.role_category == 'sales').count()
            ai_jobs = session.query(JobPosting).filter(JobPosting.role_category == 'ai').count()
            
            logger.info(f"  Job Postings: {total_jobs} total")
            logger.info(f"  Support Jobs: {support_jobs}, Sales Jobs: {sales_jobs}, AI Jobs: {ai_jobs}")
            
            # Scraping logs
            scraping_logs = session.query(ScrapingLog).count()
            successful_scrapes = session.query(ScrapingLog).filter(ScrapingLog.status == 'completed').count()
            
            logger.info(f"  Scraping Logs: {scraping_logs} total, {successful_scrapes} successful")
            
            # Sources breakdown
            from sqlalchemy import func
            source_counts = session.query(
                Company.source, 
                func.count(Company.id)
            ).group_by(Company.source).all()
            
            logger.info("  Sources:")
            for source, count in source_counts:
                logger.info(f"    {source}: {count} companies")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        return False

def main():
    """Main initialization workflow"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Initialize Lead Generation Database')
    parser.add_argument('--reset', action='store_true', help='Reset database (drop all tables)')
    parser.add_argument('--create-db', action='store_true', help='Create database if it doesn\'t exist')
    parser.add_argument('--demo-data', action='store_true', help='Seed with demo data')
    parser.add_argument('--stats', action='store_true', help='Show database statistics')
    parser.add_argument('--health-check', action='store_true', help='Run database health check')
    
    args = parser.parse_args()
    
    success = True
    
    # Create database if requested
    if args.create_db:
        if not create_database_if_not_exists():
            logger.error("Failed to create database")
            sys.exit(1)
    
    # Initialize database
    if not any([args.stats, args.health_check]):
        success = initialize_database(reset=args.reset)
        if not success:
            logger.error("Database initialization failed")
            sys.exit(1)
    
    # Seed demo data if requested
    if args.demo_data:
        success = seed_demo_data()
        if not success:
            logger.error("Demo data seeding failed")
            sys.exit(1)
    
    # Show stats if requested
    if args.stats:
        success = show_database_stats()
        if not success:
            sys.exit(1)
    
    # Run health check if requested
    if args.health_check:
        health = health_check()
        logger.info(f"Database Health: {health}")
        if health['status'] != 'healthy':
            sys.exit(1)
    
    if success:
        logger.info("🎉 All operations completed successfully!")
        logger.info("\nNext steps:")
        logger.info("1. Update your .env file with correct database credentials")
        logger.info("2. Run: python app.py to start the web application")
        logger.info("3. Run: python company_seeder.py to seed companies")
    
if __name__ == "__main__":
    main()