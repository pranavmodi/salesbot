import csv
import smtplib
import time
import ssl
import os
from email.message import EmailMessage
from dotenv import load_dotenv
from database import InteractionsDB
from composer_instance import composer

# Load environment variables from .env file
load_dotenv()

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
# Load CSV Path from .env, with a default value
CSV_FILE_PATH = os.getenv("CSV_FILE_PATH", 'leads_with_messages.csv')

# Validate essential environment variables
if not all([SMTP_HOST, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD]):
    print("Error: One or more environment variables (SMTP_HOST, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD) are missing.")
    print("Please ensure they are defined in your .env file or system environment.")
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
    """Reads CSV and sends emails."""
    print(f"Attempting to read CSV file: {CSV_FILE_PATH}")
    try:
        with open(CSV_FILE_PATH, mode='r', encoding='utf-8') as file:
            csv_reader = csv.reader(file)
            header = next(csv_reader)  # Skip header row

            # Find column indices (more robust than fixed indices)
            required_columns = ['Work Email', 'First Name', 'Company', 'Position']
            column_indices = {}
            
            for col in required_columns:
                try:
                    column_indices[col] = header.index(col)
                except ValueError:
                    print(f"Error: Missing required column: {col}")
                    return

            print("Starting email sending process...")
            for i, row in enumerate(csv_reader):
                try:
                    # Extract lead information
                    lead_info = {
                        'name': row[column_indices['First Name']].strip(),
                        'email': row[column_indices['Work Email']].strip(),
                        'company': row[column_indices['Company']].strip(),
                        'position': row[column_indices['Position']].strip()
                    }

                    # Basic validation
                    if not lead_info['email'] or "@" not in lead_info['email']:
                        print(f"Skipping row {i+2}: Invalid or missing email address '{lead_info['email']}'")
                        continue

                    # Generate email content using GPT-4
                    email_content = composer.compose_email(lead_info)
                    if not email_content:
                        print(f"Skipping row {i+2}: Failed to generate email content")
                        continue

                    # Send the email
                    if send_email(lead_info['email'], email_content['subject'], email_content['body']):
                        # Optional: Add a delay to avoid rate limiting
                        time.sleep(1)  # Delay for 1 second between emails
                    else:
                        print(f"Failed to send email to {lead_info['email']}. Continuing...")

                except IndexError:
                    print(f"Skipping row {i+2}: Row has fewer columns than expected.")
                except Exception as e:
                    print(f"An unexpected error occurred processing row {i+2}: {e}")

            print("Email sending process finished.")

    except FileNotFoundError:
        print(f"Error: CSV file not found at {CSV_FILE_PATH}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    # Add socket import for error handling
    import socket
    main() 