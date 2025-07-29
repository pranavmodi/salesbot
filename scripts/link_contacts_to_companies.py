#!/usr/bin/env python3
"""
Link Contacts to Companies Script

This script updates the company_id field in contacts to link them to their companies.
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Add the parent directory to sys.path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

def main():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        return
    
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as conn:
            with conn.begin():
                # Update contacts to reference company IDs
                result = conn.execute(text("""
                    UPDATE contacts 
                    SET company_id = companies.id
                    FROM companies
                    WHERE LOWER(contacts.company_name) = LOWER(companies.company_name)
                        AND contacts.company_name IS NOT NULL
                        AND contacts.company_name != ''
                """))
                
                print(f"✅ Updated {result.rowcount} contacts with company IDs")
                
    except Exception as e:
        print(f"❌ Error linking contacts to companies: {e}")

if __name__ == "__main__":
    main()