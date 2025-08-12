#!/usr/bin/env python3
"""
Sales Bot Data Ingestion System

This system ingests data from multiple CSV files in the contacts directory,
handling different column structures while preserving all information.
Uses email as the primary key for deduplication.
Uses PostgreSQL database with SQLAlchemy.
"""

import os
import pandas as pd
import json
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import re
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, MetaData, Table, Column, String, Integer, DateTime, Text, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ContactDataIngester:
    def __init__(self, contacts_dir: str = "contacts"):
        self.contacts_dir = contacts_dir
        self.engine = None
        self.Session = None
        self.email_patterns = [
            r'email',
            r'e-mail',
            r'mail',
            r'work email',
            r'primary email',
            r'contact'
        ]
        
    def connect_db(self):
        """Create database connection"""
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
            self.Session = sessionmaker(bind=self.engine)
            logger.info("Connected to PostgreSQL database successfully")
        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            raise
        
    def identify_email_columns(self, columns: List[str]) -> List[str]:
        """Identify potential email columns in the dataframe"""
        email_columns = []
        
        for col in columns:
            col_lower = col.lower().strip()
            # Direct matches
            if any(pattern in col_lower for pattern in self.email_patterns):
                email_columns.append(col)
            # Check if column contains email-like data
            elif 'find' in col_lower and 'email' in col_lower:
                email_columns.append(col)
                
        return email_columns
    
    def extract_primary_email(self, row: pd.Series, email_columns: List[str]) -> Optional[str]:
        """Extract the best primary email from available email columns"""
        emails = []
        
        for col in email_columns:
            email_val = row.get(col, '')
            if pd.notna(email_val) and email_val and email_val != '❌ No email found' and email_val != '❌ No Email Found':
                # Clean email - remove any prefixes like "✅ "
                clean_email = re.sub(r'^[✅❌]\s*', '', str(email_val).strip())
                if '@' in clean_email and '.' in clean_email:
                    emails.append(clean_email)
        
        # Prioritize primary email columns
        for email in emails:
            if email:  # Return first valid email found
                return email.lower().strip()
                
        return None
    
    def map_columns(self, df_columns: List[str]) -> Dict[str, str]:
        """Map CSV columns to standardized database columns"""
        column_mapping = {}
        
        # Define mapping patterns (case insensitive)
        mappings = {
            'first_name': ['first name', 'firstname', 'first_name', 'fname'],
            'last_name': ['last name', 'lastname', 'last_name', 'lname', 'surname'],
            'full_name': ['full name', 'fullname', 'full_name', 'name', 'contact name'],
            'job_title': ['title', 'job title', 'job_title', 'position', 'role'],
            'company_name': ['company', 'company name', 'company_name', 'organization', 'employer'],
            'company_domain': ['company domain', 'domain', 'website', 'company_domain'],
            'linkedin_profile': ['linkedin', 'linkedin profile', 'linkedin_profile', 'linkedin url', 'person linkedin url'],
            'location': ['location', 'city', 'state', 'country', 'address'],
            'phone': ['phone', 'mobile', 'work phone', 'corporate phone', 'work direct phone'],
            'linkedin_message': ['linkedin message', 'message', 'personalized message']
        }
        
        for standard_col, patterns in mappings.items():
            for df_col in df_columns:
                df_col_lower = df_col.lower().strip()
                if any(pattern in df_col_lower for pattern in patterns):
                    if standard_col not in column_mapping:  # Take first match
                        column_mapping[standard_col] = df_col
                        break
        
        return column_mapping
    
    def process_csv_file(self, file_path: str) -> Tuple[int, int, int]:
        """Process a single CSV file and return (total_rows, successful_inserts, errors)"""
        logger.info(f"Processing file: {file_path}")
        
        try:
            df = pd.read_csv(file_path)
            total_rows = len(df)
            successful_inserts = 0
            errors = 0
            
            # Identify email columns
            email_columns = self.identify_email_columns(df.columns.tolist())
            logger.info(f"Found email columns: {email_columns}")
            
            # Map columns to standard format
            column_mapping = self.map_columns(df.columns.tolist())
            logger.info(f"Column mapping: {column_mapping}")
            
            # Save column mapping for future reference
            self.save_column_mapping(column_mapping, file_path)
            
            for index, row in df.iterrows():
                try:
                    # Extract primary email
                    primary_email = self.extract_primary_email(row, email_columns)
                    
                    if not primary_email:
                        logger.warning(f"No valid email found in row {index}")
                        errors += 1
                        continue
                    
                    # Extract mapped data
                    contact_data = {}
                    for std_col, csv_col in column_mapping.items():
                        if csv_col in df.columns:
                            value = row.get(csv_col, '')
                            if pd.notna(value) and value:
                                contact_data[std_col] = str(value).strip()
                    
                    # Store all original data as JSON
                    all_data = {}
                    for col in df.columns:
                        val = row.get(col, '')
                        if pd.notna(val) and val:
                            all_data[col] = str(val).strip()
                    
                    # Insert or update contact
                    self.upsert_contact(
                        email=primary_email,
                        contact_data=contact_data,
                        all_data=all_data,
                        source_file=os.path.basename(file_path)
                    )
                    
                    successful_inserts += 1
                    
                except Exception as e:
                    logger.error(f"Error processing row {index}: {str(e)}")
                    errors += 1
                    continue
            
            # Save file metadata
            self.save_file_metadata(file_path, total_rows, successful_inserts, errors, column_mapping)
            
            return total_rows, successful_inserts, errors
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            return 0, 0, 1
    
    def upsert_contact(self, email: str, contact_data: Dict, all_data: Dict, source_file: str):
        """Insert new contact or update existing one, automatically creating and linking companies"""
        
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    # First, handle company creation/linking if company info exists
                    company_id = None
                    company_name = contact_data.get('company_name', '').strip()
                    company_domain = contact_data.get('company_domain', '').strip()
                    
                    if company_name or company_domain:
                        # Check if company already exists (by name first, then domain)
                        if company_name:
                            result = conn.execute(text("""
                                SELECT id FROM companies 
                                WHERE LOWER(company_name) = LOWER(:company_name) 
                                AND tenant_id = :tenant_id
                                LIMIT 1
                            """), {"company_name": company_name, "tenant_id": 1})
                            row = result.fetchone()
                            if row:
                                company_id = row.id
                        
                        # If not found by name, check by domain
                        if not company_id and company_domain:
                            domain_pattern = f"%{company_domain.lower()}%"
                            result = conn.execute(text("""
                                SELECT id FROM companies 
                                WHERE LOWER(website_url) LIKE :domain_pattern 
                                AND tenant_id = :tenant_id
                                LIMIT 1
                            """), {"domain_pattern": domain_pattern, "tenant_id": 1})
                            row = result.fetchone()
                            if row:
                                company_id = row.id
                        
                        # Create new company if it doesn't exist
                        if not company_id:
                            website_url = ''
                            if company_domain:
                                website_url = company_domain if company_domain.startswith(('http://', 'https://')) else f"https://{company_domain}"
                            
                            fallback_name = company_name or company_domain or 'Unknown'
                            # TODO: Add tenant_id support when used in multi-tenant context
                            result = conn.execute(text("""
                                INSERT INTO companies (
                                    company_name, website_url, company_research, 
                                    research_status, created_at, updated_at, tenant_id
                                ) VALUES (
                                    :company_name, :website_url, :company_research,
                                    'pending', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, :tenant_id
                                ) RETURNING id
                            """), {
                                "company_name": fallback_name,
                                "website_url": website_url,
                                "company_research": f"Company automatically created during contact import from {source_file}. Research pending.",
                                "tenant_id": 1  # Default tenant for standalone script - TODO: make configurable
                            })
                            company_id = result.fetchone().id
                            logger.info(f"Created new company '{fallback_name}' with ID {company_id}")
                    
                    # Check if contact exists
                    result = conn.execute(
                        text("SELECT source_files, all_data, company_id FROM contacts WHERE email = :email AND tenant_id = :tenant_id"),
                        {"email": email, "tenant_id": 1}  # Default tenant for standalone script
                    )
                    existing = result.fetchone()
                    
                    if existing:
                        # Update existing contact
                        existing_source_files = existing[0] if existing[0] else []
                        existing_all_data = existing[1] if existing[1] else {}
                        existing_company_id = existing[2]
                        
                        # Add new source file if not already present
                        if source_file not in existing_source_files:
                            existing_source_files.append(source_file)
                        
                        # Merge all_data (new data takes precedence)
                        merged_all_data = {**existing_all_data, **all_data}
                        
                        # Build update query
                        update_fields = []
                        update_params = {"email": email}
                        
                        for field, value in contact_data.items():
                            if value:  # Only update non-empty values
                                update_fields.append(f"{field} = :{field}")
                                update_params[field] = value
                        
                        # Update company_id if we found/created one and it's different
                        if company_id and company_id != existing_company_id:
                            update_fields.append("company_id = :company_id")
                            update_params["company_id"] = company_id
                        
                        if update_fields:
                            update_fields.extend([
                                "source_files = :source_files",
                                "all_data = :all_data",
                                "updated_at = :updated_at"
                            ])
                            update_params.update({
                                "source_files": json.dumps(existing_source_files),
                                "all_data": json.dumps(merged_all_data),
                                "updated_at": datetime.now()
                            })
                            
                            update_params["tenant_id"] = 1  # Default tenant for standalone script
                            query = f"UPDATE contacts SET {', '.join(update_fields)} WHERE email = :email AND tenant_id = :tenant_id"
                            conn.execute(text(query), update_params)
                    else:
                        # Insert new contact with company_id
                        insert_params = {
                            "email": email,
                            "first_name": contact_data.get('first_name', ''),
                            "last_name": contact_data.get('last_name', ''),
                            "full_name": contact_data.get('full_name', ''),
                            "job_title": contact_data.get('job_title', ''),
                            "company_name": contact_data.get('company_name', ''),
                            "company_domain": contact_data.get('company_domain', ''),
                            "linkedin_profile": contact_data.get('linkedin_profile', ''),
                            "location": contact_data.get('location', ''),
                            "phone": contact_data.get('phone', ''),
                            "linkedin_message": contact_data.get('linkedin_message', ''),
                            "company_id": company_id,
                            "source_files": json.dumps([source_file]),
                            "all_data": json.dumps(all_data),
                            "tenant_id": 1  # Default tenant for standalone script - TODO: make configurable
                        }
                        
                        conn.execute(text("""
                            INSERT INTO contacts (
                                email, first_name, last_name, full_name, job_title, 
                                company_name, company_domain, linkedin_profile, location, 
                                phone, linkedin_message, company_id, source_files, all_data, tenant_id
                            ) VALUES (
                                :email, :first_name, :last_name, :full_name, :job_title,
                                :company_name, :company_domain, :linkedin_profile, :location,
                                :phone, :linkedin_message, :company_id, :source_files, :all_data, :tenant_id
                            )
                        """), insert_params)
                        
        except SQLAlchemyError as e:
            logger.error(f"Database error in upsert_contact: {str(e)}")
            raise
    
    def save_file_metadata(self, file_path: str, total_rows: int, successful_inserts: int, 
                          errors: int, column_mapping: Dict):
        """Save file processing metadata"""
        filename = os.path.basename(file_path)
        
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    # Get default tenant ID for file ingestion
                    tenant_result = conn.execute(text("""
                        SELECT id FROM tenants WHERE slug = 'default' LIMIT 1
                    """))
                    tenant_row = tenant_result.fetchone()
                    if not tenant_row:
                        logger.error("No default tenant found - cannot save file metadata")
                        return
                    default_tenant_id = tenant_row.id
                    
                    conn.execute(text("""
                        INSERT INTO file_metadata 
                        (tenant_id, filename, file_path, total_rows, successful_inserts, errors, column_mapping)
                        VALUES (:tenant_id, :filename, :file_path, :total_rows, :successful_inserts, :errors, :column_mapping)
                        ON CONFLICT (tenant_id, filename) DO UPDATE SET
                            file_path = EXCLUDED.file_path,
                            processed_at = CURRENT_TIMESTAMP,
                            total_rows = EXCLUDED.total_rows,
                            successful_inserts = EXCLUDED.successful_inserts,
                            errors = EXCLUDED.errors,
                            column_mapping = EXCLUDED.column_mapping
                    """), {
                        "tenant_id": default_tenant_id,
                        "filename": filename,
                        "file_path": file_path,
                        "total_rows": total_rows,
                        "successful_inserts": successful_inserts,
                        "errors": errors,
                        "column_mapping": json.dumps(column_mapping)
                    })
        except SQLAlchemyError as e:
            logger.error(f"Error saving file metadata: {str(e)}")
    
    def save_column_mapping(self, column_mapping: Dict, file_path: str):
        """Save column mapping for future reference"""
        try:
            with self.engine.connect() as conn:
                with conn.begin():
                    for standard_col, source_col in column_mapping.items():
                        conn.execute(text("""
                            INSERT INTO column_mappings 
                            (source_column, standard_column, confidence_score, file_source)
                            VALUES (:source_column, :standard_column, :confidence_score, :file_source)
                        """), {
                            "source_column": source_col,
                            "standard_column": standard_col,
                            "confidence_score": 1.0,
                            "file_source": os.path.basename(file_path)
                        })
        except SQLAlchemyError as e:
            logger.error(f"Error saving column mapping: {str(e)}")
    
    def process_all_files(self):
        """Process all CSV files in the contacts directory"""
        if not os.path.exists(self.contacts_dir):
            logger.error(f"Contacts directory '{self.contacts_dir}' does not exist")
            return
        
        csv_files = [f for f in os.listdir(self.contacts_dir) if f.endswith('.csv')]
        
        if not csv_files:
            logger.warning(f"No CSV files found in '{self.contacts_dir}' directory")
            return
        
        logger.info(f"Found {len(csv_files)} CSV files to process")
        
        total_processed = 0
        total_inserted = 0
        total_errors = 0
        
        for csv_file in csv_files:
            file_path = os.path.join(self.contacts_dir, csv_file)
            rows, inserts, errs = self.process_csv_file(file_path)
            
            total_processed += rows
            total_inserted += inserts
            total_errors += errs
            
            logger.info(f"File {csv_file}: {rows} rows, {inserts} inserted, {errs} errors")
        
        logger.info(f"Processing complete: {total_processed} total rows, {total_inserted} successful inserts, {total_errors} errors")
    
    def get_statistics(self) -> Dict:
        """Get database statistics"""
        stats = {}
        
        try:
            with self.engine.connect() as conn:
                # Total contacts
                result = conn.execute(text("SELECT COUNT(*) FROM contacts"))
                stats['total_contacts'] = result.scalar()
                
                # Contacts by source file - GLOBAL across all tenants
                # TODO: Make this tenant-aware if needed for per-tenant stats
                result = conn.execute(text("""
                    SELECT filename, successful_inserts, total_rows, errors 
                    FROM file_metadata 
                    ORDER BY processed_at DESC
                """))
                stats['files_processed'] = [dict(row._mapping) for row in result]
                
                # Companies represented
                result = conn.execute(text("""
                    SELECT COUNT(DISTINCT company_name) FROM contacts 
                    WHERE company_name IS NOT NULL AND company_name != ''
                """))
                stats['unique_companies'] = result.scalar()
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting statistics: {str(e)}")
            stats = {'total_contacts': 0, 'files_processed': [], 'unique_companies': 0}
        
        return stats
    
    def search_contacts(self, search_term: str, limit: int = 10) -> List[Dict]:
        """Search contacts by name, company, or email"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT email, first_name, last_name, job_title, company_name, linkedin_profile
                    FROM contacts 
                    WHERE first_name ILIKE :search OR last_name ILIKE :search 
                       OR company_name ILIKE :search OR email ILIKE :search
                    LIMIT :limit
                """), {
                    "search": f"%{search_term}%",
                    "limit": limit
                })
                
                return [dict(row._mapping) for row in result]
                
        except SQLAlchemyError as e:
            logger.error(f"Error searching contacts: {str(e)}")
            return []
    
    def close(self):
        """Close database connection"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection closed")

def main():
    """Main function to run the data ingestion"""
    ingester = ContactDataIngester()
    
    try:
        ingester.connect_db()
        ingester.process_all_files()
        
        # Print statistics
        stats = ingester.get_statistics()
        print("\n" + "="*50)
        print("INGESTION COMPLETE - STATISTICS")
        print("="*50)
        print(f"Total contacts: {stats['total_contacts']}")
        print(f"Unique companies: {stats['unique_companies']}")
        print("\nFiles processed:")
        for file_info in stats['files_processed']:
            print(f"  {file_info['filename']}: {file_info['successful_inserts']}/{file_info['total_rows']} successful ({file_info['errors']} errors)")
        
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
    finally:
        ingester.close()

if __name__ == "__main__":
    main() 