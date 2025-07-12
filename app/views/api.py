from flask import Blueprint, request, jsonify, current_app
from datetime import datetime

from app.models.contact import Contact
from app.models.company import Company
from app.services.email_service import EmailService
from app.services.email_reader_service import email_reader, configure_email_reader
from app.utils.email_config import email_config, EmailAccount
import os
import tempfile
import pandas as pd
import numpy as np
from data_ingestion_system import ContactDataIngester
from app.models.email_history import EmailHistory
import subprocess
import threading

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

@bp.route('/contact/<email>', methods=['PUT'])
def update_contact(email):
    """Update an existing contact's details."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
 
        # Allowed fields for update (matching column names)
        allowed_fields = [
            'first_name', 'last_name', 'full_name', 'job_title', 'company_name',
            'company_domain', 'linkedin_profile', 'location', 'phone', 'linkedin_message', 'company_id'
        ]
 
        update_fields = {k: v.strip() if isinstance(v, str) else v for k, v in data.items() if k in allowed_fields}
        if not update_fields:
            return jsonify({'success': False, 'message': 'No valid fields to update'}), 400
 
        from sqlalchemy import create_engine, text
        import os
        from datetime import datetime
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            return jsonify({'success': False, 'message': 'Database connection error'}), 500
 
        engine = create_engine(database_url)
        with engine.connect() as conn:
            with conn.begin():
                # Handle company_id if company info is being updated
                company_id = None
                company_name = update_fields.get('company_name') or data.get('company_name')
                company_domain = update_fields.get('company_domain') or data.get('company_domain')
                
                if company_name or company_domain:
                    # Check by name first
                    if company_name:
                        result = conn.execute(text("""
                            SELECT id FROM companies WHERE LOWER(company_name) = LOWER(:company_name) LIMIT 1
                        """), {"company_name": company_name})
                        row = result.fetchone()
                        if row:
                            company_id = row.id
                    
                    # If not found by name, check by domain
                    if not company_id and company_domain:
                        domain_pattern = f"%{company_domain.lower()}%"
                        result = conn.execute(text("""
                            SELECT id FROM companies WHERE LOWER(website_url) LIKE :domain_pattern LIMIT 1
                        """), {"domain_pattern": domain_pattern})
                        row = result.fetchone()
                        if row:
                            company_id = row.id
                    
                    # Create new company if not found
                    if not company_id:
                        website_url = ''
                        if company_domain:
                            website_url = company_domain if company_domain.startswith(('http://', 'https://')) else f"https://{company_domain}"
                        fallback_name = company_name or company_domain or 'Unknown'
                        result = conn.execute(text("""
                            INSERT INTO companies (company_name, website_url)
                            VALUES (:company_name, :website_url)
                            RETURNING id
                        """), {
                            "company_name": fallback_name,
                            "website_url": website_url
                        })
                        company_id = result.fetchone().id
                    
                    # Add company_id to update fields
                    update_fields['company_id'] = company_id

                # Build dynamic SET clause
                set_clause = ", ".join([f"{field} = :{field}" for field in update_fields.keys()])
                update_fields['updated_at'] = datetime.now()
                update_fields['email'] = email
                conn.execute(text(f"""
                    UPDATE contacts 
                    SET {set_clause}, updated_at = :updated_at
                    WHERE LOWER(email) = LOWER(:email)
                """), update_fields)
 
        current_app.logger.info(f"Updated contact: {email}")
        return jsonify({'success': True, 'message': f'Contact {email} updated successfully'})
    except Exception as e:
        current_app.logger.error(f"Error updating contact: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

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
                from email_composers.email_composer_alt_subject import AltSubjectEmailComposer
                composer = AltSubjectEmailComposer()
            else:
                from email_composers.email_composer_warm import WarmEmailComposer
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
        # Force reload of email configuration
        from app.utils.email_config import email_config
        email_config.load_accounts()
        
        # Get full account details for config page
        all_accounts = email_config.get_all_accounts()
        accounts = [account.to_dict() for account in all_accounts]
        
        # Debug logging
        current_app.logger.info(f"Retrieved {len(accounts)} accounts from configuration")
        for account in accounts:
            current_app.logger.info(f"Account: {account['name']}, IMAP: {account['imap_host']}")
        
        # Check which config storage is being used
        import os
        config_file_path = email_config.config_file_path
        env_file_info = {
            'env_exists': os.path.exists('.env'),
            'env2_exists': os.path.exists('.env2'),
            'json_config_exists': os.path.exists(config_file_path),
            'primary_env_file': config_file_path if os.path.exists(config_file_path) else '.env',
            'config_source': 'JSON config file' if os.path.exists(config_file_path) else 'EMAIL_ACCOUNTS variable'
        }
        
        return jsonify({
            'success': True,
            'accounts': accounts,
            'env_info': env_file_info
        })
    except Exception as e:
        current_app.logger.error(f"Error getting email accounts: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to load email accounts'
        }), 500

@bp.route('/email/accounts/<account_name>/test', methods=['POST'])
def test_email_account(account_name):
    """Test a specific email account connection (both SMTP and IMAP)."""
    try:
        account = email_config.get_account_by_name(account_name)
        if not account:
            return jsonify({
                'success': False,
                'message': f'Account "{account_name}" not found'
            }), 404
        
        test_results = {
            'smtp': {'success': False, 'message': ''},
            'imap': {'success': False, 'message': ''}
        }
        
        # Test SMTP connection (without sending email)
        try:
            import smtplib
            import ssl
            
            # Create SMTP connection
            if account.smtp_use_ssl and account.smtp_port == 465:
                # SSL connection
                smtp_server = smtplib.SMTP_SSL(account.smtp_host, account.smtp_port)
            else:
                # TLS connection
                smtp_server = smtplib.SMTP(account.smtp_host, account.smtp_port)
                if account.smtp_use_ssl:
                    smtp_server.starttls()
            
            # Test authentication
            smtp_server.login(account.email, account.password)
            smtp_server.quit()
            
            test_results['smtp']['success'] = True
            test_results['smtp']['message'] = 'SMTP connection and authentication successful'
            
        except Exception as e:
            test_results['smtp']['success'] = False
            test_results['smtp']['message'] = f'SMTP connection failed: {str(e)}'
        
        # Test IMAP connection
        try:
            from app.services.email_reader_service import EmailReaderService
            imap_reader = EmailReaderService()
            imap_reader.configure_imap(
                host=account.imap_host,
                email=account.email,
                password=account.password,
                port=account.imap_port
            )
            
            imap_success = imap_reader.connect()
            test_results['imap']['success'] = imap_success
            test_results['imap']['message'] = 'IMAP connection successful' if imap_success else 'IMAP connection failed'
            
            if imap_success:
                imap_reader.disconnect()
            
        except Exception as e:
            test_results['imap']['message'] = f'IMAP error: {str(e)}'
        
        # Overall success if both work
        overall_success = test_results['smtp']['success'] and test_results['imap']['success']
        
        # Create summary message
        messages = []
        if test_results['smtp']['success']:
            messages.append('✓ SMTP working')
        else:
            messages.append('✗ SMTP failed')
            
        if test_results['imap']['success']:
            messages.append('✓ IMAP working')
        else:
            messages.append('✗ IMAP failed')
        
        summary_message = f"Account \"{account_name}\": {' | '.join(messages)}"
        
        return jsonify({
            'success': overall_success,
            'message': summary_message,
            'account_email': account.email,
            'details': test_results
        })
        
    except Exception as e:
        current_app.logger.error(f"Error testing email account {account_name}: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to test email account',
            'details': {'error': str(e)}
        }), 500

@bp.route('/email/config/save', methods=['POST'])
def save_email_configuration():
    """Save email configuration to JSON file."""
    try:
        data = request.get_json()
        current_app.logger.info(f"Saving email configuration with {len(data.get('accounts', []))} accounts")
        
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
        
        # Use the new JSON-based saving mechanism
        from app.utils.email_config import email_config
        
        success = email_config.update_accounts(accounts)
        
        if success:
            current_app.logger.info(f"Successfully saved {len(accounts)} email accounts to JSON config")
            
            # Verify the save worked by reloading
            try:
                email_config.load_accounts()
                reloaded_accounts = email_config.get_all_accounts()
                current_app.logger.info(f"Verification: Reloaded {len(reloaded_accounts)} accounts from JSON file")
                
                for account in reloaded_accounts:
                    current_app.logger.info(f"Verified account: {account.name} ({account.email})")
                
                return jsonify({
                    'success': True,
                    'message': 'Configuration saved successfully to JSON file and applied immediately!',
                    'accounts_count': len(accounts),
                    'config_reloaded': True,
                    'storage_type': 'JSON file'
                })
                
            except Exception as e:
                current_app.logger.warning(f"Failed to verify saved config: {e}")
                return jsonify({
                    'success': True,
                    'message': 'Configuration saved to JSON file but verification failed',
                    'accounts_count': len(accounts),
                    'config_reloaded': False,
                    'storage_type': 'JSON file'
                })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to save configuration to JSON file'
            }), 500
        
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
        
        # Handle company selection/creation
        company_id = None
        company_name = ''
        company_domain = ''
        
        # Check if user selected existing company or wants to create new one
        selected_company_id = data.get('company_id')
        create_new_company = data.get('create_new_company', False)
        
        if selected_company_id and not create_new_company:
            # User selected existing company
            company_id = selected_company_id
            # Get company details for contact record
            existing_company = Company.get_by_id(company_id)
            if existing_company:
                company_name = existing_company.company_name
                company_domain = existing_company.website_url
        elif create_new_company:
            # User wants to create new company - validate mandatory fields
            new_company_name = data.get('new_company_name', '').strip()
            new_company_website = data.get('new_company_website', '').strip()
            
            if not new_company_name:
                return jsonify({
                    'success': False,
                    'message': 'Company name is required when creating a new company'
                }), 400
            
            if not new_company_website:
                return jsonify({
                    'success': False,
                    'message': 'Company website is required when creating a new company'
                }), 400
            
            company_name = new_company_name
            company_domain = new_company_website
        else:
            # Backward compatibility - check for old company_name field
            company_name = data.get('company_name', '').strip()
            company_domain = data.get('company_domain', '').strip()
        
        # Create contact data dictionary
        contact_data = {
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'full_name': full_name,
            'job_title': data.get('job_title', '').strip(),
            'company_name': company_name,
            'company_domain': company_domain,
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
            with conn.begin():
                # -------------------------------------------------------------
                # First, ensure the associated company exists and get its ID
                # -------------------------------------------------------------
                final_company_id = company_id  # Use pre-selected company_id if available
                contact_company_name = contact_data.get('company_name')
                contact_company_domain = contact_data.get('company_domain')

                # Only search/create company if we don't already have a company_id
                if not final_company_id and (contact_company_name or contact_company_domain):
                    # Check by company name (case-insensitive)
                    if contact_company_name:
                        result = conn.execute(text("""
                            SELECT id FROM companies
                            WHERE LOWER(company_name) = LOWER(:company_name)
                            LIMIT 1
                        """), {"company_name": contact_company_name})
                        row = result.fetchone()
                        if row:
                            final_company_id = row.id

                    # If not found by name, check by website_url/domain
                    if not final_company_id and contact_company_domain:
                        domain_pattern = f"%{contact_company_domain.lower()}%"
                        result = conn.execute(text("""
                            SELECT id FROM companies
                            WHERE LOWER(website_url) LIKE :domain_pattern
                            LIMIT 1
                        """), {"domain_pattern": domain_pattern})
                        row = result.fetchone()
                        if row:
                            final_company_id = row.id

                    # Insert new company if it doesn't exist
                    if not final_company_id:
                        website_url = ''
                        if contact_company_domain:
                            website_url = contact_company_domain if contact_company_domain.startswith(('http://', 'https://')) else f"https://{contact_company_domain}"
                        # Use company_name if available, otherwise fallback to domain
                        fallback_name = contact_company_name or contact_company_domain or 'Unknown'
                        result = conn.execute(text("""
                            INSERT INTO companies (company_name, website_url)
                            VALUES (:company_name, :website_url)
                            RETURNING id
                        """), {
                            "company_name": fallback_name,
                            "website_url": website_url
                        })
                        final_company_id = result.fetchone().id

                # Insert new contact with company_id foreign key
                conn.execute(text("""
                    INSERT INTO contacts (
                        email, first_name, last_name, full_name, job_title, 
                        company_name, company_domain, linkedin_profile, location, 
                        phone, linkedin_message, company_id, source_files, all_data
                    ) VALUES (
                        :email, :first_name, :last_name, :full_name, :job_title,
                        :company_name, :company_domain, :linkedin_profile, :location,
                        :phone, :linkedin_message, :company_id, :source_files, :all_data
                    )
                """), {
                    **contact_data,
                    'company_id': final_company_id,
                    'source_files': json.dumps(["manual_entry"]),
                    'all_data': json.dumps({
                        'source': 'manual_entry',
                        'created_by': 'user',
                        'entry_date': datetime.now().isoformat()
                    })
                })
                # -------------------------------------------------------------
        
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
            return jsonify({
                'success': True,
                'contacts': [], 
                'count': 0,
                'query': ''
            })
        
        contacts = Contact.search(query)
        
        return jsonify({
            'success': True,
            'contacts': [contact.to_dict() for contact in contacts],
            'count': len(contacts),
            'query': query
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in search_contacts: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to search contacts',
            'contacts': [],
            'count': 0
        }), 500

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

@bp.route('/contacts/count-filtered', methods=['POST'])
def count_filtered_contacts():
    """Count contacts based on filter criteria for campaign selection."""
    try:
        data = request.get_json()
        filter_type = data.get('type', 'quick')
        
        # Get all contacts
        all_contacts = Contact.load_all()
        
        if filter_type == 'quick':
            filter_value = data.get('filter_type', 'all')
            company_filter = data.get('company', '')
            
            if filter_value == 'all':
                filtered_contacts = all_contacts
            elif filter_value == 'uncontacted':
                # Get contacted emails from history
                email_history = EmailHistory.load_all()
                contacted_emails = set()
                for email in email_history:
                    if email.to:
                        contacted_emails.add(email.to.lower().strip())
                
                filtered_contacts = [
                    contact for contact in all_contacts
                    if contact.email and contact.email.lower().strip() not in contacted_emails
                ]
            elif filter_value == 'has_phone':
                filtered_contacts = [
                    contact for contact in all_contacts
                    if contact.raw_data and contact.raw_data.get('phone')
                ]
            elif filter_value == 'has_linkedin':
                filtered_contacts = [
                    contact for contact in all_contacts
                    if contact.raw_data and contact.raw_data.get('linkedin_profile')
                ]
            elif filter_value == 'recent':
                # Get contacts from last 30 days (simplified)
                filtered_contacts = all_contacts[:50]  # Placeholder
            else:
                filtered_contacts = all_contacts
            
            # Apply company filter if specified
            if company_filter:
                filtered_contacts = [
                    contact for contact in filtered_contacts
                    if contact.company and company_filter.lower() in contact.company.lower()
                ]
            
        elif filter_type == 'advanced':
            filtered_contacts = all_contacts
            
            # Apply advanced filters
            company = data.get('company', '').lower()
            job_title = data.get('job_title', '').lower()
            location = data.get('location', '').lower()
            exclude_contacted = data.get('exclude_contacted', False)
            require_phone = data.get('require_phone', False)
            require_linkedin = data.get('require_linkedin', False)
            
            if company:
                filtered_contacts = [
                    contact for contact in filtered_contacts
                    if contact.company and company in contact.company.lower()
                ]
            
            if job_title:
                filtered_contacts = [
                    contact for contact in filtered_contacts
                    if contact.job_title and job_title in contact.job_title.lower()
                ]
            
            if location:
                filtered_contacts = [
                    contact for contact in filtered_contacts
                    if contact.location and location in contact.location.lower()
                ]
            
            if require_phone:
                filtered_contacts = [
                    contact for contact in filtered_contacts
                    if contact.raw_data and contact.raw_data.get('phone')
                ]
            
            if require_linkedin:
                filtered_contacts = [
                    contact for contact in filtered_contacts
                    if contact.raw_data and contact.raw_data.get('linkedin_profile')
                ]
            
            if exclude_contacted:
                email_history = EmailHistory.load_all()
                contacted_emails = set()
                for email in email_history:
                    if email.to:
                        contacted_emails.add(email.to.lower().strip())
                
                filtered_contacts = [
                    contact for contact in filtered_contacts
                    if contact.email and contact.email.lower().strip() not in contacted_emails
                ]
        
        else:  # manual selection
            # For manual selection, count is handled on frontend
            return jsonify({'count': 0})
        
        return jsonify({
            'count': len(filtered_contacts),
            'total_contacts': len(all_contacts)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error counting filtered contacts: {str(e)}")
        return jsonify({'error': 'Failed to count contacts', 'count': 0}), 500

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

@bp.route('/email/config/debug', methods=['GET'])
def debug_email_configuration():
    """Debug endpoint to show current email configuration state."""
    try:
        import os
        import json
        from app.utils.email_config import email_config
        
        config_file_path = email_config.config_file_path
        
        debug_info = {
            'storage_mechanism': 'JSON file' if os.path.exists(config_file_path) else 'Environment variable',
            'json_config_file': config_file_path,
            'json_config_exists': os.path.exists(config_file_path),
            'env_file_exists': os.path.exists('.env'),
            'env2_file_exists': os.path.exists('.env2'),
            'email_accounts_env_var': os.getenv('EMAIL_ACCOUNTS', 'NOT_SET'),
            'loaded_accounts': [],
            'config_manager_status': 'unknown'
        }
        
        # Try to reload and get accounts
        try:
            email_config.load_accounts()
            all_accounts = email_config.get_all_accounts()
            debug_info['loaded_accounts'] = [account.to_dict() for account in all_accounts]
            debug_info['config_manager_status'] = 'working'
            debug_info['accounts_count'] = len(all_accounts)
        except Exception as e:
            debug_info['config_manager_status'] = f'error: {str(e)}'
            debug_info['accounts_count'] = 0
        
        # Read JSON config file if it exists
        if os.path.exists(config_file_path):
            try:
                with open(config_file_path, 'r') as f:
                    json_content = json.load(f)
                    debug_info['json_config_content'] = json_content
                    debug_info['json_accounts_count'] = len(json_content) if isinstance(json_content, list) else 0
            except Exception as e:
                debug_info['json_config_error'] = str(e)
        
        # Read .env file content for EMAIL_ACCOUNTS line (for fallback info)
        try:
            with open('.env', 'r') as f:
                lines = f.readlines()
                for i, line in enumerate(lines):
                    if line.startswith('EMAIL_ACCOUNTS='):
                        debug_info['env_file_line'] = line.strip()
                        debug_info['env_file_line_number'] = i + 1
                        break
                else:
                    debug_info['env_file_line'] = 'NOT_FOUND'
        except Exception as e:
            debug_info['env_file_error'] = str(e)
        
        return jsonify({
            'success': True,
            'debug_info': debug_info
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in debug endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Debug failed: {str(e)}'
        }), 500

@bp.route('/companies/extract', methods=['POST'])
def extract_companies():
    """Extract unique companies from contacts table and insert into companies table."""
    try:
        # Run the extraction script
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'scripts', 'extract_companies.py')
        current_app.logger.info(f"Running company extraction script: {script_path}")
        
        result = subprocess.run([
            'python', script_path
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        
        if result.returncode == 0:
            current_app.logger.info(f"Company extraction completed successfully: {result.stdout}")
            return jsonify({
                'success': True,
                'message': 'Companies extracted successfully',
                'output': result.stdout.strip()
            })
        else:
            current_app.logger.error(f"Company extraction failed: {result.stderr}")
            return jsonify({
                'success': False,
                'message': 'Company extraction failed',
                'error': result.stderr.strip()
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Error in company extraction: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Company extraction failed: {str(e)}'
        }), 500

@bp.route('/companies/research', methods=['POST'])
def research_companies():
    """Trigger company research for companies without research data."""
    try:
        data = request.get_json()
        max_companies = data.get('max_companies', 10) if data else 10
        force_refresh = data.get('force_refresh', False) if data else False
        
        # Import the new modular research system
        from deepresearch.company_researcher import CompanyResearcher
        
        current_app.logger.info(f"Starting company research with max_companies={max_companies}, force_refresh={force_refresh}")
        
        # Get the current app instance to pass to the background thread
        app_instance = current_app._get_current_object()
        
        def run_research():
            # Set up Flask application context for background thread
            with app_instance.app_context():
                try:
                    researcher = CompanyResearcher()
                    
                    if force_refresh:
                        companies = researcher.database_service.get_all_companies()
                        app_instance.logger.info(f"Force refresh mode: processing all {len(companies)} companies")
                        companies_to_research = companies[:max_companies]
                    else:
                        companies_to_research = researcher.database_service.get_companies_without_research()
                        app_instance.logger.info(f"Found {len(companies_to_research)} companies without research")
                        companies_to_research = companies_to_research[:max_companies]
                    
                    app_instance.logger.info(f"Processing {len(companies_to_research)} companies")
                    
                    for company in companies_to_research:
                        try:
                            app_instance.logger.info(f"Researching company: {company.company_name}")
                            researcher.research_company(company, force_refresh=force_refresh)
                        except Exception as e:
                            app_instance.logger.error(f"Error researching company {company.company_name}: {str(e)}")
                    
                    app_instance.logger.info("Company research completed successfully")
                    
                except Exception as e:
                    app_instance.logger.error(f"Error in background research process: {str(e)}")
        
        # Start the research in a background thread
        research_thread = threading.Thread(target=run_research)
        research_thread.daemon = True
        research_thread.start()
        
        return jsonify({
            'success': True,
            'message': f'Company research started for up to {max_companies} companies. This process will run in the background.',
            'status': 'started',
            'force_refresh': force_refresh
        })
        
    except Exception as e:
        current_app.logger.error(f"Error starting company research: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to start company research: {str(e)}'
        }), 500

@bp.route('/companies', methods=['GET'])
def get_companies():
    """Get all companies with pagination."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        result = Company.get_paginated(page=page, per_page=per_page)
        
        # Convert companies to dict format
        companies_data = []
        for company in result['companies']:
            company_dict = company.to_dict()
            # Add a flag to indicate if research is needed
            company_dict['needs_research'] = not company.company_research or 'Research pending' in company.company_research
            companies_data.append(company_dict)
        
        return jsonify({
            'success': True,
            'companies': companies_data,
            'pagination': {
                'current_page': result['current_page'],
                'total_pages': result['total_pages'],
                'per_page': result['per_page'],
                'total_companies': result['total_companies']
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting companies: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to load companies'
        }), 500

@bp.route('/companies/<int:company_id>', methods=['GET'])
def get_company_details(company_id):
    """Get detailed information about a specific company."""
    try:
        company = Company.get_by_id(company_id)
        if not company:
            return jsonify({
                'success': False,
                'message': 'Company not found'
            }), 404
        
        company_dict = company.to_dict()
        company_dict['needs_research'] = not company.company_research or 'Research pending' in company.company_research
        
        return jsonify({
            'success': True,
            'company': company_dict
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting company details: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to load company details'
        }), 500

@bp.route('/companies/search', methods=['GET'])
def search_companies():
    """Search companies by name, website, or research content."""
    try:
        query = request.args.get('q', '')
        
        if not query:
            return jsonify({
                'success': False,
                'message': 'Search query is required'
            }), 400
        
        companies = Company.search(query)
        companies_data = []
        for company in companies:
            company_dict = company.to_dict()
            company_dict['needs_research'] = not company.company_research or 'Research pending' in company.company_research
            companies_data.append(company_dict)
        
        return jsonify({
            'success': True,
            'companies': companies_data,
            'count': len(companies_data)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error searching companies: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to search companies'
        }), 500

@bp.route('/companies/<int:company_id>/research', methods=['POST'])
def research_single_company(company_id):
    """Research a specific company by ID using step-by-step deep research."""
    try:
        data = request.get_json() or {}
        force_refresh = data.get('force_refresh', False)
        
        # Get the company from database
        company = Company.get_by_id(company_id)
        if not company:
            return jsonify({
                'success': False,
                'message': 'Company not found'
            }), 404
        
        # Import the new step-by-step research system
        from deepresearch.step_by_step_researcher import StepByStepResearcher
        
        current_app.logger.info(f"Starting step-by-step research for company ID {company_id}: {company.company_name}, force_refresh={force_refresh}")
        
        # Get the current app instance to pass to the background thread
        app_instance = current_app._get_current_object()
        
        def run_step_by_step_research():
            # Set up Flask application context for background thread
            with app_instance.app_context():
                try:
                    researcher = StepByStepResearcher()
                    result = researcher.start_deep_research(company_id, force_refresh=force_refresh)
                    
                    if result['success']:
                        app_instance.logger.info(f"Step-by-step research completed successfully for {company.company_name}")
                    else:
                        app_instance.logger.error(f"Step-by-step research failed for {company.company_name}: {result.get('error', 'Unknown error')}")
                    
                except Exception as e:
                    app_instance.logger.error(f"Error in step-by-step research for company {company_id}: {str(e)}")
        
        # Start the research in a background thread
        research_thread = threading.Thread(target=run_step_by_step_research)
        research_thread.daemon = True
        research_thread.start()
        
        return jsonify({
            'success': True,
            'message': f'Step-by-step deep research started for {company.company_name}. This process will run in the background.',
            'company_name': company.company_name,
            'status': 'started',
            'force_refresh': force_refresh,
            'research_type': 'step_by_step'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error starting step-by-step research for company {company_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to start research: {str(e)}'
        }), 500

@bp.route('/companies/<int:company_id>/research/progress', methods=['GET'])
def get_research_progress(company_id):
    """Get research progress for a specific company."""
    try:
        from deepresearch.step_by_step_researcher import StepByStepResearcher
        
        researcher = StepByStepResearcher()
        progress = researcher.get_research_progress(company_id)
        
        return jsonify(progress)
        
    except Exception as e:
        current_app.logger.error(f"Error getting research progress for company {company_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to get research progress: {str(e)}'
        }), 500

@bp.route('/companies/<int:company_id>/research/resume', methods=['POST'])
def resume_research(company_id):
    """Resume incomplete research for a specific company."""
    try:
        from deepresearch.step_by_step_researcher import StepByStepResearcher
        
        # Get the company from database
        company = Company.get_by_id(company_id)
        if not company:
            return jsonify({
                'success': False,
                'message': 'Company not found'
            }), 404
        
        current_app.logger.info(f"Resuming research for company ID {company_id}: {company.company_name}")
        
        # Get the current app instance to pass to the background thread
        app_instance = current_app._get_current_object()
        
        def run_resume_research():
            # Set up Flask application context for background thread
            with app_instance.app_context():
                try:
                    researcher = StepByStepResearcher()
                    result = researcher.resume_research(company_id)
                    
                    if result['success']:
                        app_instance.logger.info(f"Resume research completed for {company.company_name}")
                    else:
                        app_instance.logger.error(f"Resume research failed for {company.company_name}: {result.get('error', 'Unknown error')}")
                    
                except Exception as e:
                    app_instance.logger.error(f"Error resuming research for company {company_id}: {str(e)}")
        
        # Start the resume in a background thread
        resume_thread = threading.Thread(target=run_resume_research)
        resume_thread.daemon = True
        resume_thread.start()
        
        return jsonify({
            'success': True,
            'message': f'Resume research started for {company.company_name}. This process will run in the background.',
            'company_name': company.company_name,
            'status': 'resuming'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error resuming research for company {company_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to resume research: {str(e)}'
        }), 500

@bp.route('/companies/<int:company_id>/research/step/<int:step>', methods=['GET'])
def get_research_step(company_id, step):
    """Get a specific research step content for a company."""
    try:
        company = Company.get_by_id(company_id)
        if not company:
            return jsonify({
                'success': False,
                'message': 'Company not found'
            }), 404
        
        if step not in [1, 2, 3]:
            return jsonify({
                'success': False,
                'message': 'Invalid step number. Must be 1, 2, or 3.'
            }), 400
        
        step_titles = {
            1: 'Basic Company Research',
            2: 'Strategic Analysis',
            3: 'Final Report'
        }
        
        step_content = ''
        if step == 1:
            step_content = company.research_step_1_basic or ''
        elif step == 2:
            step_content = company.research_step_2_strategic or ''
        elif step == 3:
            step_content = company.research_step_3_report or ''
        
        return jsonify({
            'success': True,
            'company_name': company.company_name,
            'step': step,
            'step_title': step_titles[step],
            'content': step_content,
            'has_content': bool(step_content),
            'content_length': len(step_content)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting research step {step} for company {company_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to get research step: {str(e)}'
        }), 500

@bp.route('/campaigns', methods=['POST'])
def create_campaign():
    """Create a new GTM campaign with database storage and background processing."""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({
                'success': False,
                'message': 'Campaign name is required'
            }), 400
        
        if not data.get('type'):
            return jsonify({
                'success': False,
                'message': 'Campaign type is required'
            }), 400
        
        if not data.get('email_template'):
            return jsonify({
                'success': False,
                'message': 'Email template is required'
            }), 400
        
        # Import required models and scheduler
        from app.models.campaign import Campaign
        from app.services.campaign_scheduler import campaign_scheduler
        
        # Get campaign data
        campaign_name = data.get('name')
        campaign_type = data.get('type')
        description = data.get('description', '')
        email_template = data.get('email_template')
        priority = data.get('priority', 'medium')
        schedule_date = data.get('schedule_date')
        followup_days = data.get('followup_days', 3)
        selection_criteria = data.get('selection_criteria', {})
        selected_contacts = data.get('selected_contacts', [])
        
        # Log campaign creation
        current_app.logger.info(f"Creating database campaign: {campaign_name}")
        current_app.logger.info(f"Campaign type: {campaign_type}")
        current_app.logger.info(f"Selection criteria: {selection_criteria}")
        current_app.logger.info(f"Selected contacts count: {len(selected_contacts)}")
        
        # Get target contacts based on selection criteria (same logic as before)
        target_contacts = []
        if selection_criteria.get('type') == 'manual':
            target_contacts = selected_contacts
        else:
            # For quick and advanced filters, we need to query contacts
            try:
                if selection_criteria.get('type') == 'quick':
                    filter_type = selection_criteria.get('filter_type', 'all')
                    company_filter = selection_criteria.get('company', '')
                    
                    contacts = Contact.load_all()
                    
                    if filter_type == 'uncontacted':
                        # Filter uncontacted contacts
                        uncontacted_emails = EmailHistory.get_uncontacted_emails()
                        target_contacts = [c.to_dict() for c in contacts if c.email in uncontacted_emails]
                    elif filter_type == 'has_phone':
                        target_contacts = [c.to_dict() for c in contacts if c.phone_number]
                    elif filter_type == 'has_linkedin':
                        target_contacts = [c.to_dict() for c in contacts if c.linkedin_url]
                    elif filter_type == 'recent':
                        # Get recently added contacts (last 30 days)
                        from datetime import timedelta
                        thirty_days_ago = datetime.now() - timedelta(days=30)
                        target_contacts = [c.to_dict() for c in contacts if c.created_at and c.created_at >= thirty_days_ago]
                    else:  # 'all'
                        target_contacts = [c.to_dict() for c in contacts]
                    
                    # Apply company filter if specified
                    if company_filter:
                        target_contacts = [c for c in target_contacts if c.get('company', '').lower().find(company_filter.lower()) != -1]
                        
                elif selection_criteria.get('type') == 'advanced':
                    contacts = Contact.load_all()
                    target_contacts = [c.to_dict() for c in contacts]
                    
                    # Apply advanced filters
                    company_contains = selection_criteria.get('company', '').lower()
                    title_contains = selection_criteria.get('job_title', '').lower()
                    location_contains = selection_criteria.get('location', '').lower()
                    
                    if company_contains:
                        target_contacts = [c for c in target_contacts if company_contains in c.get('company', '').lower()]
                    
                    if title_contains:
                        target_contacts = [c for c in target_contacts if title_contains in c.get('job_title', '').lower()]
                    
                    if location_contains:
                        target_contacts = [c for c in target_contacts if location_contains in c.get('location', '').lower()]
                    
                    # Apply boolean filters
                    if selection_criteria.get('exclude_contacted'):
                        uncontacted_emails = EmailHistory.get_uncontacted_emails()
                        target_contacts = [c for c in target_contacts if c.get('email') in uncontacted_emails]
                    
                    if selection_criteria.get('require_phone'):
                        target_contacts = [c for c in target_contacts if c.get('phone_number')]
                    
                    if selection_criteria.get('require_linkedin'):
                        target_contacts = [c for c in target_contacts if c.get('linkedin_url')]
                
            except Exception as filter_error:
                current_app.logger.error(f"Error filtering contacts: {str(filter_error)}")
                return jsonify({
                    'success': False,
                    'message': f'Error filtering contacts: {str(filter_error)}'
                }), 500
        
        if not target_contacts:
            return jsonify({
                'success': False,
                'message': 'No contacts match the selection criteria'
            }), 400
        
        current_app.logger.info(f"Final target contacts count: {len(target_contacts)}")
        
        # Extract email sending settings
        email_frequency = data.get('email_frequency', {'value': 30, 'unit': 'minutes'})
        timezone = data.get('timezone', 'America/Los_Angeles')
        daily_email_limit = data.get('daily_email_limit', 50)
        respect_business_hours = data.get('respect_business_hours', True)
        business_hours = data.get('business_hours', {
            'start_time': '09:00',
            'end_time': '17:00',
            'days': {
                'monday': True, 'tuesday': True, 'wednesday': True, 
                'thursday': True, 'friday': True, 'saturday': False, 'sunday': False
            }
        })
        
        # Extract additional sending preferences
        enable_spam_check = data.get('enable_spam_check', True)
        enable_unsubscribe_link = data.get('enable_unsubscribe_link', True)
        
        # Prepare campaign data for database
        campaign_data = {
            'name': campaign_name,
            'description': description,
            'status': 'draft' if schedule_date else 'ready'
        }
        
        # Prepare campaign settings
        campaign_settings = {
            'email_template': email_template,
            'email_frequency': email_frequency,
            'timezone': timezone,
            'daily_email_limit': daily_email_limit,
            'respect_business_hours': respect_business_hours,
            'business_hours': business_hours if respect_business_hours else None,
            'enable_spam_check': enable_spam_check,
            'enable_unsubscribe_link': enable_unsubscribe_link,
            'enable_tracking': data.get('enable_tracking', True),
            'enable_personalization': data.get('enable_personalization', True),
            'priority': priority,
            'followup_days': followup_days
        }
        
        # Extract contact emails for database storage
        contact_emails = [contact.get('email') for contact in target_contacts if contact.get('email')]
        
        # Create campaign in database
        campaign_id = Campaign.create_campaign_with_settings(
            campaign_data, 
            campaign_settings, 
            contact_emails
        )
        
        if not campaign_id:
            return jsonify({
                'success': False,
                'message': 'Failed to create campaign in database'
            }), 500
        
        current_app.logger.info(f"Campaign created in database with ID: {campaign_id}")
        
        # Schedule campaign execution
        try:
            success = campaign_scheduler.schedule_campaign(campaign_id, schedule_date)
            
            if success:
                status_message = f'Campaign "{campaign_name}" created and scheduled successfully!'
                if not schedule_date:
                    status_message += ' Background processing started.'
                else:
                    status_message += f' Scheduled for {schedule_date}.'
                
                return jsonify({
                    'success': True,
                    'message': status_message,
                    'campaign_id': campaign_id,
                    'target_contacts_count': len(target_contacts)
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Campaign created but failed to schedule execution'
                }), 500
                
        except Exception as schedule_error:
            current_app.logger.error(f"Error scheduling campaign: {str(schedule_error)}")
            return jsonify({
                'success': False,
                'message': f'Campaign created but scheduling failed: {str(schedule_error)}'
            }), 500
        
    except Exception as e:
        current_app.logger.error(f"Error creating campaign: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to create campaign: {str(e)}'
        }), 500

@bp.route('/campaigns/draft', methods=['POST'])
def save_campaign_draft():
    """Save a campaign as draft."""
    try:
        data = request.get_json()
        
        # Validate required fields for draft
        if not data.get('name'):
            return jsonify({
                'success': False,
                'message': 'Campaign name is required'
            }), 400
        
        # Create draft campaign data
        draft_data = {
            'id': f"draft_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'name': data.get('name'),
            'type': data.get('type'),
            'description': data.get('description', ''),
            'email_template': data.get('email_template'),
            'priority': data.get('priority', 'medium'),
            'schedule_date': data.get('schedule_date'),
            'followup_days': data.get('followup_days', 3),
            'selection_criteria': data.get('selection_criteria', {}),
            'selected_contacts': data.get('selected_contacts', []),
            'created_at': datetime.now().isoformat(),
            'status': 'draft'
        }
        
        current_app.logger.info(f"Campaign draft saved: {draft_data['name']}")
        
        return jsonify({
            'success': True,
            'message': f'Campaign "{draft_data["name"]}" saved as draft!',
            'campaign': draft_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error saving campaign draft: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to save campaign draft: {str(e)}'
        }), 500

@bp.route('/campaigns', methods=['GET'])
def get_campaigns():
    """Get all campaigns from database."""
    try:
        from app.models.campaign import Campaign
        
        # Load campaigns from database
        campaigns = Campaign.load_all()
        campaigns_list = []
        
        for campaign in campaigns:
            campaign_dict = campaign.to_dict()
            
            # Get campaign settings to include email_template, priority, etc.
            try:
                settings = Campaign.get_campaign_settings(campaign_dict['id'])
                campaign_dict.update({
                    'email_template': settings.get('email_template', 'deep_research'),
                    'priority': settings.get('priority', 'medium'),
                    'followup_days': settings.get('followup_days', 3),
                    'type': 'cold_outreach'  # Default type since we don't store it separately yet
                })
            except Exception as settings_error:
                current_app.logger.error(f"Error getting settings for campaign {campaign_dict['id']}: {settings_error}")
                # Add default values
                campaign_dict.update({
                    'email_template': 'deep_research',
                    'priority': 'medium', 
                    'followup_days': 3,
                    'type': 'cold_outreach'
                })
            
            # Get and add campaign stats
            try:
                stats = Campaign.get_campaign_stats(campaign_dict['id'])
                campaign_dict.update(stats)
                
                # Add frontend-expected field names (map API names to frontend names)
                campaign_dict['target_contacts_count'] = stats.get('total_contacts', 0)
                campaign_dict['emails_sent'] = stats.get('sent_emails', 0)
                campaign_dict['responses_received'] = 0  # Placeholder - we don't track responses yet
                
            except Exception as stats_error:
                current_app.logger.error(f"Error getting stats for campaign {campaign_dict['id']}: {stats_error}")
                # Add default stats with both API and frontend field names
                default_stats = {
                    'total_emails': 0,
                    'sent_emails': 0,
                    'failed_emails': 0,
                    'total_contacts': 0,
                    'active_contacts': 0,
                    'completed_contacts': 0,
                    'success_rate': 0,
                    'target_contacts_count': 0,  # Frontend field name
                    'emails_sent': 0,            # Frontend field name  
                    'responses_received': 0      # Frontend field name
                }
                campaign_dict.update(default_stats)
            
            campaigns_list.append(campaign_dict)
        
        return jsonify({
            'success': True,
            'campaigns': campaigns_list,
            'total': len(campaigns_list)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting campaigns: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to load campaigns: {str(e)}'
        }), 500

@bp.route('/campaigns/<int:campaign_id>/pause', methods=['POST'])
def pause_campaign(campaign_id):
    """Pause a running campaign."""
    try:
        from app.services.campaign_scheduler import campaign_scheduler
        
        success = campaign_scheduler.pause_campaign(campaign_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Campaign {campaign_id} paused successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Failed to pause campaign {campaign_id}'
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Error pausing campaign {campaign_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error pausing campaign: {str(e)}'
        }), 500

@bp.route('/campaigns/<int:campaign_id>/resume', methods=['POST'])
def resume_campaign(campaign_id):
    """Resume a paused campaign."""
    try:
        from app.services.campaign_scheduler import campaign_scheduler
        
        success = campaign_scheduler.resume_campaign(campaign_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Campaign {campaign_id} resumed successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Failed to resume campaign {campaign_id}'
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Error resuming campaign {campaign_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error resuming campaign: {str(e)}'
        }), 500

@bp.route('/campaigns/<int:campaign_id>/status', methods=['GET'])
def get_campaign_status(campaign_id):
    """Get detailed status of a campaign."""
    try:
        from app.services.campaign_scheduler import campaign_scheduler
        
        status = campaign_scheduler.get_campaign_status(campaign_id)
        
        if 'error' in status:
            return jsonify({
                'success': False,
                'message': status['error']
            }), 404
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting campaign status {campaign_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting campaign status: {str(e)}'
        }), 500

@bp.route('/companies/<int:company_id>/report', methods=['GET'])
def get_company_report(company_id):
    """Get the markdown report for a specific company."""
    try:
        # Get the company from database
        company = Company.get_by_id(company_id)
        if not company:
            return jsonify({
                'success': False,
                'message': 'Company not found'
            }), 404
        
        # Check if company has a markdown report
        if not company.markdown_report:
            return jsonify({
                'success': False,
                'message': 'No markdown report available for this company'
            }), 404
        
        return jsonify({
            'success': True,
            'company_name': company.company_name,
            'markdown_report': company.markdown_report,
            'has_report': True
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting company report for ID {company_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to load company report: {str(e)}'
        }), 500

@bp.route('/public/reports/<int:company_id>', methods=['GET'])
def get_public_company_report(company_id):
    """Get a public web-accessible HTML version of the company report."""
    try:
        from flask import render_template
        import markdown
        from datetime import datetime
        
        # Get the company from database
        company = Company.get_by_id(company_id)
        if not company:
            return jsonify({
                'success': False,
                'message': 'Company not found'
            }), 404
        
        # Check if company has a markdown report
        if not company.markdown_report:
            return jsonify({
                'success': False,
                'message': 'No strategic report available for this company'
            }), 404
        
        # Convert markdown to HTML
        html_content = markdown.markdown(
            company.markdown_report,
            extensions=['tables', 'fenced_code', 'toc']
        )
        
        # Generate a shareable URL
        report_url = request.url
        
        # Render as HTML page
        return render_template('public_report.html',
            company_name=company.company_name,
            html_content=html_content,
            report_url=report_url,
            generated_date=company.updated_at or datetime.now(),
            company_website=company.website_url
        )
        
    except Exception as e:
        current_app.logger.error(f"Error generating public report for company {company_id}: {str(e)}")
        return f"<h1>Error</h1><p>Failed to load strategic report: {str(e)}</p>", 500

@bp.route('/public/reports/<int:company_id>/pdf', methods=['GET'])
def get_company_report_pdf(company_id):
    """Generate and return PDF version of the company report."""
    try:
        from flask import make_response
        import pdfkit
        import markdown
        
        # Get the company from database
        company = Company.get_by_id(company_id)
        if not company:
            return jsonify({
                'success': False,
                'message': 'Company not found'
            }), 404
        
        if not company.markdown_report:
            return jsonify({
                'success': False,
                'message': 'No strategic report available for this company'
            }), 404
        
        # Convert markdown to HTML
        html_content = markdown.markdown(
            company.markdown_report,
            extensions=['tables', 'fenced_code', 'toc']
        )
        
        # Create professional PDF styling
        pdf_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Strategic Analysis: {company.company_name}</title>
            <style>
                body {{ font-family: 'Helvetica', Arial, sans-serif; line-height: 1.6; margin: 40px; }}
                h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
                h2 {{ color: #34495e; margin-top: 30px; }}
                h3 {{ color: #5d6d7e; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                th {{ background-color: #f8f9fa; font-weight: bold; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .footer {{ text-align: center; margin-top: 30px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Strategic Analysis Report</h1>
                <p><strong>{company.company_name}</strong></p>
                <p>Generated by AI-Powered Strategic Analysis</p>
            </div>
            {html_content}
            <div class="footer">
                <p>This report was generated using advanced AI research and strategic analysis tools.</p>
                <p>All recommendations should be validated with current market data and company-specific context.</p>
            </div>
        </body>
        </html>
        """
        
        # Generate PDF
        options = {
            'page-size': 'A4',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
            'no-outline': None,
            'enable-local-file-access': None
        }
        
        pdf = pdfkit.from_string(pdf_html, False, options=options)
        
        # Create response
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename="strategic_analysis_{company.company_name.replace(" ", "_").lower()}.pdf"'
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error generating PDF report for company {company_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to generate PDF report: {str(e)}'
        }), 500

@bp.route('/public/reports/<int:company_id>/embed', methods=['GET'])
def get_embeddable_report(company_id):
    """Get an embeddable iframe version of the company report."""
    try:
        from flask import render_template
        import markdown
        
        # Get the company from database
        company = Company.get_by_id(company_id)
        if not company:
            return "<p>Company not found</p>", 404
        
        if not company.markdown_report:
            return "<p>No strategic report available</p>", 404
        
        # Convert markdown to HTML
        html_content = markdown.markdown(
            company.markdown_report,
            extensions=['tables', 'fenced_code', 'toc']
        )
        
        # Render as embeddable content (no navigation)
        return render_template('embeddable_report.html',
            company_name=company.company_name,
            html_content=html_content
        )
        
    except Exception as e:
        current_app.logger.error(f"Error generating embeddable report for company {company_id}: {str(e)}")
        return f"<p>Error: Failed to load report</p>", 500

@bp.route('/public/reports', methods=['GET'])
def list_public_reports():
    """Get a list of all companies with available public reports."""
    try:
        # Get all companies with reports
        companies_with_reports = Company.get_companies_with_reports()
        
        public_reports = []
        for company in companies_with_reports:
            public_reports.append({
                'id': company['id'],
                'company_name': company['company_name'],
                'website_url': company.get('website_url'),
                'updated_at': company['updated_at'].isoformat() if company['updated_at'] else None,
                'public_url': f"/api/public/reports/{company['id']}",
                'pdf_url': f"/api/public/reports/{company['id']}/pdf",
                'embed_url': f"/api/public/reports/{company['id']}/embed"
            })
        
        return jsonify({
            'success': True,
            'reports': public_reports,
            'total_count': len(public_reports)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error listing public reports: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to list public reports: {str(e)}'
        }), 500

@bp.route('/companies/add', methods=['POST'])
def add_company():
    """Add a new company manually."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
 
        company_name = data.get('company_name', '').strip()
        if not company_name:
            return jsonify({'success': False, 'message': 'Company name is required'}), 400
 
        company_data = {
            'company_name': company_name,
            'website_url': data.get('website_url', '').strip(),
            'company_research': data.get('company_research', '').strip()
        }
 
        if Company.save(company_data):
            return jsonify({'success': True, 'message': f'Company {company_name} added successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to save company'}), 500
    except Exception as e:
        current_app.logger.error(f"Error adding company: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500
 
@bp.route('/companies/<int:company_id>', methods=['PUT'])
def update_company(company_id):
    """Update an existing company's details."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
 
        # Allow partial updates
        company = Company.get_by_id(company_id)
        if not company:
            return jsonify({'success': False, 'message': 'Company not found'}), 404
 
        company_data = {
            'company_name': data.get('company_name', company.company_name).strip(),
            'website_url': data.get('website_url', company.website_url or '').strip(),
            'company_research': data.get('company_research', company.company_research or '').strip()
        }
 
        if Company.update(company_id, company_data):
            return jsonify({'success': True, 'message': f'Company {company_data["company_name"]} updated successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to update company'}), 500
    except Exception as e:
        current_app.logger.error(f"Error updating company: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@bp.route('/campaigns/<int:campaign_id>/execute-now', methods=['POST'])
def execute_campaign_now(campaign_id):
    """Execute a campaign immediately for testing - bypasses all time constraints."""
    try:
        from app.services.campaign_scheduler import execute_campaign_job_test_mode
        import threading
        
        # Get campaign to verify it exists
        from app.models.campaign import Campaign
        campaign = Campaign.get_by_id(campaign_id)
        
        if not campaign:
            return jsonify({
                'success': False,
                'message': f'Campaign {campaign_id} not found'
            }), 404
        
        # Update campaign status to active
        Campaign.update_status(campaign_id, 'active')
        current_app.logger.info(f"Starting immediate execution of campaign {campaign_id} for testing")
        
        # Execute campaign in background thread with test mode
        def execute_with_test_mode():
            try:
                from app import create_app
                app = create_app()
                with app.app_context():
                    # Call modified execution function that bypasses delays
                    execute_campaign_job_test_mode(campaign_id)
            except Exception as e:
                app.logger.error(f"Error in immediate campaign execution: {e}")
        
        thread = threading.Thread(target=execute_with_test_mode)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': f'Campaign {campaign_id} is now executing immediately (test mode)'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error executing campaign {campaign_id} immediately: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error executing campaign immediately: {str(e)}'
        }), 500

@bp.route('/campaigns/<int:campaign_id>/reset-for-testing', methods=['POST'])
def reset_campaign_for_testing(campaign_id):
    """Reset a campaign's contact statuses to 'active' for testing purposes."""
    try:
        from app.models.campaign import Campaign
        
        # Get campaign to verify it exists
        campaign = Campaign.get_by_id(campaign_id)
        if not campaign:
            return jsonify({
                'success': False,
                'message': f'Campaign {campaign_id} not found'
            }), 404
        
        current_app.logger.info(f"🔄 TEST MODE: Resetting campaign {campaign_id} for testing")
        
        # Get all contacts in the campaign
        contacts = Campaign.get_campaign_contacts(campaign_id)
        reset_count = 0
        
        # Reset all contacts to 'active' status
        for contact in contacts:
            if contact.get('campaign_status') != 'active':
                success = Campaign.update_contact_status_in_campaign(
                    campaign_id, contact['email'], 'active'
                )
                if success:
                    reset_count += 1
                    current_app.logger.info(f"  ✅ Reset {contact['email']} to active")
        
        # Reset campaign status to 'ready'
        Campaign.update_status(campaign_id, 'ready')
        
        return jsonify({
            'success': True,
            'message': f'Campaign "{campaign.name}" reset successfully! {reset_count} contacts reactivated.',
            'reset_count': reset_count,
            'total_contacts': len(contacts)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error resetting campaign {campaign_id} for testing: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error resetting campaign: {str(e)}'
        }), 500

@bp.route('/campaigns/<int:campaign_id>/activity', methods=['GET'])
def get_campaign_activity(campaign_id):
    """Get comprehensive campaign activity including emails, logs, and next actions."""
    try:
        from app.models.campaign import Campaign
        from app.models.email_history import EmailHistory
        from datetime import datetime, timedelta
        
        # Get campaign to verify it exists
        campaign = Campaign.get_by_id(campaign_id)
        if not campaign:
            return jsonify({
                'success': False,
                'message': f'Campaign {campaign_id} not found'
            }), 404
        
        # Get email history for this campaign
        email_history = EmailHistory.get_by_campaign(campaign_id)
        
        # Get campaign contacts and their status
        campaign_contacts = Campaign.get_campaign_contacts(campaign_id)
        
        # Get campaign settings for next actions prediction
        settings = Campaign.get_campaign_settings(campaign_id)
        
        # Format email history
        emails = []
        for email in email_history:
            emails.append({
                'id': email.id,
                'recipient_email': email.to,
                'subject': email.subject,
                'status': email.status,
                'sent_at': email.date.isoformat() if email.date else None,
                'error_message': None,  # Not stored in current model
                'contact_name': email.to  # Could enhance with contact name lookup
            })
        
        # Generate execution logs based on campaign status and contacts
        logs = []
        
        # Campaign creation log
        logs.append({
            'timestamp': campaign.created_at.isoformat(),
            'level': 'INFO',
            'message': f'Campaign "{campaign.name}" created with {len(campaign_contacts)} contacts',
            'details': f'Template: {settings.get("email_template", "deep_research")}, Status: {campaign.status}'
        })
        
        # Contact processing logs
        for contact in campaign_contacts:
            status = contact.get('status', 'active')
            if status == 'completed':
                logs.append({
                    'timestamp': datetime.now().isoformat(),  # This would be actual completion time in real system
                    'level': 'SUCCESS',
                    'message': f'Email sent successfully to {contact["email"]}',
                    'details': f'Contact: {contact.get("full_name", contact["email"])}'
                })
            elif status == 'failed':
                logs.append({
                    'timestamp': datetime.now().isoformat(),
                    'level': 'ERROR',
                    'message': f'Failed to send email to {contact["email"]}',
                    'details': 'Check email configuration and contact details'
                })
        
        # Business hours restriction log (if applicable)
        if campaign.status in ['ready', 'scheduled'] and settings.get('respect_business_hours', True):
            bh = settings.get('business_hours', {})
            start_time = bh.get('start_time', '09:00')
            end_time = bh.get('end_time', '17:00')
            logs.append({
                'timestamp': datetime.now().isoformat(),
                'level': 'WARNING',
                'message': 'Campaign execution paused - outside business hours',
                'details': f'Business hours: {start_time} - {end_time} in {settings.get("timezone", "America/Los_Angeles")}'
            })
        
        # Generate next actions
        next_actions = []
        
        if campaign.status == 'ready' or campaign.status == 'scheduled':
            # Calculate when next email would be sent
            email_frequency = settings.get('email_frequency', {'value': 30, 'unit': 'minutes'})
            business_hours = settings.get('business_hours', {'start': '9:00', 'end': '17:00'})
            timezone_str = settings.get('timezone', 'America/Los_Angeles')
            
            next_actions.append({
                'action': 'Resume Email Sending',
                'scheduled_time': 'Next business hours',
                'description': f'Campaign will resume sending emails during business hours ({business_hours.get("start_time", "9:00")} - {business_hours.get("end_time", "17:00")} {timezone_str})',
                'type': 'scheduled'
            })
            
            next_actions.append({
                'action': 'Process Next Contact',
                'scheduled_time': f'Every {email_frequency["value"]} {email_frequency["unit"]}',
                'description': f'Emails will be sent with {email_frequency["value"]} {email_frequency["unit"]} intervals between contacts',
                'type': 'recurring'
            })
        
        elif campaign.status == 'paused':
            next_actions.append({
                'action': 'Waiting for Resume',
                'scheduled_time': 'Manual action required',
                'description': 'Campaign is paused. Click "Resume Campaign" to continue email sending.',
                'type': 'manual'
            })
        
        elif campaign.status == 'completed':
            next_actions.append({
                'action': 'Campaign Completed',
                'scheduled_time': 'No further actions',
                'description': 'All emails have been sent. Consider creating follow-up campaigns for non-responders.',
                'type': 'completed'
            })
        
        # Count contacts by status
        contact_stats = {
            'total': len(campaign_contacts),
            'pending': len([c for c in campaign_contacts if c.get('status') == 'active']),
            'completed': len([c for c in campaign_contacts if c.get('status') == 'completed']),
            'failed': len([c for c in campaign_contacts if c.get('status') == 'failed'])
        }
        
        return jsonify({
            'success': True,
            'data': {
                'emails': sorted(emails, key=lambda x: x['sent_at'] or '', reverse=True),
                'logs': sorted(logs, key=lambda x: x['timestamp'], reverse=True),
                'next_actions': next_actions,
                'contact_stats': contact_stats,
                'last_updated': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting campaign activity for {campaign_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting campaign activity: {str(e)}'
        }), 500

@bp.route('/campaigns/<int:campaign_id>/update-template', methods=['POST'])
def update_campaign_template(campaign_id):
    """Update a campaign's email template in the JSON file."""
    try:
        from app.models.campaign import Campaign
        import json
        import os
        
        # Get campaign to verify it exists in database
        campaign = Campaign.get_by_id(campaign_id)
        if not campaign:
            return jsonify({
                'success': False,
                'message': f'Campaign {campaign_id} not found'
            }), 404
        
        # Get new template from request
        data = request.get_json() or {}
        new_template = data.get('email_template', 'deep_research')
        
        if new_template not in ['deep_research', 'warm', 'alt_subject']:
            return jsonify({
                'success': False,
                'message': 'Invalid email template. Must be one of: deep_research, warm, alt_subject'
            }), 400
        
        current_app.logger.info(f"Updating campaign {campaign_id} template to: {new_template}")
        
        # Load campaigns.json file
        campaigns_file = 'campaigns.json'
        campaigns_data = []
        old_template = 'not set'
        campaign_updated = False
        
        if os.path.exists(campaigns_file):
            try:
                with open(campaigns_file, 'r') as f:
                    campaigns_data = json.load(f)
            except json.JSONDecodeError:
                current_app.logger.warning("campaigns.json file is corrupted, creating new one")
                campaigns_data = []
        
        # Find and update the campaign
        for camp in campaigns_data:
            if str(camp.get('id', '')).endswith(str(campaign_id)) or str(camp.get('id', '')) == str(campaign_id):
                old_template = camp.get('email_template', 'not set')
                camp['email_template'] = new_template
                campaign_updated = True
                current_app.logger.info(f"Updated campaign {camp.get('id')} template from {old_template} to {new_template}")
                break
        
        # If campaign not found in JSON, create a new entry
        if not campaign_updated:
            new_campaign_entry = {
                'id': f"camp_{campaign_id}",
                'name': campaign.name,
                'type': 'cold_outreach',
                'description': campaign.description or '',
                'email_template': new_template,
                'priority': 'medium',
                'status': campaign.status,
                'created_at': campaign.created_at.isoformat() if hasattr(campaign.created_at, 'isoformat') else str(campaign.created_at),
                'emails_sent': 0,
                'emails_opened': 0,
                'emails_clicked': 0,
                'responses_received': 0
            }
            campaigns_data.append(new_campaign_entry)
            current_app.logger.info(f"Created new JSON entry for campaign {campaign_id}")
            campaign_updated = True
        
        # Save back to file
        if campaign_updated:
            try:
                with open(campaigns_file, 'w') as f:
                    json.dump(campaigns_data, f, indent=2)
                current_app.logger.info(f"Successfully saved campaigns.json with updated template")
            except Exception as file_error:
                current_app.logger.error(f"Error saving campaigns.json: {file_error}")
                return jsonify({
                    'success': False,
                    'message': f'Failed to save campaign settings: {str(file_error)}'
                }), 500
        
        return jsonify({
            'success': True,
            'message': f'Campaign "{campaign.name}" template updated from "{old_template}" to "{new_template}"',
            'old_template': old_template,
            'new_template': new_template
        })
        
    except Exception as e:
        current_app.logger.error(f"Error updating campaign {campaign_id} template: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error updating campaign template: {str(e)}'
        }), 500

@bp.route('/campaigns/delete-all', methods=['DELETE'])
def delete_all_campaigns():
    """Delete all campaigns and their associated data (campaign_contacts and email_history)."""
    try:
        from app.models.campaign import Campaign
        import os
        
        current_app.logger.info("🗑️  Starting deletion of all campaigns and associated data")
        
        # Delete all campaigns and associated data from database
        delete_counts = Campaign.delete_all_campaigns()
        
        if delete_counts['campaigns'] == 0 and delete_counts['campaign_contacts'] == 0 and delete_counts['email_history'] == 0:
            return jsonify({
                'success': False,
                'message': 'No campaigns found to delete'
            }), 404
        
        # Also clear the campaigns.json file if it exists
        campaigns_file = 'campaigns.json'
        json_cleared = False
        if os.path.exists(campaigns_file):
            try:
                with open(campaigns_file, 'w') as f:
                    f.write('[]')
                json_cleared = True
                current_app.logger.info("Cleared campaigns.json file")
            except Exception as json_error:
                current_app.logger.warning(f"Could not clear campaigns.json: {json_error}")
        
        message = (
            f"Successfully deleted all campaigns and associated data! "
            f"Deleted: {delete_counts['campaigns']} campaigns, "
            f"{delete_counts['campaign_contacts']} campaign-contact links, "
            f"{delete_counts['email_history']} email history records"
        )
        
        if json_cleared:
            message += ", and cleared campaigns.json file"
        
        return jsonify({
            'success': True,
            'message': message,
            'deleted_counts': delete_counts
        })
        
    except Exception as e:
        current_app.logger.error(f"Error deleting all campaigns: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error deleting campaigns: {str(e)}'
        }), 500

@bp.route('/companies/list', methods=['GET'])
def get_companies_list():
    """Get a simple list of all companies for dropdown selection."""
    try:
        companies = Company.load_all()
        companies_data = []
        for company in companies:
            companies_data.append({
                'id': company.id,
                'company_name': company.company_name,
                'website_url': company.website_url or ''
            })
        
        return jsonify({
            'success': True,
            'companies': companies_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting companies list: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to load companies'
        }), 500