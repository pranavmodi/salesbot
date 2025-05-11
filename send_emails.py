import csv
import smtplib
import time
import ssl
import os
from email.message import EmailMessage
from dotenv import load_dotenv
from database import InteractionsDB
from email_composer import EmailComposer  # Add this import

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

# Initialize the database and email composer
db = InteractionsDB()
composer = EmailComposer()

import re
from email.utils import make_msgid

# ------------------------------------------------------------------ #
def _markdown_to_html(markdown: str) -> str:
    """Basic Markdown-ish → HTML for cold-email body."""
    text = markdown.strip()

    # First convert markdown bold to HTML strong tags
    text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)

    # escape any stray angle brackets
    text = text.replace("<", "&lt;").replace(">", "&gt;")

    # Now unescape the strong tags we want to keep
    text = text.replace("&lt;strong&gt;", "<strong>").replace("&lt;/strong&gt;", "</strong>")

    # split into lines so we can detect lists / paras
    html_lines = []
    for line in text.splitlines():
        line = line.rstrip()
        if not line:
            html_lines.append("")                # blank line → paragraph break
        elif re.match(r"^(\* |- |• )", line) or "<strong>" in line:
            clean = re.sub(r"^(\* |- |• )\s*", "", line)
            html_lines.append(f"<li>{clean}</li>")
        else:
            html_lines.append(line)

    # Collapse into blocks
    html_body = []
    in_list = False
    for l in html_lines:
        if l.startswith("<li>"):
            if not in_list:
                html_body.append("<ul style='margin-top:0; margin-bottom:1em;'>"); in_list = True
            html_body.append(l)
        else:
            if in_list:                          # close any open list
                html_body.append("</ul>"); in_list = False
            if l == "":
                html_body.append("</p><p>")
            else:
                html_body.append(l)

    if in_list:
        html_body.append("</ul>")

    # Split the body into main content and signature
    content = "".join(html_body).strip()
    signature_parts = content.split("Cheers,")
    
    if len(signature_parts) > 1:
        main_content = signature_parts[0].strip()
        signature = "Cheers," + signature_parts[1].strip()
        
        # Format signature with proper line breaks
        signature_lines = signature.split('\n')
        signature_html = []
        for line in signature_lines:
            if line.strip():
                signature_html.append(line.strip())
        
        return f"<p>{main_content}</p><div class='signature'>{'<br>'.join(signature_html)}</div>"
    else:
        return f"<p>{content}</p>"

def send_email(recipient_email: str, subject: str, body_markdown: str) -> bool:
    """Render a nicer HTML template & send."""
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = recipient_email
    msg["Message-ID"] = make_msgid()             # helpful for threading

    # ---------- plain-text part -------------
    msg.set_content(body_markdown)

    # ---------- HTML part -------------------
    html_body   = _markdown_to_html(body_markdown)
    full_html = f"""\
<!DOCTYPE html><html><head>
<meta charset="UTF-8">
<style>
  body {{ font-family: Arial, sans-serif; color:#333; line-height: 1.6; }}
  a {{ color:#0066cc; text-decoration: none; }}
  .container {{ max-width:600px; margin:0 auto; padding:24px; }}
  p {{ margin: 0 0 1.2em 0; }}
  ul {{ margin: 0 0 1.2em 0; padding-left: 1.5em; }}
  li {{ margin: 0.8em 0; }}
  strong {{ color: #000; font-weight: 600; }}
  .signature {{ margin-top: 2em; line-height: 1.8; }}
</style>
</head><body>
  <table role="presentation" class="container" width="100%" cellspacing="0" cellpadding="0">
    <tr><td>
      {html_body}
    </td></tr>
  </table>
</body></html>"""

    msg.add_alternative(full_html, subtype="html")

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