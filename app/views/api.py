from flask import Blueprint, request, jsonify, current_app

from app.models.contact import Contact
from app.services.email_service import EmailService
from app.services.email_reader_service import email_reader, configure_email_reader
from app.utils.email_config import email_config, EmailAccount
import os
import tempfile
import pandas as pd
import numpy as np
from data_ingestion_system import ContactDataIngester
from app.models.email_history import EmailHistory

bp = Blueprint('api', __name__, url_prefix='/api')

def clean_data_for_json(data):
    """Clean pandas data for JSON serialization by handling NaN values and other types."""
    if isinstance(data, dict):
        return {k: clean_data_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_data_for_json(item) for item in data]
    elif pd.isna(data) or data is np.nan:
        return None
    elif isinstance(data, (np.integer, np.int64)):
        return int(data)
    elif isinstance(data, (np.floating, np.float64)):
        return float(data) if not pd.isna(data) else None
    elif isinstance(data, np.bool_):
        return bool(data)
    elif isinstance(data, (pd.Timestamp, np.datetime64)):
        return data.isoformat() if not pd.isna(data) else None
    else:
        return str(data) if data is not None else None

@bp.route('/contacts', methods=['GET'])
def get_contacts():
    """Get all contacts."""
    try:
        contacts = Contact.load_all()
        return jsonify([contact.to_dict() for contact in contacts])
    except Exception as e:
        current_app.logger.error(f"Error getting contacts: {str(e)}")
        return jsonify({'error': 'Failed to load contacts'}), 500

@bp.route('/contact/<email>', methods=['GET'])
def get_contact(email):
    """Get a specific contact by email."""
    try:
        contacts = Contact.search(email)
        if contacts:
            return jsonify(contacts[0].to_dict())
        return jsonify({'error': 'Contact not found'}), 404
    except Exception as e:
        current_app.logger.error(f"Error getting contact: {str(e)}")
        return jsonify({'error': 'Failed to load contact'}), 500

@bp.route('/preview_email', methods=['POST'])
def preview_email():
    """Generate email preview for a contact."""
    try:
        data = request.get_json()
        composer_type = data.get('composer_type', 'warm')
        
        # Handle new format (contact_id)
        contact_id = data.get('contact_id')
        if contact_id:
            email_content = EmailService.compose_email(
                contact_id=contact_id, 
                calendar_url=data.get('calendar_url'), 
                extra_context=data.get('extra_context'), 
                composer_type=composer_type
            )
            if email_content:
                return jsonify(email_content)
            else:
                return jsonify({"error": "Failed to compose email"}), 500
        
        # Handle old format (contact_data) for backward compatibility
        contact_data = data.get('contact_data')
        if contact_data:
            # For the old format, we need to create a temporary contact or use the composer directly
            # Import the composers directly
            if composer_type == "alt_subject":
                from email_composer_alt_subject import AltSubjectEmailComposer
                composer = AltSubjectEmailComposer()
            else:
                from email_composer_warm import WarmEmailComposer
                composer = WarmEmailComposer()
            
            # Use the composer directly with the contact data
            lead_data = {
                "name": contact_data.get('name', ''),
                "email": contact_data.get('email', ''),
                "company": contact_data.get('company', ''),
                "position": contact_data.get('position', ''),
                "website": contact_data.get('website', ''),
                "notes": contact_data.get('notes', ''),
            }
            
            calendar_url = data.get('calendar_url') or os.getenv("CALENDAR_URL", "https://calendly.com/pranav-modi/15-minute-meeting")
            email_content = composer.compose_email(lead=lead_data, calendar_url=calendar_url, extra_context=data.get('extra_context'))
            
            if email_content and 'subject' in email_content and 'body' in email_content:
                return jsonify({
                    'subject': email_content['subject'],
                    'body': email_content['body']
                })
            else:
                return jsonify({"error": "Failed to compose email"}), 500
        
        return jsonify({"error": "Missing contact_id or contact_data"}), 400
        
    except Exception as e:
        current_app.logger.error(f"Error generating email preview: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/send_email', methods=['POST'])
def send_email():
    """Send an email to a specific recipient."""
    try:
        recipient_email = request.form.get('recipient_email')
        recipient_name = request.form.get('recipient_name')
        subject = request.form.get('preview_subject')
        body = request.form.get('preview_body')
        account_name = request.form.get('account_name')  # Optional account selection
        
        if not all([recipient_email, recipient_name, subject, body]):
            return jsonify({
                'success': False,
                'message': 'Missing required email information'
            }), 400
        
        # Use the new multi-account send method
        success = EmailService.send_email_with_account(
            recipient_email, recipient_name, subject, body, account_name
        )
        
        return jsonify({
            'success': success,
            'message': f"Email {'sent' if success else 'failed'} to {recipient_email}"
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in send_email: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500

@bp.route('/email/accounts', methods=['GET'])
def get_email_accounts():
    """Get all configured email accounts."""
    try:
        accounts = EmailService.get_available_accounts()
        return jsonify({
            'success': True,
            'accounts': accounts
        })
    except Exception as e:
        current_app.logger.error(f"Error getting email accounts: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to load email accounts'
        }), 500

@bp.route('/email/accounts/<account_name>/test', methods=['POST'])
def test_email_account(account_name):
    """Test a specific email account connection."""
    try:
        account = email_config.get_account_by_name(account_name)
        if not account:
            return jsonify({
                'success': False,
                'message': f'Account "{account_name}" not found'
            }), 404
        
        # Try to send a test email to verify the account works
        test_success = EmailService._send_with_account(
            account, 
            account.email,  # Send to self
            "Test Email Configuration", 
            "This is a test email to verify your account configuration is working."
        )
        
        return jsonify({
            'success': test_success,
            'message': f'Account "{account_name}" {"works correctly" if test_success else "failed to send test email"}',
            'account_email': account.email
        })
        
    except Exception as e:
        current_app.logger.error(f"Error testing email account {account_name}: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to test email account'
        }), 500

@bp.route('/email/config/save', methods=['POST'])
def save_email_configuration():
    """Save email configuration to environment file."""
    try:
        data = request.get_json()
        if not data or 'accounts' not in data:
            return jsonify({
                'success': False,
                'message': 'Invalid configuration data'
            }), 400
        
        accounts = data['accounts']
        if not accounts:
            return jsonify({
                'success': False,
                'message': 'At least one account must be configured'
            }), 400
        
        # Validate accounts
        for i, account in enumerate(accounts):
            required_fields = ['name', 'email', 'password']
            for field in required_fields:
                if not account.get(field):
                    return jsonify({
                        'success': False,
                        'message': f'Account {i+1}: {field} is required'
                    }), 400
        
        # Convert to JSON string for environment file
        import json
        import os
        
        config_json = json.dumps(accounts, separators=(',', ':'))
        
        # Read current .env2 file
        env_file_path = '.env2'
        lines = []
        
        if os.path.exists(env_file_path):
            with open(env_file_path, 'r') as f:
                lines = f.readlines()
        
        # Update or add EMAIL_ACCOUNTS line
        found = False
        for i, line in enumerate(lines):
            if line.startswith('EMAIL_ACCOUNTS='):
                lines[i] = f'EMAIL_ACCOUNTS={config_json}\n'
                found = True
                break
        
        if not found:
            lines.append(f'EMAIL_ACCOUNTS={config_json}\n')
        
        # Write back to file
        with open(env_file_path, 'w') as f:
            f.writelines(lines)
        
        return jsonify({
            'success': True,
            'message': 'Configuration saved successfully',
            'accounts_count': len(accounts)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error saving email configuration: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to save configuration: {str(e)}'
        }), 500

@bp.route('/send_bulk_emails', methods=['POST'])
def send_bulk_emails():
    """Send emails to multiple recipients."""
    try:
        data = request.get_json()
        recipients_data = data.get('recipients_data')
        composer_type = data.get('composer_type', 'warm')
        calendar_url = data.get('calendar_url')
        extra_context = data.get('extra_context')
        account_name = data.get('account_name')  # New account selection parameter

        if not recipients_data or not isinstance(recipients_data, list):
            return jsonify({"error": "Missing or invalid recipients_data"}), 400

        results = EmailService.send_bulk_emails(
            recipients_data=recipients_data, 
            composer_type=composer_type, 
            calendar_url=calendar_url, 
            extra_context=extra_context,
            account_name=account_name
        )
        
        return jsonify(results)
        
    except Exception as e:
        current_app.logger.error(f"Error in send_bulk_emails: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500

# New Email Reading Endpoints

@bp.route('/email/configure', methods=['POST'])
def configure_email():
    """Configure email reading service."""
    try:
        success = configure_email_reader()
        return jsonify({
            'success': success,
            'message': 'Email reader configured successfully' if success else 'Failed to configure email reader'
        })
    except Exception as e:
        current_app.logger.error(f"Error configuring email reader: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to configure email reader'
        }), 500

@bp.route('/email/accounts/<account_name>/emails', methods=['GET'])
def get_account_emails(account_name):
    """Get emails for a specific account."""
    try:
        from app.utils.email_config import email_config
        
        account = email_config.get_account_by_name(account_name)
        if not account:
            return jsonify({
                'success': False,
                'message': f'Account "{account_name}" not found'
            }), 404
        
        # Configure email reader for this specific account
        from app.services.email_reader_service import EmailReaderService
        
        account_reader = EmailReaderService()
        account_reader.configure_imap(
            host=account.imap_host,
            email=account.email,
            password=account.password,
            port=account.imap_port
        )
        
        if not account_reader.connect():
            return jsonify({
                'success': False,
                'message': f'Failed to connect to {account.email}'
            }), 500
        
        # Fetch emails from both INBOX and Sent folders
        emails = []
        for folder in ['INBOX', 'Sent']:
            try:
                account_reader.connection.select(folder)
                status, message_ids = account_reader.connection.search(None, 'ALL')
                if status == 'OK' and message_ids[0]:
                    ids = message_ids[0].split()
                    # Limit to last 50 emails per folder for performance
                    for msg_id in ids[-50:]:
                        email_data = account_reader._fetch_email_data(msg_id, folder)
                        if email_data:
                            emails.append(email_data)
            except Exception as e:
                current_app.logger.warning(f"Error fetching emails from {folder} for {account.email}: {e}")
        
        # Sort emails by date, newest first
        emails.sort(key=lambda x: x.get('date', datetime.min), reverse=True)
        
        # Convert datetime to isoformat for JSON
        for email in emails:
            if email.get('date') and hasattr(email['date'], 'isoformat'):
                email['date'] = email['date'].isoformat()
        
        account_reader.connection.close()
        
        return jsonify({
            'success': True,
            'emails': emails,
            'account': account.email,
            'count': len(emails)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching emails for account {account_name}: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch emails'
        }), 500

@bp.route('/email/conversations/<contact_email>', methods=['GET'])
def get_contact_conversations(contact_email):
    """Get email conversations with a specific contact."""
    try:
        # Check if email reading feature is enabled
        if not EMAIL_READING_ENABLED:
            return jsonify({
                'error': 'Email reading feature is currently disabled',
                'message': 'Email conversation access requires IMAP access, which needs a plan upgrade. This feature is temporarily disabled.',
                'feature_disabled': True
            }), 503
        
        # Get query parameters
        days_back = request.args.get('days_back', 365, type=int)
        
        # Configure email reader if not already done
        if not email_reader.connection:
            success = configure_email_reader()
            if not success:
                return jsonify({
                    'error': 'Email reader not configured',
                    'message': 'Please check email credentials'
                }), 503
        
        # Get conversation summary
        conversation_data = email_reader.get_conversation_summary(contact_email)
        
        return jsonify({
            'contact_email': contact_email,
            'conversation_summary': conversation_data,
            'success': True
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting conversations for {contact_email}: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve conversations',
            'message': str(e)
        }), 500

@bp.route('/email/conversations/<contact_email>/detailed', methods=['GET'])
def get_detailed_conversations(contact_email):
    """Get detailed email conversations with threading."""
    try:
        # Check if email reading feature is enabled
        if not EMAIL_READING_ENABLED:
            return jsonify({
                'error': 'Email reading feature is currently disabled',
                'message': 'Email conversation access requires IMAP access, which needs a plan upgrade. This feature is temporarily disabled.',
                'feature_disabled': True
            }), 503
            
        days_back = request.args.get('days_back', 365, type=int)
        
        # Configure email reader if needed
        if not email_reader.connection:
            success = configure_email_reader()
            if not success:
                return jsonify({
                    'error': 'Email reader not configured'
                }), 503
        
        # Get all conversations
        conversations = email_reader.search_conversations_with_contact(contact_email, days_back)
        
        # Group by threads
        threads = email_reader.group_emails_by_thread(conversations)
        
        # Format for JSON serialization
        formatted_threads = {}
        for thread_id, emails in threads.items():
            formatted_emails = []
            for email_data in emails:
                formatted_email = {
                    'id': email_data['id'],
                    'subject': email_data['subject'],
                    'from': email_data['from'],
                    'to': email_data['to'],
                    'date': email_data['date'].isoformat() if email_data['date'] else None,
                    'body': email_data['body'][:500] + '...' if len(email_data['body']) > 500 else email_data['body'],
                    'direction': email_data['direction'],
                    'folder': email_data['folder']
                }
                formatted_emails.append(formatted_email)
            
            formatted_threads[thread_id] = {
                'thread_id': thread_id,
                'email_count': len(formatted_emails),
                'emails': formatted_emails
            }
        
        return jsonify({
            'contact_email': contact_email,
            'total_emails': len(conversations),
            'thread_count': len(threads),
            'threads': formatted_threads,
            'success': True
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting detailed conversations: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve detailed conversations',
            'message': str(e)
        }), 500

@bp.route('/email/test-connection', methods=['POST'])
def test_email_connection():
    """Test email connection."""
    try:
        # Check if email reading feature is enabled
        if not EMAIL_READING_ENABLED:
            return jsonify({
                'success': False,
                'message': 'Email reading feature is currently disabled. This feature requires IMAP access which needs a plan upgrade.',
                'feature_disabled': True
            })
        
        # Configure email reader
        success = configure_email_reader()
        if not success:
            return jsonify({
                'success': False,
                'message': 'Failed to configure email reader - check SENDER_EMAIL and SENDER_PASSWORD environment variables'
            })
        
        # Test connection
        connected = email_reader.connect()
        
        if connected:
            # Try to list folders to verify access
            try:
                status, folders = email_reader.connection.list()
                folder_count = len(folders) if folders else 0
                email_reader.disconnect()
                
                return jsonify({
                    'success': True,
                    'message': f'Successfully connected to email account',
                    'email': email_reader.email,
                    'imap_host': email_reader.imap_host,
                    'folder_count': folder_count
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'Connected but failed to access folders: {str(e)}'
                })
        else:
            # Check if it's an IMAP not enabled error
            error_message = 'Failed to connect to email server'
            
            # Try to extract more specific error information from logs
            # This is a simplified approach - in a real scenario you'd want to capture the actual error
            if email_reader.email and 'possibleminds.in' in email_reader.email:
                error_message = '''IMAP access not enabled for your Zoho account. 

To enable IMAP access:
1. Login to Zoho Mail (www.zoho.com/mail)
2. Go to Settings > Mail Accounts
3. Click on your email address
4. Under IMAP section, check "IMAP Access"
5. Click Save

Then try testing the connection again.'''
            
            return jsonify({
                'success': False,
                'message': error_message,
                'help_url': 'https://www.zoho.com/mail/help/imap-access.html'
            })
            
    except Exception as e:
        current_app.logger.error(f"Error testing email connection: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Connection test failed: {str(e)}'
        }), 500

@bp.route('/contacts/add', methods=['POST'])
def add_contact():
    """Add a new contact manually."""
    try:
        data = request.get_json()
        
        # Validate required fields
        email = data.get('email', '').strip()
        if not email:
            return jsonify({
                'success': False,
                'message': 'Email is required'
            }), 400
        
        # Basic email validation
        if '@' not in email or '.' not in email.split('@')[-1]:
            return jsonify({
                'success': False,
                'message': 'Please enter a valid email address'
            }), 400
        
        # Check if contact already exists
        existing_contacts = Contact.search(email)
        if existing_contacts:
            return jsonify({
                'success': False,
                'message': 'A contact with this email already exists'
            }), 400
        
        # Prepare contact data
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        full_name = data.get('full_name', '').strip()
        
        # Auto-generate full_name if not provided
        if not full_name and (first_name or last_name):
            full_name = f"{first_name} {last_name}".strip()
        
        # Create contact data dictionary
        contact_data = {
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'full_name': full_name,
            'job_title': data.get('job_title', '').strip(),
            'company_name': data.get('company_name', '').strip(),
            'company_domain': data.get('company_domain', '').strip(),
            'linkedin_profile': data.get('linkedin_profile', '').strip(),
            'location': data.get('location', '').strip(),
            'phone': data.get('phone', '').strip(),
            'linkedin_message': data.get('linkedin_message', '').strip(),
        }
        
        # Use the Contact model to save the contact
        # Since Contact model doesn't have a save method, we'll use the database directly
        from sqlalchemy import create_engine, text
        from datetime import datetime
        import json
        import os
        
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            return jsonify({
                'success': False,
                'message': 'Database connection error'
            }), 500
        
        engine = create_engine(database_url)
        with engine.connect() as conn:
            # Insert new contact
            with conn.begin():
                conn.execute(text("""
                    INSERT INTO contacts (
                        email, first_name, last_name, full_name, job_title, 
                        company_name, company_domain, linkedin_profile, location, 
                        phone, linkedin_message, source_files, all_data
                    ) VALUES (
                        :email, :first_name, :last_name, :full_name, :job_title,
                        :company_name, :company_domain, :linkedin_profile, :location,
                        :phone, :linkedin_message, :source_files, :all_data
                    )
                """), {
                    **contact_data,
                    'source_files': json.dumps(["manual_entry"]),
                    'all_data': json.dumps({
                        'source': 'manual_entry',
                        'created_by': 'user',
                        'entry_date': datetime.now().isoformat()
                    })
                })
        
        current_app.logger.info(f"Successfully added new contact: {email}")
        
        return jsonify({
            'success': True,
            'message': f'Contact {full_name or email} added successfully',
            'contact': {
                'email': email,
                'name': full_name or f"{first_name} {last_name}".strip() or email,
                'company': contact_data['company_name'],
                'job_title': contact_data['job_title']
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error adding contact: {e}")
        return jsonify({
            'success': False,
            'message': 'An unexpected error occurred'
        }), 500

@bp.route('/contacts/export', methods=['GET'])
def export_contacts():
    """Export contacts to CSV."""
    try:
        import csv
        import io
        
        contacts = Contact.load_all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Email', 'First Name', 'Last Name', 'Full Name', 'Company', 
                        'Job Title', 'Location', 'LinkedIn Profile', 'Company Domain'])
        
        # Write contact data
        for contact in contacts:
            writer.writerow([
                contact.email,
                contact.first_name,
                contact.last_name,
                contact.full_name,
                contact.company,
                contact.job_title,
                contact.location,
                contact.linkedin_profile,
                contact.company_domain
            ])
        
        output.seek(0)
        
        from flask import Response
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={"Content-disposition": "attachment; filename=contacts.csv"}
        )
        
    except Exception as e:
        current_app.logger.error(f"Error exporting contacts: {str(e)}")
        return jsonify({'error': 'Failed to export contacts'}), 500

@bp.route('/get_unsent_leads', methods=['GET'])
def get_unsent_leads():
    """Get contacts who haven't received emails yet."""
    try:
        unsent_contacts = EmailService.get_unsent_contacts()
        
        return jsonify({
            'unsent_leads': [contact.raw_data for contact in unsent_contacts],
            'count': len(unsent_contacts)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in get_unsent_leads: {str(e)}")
        return jsonify({
            'unsent_leads': [],
            'count': 0,
            'error': 'Failed to load unsent leads'
        }), 500

@bp.route('/search_contacts', methods=['GET'])
def search_contacts():
    """Search contacts by query."""
    try:
        query = request.args.get('q', '').strip()
        
        if not query:
            return jsonify({'contacts': [], 'count': 0})
        
        contacts = Contact.search(query)
        
        return jsonify({
            'contacts': [contact.to_dict() for contact in contacts],
            'count': len(contacts)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in search_contacts: {str(e)}")
        return jsonify({'error': 'Failed to search contacts'}), 500

@bp.route('/contacts/import', methods=['POST'])
def import_contacts():
    """Import contacts from uploaded CSV file."""
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({'error': 'File must be a CSV'}), 400
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as temp_file:
            file.save(temp_file.name)
            temp_file_path = temp_file.name
        
        try:
            # Read CSV file with better encoding handling
            try:
                df = pd.read_csv(temp_file_path)
            except UnicodeDecodeError:
                # Try with different encoding
                df = pd.read_csv(temp_file_path, encoding='latin-1')
            except Exception as e:
                raise Exception(f"Could not read CSV file. Please ensure it's a valid CSV format. Error: {str(e)}")
            
            # Check if DataFrame is empty
            if df.empty:
                raise Exception("CSV file is empty or contains no valid data")
            
            # Log basic info about the file
            current_app.logger.info(f"Processing CSV: {file.filename}, Shape: {df.shape}, Columns: {list(df.columns)}")
            
            # Check for basic data quality issues
            if len(df.columns) == 0:
                raise Exception("CSV file has no columns")
            
            # Initialize data ingester
            ingester = ContactDataIngester()
            ingester.connect_db()
            
            # Get statistics before import
            stats_before = ingester.get_statistics()
            contacts_before = stats_before['total_contacts']
            
            # Process the CSV file
            total_rows, successful_inserts, errors = ingester.process_csv_file(temp_file_path)
            
            # Get statistics after import
            stats_after = ingester.get_statistics()
            contacts_after = stats_after['total_contacts']
            
            # Calculate duplicates (rows that didn't increase total count)
            new_contacts = contacts_after - contacts_before
            duplicates = successful_inserts - new_contacts
            
            # Read CSV to get column preview
            try:
                df = pd.read_csv(temp_file_path)
            except UnicodeDecodeError:
                df = pd.read_csv(temp_file_path, encoding='latin-1')
            except Exception as e:
                raise Exception(f"Could not read CSV file for preview. Error: {str(e)}")
            
            columns = df.columns.tolist()
            sample_data_raw = df.head(3).to_dict('records') if len(df) > 0 else []
            sample_data = clean_data_for_json(sample_data_raw)
            
            # Clean up temporary file
            os.unlink(temp_file_path)
            
            return jsonify({
                'success': True,
                'statistics': {
                    'total_rows': total_rows,
                    'successful_inserts': successful_inserts,
                    'new_contacts': new_contacts,
                    'duplicates': duplicates,
                    'errors': errors,
                    'contacts_before': contacts_before,
                    'contacts_after': contacts_after
                },
                'file_info': {
                    'filename': file.filename,
                    'columns': columns,
                    'sample_data': sample_data
                },
                'message': f'Successfully processed {total_rows} rows. {new_contacts} new contacts added, {duplicates} duplicates updated, {errors} errors.'
            })
            
        except Exception as e:
            # Clean up temporary file on error
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            current_app.logger.error(f"Error processing CSV file: {str(e)}")
            return jsonify({'error': f'Failed to process CSV file: {str(e)}'}), 500
        
        finally:
            if 'ingester' in locals():
                ingester.close()
        
    except Exception as e:
        current_app.logger.error(f"Error in CSV import: {str(e)}")
        return jsonify({'error': 'Failed to import CSV file'}), 500

@bp.route('/contacts/preview', methods=['POST'])
def preview_csv():
    """Preview CSV file contents and column mapping."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({'error': 'File must be a CSV'}), 400
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as temp_file:
            file.save(temp_file.name)
            temp_file_path = temp_file.name
        
        try:
            # Read CSV file with better encoding handling
            try:
                df = pd.read_csv(temp_file_path)
            except UnicodeDecodeError:
                # Try with different encoding
                df = pd.read_csv(temp_file_path, encoding='latin-1')
            except Exception as e:
                raise Exception(f"Could not read CSV file. Please ensure it's a valid CSV format. Error: {str(e)}")
            
            # Check if DataFrame is empty
            if df.empty:
                raise Exception("CSV file is empty or contains no valid data")
            
            # Log basic info about the file
            current_app.logger.info(f"Processing CSV: {file.filename}, Shape: {df.shape}, Columns: {list(df.columns)}")
            
            # Check for basic data quality issues
            if len(df.columns) == 0:
                raise Exception("CSV file has no columns")
            
            # Initialize data ingester for column mapping
            ingester = ContactDataIngester()
            
            # Get column information
            columns = df.columns.tolist()
            email_columns = ingester.identify_email_columns(columns)
            column_mapping = ingester.map_columns(columns)
            
            # Get sample data (first 5 rows) and clean for JSON
            sample_data_raw = df.head(5).to_dict('records')
            sample_data = clean_data_for_json(sample_data_raw)
            
            # Clean up temporary file
            os.unlink(temp_file_path)
            
            return jsonify({
                'success': True,
                'file_info': {
                    'filename': file.filename,
                    'total_rows': len(df),
                    'columns': columns,
                    'email_columns': email_columns,
                    'column_mapping': column_mapping,
                    'sample_data': sample_data
                }
            })
            
        except Exception as e:
            # Clean up temporary file on error
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            current_app.logger.error(f"Error previewing CSV file: {str(e)}")
            return jsonify({'error': f'Failed to preview CSV file: {str(e)}'}), 500
        
    except Exception as e:
        current_app.logger.error(f"Error in CSV preview: {str(e)}")
        return jsonify({'error': 'Failed to preview CSV file'}), 500

@bp.route('/contacts/uncontacted', methods=['GET'])
def get_uncontacted_contacts():
    """Get contacts who haven't received any emails yet."""
    try:
        # Get all contacts
        all_contacts = Contact.load_all()
        
        # Get all email recipients from history
        email_history = EmailHistory.load_all()
        contacted_emails = set()
        
        for email in email_history:
            if email.to:
                contacted_emails.add(email.to.lower().strip())
        
        # Filter contacts who haven't been contacted
        uncontacted_contacts = []
        for contact in all_contacts:
            if contact.email and contact.email.lower().strip() not in contacted_emails:
                uncontacted_contacts.append(contact)
        
        return jsonify({
            'contacts': [contact.to_dict() for contact in uncontacted_contacts],
            'count': len(uncontacted_contacts),
            'total_contacts': len(all_contacts),
            'contacted_count': len(contacted_emails)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting uncontacted contacts: {str(e)}")
        return jsonify({'error': 'Failed to load uncontacted contacts'}), 500

@bp.route('/send_test_email', methods=['POST'])
def send_test_email_route():
    """Send a test email to a list of specified email addresses."""
    try:
        data = request.get_json()
        recipient_emails = data.get('recipient_emails')
        subject = data.get('subject', 'Test Email') # Default subject
        body = data.get('body')

        if not recipient_emails or not isinstance(recipient_emails, list) or not body:
            return jsonify({
                'success': False,
                'message': 'Missing required information: recipient_emails (list) and body (string) are required.'
            }), 400
        
        # Validate email formats in recipient_emails (basic check)
        for email_address in recipient_emails:
            if not isinstance(email_address, str) or "@" not in email_address:
                return jsonify({
                    'success': False,
                    'message': f'Invalid email address format: {email_address}'
                }), 400

        results = EmailService.send_test_email(recipient_emails, subject, body)
        
        return jsonify({
            'success': True,
            'message': 'Test email sending process initiated.',
            'results': results
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in send_test_email_route: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500

@bp.route('/email/all', methods=['GET'])
def get_all_emails():
    """Get all inbox and sent emails for the configured account."""
    try:
        if not email_reader.connection:
            configure_email_reader()
        emails = []
        for folder in ['INBOX', 'Sent']:
            try:
                email_reader.connection.select(folder)
                status, message_ids = email_reader.connection.search(None, 'ALL')
                if status == 'OK' and message_ids[0]:
                    ids = message_ids[0].split()
                    for msg_id in ids[-50:]:  # Limit to last 50 emails per folder
                        email_data = email_reader._fetch_email_data(msg_id, folder)
                        if email_data:
                            emails.append(email_data)
            except Exception as e:
                current_app.logger.warning(f"Error fetching emails from {folder}: {e}")
        # Sort emails by date, newest first
        emails.sort(key=lambda x: x.get('date'), reverse=True)
        # Convert datetime to isoformat for JSON
        for email in emails:
            if email.get('date'):
                email['date'] = email['date'].isoformat()
        return jsonify({'emails': emails, 'success': True})
    except Exception as e:
        current_app.logger.error(f"Error fetching all emails: {str(e)}")
        return jsonify({'error': 'Failed to fetch emails', 'success': False}), 500 