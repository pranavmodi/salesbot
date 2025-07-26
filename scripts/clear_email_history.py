#!/usr/bin/env python3
"""
Clear Email History Script

This script clears all records from the email_history table.
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
        logging.FileHandler('clear_email_history.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EmailHistoryCleaner:
    """Handles clearing email history data from the database."""
    
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
        logger.info("EmailHistoryCleaner initialized")

    def get_email_history_count(self) -> int:
        """Get count of records in email_history table."""
        logger.info("Checking email history records count...")
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT COUNT(*) as count
                    FROM email_history
                """))
                
                count = result.fetchone().count
                logger.info(f"Found {count} email history records")
                return count
                
        except SQLAlchemyError as e:
            logger.error(f"Database error checking email history count: {e}")
            return 0
        except Exception as e:
            logger.error(f"Unexpected error checking email history count: {e}")
            return 0

    def clear_all_email_history(self) -> bool:
        """Clear all records from the email_history table."""
        logger.info("Clearing all email history records...")
        
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    result = conn.execute(text("""
                        DELETE FROM email_history
                    """))
                    
                    rows_affected = result.rowcount
                    logger.info(f"Successfully deleted {rows_affected} email history records")
                    return True
            
        except SQLAlchemyError as e:
            logger.error(f"Database error clearing email history: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error clearing email history: {e}")
            return False

    def clear_email_history_by_recipient(self, recipient_email: str) -> bool:
        """Clear email history for a specific recipient."""
        logger.info(f"Clearing email history for recipient: {recipient_email}")
        
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    result = conn.execute(text("""
                        DELETE FROM email_history 
                        WHERE LOWER("to") = LOWER(:recipient)
                    """), {"recipient": recipient_email})
                    
                    rows_affected = result.rowcount
                    if rows_affected > 0:
                        logger.info(f"Successfully deleted {rows_affected} email history records for: {recipient_email}")
                        return True
                    else:
                        logger.warning(f"No email history found for recipient: {recipient_email}")
                        return False
            
        except SQLAlchemyError as e:
            logger.error(f"Database error clearing email history for {recipient_email}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error clearing email history for {recipient_email}: {e}")
            return False

    def clear_email_history_by_date_range(self, start_date: str, end_date: str = None) -> bool:
        """Clear email history within a date range."""
        logger.info(f"Clearing email history from {start_date}" + (f" to {end_date}" if end_date else " onwards"))
        
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    if end_date:
                        result = conn.execute(text("""
                            DELETE FROM email_history 
                            WHERE date >= :start_date AND date <= :end_date
                        """), {"start_date": start_date, "end_date": end_date})
                    else:
                        result = conn.execute(text("""
                            DELETE FROM email_history 
                            WHERE date >= :start_date
                        """), {"start_date": start_date})
                    
                    rows_affected = result.rowcount
                    if rows_affected > 0:
                        logger.info(f"Successfully deleted {rows_affected} email history records in date range")
                        return True
                    else:
                        logger.warning(f"No email history found in the specified date range")
                        return False
            
        except SQLAlchemyError as e:
            logger.error(f"Database error clearing email history by date range: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error clearing email history by date range: {e}")
            return False

    def get_email_history_summary(self) -> dict:
        """Get summary statistics of email history."""
        logger.info("Getting email history summary...")
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT 
                        COUNT(*) as total_emails,
                        COUNT(DISTINCT "to") as unique_recipients,
                        MIN(date) as earliest_date,
                        MAX(date) as latest_date,
                        status,
                        COUNT(*) as status_count
                    FROM email_history
                    GROUP BY status
                """))
                
                summary = {
                    'total_emails': 0,
                    'unique_recipients': 0,
                    'earliest_date': None,
                    'latest_date': None,
                    'status_breakdown': {}
                }
                
                for row in result:
                    summary['total_emails'] += row.status_count
                    summary['unique_recipients'] = row.unique_recipients
                    summary['earliest_date'] = row.earliest_date
                    summary['latest_date'] = row.latest_date
                    summary['status_breakdown'][row.status] = row.status_count
                
                return summary
                
        except SQLAlchemyError as e:
            logger.error(f"Database error getting email history summary: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error getting email history summary: {e}")
            return {}

def main():
    """Main function to run the email history clearing script."""
    parser = argparse.ArgumentParser(description='Clear email history data from email_history table')
    parser.add_argument('--recipient', type=str, help='Clear history for a specific recipient email')
    parser.add_argument('--start-date', type=str, help='Clear history from this date (YYYY-MM-DD format)')
    parser.add_argument('--end-date', type=str, help='Clear history up to this date (YYYY-MM-DD format)')
    parser.add_argument('--all', action='store_true', help='Clear all email history')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be cleared without actually doing it')
    parser.add_argument('--summary', action='store_true', help='Show email history summary statistics')
    
    args = parser.parse_args()
    
    # Show summary if requested
    if args.summary:
        try:
            cleaner = EmailHistoryCleaner()
            summary = cleaner.get_email_history_summary()
            if summary:
                logger.info("📊 Email History Summary:")
                logger.info(f"   Total emails: {summary.get('total_emails', 0)}")
                logger.info(f"   Unique recipients: {summary.get('unique_recipients', 0)}")
                logger.info(f"   Date range: {summary.get('earliest_date', 'N/A')} to {summary.get('latest_date', 'N/A')}")
                logger.info(f"   Status breakdown: {summary.get('status_breakdown', {})}")
        except Exception as e:
            logger.error(f"Error getting summary: {e}")
        return
    
    # Validate arguments for clearing operations
    if not any([args.recipient, args.start_date, args.all]):
        parser.error("Must specify one of: --recipient, --start-date, or --all (or use --summary)")
    
    try:
        cleaner = EmailHistoryCleaner()
        
        if args.dry_run:
            logger.info("🔍 DRY RUN MODE - No actual clearing will occur")
            count = cleaner.get_email_history_count()
            
            if args.all:
                logger.info(f"Would clear all {count} email history records")
            elif args.recipient:
                logger.info(f"Would clear email history for recipient: {args.recipient}")
            elif args.start_date:
                date_info = f"from {args.start_date}"
                if args.end_date:
                    date_info += f" to {args.end_date}"
                logger.info(f"Would clear email history {date_info}")
            return
        
        # Perform the actual clearing
        success = False
        
        if args.all:
            if input("⚠️  Are you sure you want to clear ALL email history? This cannot be undone! (yes/no): ").lower() == 'yes':
                success = cleaner.clear_all_email_history()
                if success:
                    logger.info("✅ Successfully cleared all email history")
            else:
                logger.info("❌ Operation cancelled")
                
        elif args.recipient:
            if input(f"⚠️  Are you sure you want to clear email history for {args.recipient}? (yes/no): ").lower() == 'yes':
                success = cleaner.clear_email_history_by_recipient(args.recipient)
                if success:
                    logger.info(f"✅ Successfully cleared email history for {args.recipient}")
            else:
                logger.info("❌ Operation cancelled")
                
        elif args.start_date:
            date_info = f"from {args.start_date}"
            if args.end_date:
                date_info += f" to {args.end_date}"
            if input(f"⚠️  Are you sure you want to clear email history {date_info}? (yes/no): ").lower() == 'yes':
                success = cleaner.clear_email_history_by_date_range(args.start_date, args.end_date)
                if success:
                    logger.info(f"✅ Successfully cleared email history {date_info}")
            else:
                logger.info("❌ Operation cancelled")
        
        if not success and not args.dry_run:
            logger.error("❌ Failed to clear email history")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Script execution error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 