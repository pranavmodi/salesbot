#!/usr/bin/env python3
"""
Database Cleaning Service

Handles complete cleaning of all database tables while preserving structure.
Integrated into the Flask application for API access.
"""

import os
import logging
from typing import Dict
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

class DatabaseCleanerService:
    """Handles complete cleaning of all database tables."""
    
    # Define table order for deletion (child tables first to avoid foreign key constraints)
    TABLE_ORDER = [
        'report_clicks',           # Has foreign keys to companies, campaigns, email_history
        'campaign_email_jobs',     # Has foreign key to campaigns
        'email_history',           # Has foreign key to campaigns
        'email_tracking',          # Email tracking data
        'campaign_contacts',       # Junction table between campaigns and contacts
        'scheduler_jobs',          # Independent table (if exists)
        'campaigns',               # Has no foreign key dependencies after above are deleted
        'contacts',                # Has foreign key to companies
        'companies',               # Base table with no dependencies after contacts are deleted
        'tenant_settings',         # Contains API keys, email configurations, and other tenant settings
        'file_metadata'            # File upload metadata (if exists)
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
        logger.info("DatabaseCleanerService initialized")

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

    def clean_table(self, table_name: str, tenant_id: str = None) -> int:
        """Clean records from a specific table, optionally filtered by tenant."""
        if not self.verify_table_exists(table_name):
            logger.warning(f"Table '{table_name}' does not exist, skipping...")
            return 0
        
        # Check if table has tenant_id column for filtering
        has_tenant_column = self._table_has_tenant_column(table_name)
        
        if tenant_id and has_tenant_column:
            logger.info(f"Cleaning table '{table_name}' for tenant {tenant_id}...")
            query = f"DELETE FROM {table_name} WHERE tenant_id = :tenant_id"
            params = {"tenant_id": tenant_id}
        elif tenant_id and not has_tenant_column:
            logger.warning(f"Table '{table_name}' has no tenant_id column - skipping for safety")
            return 0
        else:
            logger.warning(f"Cleaning ALL records from table '{table_name}' (no tenant filter)")
            query = f"DELETE FROM {table_name}"
            params = {}
        
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    result = conn.execute(text(query), params)
                    rows_affected = result.rowcount
                    logger.info(f"Successfully deleted {rows_affected} records from '{table_name}'")
                    return rows_affected
            
        except SQLAlchemyError as e:
            logger.error(f"Database error cleaning table '{table_name}': {e}")
            return 0
        except Exception as e:
            logger.error(f"Unexpected error cleaning table '{table_name}': {e}")
            return 0

    def _table_has_tenant_column(self, table_name: str) -> bool:
        """Check if a table has a tenant_id column."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = :table_name 
                        AND column_name = 'tenant_id'
                    )
                """), {"table_name": table_name})
                return result.fetchone()[0]
        except Exception as e:
            logger.warning(f"Could not check tenant_id column for table '{table_name}': {e}")
            return False

    def clean_all_tables(self, tenant_id: str = None) -> Dict[str, int]:
        """Clean all records from all tables in the correct order, optionally filtered by tenant."""
        if tenant_id:
            logger.info(f"Starting database cleaning for tenant {tenant_id}...")
        else:
            logger.info("Starting complete database cleaning...")
        
        results = {}
        total_deleted = 0
        
        # Delete in the specified order to handle foreign key constraints
        for table_name in self.TABLE_ORDER:
            deleted_count = self.clean_table(table_name, tenant_id)
            results[table_name] = deleted_count
            total_deleted += deleted_count
        
        if tenant_id:
            logger.info(f"✅ Database cleaning completed for tenant {tenant_id}. Total records deleted: {total_deleted}")
        else:
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

    def execute_complete_clean(self, tenant_id: str = None) -> dict:
        """Execute complete database cleaning and return results."""
        try:
            # Get initial counts for reporting
            initial_counts = self.get_table_counts()
            initial_total = sum(initial_counts.values())
            
            if tenant_id:
                logger.info(f"Starting database cleaning for tenant {tenant_id} - checking {initial_total} total records")
            else:
                logger.info(f"Starting database cleaning - {initial_total} total records to delete")
            
            # Clean all tables
            results = self.clean_all_tables(tenant_id)
            
            if results:
                total_deleted = sum(results.values())
                
                # Reset sequences only if cleaning entire database (no tenant filter)
                sequences_reset = False
                if not tenant_id:
                    sequences_reset = self.reset_sequences()
                
                logger.info("✅ Database cleaning completed successfully!")
                logger.info("📊 Deletion Summary:")
                for table_name, count in results.items():
                    if count > 0:
                        logger.info(f"   - {table_name}: {count} records deleted")
                logger.info(f"   Total records deleted: {total_deleted}")
                
                if tenant_id:
                    message = f'Database cleaned successfully for tenant {tenant_id}. {total_deleted} records deleted.'
                else:
                    message = f'Database cleaned successfully. {total_deleted} records deleted.'
                
                return {
                    'success': True,
                    'message': message,
                    'details': {
                        'total_deleted': total_deleted,
                        'tables_cleaned': results,
                        'sequences_reset': sequences_reset,
                        'tenant_id': tenant_id
                    }
                }
            else:
                logger.error("❌ Database cleaning failed")
                return {
                    'success': False,
                    'message': 'Database cleaning failed - no results returned',
                    'details': {}
                }
                
        except Exception as e:
            logger.error(f"Database cleaning execution error: {e}")
            return {
                'success': False,
                'message': f'Database cleaning failed: {str(e)}',
                'details': {}
            }