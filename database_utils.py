#!/usr/bin/env python3
"""
Database Utilities for Sales Bot Contact Management

This module provides utilities for querying, managing, and maintaining
the contact database created by the data ingestion system.
Uses PostgreSQL database with SQLAlchemy.
"""

import os
import json
import pandas as pd
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ContactDatabase:
    def __init__(self):
        self.engine = None
    
    def connect(self):
        """Connect to the PostgreSQL database"""
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        
        try:
            self.engine = create_engine(
                database_url,
                pool_size=5,          # Maximum number of permanent connections
                max_overflow=10,      # Maximum number of overflow connections  
                pool_pre_ping=True,   # Verify connections before use
                pool_recycle=3600     # Recycle connections every hour
            )
            logger.info("Connected to PostgreSQL database successfully")
        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            raise
    
    def disconnect(self):
        """Close database connection"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection closed")
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
    
    def get_contact_by_email(self, email: str) -> Optional[Dict]:
        """Get a specific contact by email"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT * FROM contacts WHERE email = :email"),
                    {"email": email}
                )
                
                row = result.fetchone()
                if row:
                    contact = dict(row._mapping)
                    # Parse JSON fields - PostgreSQL JSONB is automatically parsed
                    return contact
                return None
        except SQLAlchemyError as e:
            logger.error(f"Error getting contact by email: {str(e)}")
            return None
    
    def search_contacts(self, query: str, fields: List[str] = None, limit: int = 50) -> List[Dict]:
        """
        Search contacts with flexible field matching
        
        Args:
            query: Search term
            fields: List of fields to search in (default: name, company, job_title)
            limit: Maximum results to return
        """
        if fields is None:
            fields = ['first_name', 'last_name', 'company_name', 'job_title', 'email']
        
        try:
            with self.engine.connect() as conn:
                # Build dynamic WHERE clause using ILIKE for case-insensitive search
                where_conditions = []
                for field in fields:
                    where_conditions.append(f"{field} ILIKE :search")
                
                where_clause = " OR ".join(where_conditions)
                
                sql = text(f"""
                    SELECT email, first_name, last_name, job_title, company_name, 
                           linkedin_profile, location, phone, source_files
                    FROM contacts 
                    WHERE {where_clause}
                    ORDER BY company_name, last_name
                    LIMIT :limit
                """)
                
                result = conn.execute(sql, {
                    "search": f"%{query}%",
                    "limit": limit
                })
                
                results = []
                for row in result:
                    contact = dict(row._mapping)
                    results.append(contact)
                
                return results
        except SQLAlchemyError as e:
            logger.error(f"Error searching contacts: {str(e)}")
            return []
    
    def get_contacts_by_company(self, company_name: str) -> List[Dict]:
        """Get all contacts from a specific company"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT email, first_name, last_name, job_title, linkedin_profile, phone
                    FROM contacts 
                    WHERE company_name ILIKE :company_name
                    ORDER BY job_title, last_name
                """), {"company_name": f"%{company_name}%"})
                
                return [dict(row._mapping) for row in result]
        except SQLAlchemyError as e:
            logger.error(f"Error getting contacts by company: {str(e)}")
            return []
    
    def get_companies_with_contact_count(self) -> List[Dict]:
        """Get list of companies with their contact counts"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT company_name, COUNT(*) as contact_count
                    FROM contacts 
                    WHERE company_name IS NOT NULL AND company_name != ''
                    GROUP BY company_name
                    ORDER BY contact_count DESC, company_name
                """))
                
                return [{'company_name': row[0], 'contact_count': row[1]} for row in result]
        except SQLAlchemyError as e:
            logger.error(f"Error getting companies with contact count: {str(e)}")
            return []
    
    def get_contacts_with_linkedin_messages(self) -> List[Dict]:
        """Get contacts who have LinkedIn messages"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT email, first_name, last_name, company_name, job_title, linkedin_message
                    FROM contacts 
                    WHERE linkedin_message IS NOT NULL AND linkedin_message != ''
                    ORDER BY company_name, last_name
                """))
                
                return [dict(row._mapping) for row in result]
        except SQLAlchemyError as e:
            logger.error(f"Error getting contacts with LinkedIn messages: {str(e)}")
            return []
    
    def get_contacts_missing_info(self, field: str) -> List[Dict]:
        """Get contacts missing specific information"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(f"""
                    SELECT email, first_name, last_name, company_name, job_title
                    FROM contacts 
                    WHERE {field} IS NULL OR {field} = ''
                    ORDER BY company_name, last_name
                """))
                
                return [dict(row._mapping) for row in result]
        except SQLAlchemyError as e:
            logger.error(f"Error getting contacts missing info: {str(e)}")
            return []
    
    def export_to_csv(self, filename: str, filters: Dict = None) -> bool:
        """
        Export contacts to CSV with optional filters
        
        Args:
            filename: Output CSV filename
            filters: Dictionary of field filters (e.g., {'company_name': 'GoHealth'})
        """
        try:
            with self.engine.connect() as conn:
                # Build query with filters
                where_conditions = []
                params = {}
                
                if filters:
                    for field, value in filters.items():
                        where_conditions.append(f"{field} ILIKE :filter_{field}")
                        params[f"filter_{field}"] = f"%{value}%"
                
                where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
                
                query = text(f"""
                    SELECT email, first_name, last_name, full_name, job_title, 
                           company_name, company_domain, linkedin_profile, location, 
                           phone, linkedin_message, created_at, updated_at, source_files
                    FROM contacts 
                    {where_clause}
                    ORDER BY company_name, last_name
                """)
                
                df = pd.read_sql_query(query, self.engine, params=params)
                df.to_csv(filename, index=False)
                
                logger.info(f"Exported {len(df)} contacts to {filename}")
                return True
                
        except Exception as e:
            logger.error(f"Error exporting to CSV: {str(e)}")
            return False
    
    def get_database_stats(self) -> Dict:
        """Get comprehensive database statistics"""
        stats = {}
        
        try:
            with self.engine.connect() as conn:
                # Total contacts
                result = conn.execute(text("SELECT COUNT(*) FROM contacts"))
                stats['total_contacts'] = result.scalar()
                
                # Contacts with complete info
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM contacts 
                    WHERE first_name IS NOT NULL AND first_name != '' 
                      AND last_name IS NOT NULL AND last_name != '' 
                      AND company_name IS NOT NULL AND company_name != ''
                """))
                stats['complete_contacts'] = result.scalar()
                
                # Contacts with LinkedIn profiles
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM contacts 
                    WHERE linkedin_profile IS NOT NULL AND linkedin_profile != ''
                """))
                stats['linkedin_contacts'] = result.scalar()
                
                # Contacts with messages
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM contacts 
                    WHERE linkedin_message IS NOT NULL AND linkedin_message != ''
                """))
                stats['contacts_with_messages'] = result.scalar()
                
                # Unique companies
                result = conn.execute(text("""
                    SELECT COUNT(DISTINCT company_name) FROM contacts 
                    WHERE company_name IS NOT NULL AND company_name != ''
                """))
                stats['unique_companies'] = result.scalar()
                
                # Source file breakdown
                result = conn.execute(text("""
                    SELECT filename, successful_inserts, total_rows, errors, processed_at
                    FROM file_metadata 
                    ORDER BY processed_at DESC
                """))
                stats['source_files'] = [dict(row._mapping) for row in result]
                
                # Top companies by contact count
                result = conn.execute(text("""
                    SELECT company_name, COUNT(*) as contact_count
                    FROM contacts 
                    WHERE company_name IS NOT NULL AND company_name != ''
                    GROUP BY company_name
                    ORDER BY contact_count DESC
                    LIMIT 10
                """))
                stats['top_companies'] = [{'company': row[0], 'count': row[1]} for row in result]
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting database stats: {str(e)}")
            stats = {
                'total_contacts': 0,
                'complete_contacts': 0,
                'linkedin_contacts': 0,
                'contacts_with_messages': 0,
                'unique_companies': 0,
                'source_files': [],
                'top_companies': []
            }
        
        return stats
    
    def clean_duplicates(self, dry_run: bool = True) -> Dict:
        """
        Identify and optionally clean duplicate contacts (same email)
        
        Args:
            dry_run: If True, only report duplicates without deleting
        """
        try:
            with self.engine.connect() as conn:
                # Find emails with multiple entries (shouldn't happen with current design, but useful for maintenance)
                result = conn.execute(text("""
                    SELECT email, COUNT(*) as count
                    FROM contacts 
                    GROUP BY email
                    HAVING COUNT(*) > 1
                """))
                
                duplicates = result.fetchall()
                
                result_dict = {
                    'duplicates_found': len(duplicates),
                    'duplicate_emails': [row[0] for row in duplicates]
                }
                
                if not dry_run and duplicates:
                    # This shouldn't happen with current schema (email is primary key)
                    # But including for completeness
                    logger.warning("Found duplicates in database with email primary key - this indicates a data integrity issue")
                
                return result_dict
        except SQLAlchemyError as e:
            logger.error(f"Error cleaning duplicates: {str(e)}")
            return {'duplicates_found': 0, 'duplicate_emails': []}
    
    def update_contact_field(self, email: str, field: str, value: str) -> bool:
        """Update a specific field for a contact"""
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    result = conn.execute(text(f"""
                        UPDATE contacts 
                        SET {field} = :value, updated_at = :updated_at
                        WHERE email = :email
                    """), {
                        "value": value,
                        "updated_at": datetime.now(),
                        "email": email
                    })
                    
                    if result.rowcount > 0:
                        logger.info(f"Updated {field} for {email}")
                        return True
                    else:
                        logger.warning(f"No contact found with email {email}")
                        return False
                        
        except SQLAlchemyError as e:
            logger.error(f"Error updating contact: {str(e)}")
            return False
    
    def delete_contact(self, email: str) -> bool:
        """Delete a contact by email"""
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    result = conn.execute(
                        text("DELETE FROM contacts WHERE email = :email"),
                        {"email": email}
                    )
                    
                    if result.rowcount > 0:
                        logger.info(f"Deleted contact {email}")
                        return True
                    else:
                        logger.warning(f"No contact found with email {email}")
                        return False
                        
        except SQLAlchemyError as e:
            logger.error(f"Error deleting contact: {str(e)}")
            return False

def main():
    """Example usage of database utilities"""
    with ContactDatabase() as db:
        # Get database statistics
        stats = db.get_database_stats()
        
        print("="*50)
        print("DATABASE STATISTICS")
        print("="*50)
        print(f"Total contacts: {stats['total_contacts']}")
        print(f"Complete contacts: {stats['complete_contacts']}")
        print(f"LinkedIn contacts: {stats['linkedin_contacts']}")
        print(f"Contacts with messages: {stats['contacts_with_messages']}")
        print(f"Unique companies: {stats['unique_companies']}")
        
        print("\nTop 10 Companies:")
        for company in stats['top_companies']:
            print(f"  {company['company']}: {company['count']} contacts")
        
        print("\nSource Files:")
        for file_info in stats['source_files']:
            print(f"  {file_info['filename']}: {file_info['successful_inserts']}/{file_info['total_rows']} successful")

if __name__ == "__main__":
    main() 