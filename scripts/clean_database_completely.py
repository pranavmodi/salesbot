#!/usr/bin/env python3
"""
Complete Database Cleaning Script

This script completely cleans all data from all tables in the salesbot database.
It removes all records from all tables while preserving the table structure.

DANGER: This script will DELETE ALL DATA from the database.
Use with extreme caution and only when you need a completely clean database.
"""

import os
import sys
import logging
import argparse
from typing import Dict, List
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
        logging.FileHandler('clean_database_completely.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DatabaseCleaner:
    """Handles complete cleaning of all database tables."""
    
    # Define table order for deletion (child tables first to avoid foreign key constraints)
    TABLE_ORDER = [
        'report_clicks',           # Has foreign keys to companies, campaigns, email_history
        'campaign_email_jobs',     # Has foreign key to campaigns
        'email_history',           # Has foreign key to campaigns
        'campaign_contacts',       # Junction table between campaigns and contacts
        'scheduler_jobs',          # Independent table (if exists)
        'campaigns',               # Has no foreign key dependencies after above are deleted
        'contacts',                # Has foreign key to companies
        'companies'                # Base table with no dependencies after contacts are deleted
    ]
    
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
        logger.info("DatabaseCleaner initialized")

    def get_table_counts(self) -> Dict[str, int]:
        """Get record counts for all tables."""
        logger.info("Getting record counts for all tables...")
        
        table_counts = {}
        
        try:
            with self.engine.connect() as conn:
                for table_name in self.TABLE_ORDER:
                    try:
                        result = conn.execute(text(f"SELECT COUNT(*) as count FROM {table_name}"))
                        count = result.fetchone().count
                        table_counts[table_name] = count
                        logger.info(f"Table '{table_name}': {count} records")
                    except SQLAlchemyError as e:
                        # Table might not exist
                        logger.warning(f"Could not count records in table '{table_name}': {e}")
                        table_counts[table_name] = 0
                
                return table_counts
                
        except SQLAlchemyError as e:
            logger.error(f"Database error getting table counts: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error getting table counts: {e}")
            return {}

    def verify_table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = :table_name
                    )
                """), {"table_name": table_name})
                return result.fetchone()[0]
        except Exception as e:
            logger.warning(f"Could not verify table '{table_name}' exists: {e}")
            return False

    def clean_table(self, table_name: str) -> int:
        """Clean all records from a specific table."""
        if not self.verify_table_exists(table_name):
            logger.warning(f"Table '{table_name}' does not exist, skipping...")
            return 0
            
        logger.info(f"Cleaning table '{table_name}'...")
        
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    result = conn.execute(text(f"DELETE FROM {table_name}"))
                    rows_affected = result.rowcount
                    logger.info(f"Successfully deleted {rows_affected} records from '{table_name}'")
                    return rows_affected
            
        except SQLAlchemyError as e:
            logger.error(f"Database error cleaning table '{table_name}': {e}")
            return 0
        except Exception as e:
            logger.error(f"Unexpected error cleaning table '{table_name}': {e}")
            return 0

    def clean_all_tables(self) -> Dict[str, int]:
        """Clean all records from all tables in the correct order."""
        logger.info("Starting complete database cleaning...")
        
        results = {}
        total_deleted = 0
        
        # Delete in the specified order to handle foreign key constraints
        for table_name in self.TABLE_ORDER:
            deleted_count = self.clean_table(table_name)
            results[table_name] = deleted_count
            total_deleted += deleted_count
        
        logger.info(f"✅ Database cleaning completed. Total records deleted: {total_deleted}")
        return results

    def reset_sequences(self) -> bool:
        """Reset auto-increment sequences for tables that have them."""
        logger.info("Resetting auto-increment sequences...")
        
        # Tables with auto-increment primary keys
        tables_with_sequences = [
            'companies',
            'campaigns', 
            'email_history',
            'campaign_email_jobs',
            'report_clicks'
        ]
        
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    for table_name in tables_with_sequences:
                        if self.verify_table_exists(table_name):
                            try:
                                # Reset the sequence for PostgreSQL
                                conn.execute(text(f"ALTER SEQUENCE {table_name}_id_seq RESTART WITH 1"))
                                logger.info(f"Reset sequence for table '{table_name}'")
                            except SQLAlchemyError as e:
                                logger.warning(f"Could not reset sequence for '{table_name}': {e}")
            
            logger.info("✅ Sequence reset completed")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Database error resetting sequences: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error resetting sequences: {e}")
            return False

    def get_database_summary(self) -> Dict:
        """Get a summary of the database state."""
        logger.info("Getting database summary...")
        
        try:
            with self.engine.connect() as conn:
                # Get database size
                size_result = conn.execute(text("""
                    SELECT pg_size_pretty(pg_database_size(current_database())) as db_size
                """))
                db_size = size_result.fetchone().db_size
                
                # Get table information
                tables_result = conn.execute(text("""
                    SELECT 
                        table_name,
                        pg_size_pretty(pg_total_relation_size(quote_ident(table_name)::regclass)) as table_size
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_type = 'BASE TABLE'
                    ORDER BY pg_total_relation_size(quote_ident(table_name)::regclass) DESC
                """))
                
                tables_info = []
                for row in tables_result:
                    tables_info.append({
                        'table_name': row.table_name,
                        'table_size': row.table_size
                    })
                
                return {
                    'database_size': db_size,
                    'tables': tables_info,
                    'table_counts': self.get_table_counts()
                }
                
        except SQLAlchemyError as e:
            logger.error(f"Database error getting summary: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error getting summary: {e}")
            return {}

def main():
    """Main function to run the complete database cleaning script."""
    parser = argparse.ArgumentParser(description='Complete database cleaning - REMOVES ALL DATA from all tables')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be deleted without actually doing it')
    parser.add_argument('--summary', action='store_true', 
                       help='Show database summary without cleaning')
    parser.add_argument('--reset-sequences', action='store_true',
                       help='Reset auto-increment sequences after cleaning')
    parser.add_argument('--table', type=str,
                       help='Clean only a specific table (use with caution)')
    
    args = parser.parse_args()
    
    # Show summary if requested
    if args.summary:
        try:
            cleaner = DatabaseCleaner()
            summary = cleaner.get_database_summary()
            if summary:
                logger.info("📊 Database Summary:")
                logger.info(f"   Database size: {summary.get('database_size', 'Unknown')}")
                logger.info("   Table record counts:")
                for table_name, count in summary.get('table_counts', {}).items():
                    logger.info(f"     - {table_name}: {count} records")
                logger.info("   Table sizes:")
                for table_info in summary.get('tables', []):
                    logger.info(f"     - {table_info['table_name']}: {table_info['table_size']}")
        except Exception as e:
            logger.error(f"Error getting summary: {e}")
        return
    
    try:
        cleaner = DatabaseCleaner()
        
        if args.dry_run:
            logger.info("🔍 DRY RUN MODE - No actual cleaning will occur")
            
            if args.table:
                if cleaner.verify_table_exists(args.table):
                    with cleaner.engine.connect() as conn:
                        result = conn.execute(text(f"SELECT COUNT(*) as count FROM {args.table}"))
                        count = result.fetchone().count
                        logger.info(f"Would clean table '{args.table}' with {count} records")
                else:
                    logger.warning(f"Table '{args.table}' does not exist")
            else:
                table_counts = cleaner.get_table_counts()
                total = sum(table_counts.values())
                logger.info(f"Would clean all tables with a total of {total} records:")
                for table_name, count in table_counts.items():
                    if count > 0:
                        logger.info(f"  - {table_name}: {count} records")
            return
        
        # Perform the cleaning
        if args.table:
            # Clean single table
            if cleaner.verify_table_exists(args.table):
                deleted_count = cleaner.clean_table(args.table)
                if deleted_count >= 0:
                    logger.info(f"✅ Successfully cleaned table '{args.table}' - {deleted_count} records deleted")
                else:
                    logger.error(f"❌ Failed to clean table '{args.table}'")
            else:
                logger.error(f"❌ Table '{args.table}' does not exist")
        else:
            # Clean all tables
            results = cleaner.clean_all_tables()
            
            if results:
                total_deleted = sum(results.values())
                logger.info("✅ Database cleaning completed successfully!")
                logger.info("📊 Deletion Summary:")
                for table_name, count in results.items():
                    if count > 0:
                        logger.info(f"   - {table_name}: {count} records deleted")
                logger.info(f"   Total records deleted: {total_deleted}")
                
                # Reset sequences if requested
                if args.reset_sequences:
                    if cleaner.reset_sequences():
                        logger.info("✅ Auto-increment sequences reset successfully")
                    else:
                        logger.warning("⚠️  Some sequences could not be reset")
            else:
                logger.error("❌ Database cleaning failed")
                sys.exit(1)
            
    except Exception as e:
        logger.error(f"Script execution error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()