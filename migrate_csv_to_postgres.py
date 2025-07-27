#!/usr/bin/env python3
"""
Migration script to move all CSV data to PostgreSQL database.
This script will read existing CSV files and import them into the contacts table.
"""

import os
import pandas as pd
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from data_ingestion_system import ContactDataIngester

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def migrate_csv_files():
    """Migrate all CSV files to PostgreSQL database."""
    print("="*60)
    print("CSV TO POSTGRESQL MIGRATION")
    print("="*60)
    
    # Initialize the data ingester
    ingester = ContactDataIngester()
    
    try:
        # Connect to database
        ingester.connect_db()
        print("✓ Connected to PostgreSQL database")
        
        # Process all CSV files in various locations
        csv_locations = [
            ".",  # Root directory
            "contacts",  # Contacts directory
        ]
        
        csv_files_found = []
        
        for location in csv_locations:
            if os.path.exists(location):
                files = [f for f in os.listdir(location) if f.endswith('.csv')]
                for file in files:
                    file_path = os.path.join(location, file)
                    csv_files_found.append(file_path)
        
        if not csv_files_found:
            print("No CSV files found to migrate.")
            return
        
        print(f"Found {len(csv_files_found)} CSV files to migrate:")
        for file_path in csv_files_found:
            print(f"  - {file_path}")
        
        print("\nStarting migration...")
        
        total_processed = 0
        total_inserted = 0
        total_errors = 0
        
        for file_path in csv_files_found:
            print(f"\nProcessing: {file_path}")
            try:
                rows, inserts, errors = ingester.process_csv_file(file_path)
                total_processed += rows
                total_inserted += inserts
                total_errors += errors
                
                print(f"  ✓ {rows} rows processed, {inserts} inserted, {errors} errors")
                
            except Exception as e:
                logging.error(f"Error processing {file_path}: {str(e)}")
                total_errors += 1
        
        print("\n" + "="*60)
        print("MIGRATION COMPLETE")
        print("="*60)
        print(f"Total files processed: {len(csv_files_found)}")
        print(f"Total rows processed: {total_processed}")
        print(f"Total contacts inserted: {total_inserted}")
        print(f"Total errors: {total_errors}")
        
        # Get final statistics
        stats = ingester.get_statistics()
        print(f"\nDatabase now contains:")
        print(f"  - {stats['total_contacts']} total contacts")
        print(f"  - {stats['unique_companies']} unique companies")
        
        print("\n✓ Migration completed successfully!")
        print("\nNext steps:")
        print("1. Verify data in database")
        print("2. Test email sending with PostgreSQL data")
        print("3. Consider backing up and removing CSV files")
        
    except Exception as e:
        logging.error(f"Migration failed: {str(e)}")
        print(f"\n✗ Migration failed: {str(e)}")
    
    finally:
        ingester.close()

def verify_migration():
    """Verify that data was migrated correctly."""
    print("\n" + "="*60)
    print("VERIFICATION")
    print("="*60)
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("✗ DATABASE_URL not configured")
        return False
    
    try:
        engine = create_engine(
            database_url,
            pool_size=5,          # Maximum number of permanent connections
            max_overflow=10,      # Maximum number of connections that can overflow the pool
            pool_pre_ping=True,   # Verify connections before use
            pool_recycle=3600     # Recycle connections every hour
        )
        with engine.connect() as conn:
            # Check total contacts
            result = conn.execute(text("SELECT COUNT(*) FROM contacts"))
            total_contacts = result.scalar()
            
            # Check sample contacts
            result = conn.execute(text("""
                SELECT email, first_name, last_name, company_name, job_title 
                FROM contacts 
                LIMIT 5
            """))
            sample_contacts = [dict(row._mapping) for row in result]
            
            print(f"✓ Database contains {total_contacts} contacts")
            print("\nSample contacts:")
            for i, contact in enumerate(sample_contacts, 1):
                print(f"  {i}. {contact['first_name']} {contact['last_name']} ({contact['email']}) - {contact['company_name']}")
            
            return True
            
    except SQLAlchemyError as e:
        print(f"✗ Database verification failed: {e}")
        return False

def cleanup_csv_files():
    """Move CSV files to a backup directory."""
    response = input("\nDo you want to move CSV files to a backup directory? (y/N): ")
    if response.lower() != 'y':
        print("Skipping CSV cleanup.")
        return
    
    backup_dir = "csv_backup"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    csv_files = []
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.endswith('.csv'):
                csv_files.append(os.path.join(root, file))
    
    for csv_file in csv_files:
        try:
            filename = os.path.basename(csv_file)
            backup_path = os.path.join(backup_dir, filename)
            os.rename(csv_file, backup_path)
            print(f"✓ Moved {csv_file} to {backup_path}")
        except Exception as e:
            print(f"✗ Failed to move {csv_file}: {e}")

def main():
    """Main migration function."""
    print("Starting CSV to PostgreSQL migration...")
    
    # Check if database is configured
    if not os.getenv("DATABASE_URL"):
        print("✗ DATABASE_URL environment variable not set")
        print("Please configure your PostgreSQL database connection.")
        return
    
    try:
        # Run migration
        migrate_csv_files()
        
        # Verify migration
        if verify_migration():
            # Optionally clean up CSV files
            cleanup_csv_files()
        
    except KeyboardInterrupt:
        print("\n\nMigration interrupted by user.")
    except Exception as e:
        logging.error(f"Migration script failed: {str(e)}")

if __name__ == "__main__":
    main() 