from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import os
import smtplib
import ssl
import json

from app.services.email_service import EmailService
from app.services.email_reader_service import email_reader, configure_email_reader, EmailReaderService
from app.utils.tenant_email_config import TenantEmailConfigManager, EmailAccount
# Import available composers
from email_composers.email_composer_deep_research import DeepResearchEmailComposer
from email_composers.email_composer_content_based import ContentBasedEmailComposer

email_bp = Blueprint('email_api', __name__, url_prefix='/api')

# Define EMAIL_READING_ENABLED (assuming it's a global constant or loaded from config)
# For now, let's define it here. In a real app, it might come from app.config
EMAIL_READING_ENABLED = os.getenv('EMAIL_READING_ENABLED', 'false').lower() == 'true'

@email_bp.route('/preview_email', methods=['POST'])
def preview_email():
    """Generate email preview for a contact."""
    try:
        data = request.get_json()
        composer_type = data.get('composer_type', 'deep_research')
        
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
            # Initialize the appropriate composer based on type
            if composer_type == "content_based":
                composer = ContentBasedEmailComposer()
            else:
                composer = DeepResearchEmailComposer()
            
            # Use the composer directly with the contact data
            lead_data = {
                "name": contact_data.get('name', ''),
                "email": contact_data.get('email', ''),
                "company_name": contact_data.get('company', ''),
                "position": contact_data.get('position', ''),
                "website": contact_data.get('website', ''),
                "notes": contact_data.get('notes', ''),
            }
            
            # For content-based composer, try to fetch company research data
            if composer_type == "content_based":
                try:
                    from app.models.company import Company
                    company_name = contact_data.get('company', '')
                    if company_name:
                        companies = Company.get_companies_by_name(company_name)
                        if companies:
                            company = companies[0]
                            # Add research fields to lead_data
                            lead_data.update({
                                'company_research': getattr(company, 'company_research', ''),
                                'llm_research_step_1_basic': getattr(company, 'llm_research_step_1_basic', ''),
                                'llm_research_step_2_strategic': getattr(company, 'llm_research_step_2_strategic', ''),
                                'llm_research_step_3_report': getattr(company, 'llm_research_step_3_report', ''),
                                'llm_research_step_status': getattr(company, 'llm_research_step_status', 'not_started')
                            })
                except Exception as e:
                    current_app.logger.warning(f"Could not fetch company research for {company_name}: {e}")
            
            calendar_url = data.get('calendar_url') or os.getenv("CALENDAR_URL", "https://calendly.com/pranav-modi/15-minute-meeting")
            include_tracking = data.get('include_tracking', True)  # Default to True
            
            # Handle different composer types
            if composer_type == "content_based":
                # Content-based composer requires additional parameters
                content_url = data.get('content_url', '')
                content_description = data.get('content_description', '')
                content_type = data.get('content_type', 'blog_post')
                call_to_action = data.get('call_to_action', 'learn_more')
                
                if not content_url or not content_description:
                    return jsonify({"error": "Content URL and description are required for content-based emails"}), 400
                
                email_content = composer.compose_email(
                    lead=lead_data,
                    content_url=content_url,
                    content_description=content_description,
                    content_type=content_type,
                    call_to_action=call_to_action,
                    calendar_url=calendar_url,
                    extra_context=data.get('extra_context'),
                    include_tracking=include_tracking,
                    campaign_id=data.get('campaign_id')
                )
            else:
                # Deep research composer
                email_content = composer.compose_email(
                    lead=lead_data, 
                    calendar_url=calendar_url, 
                    extra_context=data.get('extra_context'),
                    include_tracking=include_tracking,
                    campaign_id=data.get('campaign_id')
                )
            
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
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
            recipient_email = data.get('recipient_email')
            recipient_name = data.get('recipient_name', '')
            subject = data.get('subject')
            body = data.get('body')
            account_name = data.get('sender_email')  # Use sender_email as account_name
            include_tracking = data.get('include_tracking', True)
            campaign_id = data.get('campaign_id')
        else:
            recipient_email = request.form.get('recipient_email')
            recipient_name = request.form.get('recipient_name', '')
            subject = request.form.get('preview_subject')
            body = request.form.get('preview_body')
            account_name = request.form.get('account_name')
            include_tracking = request.form.get('include_tracking', 'true').lower() == 'true'
            campaign_id = request.form.get('campaign_id')
        
        if not all([recipient_email, subject, body]):
            return jsonify({
                'success': False,
                'message': 'Missing required email information'
            }), 400
        
        # Validate campaign_id if provided
        if campaign_id:
            try:
                from app.models.campaign import Campaign
                campaign = Campaign.get_by_id(int(campaign_id))
                if not campaign:
                    return jsonify({
                        'success': False,
                        'message': 'Invalid campaign ID'
                    }), 400
            except (ValueError, Exception) as e:
                current_app.logger.error(f"Campaign validation error: {e}")
                return jsonify({
                    'success': False,
                    'message': 'Invalid campaign ID format'
                }), 400
        
        # If tracking is disabled, remove any existing tracking pixels from body
        if not include_tracking and 'track/open/' in body:
            import re
            body = re.sub(r'<img[^>]*track/open/[^>]*>', '', body)
            current_app.logger.info(f"📧 Tracking pixel removed from email to {recipient_email}")
        else:
            current_app.logger.info(f"📧 Sending email to {recipient_email} with tracking={'enabled' if include_tracking else 'disabled'}")
        
        # Use the new multi-account send method
        success = EmailService.send_email_with_account(
            recipient_email, recipient_name, subject, body, account_name
        )
        
        # If email sent successfully and campaign_id provided, associate contact with campaign
        if success and campaign_id:
            try:
                from app.models.campaign import Campaign
                
                # Add contact to campaign (this will handle duplicates automatically)
                campaign_association_success = Campaign.add_contact_to_campaign(
                    int(campaign_id), recipient_email, status='active'
                )
                
                if campaign_association_success:
                    current_app.logger.info(f"Contact {recipient_email} successfully added to campaign {campaign_id}")
                else:
                    current_app.logger.warning(f"Failed to add contact {recipient_email} to campaign {campaign_id}")
                    
            except Exception as e:
                current_app.logger.error(f"Error associating contact with campaign: {e}")
                # Don't fail the email send if campaign association fails
        
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
        # Get tenant-specific email configuration
        email_manager = TenantEmailConfigManager()
        
        # Get full account details for config page
        all_accounts = email_manager.get_accounts()
        accounts = [account.to_dict() for account in all_accounts]
        
        # Debug logging
        current_app.logger.info(f"Retrieved {len(accounts)} accounts from configuration")
        for account in accounts:
            current_app.logger.info(f"Account: {account['name']}, IMAP: {account['imap_host']}")
        
        # For tenant-based config, show tenant-specific info
        config_file_path = "tenant_settings (database)"
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


@email_bp.route('/send_bulk_emails', methods=['POST'])
def send_bulk_emails():
    """Send emails to multiple recipients."""
    try:
        data = request.get_json()
        recipients_data = data.get('recipients_data')
        composer_type = data.get('composer_type', 'deep_research')
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


@email_bp.route('/contacts-with-research-status', methods=['GET'])
def get_contacts_with_research_status():
    """Get all contacts with their company's deep research completion status."""
    try:
        from app.models.contact import Contact
        from app.models.company import Company
        
        # Get contacts using pagination (get all by using a large per_page value)
        paginated_result = Contact.get_paginated(page=1, per_page=1000)
        contacts = paginated_result.get('contacts', [])  # These are already Contact objects
        contacts_with_status = []
        
        for contact in contacts:
            company_name = contact.company  # Use company property, not company_name
            research_status = {
                'has_completed_research': False,
                'research_status': 'not_started',
                'company_id': None
            }
            
            if company_name:
                # Find company by name
                companies = Company.get_companies_by_name(company_name)
                if companies:
                    company = companies[0]
                    research_status['company_id'] = company.id
                    
                    # Check if deep research is completed
                    has_html_report = (hasattr(company, 'html_report') and company.html_report) or (hasattr(company, 'llm_html_report') and company.llm_html_report)
                    current_status = getattr(company, 'llm_research_step_status', 'not_started')
                    
                    # Accept multiple completion status values
                    is_completed = current_status in ['step_3_completed', 'completed'] and has_html_report
                    research_status['has_completed_research'] = is_completed
                    research_status['research_status'] = current_status
            
            # Only include contacts with completed research
            if research_status['has_completed_research']:
                contacts_with_status.append({
                    'id': contact.email,  # Use email as ID
                    'name': contact.display_name,  # Use display_name property
                    'email': contact.email,
                    'company_name': company_name,
                    'position': contact.job_title,  # Use job_title property
                    'research_status': research_status
                })
        
        return jsonify({
            'success': True,
            'contacts': contacts_with_status
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting contacts with research status: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to get contacts: {str(e)}'
        }), 500

@email_bp.route('/validate-deep-research/<company_name>', methods=['GET'])
def validate_company_deep_research(company_name):
    """Validate if a company has completed deep research."""
    try:
        from app.models.company import Company
        
        companies = Company.get_companies_by_name(company_name)
        if not companies:
            return jsonify({
                'success': False,
                'has_completed_research': False,
                'message': f'Company "{company_name}" not found'
            })
        
        company = companies[0]
        
        # Check if deep research is completed
        has_html_report = (hasattr(company, 'html_report') and company.html_report) or (hasattr(company, 'llm_html_report') and company.llm_html_report)
        current_status = getattr(company, 'llm_research_step_status', 'not_started')
        has_completed_research = has_html_report and current_status == 'step_3_completed'
        
        return jsonify({
            'success': True,
            'has_completed_research': has_completed_research,
            'research_status': current_status,
            'company_id': company.id,
            'company_name': company.company_name,
            'html_report_length': len(company.html_report) if company.html_report else 0
        })
        
    except Exception as e:
        current_app.logger.error(f"Error validating deep research for {company_name}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Validation failed: {str(e)}'
        }), 500
