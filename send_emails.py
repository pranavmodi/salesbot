import smtplib
import time
import ssl
import os
from email.message import EmailMessage
from dotenv import load_dotenv
from database import InteractionsDB
from composer_instance import composer
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
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = os.getenv("SMTP_PORT")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
DATABASE_URL = os.getenv("DATABASE_URL")
EMAIL_DELAY_MINUTES = int(os.getenv("EMAIL_DELAY_MINUTES", "30"))  # Default to 30 minutes

# Validate essential environment variables
if not all([SENDER_EMAIL, SENDER_PASSWORD]):
    logging.error("Error: SENDER_EMAIL and SENDER_PASSWORD must be set in environment.")
    exit(1)

# Auto-detect SMTP settings from email if not explicitly set
if not SMTP_HOST:
    domain = SENDER_EMAIL.split('@')[-1].lower()
    if domain in ['zoho.in', 'possibleminds.in', 'possiblemindshq.com']:
        SMTP_HOST = 'smtp.zoho.in'
        SMTP_PORT = 465 # Or 587 for TLS
        logging.info(f"Auto-detected Zoho India SMTP settings: {SMTP_HOST}:{SMTP_PORT}")
    elif 'zoho.com' in domain:
        SMTP_HOST = 'smtp.zoho.com'
        SMTP_PORT = 465
        logging.info(f"Auto-detected Zoho SMTP settings: {SMTP_HOST}:{SMTP_PORT}")
    # Add other provider detections as needed

# Validate essential environment variables
if not all([SMTP_HOST, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD]):
    logging.error("Error: One or more environment variables (SMTP_HOST, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD) are missing.")
    logging.error("Please ensure they are defined in your .env file or system environment.")
    exit(1)

if not DATABASE_URL:
    print("Error: DATABASE_URL environment variable is missing.")
    print("Please ensure it is defined in your .env file or system environment.")
    exit(1)

# Try converting port to integer
try:
    SMTP_PORT = int(SMTP_PORT)
except (ValueError, TypeError):
     print(f"Error: SMTP_PORT ('{SMTP_PORT}') is not a valid integer.")
     print("Please check the SMTP_PORT value in your .env file.")
     exit(1)

# Initialize the database
db = InteractionsDB()

import re
from email.utils import make_msgid

# ------------------------------------------------------------------ #

def get_db_engine():
    """Get database engine."""
    try:
        return create_engine(DATABASE_URL)
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

def send_email(recipient_email: str, subject: str, body_markdown: str) -> bool:
    """Render a nicer HTML template & send."""
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = recipient_email
    msg["Message-ID"] = make_msgid()             # helpful for threading

    # ---------- plain-text part -------------
    msg.set_content(body_markdown)

    # ---------- send ------------------------
    context = ssl.create_default_context()
    try:
        use_ssl = int(SMTP_PORT) == 465 or os.getenv("SMTP_USE_SSL", "False").lower() == "true"
        if use_ssl:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls(context=context)
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.send_message(msg)
        print(f"✓ Email sent to {recipient_email}")
        db.add_interaction(recipient_email, "email_sent", f"Subject: {subject}")
        return True
    except Exception as e:
        print(f"✗ Failed to send to {recipient_email}: {e}")
        db.add_interaction(recipient_email, "email_failed", str(e))
        return False


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