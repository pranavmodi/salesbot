from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import os
import smtplib
import ssl
import json

from app.services.email_service import EmailService
from app.services.email_reader_service import email_reader, configure_email_reader, EmailReaderService
from app.utils.email_config import email_config, EmailAccount
from email_composers.email_composer_alt_subject import AltSubjectEmailComposer
from email_composers.email_composer_warm import WarmEmailComposer

email_bp = Blueprint('email_api', __name__, url_prefix='/api')

# Define EMAIL_READING_ENABLED (assuming it's a global constant or loaded from config)
# For now, let's define it here. In a real app, it might come from app.config
EMAIL_READING_ENABLED = os.getenv('EMAIL_READING_ENABLED', 'false').lower() == 'true'

@email_bp.route('/preview_email', methods=['POST'])
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
                composer = AltSubjectEmailComposer()
            else:
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

@email_bp.route('/send_email', methods=['POST'])
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

@email_bp.route('/email/accounts', methods=['GET'])
def get_email_accounts():
    """Get all configured email accounts."""
    try:
        # Force reload of email configuration
        email_config.load_accounts()
        
        # Get full account details for config page
        all_accounts = email_config.get_all_accounts()
        accounts = [account.to_dict() for account in all_accounts]
        
        # Debug logging
        current_app.logger.info(f"Retrieved {len(accounts)} accounts from configuration")
        for account in accounts:
            current_app.logger.info(f"Account: {account['name']}, IMAP: {account['imap_host']}")
        
        # Check which config storage is being used
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

@email_bp.route('/email/accounts/<account_name>/test', methods=['POST'])
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

@email_bp.route('/email/config/save', methods=['POST'])
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

@email_bp.route('/send_bulk_emails', methods=['POST'])
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

@email_bp.route('/email/configure', methods=['POST'])
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

@email_bp.route('/email/accounts/<account_name>/emails', methods=['GET'])
def get_account_emails(account_name):
    """Get emails for a specific account."""
    try:
        account = email_config.get_account_by_name(account_name)
        if not account:
            return jsonify({
                'success': False,
                'message': f'Account "{account_name}" not found'
            }), 404
        
        # Configure email reader for this specific account
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

@email_bp.route('/email/conversations/<contact_email>', methods=['GET'])
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

@email_bp.route('/email/conversations/<contact_email>/detailed', methods=['GET'])
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

@email_bp.route('/email/test-connection', methods=['POST'])
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

@email_bp.route('/send_test_email', methods=['POST'])
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

@email_bp.route('/email/all', methods=['GET'])
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

@email_bp.route('/email/config/debug', methods=['GET'])
def debug_email_configuration():
    """Debug endpoint to show current email configuration state."""
    try:
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
