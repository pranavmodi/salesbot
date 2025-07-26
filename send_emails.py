import smtplib
import time
import ssl
import os
from email.message import EmailMessage
from dotenv import load_dotenv
from database import InteractionsDB
from email_composers.composer_instance import composer
from app.utils.email_config import email_config, EmailAccount
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import logging

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Import non-sensitive configuration
try:
    import config
except ImportError:
    print("Warning: Configuration file config.py not found or could not be imported.")
    # Set a default subject if config.py is missing
    EMAIL_SUBJECT = "Following up"
    # Or exit if config.py is strictly required for other settings:
    # print("Please ensure config.py exists.")
    # exit(1)
else:
    EMAIL_SUBJECT = getattr(config, 'EMAIL_SUBJECT', 'Following up') # Get subject safely


# Constants from environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
EMAIL_DELAY_MINUTES = int(os.getenv("EMAIL_DELAY_MINUTES", "30"))  # Default to 30 minutes

# Check for multi-account configuration
try:
    accounts_available = email_config.get_all_accounts()
    if not accounts_available:
        logging.error("Error: No email accounts configured.")
        logging.error("Please configure EMAIL_ACCOUNTS in .env file using the web UI at /config")
        exit(1)
    else:
        logging.info(f"Using multi-account configuration with {len(accounts_available)} account(s)")
except Exception as e:
    logging.error(f"Error loading email configuration: {e}")
    logging.error("Please configure EMAIL_ACCOUNTS in .env file using the web UI at /config")
    exit(1)

# Legacy environment variables no longer needed - using multi-account configuration

if not DATABASE_URL:
    print("Error: DATABASE_URL environment variable is missing.")
    print("Please ensure it is defined in your .env file or system environment.")
    exit(1)

# SMTP configuration handled by EmailConfigManager

# Initialize the database
db = InteractionsDB()

import re
from email.utils import make_msgid

# ------------------------------------------------------------------ #

def get_db_engine():
    """Get database engine."""
    try:
        return create_engine(
            DATABASE_URL,
            pool_size=5,          # Maximum number of permanent connections
            max_overflow=10,      # Maximum number of connections that can overflow the pool
            pool_pre_ping=True,   # Verify connections before use
            pool_recycle=3600     # Recycle connections every hour
        )
    except Exception as e:
        logging.error(f"Error creating database engine: {e}")
        return None

def load_contacts_from_db():
    """Load all contacts from PostgreSQL database."""
    contacts = []
    engine = get_db_engine()
    if not engine:
        return contacts
        
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT email, first_name, last_name, full_name, job_title, 
                       company_name, company_domain, linkedin_profile, location, 
                       phone, linkedin_message, created_at, updated_at
                FROM contacts 
                WHERE email IS NOT NULL AND email != ''
                ORDER BY created_at DESC
            """))
            
            for row in result:
                contact_data = dict(row._mapping)
                # Convert to the format expected by the email composer
                lead_info = {
                    'name': contact_data.get('first_name', ''),
                    'email': contact_data.get('email', ''),
                    'company': contact_data.get('company_name', ''),
                    'position': contact_data.get('job_title', ''),
                    'full_name': contact_data.get('full_name', ''),
                    'last_name': contact_data.get('last_name', ''),
                    'location': contact_data.get('location', ''),
                    'linkedin_profile': contact_data.get('linkedin_profile', ''),
                    'company_domain': contact_data.get('company_domain', ''),
                }
                contacts.append(lead_info)
                
    except SQLAlchemyError as e:
        logging.error(f"Error loading contacts from database: {e}")
    except Exception as e:
        logging.error(f"Unexpected error loading contacts: {e}")
        
    return contacts

def send_email(recipient_email: str, subject: str, body_markdown: str, account_name: str = None) -> bool:
    """Send email using configured account (multi-account support)."""
    try:
        # Get the account to use
        if account_name:
            account = email_config.get_account_by_name(account_name)
            if not account:
                print(f"✗ Account '{account_name}' not found")
                return False
        else:
            account = email_config.get_default_account()
            if not account:
                print("✗ No default account available")
                return False

        # Use the EmailService method
        from app.services.email_service import EmailService
        success = EmailService._send_with_account(account, recipient_email, subject, body_markdown)
        
        if success:
            print(f"✓ Email sent to {recipient_email} from {account.email}")
            db.add_interaction(recipient_email, "email_sent", f"Subject: {subject} (via {account.email})")
        else:
            print(f"✗ Failed to send to {recipient_email} from {account.email}")
            db.add_interaction(recipient_email, "email_failed", f"Failed via {account.email}")
        
        return success
        
    except Exception as e:
        print(f"✗ Failed to send to {recipient_email}: {e}")
        db.add_interaction(recipient_email, "email_failed", str(e))
        return False

# Legacy send function removed - using multi-account system


# --- Main Logic ---
def main():
    """Loads contacts from PostgreSQL database and sends emails."""
    print("Loading contacts from PostgreSQL database...")
    contacts = load_contacts_from_db()
    
    if not contacts:
        print("No contacts found in database. Please ensure contacts have been imported using the data ingestion system.")
        return
    
    print(f"Found {len(contacts)} contacts in database")
    print("Starting email sending process...")
    
    for i, lead_info in enumerate(contacts):
        try:
            # Basic validation
            if not lead_info['email'] or "@" not in lead_info['email']:
                print(f"Skipping contact {i+1}: Invalid or missing email address '{lead_info['email']}'")
                continue

            # Generate email content using GPT-4
            email_content = composer.compose_email(lead_info)
            if not email_content:
                print(f"Skipping contact {i+1}: Failed to generate email content")
                continue

            # Send the email
            if send_email(lead_info['email'], email_content['subject'], email_content['body']):
                # Add configurable delay to avoid rate limiting and respect Zoho's policies
                delay_seconds = EMAIL_DELAY_MINUTES * 60
                print(f"Email sent. Waiting {EMAIL_DELAY_MINUTES} minutes before next email to avoid triggering spam detection...")
                time.sleep(delay_seconds)
            else:
                print(f"Failed to send email to {lead_info['email']}. Continuing...")

        except Exception as e:
            print(f"An unexpected error occurred processing contact {i+1}: {e}")

    print("Email sending process finished.")

if __name__ == "__main__":
    # Add socket import for error handling
    import socket
    main() 